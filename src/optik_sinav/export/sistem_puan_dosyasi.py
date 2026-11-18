"""Akademik Bilgi Sistemi'nin soru bazlı puan dosyası (sorular tanımlandıktan sonra sistemden indirilen CSV).

Biçim (17 Kasım 2026, gerçek dosyadan): Windows-1254, noktalı virgül, CRLF; başlık
`Öğrenci No;Adı;Soyadı;Snf;Girme Durum;Soru1(%6,67);…;Soru15(%6,66);Sınav Notu`; numaraların sonunda
bölünmez boşluk (U+00A0) var; bütün öğrenciler "Girdi", puan hücreleri boş.

Dosya bayt düzeyinde korunur: yalnızca soru, sınav notu ve girme durumu hücreleri değişir; kodlama, ayırıcı,
satır sonu, satır sırası ve öteki hücreler (numaradaki bölünmez boşluk dahil) aynı kalır.
Soru hücresi = öğrencinin o sorudan aldığı pay × başlıktaki ağırlık (sistemin soru puanı), iki ondalık;
sınav notu = yazılan soru puanlarının toplamı.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from ..core.modeller import SinavSonucu
from ..core.puanlama import yuvarla
from ..io.kodlama import baytlari_coz
from ..io.liste_okuyucu import _sade

_SORU = re.compile(r"^\s*soru\s*(\d+)\s*\(\s*%?\s*([0-9]+(?:[.,][0-9]+)?)\s*\)\s*$", re.IGNORECASE)
GIRDI, GIRMEDI = "Girdi", "Girmedi"
GIRME_BASLIK = "Girme Durum"


@dataclass
class SistemDosyasi:
    basliklar: list[str]
    no_sutun: int
    durum_sutun: int | None
    not_sutun: int | None
    soru_sutunlari: list[int]  # dosyadaki soru sırasıyla (Soru1, Soru2 …)
    agirliklar: list[Fraction]
    ayirici: str


@dataclass
class SistemDosyasiRaporu:
    yazilan: int = 0
    girmedi: list[str] = field(default_factory=list)  # dosyada var, sınava girmemiş (ya da puanı yok)
    dosyada_olmayan: list[str] = field(default_factory=list)  # sınava girmiş, dosyada yok
    notlar: list[str] = field(default_factory=list)
    cikti: Path | None = None


def _sayi_metni(d: Decimal) -> str:
    s = f"{d:.2f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s.replace(".", ",")


def _numara(hucre: str) -> str:
    return "".join(c for c in hucre if not c.isspace()).strip('"')


def sistem_dosyasini_coz(metin: str) -> SistemDosyasi:
    """Başlık satırından sütunları bulur. Soru sütunu yoksa ya da numara sütunu yoksa ValueError."""
    ilk = metin.replace("\r\n", "\n").replace("\r", "\n").split("\n", 1)[0]
    ayirici = max((";", "\t", ","), key=ilk.count)
    basliklar = ilk.split(ayirici)
    no = durum = not_ = None
    sorular: list[tuple[int, int, Fraction]] = []
    for j, b in enumerate(basliklar):
        m = _SORU.match(b.strip().strip('"'))
        if m:
            sorular.append((int(m.group(1)), j, Fraction(m.group(2).replace(",", "."))))
            continue
        s = _sade(b)
        if no is None and s in ("ogrencino", "ogrencinumarasi", "numara", "ogrno", "no"):
            no = j
        elif durum is None and s.startswith("girme"):
            durum = j
        elif not_ is None and s in ("sinavnotu", "not", "notu", "puan", "sinavpuani"):
            not_ = j
    if no is None:
        raise ValueError("Dosyada \"Öğrenci No\" sütunu bulunamadı. Sistemden indirilen soru bazlı puan dosyasını seçin.")
    if not sorular:
        raise ValueError("Dosyada \"Soru1(%…)\" biçiminde soru sütunu bulunamadı. Önce soruları sisteme tanımlayın, "
                         "sonra sistemden puan dosyasını indirin.")
    sorular.sort()
    return SistemDosyasi(basliklar, no, durum, not_, [j for _, j, _ in sorular], [w for _, _, w in sorular], ayirici)


def sistem_dosyasini_doldur(veri: bytes, sonuc: SinavSonucu) -> tuple[bytes, SistemDosyasiRaporu]:
    """Sistemden indirilen dosyanın baytlarını alır, puanları yazılmış baytları ve raporu döndürür."""
    metin, kodlama = baytlari_coz(veri)
    d = sistem_dosyasini_coz(metin)
    sira = sonuc.anahtar.aktarim_sorulari()  # bonus soru sisteme gitmez
    if len(sira) != len(d.soru_sutunlari):
        raise ValueError(f"Dosyada {len(d.soru_sutunlari)} soru var, programda sisteme giden {len(sira)} soru var. "
                         "Sistemde tanımlanan sorular bu sınavla aynı olmalı (önce soruları yeniden tanımlayın).")
    rapor = SistemDosyasiRaporu()
    toplam_w = sum(d.agirliklar)
    if toplam_w != 100:
        rapor.notlar.append(f"Dosyadaki soru ağırlıklarının toplamı {_sayi_metni(Decimal(float(toplam_w)).quantize(Decimal('0.01')))} (100 değil).")
    if not sonuc.klasik and sonuc.ayarlar.yanlis_cezasi:
        rapor.notlar.append("Yanlış cezası soru puanlarına dağıtılamaz: dosyadaki soru puanları ve sınav notu cezasızdır.")
    okunan = sonuc.no_ile()
    satir_sonu = "\r\n" if "\r\n" in metin else ("\r" if "\r" in metin and "\n" not in metin else "\n")
    satirlar = metin.split(satir_sonu)
    dosyadaki = set()
    for r in range(1, len(satirlar)):
        if not satirlar[r].strip():
            continue
        h = satirlar[r].split(d.ayirici)
        en = max([d.no_sutun] + d.soru_sutunlari + [x for x in (d.durum_sutun, d.not_sutun) if x is not None])
        h += [""] * (en + 1 - len(h))
        no = _numara(h[d.no_sutun])
        if not no.isdigit():
            continue
        dosyadaki.add(no)
        o = okunan.get(no)
        if o is None:
            rapor.girmedi.append(no)
            for j in d.soru_sutunlari:
                h[j] = ""
            if d.not_sutun is not None:
                h[d.not_sutun] = ""
            if d.durum_sutun is not None:
                h[d.durum_sutun] = GIRMEDI
        else:
            toplam = Decimal(0)
            for k, j in enumerate(d.soru_sutunlari):
                i = sira[k]
                tam = sonuc.soru_puanlari[i]
                pay = (o.sorular[i].puan / tam) if tam else Fraction(0)
                deger = yuvarla(pay * d.agirliklar[k], 2)
                toplam += deger
                h[j] = _sayi_metni(deger)
            if d.not_sutun is not None:
                h[d.not_sutun] = _sayi_metni(toplam)
            if d.durum_sutun is not None:
                h[d.durum_sutun] = GIRDI
            rapor.yazilan += 1
        satirlar[r] = d.ayirici.join(h)
    rapor.dosyada_olmayan = [o.no for o in sonuc.ogrenciler if o.no not in dosyadaki]
    if dosyadaki and rapor.yazilan == 0:
        raise ValueError(f"Dosyadaki {len(dosyadaki)} öğrencinin hiçbiri bu sınavda yok. Sistemde başka bir dersin ya da "
                         "sınavın puan dosyası indirilmiş olabilir: dersi ve sınavı kontrol edip dosyayı yeniden indirin.")
    yeni = satir_sonu.join(satirlar)
    kod = {"utf-8-sig": "utf-8-sig", "utf-8": "utf-8"}.get(kodlama, "cp1254" if kodlama == "windows-1254" else "latin-1")
    return yeni.encode(kod, errors="replace"), rapor


def _ad_soyad(ad: str) -> tuple[str, str]:
    p = (ad or "").split()
    return (" ".join(p[:-1]), p[-1]) if len(p) > 1 else ((p[0] if p else ""), "")


def sistem_dosyasi_uret(sonuc: SinavSonucu) -> tuple[bytes, SistemDosyasiRaporu]:
    """Sistemden dosya indirilmeden, aynı biçimde (Windows-1254, noktalı virgül, CRLF) dolu puan dosyası üretir.
    Soru ağırlıkları soru tanımındaki puanlardır; öğrenciler liste sırasıyla (girmeyenler "Girmedi"), liste yoksa
    okuma sırasıyla. Sınıf (Snf) bilinmediği için boş kalır. Sistem bu dosyayı kabul etmezse sistemin kendi dosyası
    indirilip `sistem_dosyasini_doldur` ile doldurulur."""
    from .soru_tanimi import soru_tanimi_satirlari

    agirliklar = [s[1] for s in soru_tanimi_satirlari(sonuc.anahtar, sonuc.ayarlar)]
    bas = ["Öğrenci No", "Adı", "Soyadı", "Snf", GIRME_BASLIK] + [f"Soru{i}(%{w})" for i, w in enumerate(agirliklar, 1)] + ["Sınav Notu"]
    if sonuc.liste_var and sonuc.liste:
        kisiler = [(o.no, o.ad) for o in sonuc.liste.ogrenciler]
    else:
        kisiler = [(o.no, o.ad) for o in sonuc.ogrenciler]
    satirlar = [";".join(bas)]
    goruldu = set()
    for no, ad in kisiler:
        if no in goruldu:
            continue
        goruldu.add(no)
        a, s = _ad_soyad(ad)
        satirlar.append(";".join([no, a.replace(";", " "), s.replace(";", " "), "", GIRDI] + [""] * (len(agirliklar) + 1)))
    metin = "\r\n".join(satirlar) + "\r\n"
    return sistem_dosyasini_doldur(metin.encode("cp1254", errors="replace"), sonuc)


def sistem_satirlari(bayt: bytes) -> list[list[str]]:
    """Doldurulmuş dosyanın hücreleri (Excel'e yazmak için)."""
    metin, _ = baytlari_coz(bayt)
    d = sistem_dosyasini_coz(metin)
    return [s.split(d.ayirici) for s in metin.replace("\r\n", "\n").replace("\r", "\n").split("\n") if s.strip()]


AKREDITASYON_ADIMLARI = [
    "Önce soruları tanımlayın (soru tanımı dosyası ya da \"Soruları kopyala\").",
    "Akademik Bilgi Sistemi'nde aynı dersin ve sınavın öğrenci puanı toplu aktarım ekranını açın.",
    "\"Kolon Ayracı\" \"Excel'den Kopyalandı\" olsun.",
    "Bu dosyanın ilk sayfasında (Aktarım) bütün hücreleri seçip kopyalayın (Cmd+A, Cmd+C ya da Ctrl+A, Ctrl+C).",
    "Sistemdeki Aktarım Kutusu'na yapıştırıp \"Aktar\" düğmesine basın.",
]


def akreditasyon_satirlari(sonuc: SinavSonucu) -> list[list[str]]:
    """Sistemin öğrenci puanı aktarım kutusu biçimi: her satırda öğrenci numarası ve soru puanları, başlıksız
    (sistemin örneği: 2023050601;7;10;8;10;0;0;5;5;10;10). Soru puanı = alınan pay × soru tanımındaki puan (iki ondalık,
    virgül). Liste sırasıyla; sınava girmeyenlerde puanlar yerine yalnızca "G" (sistemin örneği: G Girmedi,
    D Devamsız, U Uygulamadan Kaldı); bonus soru yok."""
    bayt, _ = sistem_dosyasi_uret(sonuc)
    metin = bayt.decode("cp1254")
    d = sistem_dosyasini_coz(metin)
    cikti = []
    for satir in sistem_satirlari(bayt)[1:]:
        no = _numara(satir[d.no_sutun])
        if d.durum_sutun is not None and satir[d.durum_sutun] != GIRDI:
            cikti.append([no, "G"] + [""] * (len(d.soru_sutunlari) - 1))  # sistem satırı Excel aralığı gibi tam sütunla bekliyor
            continue
        cikti.append([no] + [satir[j] for j in d.soru_sutunlari])
    return cikti


def akreditasyon_metni(sonuc: SinavSonucu, ondalik: str = ",") -> str:
    """Aktarım kutusuna yapıştırılacak metin (Excel'den kopyalanmış gibi sekmeyle ayrılmış). `ondalik`: puanlardaki
    ondalık ayırıcı (sistem virgülü kabul etmezse nokta denenir)."""
    return "\n".join("\t".join([s[0]] + [x.replace(",", ondalik) for x in s[1:]]) for s in akreditasyon_satirlari(sonuc))


def akreditasyon_excel_yaz(sonuc: SinavSonucu, yol) -> Path:
    """İlk sayfa "Aktarım": başlıksız, metin hücreler (panodaki akreditasyon_metni ile birebir); ikinci sayfa açıklama."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Aktarım"
    for r, satir in enumerate(akreditasyon_satirlari(sonuc), start=1):
        for c, v in enumerate(satir, start=1):
            h = ws.cell(row=r, column=c, value=v)
            h.number_format = "@"
    ws.column_dimensions["A"].width = 14
    a = wb.create_sheet("Açıklama")
    a.cell(row=1, column=1, value="Öğrenci soru puanları: Akademik Bilgi Sistemi'ne nasıl aktarılır?").font = Font(bold=True, size=13)
    for i, adim in enumerate(AKREDITASYON_ADIMLARI, start=1):
        a.cell(row=2 + i, column=1, value=f"{i}. {adim}")
    a.cell(row=9, column=1, value="Aktarım sayfası").font = Font(bold=True)
    for i, (b, m) in enumerate((("1. sütun", "Öğrenci numarası."),
                                ("Sonraki sütunlar", "Soru 1, Soru 2 … puanları: öğrencinin sorudan aldığı pay × sorunun sistemdeki puanı. "
                                                     "Bonus soru yok. Sınava girmeyenlerde B sütununda yalnızca G (Girmedi).")), start=10):
        a.cell(row=i, column=1, value=b).font = Font(bold=True)
        a.cell(row=i, column=2, value=m)
    a.column_dimensions["A"].width = 20
    a.column_dimensions["B"].width = 90
    Path(yol).parent.mkdir(parents=True, exist_ok=True)
    wb.save(yol)
    return Path(yol)


def sistem_dosyasini_yaz(girdi: str | Path, sonuc: SinavSonucu, cikti: str | Path) -> SistemDosyasiRaporu:
    bayt, rapor = sistem_dosyasini_doldur(Path(girdi).read_bytes(), sonuc)
    cikti = Path(cikti)
    cikti.write_bytes(bayt)
    rapor.cikti = cikti
    return rapor


__all__ = ["akreditasyon_satirlari", "akreditasyon_metni", "akreditasyon_excel_yaz", "sistem_satirlari", "sistem_dosyasi_uret", "sistem_dosyasini_coz", "sistem_dosyasini_doldur", "sistem_dosyasini_yaz", "SistemDosyasiRaporu", "GIRDI", "GIRMEDI"]
