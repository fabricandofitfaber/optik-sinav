"""Dönem sonu notu ve harf notu (saf fonksiyonlar).

Ara sınav puanı bu sınavdan, final puanları ayrıca girilir (elle ya da Excel'den). Ham başarı notu:
    ham = ara × ara ağırlığı / 100 + final × (100 − ara ağırlığı) / 100   (kesirle, yuvarlamadan)

İki değerlendirme türü:
- Mutlak: ham başarı notu harf tablosundaki alt sınırlarla karşılaştırılır.
- Bağıl (T-puanı): final alt sınırını geçen öğrencilerin ham notlarının ortalaması ve standart sapmasıyla
  T = 50 + 10 × (ham − ortalama) / standart sapma; harf, T tablosundaki alt sınırlara göre verilir.
  Bu gruptaki öğrenci sayısı "bağıl için en az" değerinin altındaysa mutlak tabloya geçilir.
Final alt sınırının altında kalan öğrenci her iki türde de en düşük harfi alır.

Harf tabloları üniversitenin yönetmeliğine göre değişir; buradaki varsayılanlar ÖRNEKTİR ve kullanıcının
kendi yönetmeliğiyle karşılaştırması gerekir.
"""
from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass, field
from fractions import Fraction

from .modeller import SinavSonucu, fraction_decimal

ORNEK_MUTLAK = "AA 90, BA 85, BB 75, CB 70, CC 60, DC 55, DD 50, FD 40, FF 0"
ORNEK_BAGIL = "AA 63, BA 58, BB 53, CB 48, CC 43, DC 38, DD 33, FD 28, FF 0"
GECEN_HARFLER = "AA, BA, BB, CB, CC, DC, DD"


@dataclass
class HarfAyarlari:
    yontem: str = "mutlak"  # "mutlak" ya da "bagil"
    mutlak: str = ORNEK_MUTLAK
    bagil: str = ORNEK_BAGIL
    bagil_en_az: int = 30  # bağıl değerlendirme için en az öğrenci (altında mutlak tablo)
    gecen: str = GECEN_HARFLER

    def to_dict(self) -> dict:
        return {"yontem": self.yontem, "mutlak": self.mutlak, "bagil": self.bagil, "bagil_en_az": self.bagil_en_az, "gecen": self.gecen}

    @classmethod
    def from_dict(cls, d: dict | None) -> "HarfAyarlari":
        d = d or {}
        a = cls()
        for k in ("yontem", "mutlak", "bagil", "gecen"):
            if k in d:
                setattr(a, k, str(d[k]))
        if "bagil_en_az" in d:
            a.bagil_en_az = int(d["bagil_en_az"])
        return a


def tablo_coz(metin: str) -> list[tuple[str, float]]:
    """"AA 90, BA 85, ..." → [("AA", 90.0), ...], alt sınıra göre büyükten küçüğe."""
    t = []
    for parca in re.split(r"[,;\n]+", metin):
        parca = parca.strip()
        if not parca:
            continue
        m = re.match(r"^([A-Za-zÇĞİÖŞÜçğıöşü]{1,3})\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)$", parca)
        if not m:
            raise ValueError(f"Harf tablosunda anlaşılamayan parça: {parca!r}. Örnek yazım: AA 90, BA 85")
        t.append((m.group(1).upper(), float(m.group(2).replace(",", "."))))
    if not t:
        raise ValueError("Harf tablosu boş.")
    return sorted(t, key=lambda x: -x[1])


@dataclass
class OgrenciNotu:
    no: str
    ad: str
    ara: float
    final: float | None  # None: final girilmedi
    ham: float | None
    t: float | None
    harf: str
    gecti: bool | None
    aciklama: str = ""
    sinirda: str = ""  # bir üst harfe 1 puandan (ya da 1 T puanından) az kalanlar


@dataclass
class DonemSonu:
    notlar: list[OgrenciNotu]
    uygulanan: str  # "mutlak" ya da "bagil"
    ortalama: float | None  # bağılda kullanılan ham not ortalaması
    standart_sapma: float | None
    bagil_grup: int
    dagilim: dict[str, int] = field(default_factory=dict)
    notlar_metin: list[str] = field(default_factory=list)


def _harf(deger: float, tablo: list[tuple[str, float]]) -> tuple[str, str]:
    """(harf, bir üst harfe yakınlık notu)."""
    for i, (h, alt) in enumerate(tablo):
        if deger >= alt - 1e-9:
            sinir = ""
            if i > 0:
                ust_h, ust = tablo[i - 1]
                if ust - deger <= 1.0 + 1e-9:
                    sinir = f"{ust_h} için {ust - deger:.2f} eksik".replace(".", ",")
            return h, sinir
    return tablo[-1][0], ""


def donem_sonu(sonuc: SinavSonucu, finaller: dict[str, str | None], ara_agirlik: float, final_alt: float,
               gecme_ortalamasi: float, ayar: HarfAyarlari) -> DonemSonu:
    mutlak = tablo_coz(ayar.mutlak)
    bagil = tablo_coz(ayar.bagil)
    gecen = {h.strip().upper() for h in re.split(r"[,;\s]+", ayar.gecen) if h.strip()}
    w = Fraction(str(ara_agirlik))
    satirlar = []
    for o in sonuc.ogrenciler:
        ham_f = finaller.get(o.no)
        final = None
        if ham_f not in (None, ""):
            try:
                final = fraction_decimal(str(ham_f))
            except (ValueError, ArithmeticError):
                final = None
        ham = None if final is None else o.puan * w / 100 + final * (100 - w) / 100
        satirlar.append((o, final, ham))
    grup = [float(h) for o, f, h in satirlar if f is not None and float(f) >= final_alt]
    uygulanan = ayar.yontem
    notlar_metin = []
    if uygulanan == "bagil" and len(grup) < max(2, ayar.bagil_en_az):
        notlar_metin.append(f"Bağıl değerlendirmeye giren öğrenci sayısı ({len(grup)}) {ayar.bagil_en_az}'dan az; mutlak tablo uygulandı.")
        uygulanan = "mutlak"
    ort = statistics.fmean(grup) if grup else None
    sd = statistics.stdev(grup) if len(grup) > 1 else None
    if uygulanan == "bagil" and not sd:
        notlar_metin.append("Ham notların standart sapması sıfır; mutlak tablo uygulandı.")
        uygulanan = "mutlak"
    sonuc_notlar = []
    en_dusuk = (bagil if uygulanan == "bagil" else mutlak)[-1][0]
    for o, final, ham in satirlar:
        ara = float(o.puan)
        if final is None:
            sonuc_notlar.append(OgrenciNotu(o.no, o.ad, ara, None, None, None, "", None, "final girilmedi"))
            continue
        h = float(ham)
        if float(final) < final_alt:
            sonuc_notlar.append(OgrenciNotu(o.no, o.ad, ara, float(final), h, None, en_dusuk, False, f"final {final_alt:g} altında"))
            continue
        if uygulanan == "bagil":
            t = 50 + 10 * (h - ort) / sd
            harf, sinir = _harf(t, bagil)
        else:
            t = None
            harf, sinir = _harf(h, mutlak)
        gecti = harf in gecen and h >= gecme_ortalamasi - 1e-9
        aciklama = "" if gecti or harf not in gecen else f"ortalama {gecme_ortalamasi:g} altında"
        sonuc_notlar.append(OgrenciNotu(o.no, o.ad, ara, float(final), h, t, harf, gecti, aciklama, sinir))
    sirali_harfler = [h for h, _ in (bagil if uygulanan == "bagil" else mutlak)]
    dagilim = {h: sum(1 for n in sonuc_notlar if n.harf == h) for h in sirali_harfler}
    return DonemSonu(sonuc_notlar, uygulanan, ort, sd, len(grup), dagilim, notlar_metin)


def tablodan_final_puanlari(tablo: list[list[object]]) -> tuple[dict[str, str | None], list[str]]:
    """Excel'den final puanları: numara sütunu ve "final", "puan", "not", "yarıyıl sonu" başlıklı sütun;
    başlık yoksa ad sütunundan sonraki ilk sayısal sütun."""
    from ..io.liste_okuyucu import _sade, esleme_tahmin_et, numara_normalle

    e = esleme_tahmin_et(tablo)
    if e.no_sutun is None:
        return {}, ["Numara sütunu bulunamadı."]
    baslik = tablo[e.baslik_satiri - 1] if e.baslik_satiri else []
    sutun = None
    for j, h in enumerate(baslik):
        sh = _sade(h)
        if j + 1 != e.no_sutun and (sh in ("final", "puan", "not", "finalpuani", "finalnotu", "yariyilsonu", "yariyilsonusinavi", "ysn") or sh.startswith("final")):
            sutun = j
            break
    notlar = []
    veri = tablo[(e.baslik_satiri or 0):]
    if sutun is None:
        bas = max(e.no_sutun, e.ad_sutun or 0, e.soyad_sutun or 0)
        genislik = max((len(s) for s in veri), default=0)
        for j in range(bas, genislik):
            sayisal = sum(1 for s in veri if j < len(s) and _sayi_mi(s[j]))
            if sayisal >= max(1, len(veri) // 2):
                sutun = j
                notlar.append(f"Final başlığı bulunamadı; {j + 1}. sütun final puanı sayıldı.")
                break
    if sutun is None:
        return {}, ["Final puanı sütunu bulunamadı."]
    sonuc: dict[str, str | None] = {}
    for s in veri:
        no = numara_normalle(s[e.no_sutun - 1] if e.no_sutun - 1 < len(s) else None)
        if not no or not no.isdigit():
            continue
        v = s[sutun] if sutun < len(s) else None
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        sonuc[no] = None if v in (None, "") else str(v)
    return sonuc, notlar


def _sayi_mi(v: object) -> bool:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return True
    try:
        fraction_decimal(str(v))
        return True
    except (ValueError, ArithmeticError):
        return False


# ---------------------------------------------------------------- öğrenci karnesi
@dataclass
class Karne:
    no: str
    ad: str
    puan: float
    sira: int
    ogrenci_sayisi: int
    yuzdelik: float  # öğrenciden düşük alanların oranı
    sinif_ortalamasi: float
    sorular: list[tuple[int, str, str, str, float, float]]  # (soru, işaret, doğru, durum, alınan, tam)
    ciktilar: list[tuple[str, str, float, float]]  # (kod, açıklama, öğrenci %, sınıf %)
    guclu: list[str]
    gelismeli: list[str]


def karneler(sonuc: SinavSonucu, cikti_raporu=None, aciklamalar: dict[str, str] | None = None) -> list[Karne]:
    """Her öğrenci için tek sayfalık geri bildirim verisi. Güçlü/gelişmeli: sınıf ortalamasından en az
    10 puan yukarıda/aşağıda olan öğrenme çıktıları (yoksa en yüksek ve en düşük)."""
    aciklamalar = aciklamalar or {}
    ogr = sonuc.ogrenciler
    n = len(ogr)
    puanlar = [o.puan for o in ogr]
    ort = statistics.fmean(float(p) for p in puanlar) if n else 0.0
    rapor = [c for c in (cikti_raporu or []) if c.tur.startswith("Öğrenme")]
    k = []
    for o in ogr:
        sira = 1 + sum(1 for p in puanlar if p > o.puan)
        yuzdelik = sum(1 for p in puanlar if p < o.puan) / n if n else 0.0
        sorular = []
        for i, (s, q) in enumerate(zip(o.sorular, sonuc.anahtar.sorular)):
            dogru = "" if sonuc.klasik else ("İptal" if q.durum.value == "iptal" else q.dogru)
            sorular.append((i + 1, s.isaret.strip(), dogru, s.durum.value, float(s.puan), float(sonuc.soru_puanlari[i])))
        ciktilar = [(c.kod, aciklamalar.get(c.kod, c.aciklama), c.ogrenci_yuzdeleri.get(o.no, 0.0), c.sinif_yuzdesi or 0.0) for c in rapor]
        guclu = [c[0] for c in ciktilar if c[2] - c[3] >= 10]
        zayif = [c[0] for c in ciktilar if c[3] - c[2] >= 10]
        if ciktilar and not guclu and not zayif:
            guclu = [max(ciktilar, key=lambda c: c[2] - c[3])[0]]
            zayif = [min(ciktilar, key=lambda c: c[2] - c[3])[0]] if len(ciktilar) > 1 else []
        k.append(Karne(o.no, o.ad, float(o.puan), sira, n, yuzdelik, ort, sorular, ciktilar, guclu, zayif))
    return k
