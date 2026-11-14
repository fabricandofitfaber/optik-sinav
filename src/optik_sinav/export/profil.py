"""Dışa aktarma profilleri (`profiles/*.json`).

Bir profil, Akademik Bilgi Sistemi'nin bir ekranına aktarılacak dosyanın biçimini tanımlar:
dosya türü, sayfa adı, üst satırlar, sütunlar, numara biçimi, ondalık ayırıcı, "girmedi" gösterimi,
kodlama, ayraç ve satır sonu. Sistemdeki gerçek biçim henüz görülmediği için varsayılan profiller
geçicidir (PROJE_TANIMI.md bölüm 4.4).

Sütun alanları:
  ogrenci_no, ad_soyad, ad, soyad, puan, ham_puan, ceza, dogru, yanlis, bos, net,
  soru:<k> (k. sorunun puanı), soru_puanlari (her soru için bir sütun; başlıkta {n} soru no),
  cevap:<k> (işaretlenen şık), sabit (deger alanındaki metin).
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path

from ..core.modeller import Ogrenci, OgrenciSonucu, SinavBilgisi, SinavSonucu, Yuvarlama
from ..core.puanlama import net, yuvarla
from ..kaynaklar import profil_klasorleri

SAYISAL_ALANLAR = {"puan", "ham_puan", "ceza", "dogru", "yanlis", "bos", "net", "soru"}


@dataclass
class Sutun:
    alan: str
    baslik: str = ""
    deger: str = ""  # alan "sabit" ise


@dataclass
class SablonBilgisi:
    """Sistemden indirilen şablonun içine yazmak için konumlar (1'den sayılır)."""

    sayfa: str | None = None
    baslik_satiri: int = 1
    no_sutun: int = 1
    ad_sutun: int | None = None
    soru_sutunlari: dict[int, int] = field(default_factory=dict)  # soru no -> sütun
    puan_sutunu: int | None = None


@dataclass
class Profil:
    ad: str
    baslik: str = ""
    aciklama: str = ""
    dosya_turu: str = "xlsx"  # xlsx, csv, txt, sablon
    sayfa_adi: str = "Sayfa1"
    ust_satirlar: list[list[str]] = field(default_factory=list)  # başlık satırından önce gelen satırlar
    baslik_satiri_yaz: bool = True
    sutunlar: list[Sutun] = field(default_factory=list)
    ogrenci_no_bicimi: str = "metin"  # metin ya da sayi
    ondalik_ayirici: str = ","
    ondalik_basamak: int = 2
    yuvarlama: Yuvarlama = Yuvarlama.YARIM_YUKARI
    girmedi_gosterimi: str = ""
    girmeyenleri_dahil_et: bool = True
    listede_olmayanlari_dahil_et: bool = False
    sira: str = "liste"  # liste (öğrenci listesi sırası), dosya (optik dosya sırası), numara
    kodlama: str = "utf-8"
    ayrac: str = ";"
    satir_sonu: str = "CRLF"
    sablon: SablonBilgisi | None = None
    taslak: bool = True  # sistemdeki gerçek biçimle doğrulanmadı

    # ---------------------------------------------------------- JSON
    def to_dict(self) -> dict:
        d = asdict(self)
        d["yuvarlama"] = self.yuvarlama.value
        if self.sablon is not None:
            d["sablon"]["soru_sutunlari"] = {str(k): v for k, v in self.sablon.soru_sutunlari.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Profil":
        d = dict(d)
        d["sutunlar"] = [Sutun(**s) for s in d.get("sutunlar", [])]
        d["yuvarlama"] = Yuvarlama(d.get("yuvarlama", "yarim_yukari"))
        if d.get("sablon"):
            s = dict(d["sablon"])
            s["soru_sutunlari"] = {int(k): int(v) for k, v in s.get("soru_sutunlari", {}).items()}
            d["sablon"] = SablonBilgisi(**s)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def yukle(cls, yol: str | Path) -> "Profil":
        return cls.from_dict(json.loads(Path(yol).read_text(encoding="utf-8")))

    def kaydet(self, yol: str | Path) -> None:
        Path(yol).parent.mkdir(parents=True, exist_ok=True)
        Path(yol).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @property
    def satir_sonu_karakteri(self) -> str:
        return {"CRLF": "\r\n", "LF": "\n", "CR": "\r"}.get(self.satir_sonu.upper(), "\r\n")


def profilleri_listele() -> dict[str, Path]:
    """{profil adı: yol}. Kullanıcı klasöründeki profil aynı adlı paket profilinin önüne geçer."""
    bulunan: dict[str, Path] = {}
    for klasor in profil_klasorleri():
        if klasor.is_dir():
            for p in sorted(klasor.glob("*.json")):
                bulunan[p.stem] = p
    return bulunan


def profil_bul(ad_ya_da_yol: str) -> Profil:
    p = Path(ad_ya_da_yol)
    if p.suffix == ".json" and p.exists():
        return Profil.yukle(p)
    profiller = profilleri_listele()
    if ad_ya_da_yol not in profiller:
        raise KeyError(f"Profil bulunamadı: {ad_ya_da_yol}")
    return Profil.yukle(profiller[ad_ya_da_yol])


# ---------------------------------------------------------------- satır üretimi
@dataclass
class Hucre:
    """Yazıcılara giden değer. tur: metin, sayi (Decimal), tamsayi (int), girmedi."""

    deger: object
    tur: str = "metin"
    ondalik: int = 0


def _ad_bol(ad: str) -> tuple[str, str]:
    parcalar = ad.split()
    if len(parcalar) < 2:
        return ad, ""
    return " ".join(parcalar[:-1]), parcalar[-1]


def basliklari_genislet(profil: Profil, soru_sayisi: int) -> list[str]:
    basliklar = []
    for s in profil.sutunlar:
        if s.alan == "soru_puanlari":
            basliklar.extend((s.baslik or "S{n}").format(n=k) for k in range(1, soru_sayisi + 1))
        else:
            basliklar.append(s.baslik)
    return basliklar


def _no_hucresi(profil: Profil, no: str) -> Hucre:
    if profil.ogrenci_no_bicimi == "sayi" and no.isdigit():
        return Hucre(int(no), "tamsayi")
    return Hucre(no, "metin")


def ogrenci_hucreleri(profil: Profil, o: OgrenciSonucu | None, ogrenci: Ogrenci | None, sonuc: SinavSonucu) -> list[Hucre]:
    """Bir öğrenci için profil sütunlarının değerleri. `o` None ise öğrenci sınava girmemiştir."""
    no = o.no if o else ogrenci.no
    ad = (o.ad if o else ogrenci.ad) or ""
    n = sonuc.anahtar.soru_sayisi
    yuv = profil.yuvarlama

    def sayi(deger) -> Hucre:
        return Hucre(yuvarla(deger, profil.ondalik_basamak, yuv), "sayi", profil.ondalik_basamak)

    girmedi = Hucre(profil.girmedi_gosterimi, "girmedi")
    hucreler: list[Hucre] = []
    for s in profil.sutunlar:
        a = s.alan
        if a == "ogrenci_no":
            hucreler.append(_no_hucresi(profil, no))
        elif a == "ad_soyad":
            hucreler.append(Hucre(ad))
        elif a == "ad":
            hucreler.append(Hucre(_ad_bol(ad)[0]))
        elif a == "soyad":
            hucreler.append(Hucre(_ad_bol(ad)[1]))
        elif a == "sabit":
            hucreler.append(Hucre(s.deger))
        elif a == "soru_puanlari":
            hucreler.extend(sayi(o.sorular[k].puan) if o else girmedi for k in range(n))
        elif a.startswith("soru:"):
            k = int(a.split(":")[1]) - 1
            hucreler.append(sayi(o.sorular[k].puan) if o else girmedi)
        elif a.startswith("cevap:"):
            k = int(a.split(":")[1]) - 1
            hucreler.append(Hucre(o.cevaplar[k].strip() if o else ""))
        elif o is None:
            hucreler.append(girmedi)
        elif a == "puan":
            hucreler.append(sayi(o.puan))
        elif a == "ham_puan":
            hucreler.append(sayi(o.ham_puan))
        elif a == "ceza":
            hucreler.append(sayi(o.ceza))
        elif a == "net":
            hucreler.append(sayi(net(o.dogru, o.yanlis, sonuc.ayarlar)))
        elif a in ("dogru", "yanlis", "bos"):
            hucreler.append(Hucre(getattr(o, a), "tamsayi"))
        else:
            raise ValueError(f"Profilde bilinmeyen sütun alanı: {a}")
    return hucreler


def ogrenci_sirasi(profil: Profil, sonuc: SinavSonucu, sira: list[str] | None = None) -> list[tuple[OgrenciSonucu | None, Ogrenci | None]]:
    """Dışa aktarılacak öğrenciler, profilin sırasıyla. `sira` verilirse o numara sırası kullanılır."""
    okunan = sonuc.no_ile()
    if sira is not None:
        liste_ad = {o.no: o for o in (sonuc.liste.ogrenciler if sonuc.liste else [])}
        return [(okunan.get(no), liste_ad.get(no) or Ogrenci(no=no, ad="")) for no in sira]
    satirlar: list[tuple[OgrenciSonucu | None, Ogrenci | None]] = []
    if sonuc.liste_var and sonuc.liste is not None and profil.sira == "liste":
        for og in sonuc.liste.ogrenciler:
            o = okunan.get(og.no)
            if o is None and not profil.girmeyenleri_dahil_et:
                continue
            satirlar.append((o, og))
        if profil.listede_olmayanlari_dahil_et:
            satirlar.extend((o, None) for o in sonuc.listede_olmayanlar)
        return satirlar
    for o in sonuc.ogrenciler:
        if not o.listede and not profil.listede_olmayanlari_dahil_et:
            continue
        satirlar.append((o, None))
    if profil.girmeyenleri_dahil_et:
        satirlar.extend((None, g) for g in sonuc.girmeyenler)
    if profil.sira == "numara":
        satirlar.sort(key=lambda t: (t[0].no if t[0] else t[1].no))
    return satirlar


def ust_satirlari_doldur(profil: Profil, sinav: SinavBilgisi | None) -> list[list[str]]:
    degerler = (sinav or SinavBilgisi()).to_dict()
    return [[_yer_tutucu(h, degerler) for h in satir] for satir in profil.ust_satirlar]


def _yer_tutucu(metin: str, degerler: dict) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(degerler.get(m.group(1), m.group(0))), metin)


def tablo_uret(profil: Profil, sonuc: SinavSonucu, sinav: SinavBilgisi | None = None, sira: list[str] | None = None):
    """(üst satırlar, başlıklar, veri satırları) döndürür. Veri satırları `Hucre` listesidir."""
    ust = ust_satirlari_doldur(profil, sinav)
    basliklar = basliklari_genislet(profil, sonuc.anahtar.soru_sayisi)
    veri = [ogrenci_hucreleri(profil, o, og, sonuc) for o, og in ogrenci_sirasi(profil, sonuc, sira)]
    return ust, basliklar, veri


def hucre_metni(h: Hucre, profil: Profil) -> str:
    """Metin tabanlı çıktılar (csv, txt, pano) için."""
    if h.tur == "sayi":
        d: Decimal = h.deger  # type: ignore[assignment]
        s = f"{d:.{h.ondalik}f}"
        return s.replace(".", profil.ondalik_ayirici)
    return "" if h.deger is None else str(h.deger)
