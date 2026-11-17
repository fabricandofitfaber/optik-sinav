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


def sistem_dosyasini_yaz(girdi: str | Path, sonuc: SinavSonucu, cikti: str | Path) -> SistemDosyasiRaporu:
    bayt, rapor = sistem_dosyasini_doldur(Path(girdi).read_bytes(), sonuc)
    cikti = Path(cikti)
    cikti.write_bytes(bayt)
    rapor.cikti = cikti
    return rapor


__all__ = ["sistem_dosyasini_coz", "sistem_dosyasini_doldur", "sistem_dosyasini_yaz", "SistemDosyasiRaporu", "GIRDI", "GIRMEDI"]
