"""Puanlama motoru. Saf fonksiyonlardan oluşur; arayüze ve dosyalara bağlı değildir.

Kurallar (PROJE_TANIMI.md bölüm 8):
- Puanlar kesirli sayılarla tam tutulur; yuvarlama yalnızca en sonda yapılır.
- Eşit puanda soru puanı = toplam / soru sayısı; iptal sorular sayıya dahildir.
- İptal soru: herkese tam puan, doğru sayılır.
- Yanlış cezası: net = doğru - yanlış / oran; ceza soru puanlarına dağıtılmaz, puan sıfırın altına inmez.
- Çift işaret: varsayılan boş; ayarla yanlış sayılabilir.
"""
from __future__ import annotations

import math
from decimal import Decimal
from fractions import Fraction

from .modeller import (
    CIFT_ISARET,
    SIKLAR,
    CevapAnahtari,
    CiftIsaretKurali,
    PuanlamaAyarlari,
    PuanYontemi,
    Soru,
    SoruDurumu,
    SoruSonucu,
    SoruSonucuDurumu,
    Yuvarlama,
    fraction_decimal,
)

def yuvarla(deger: Fraction, ondalik: int = 2, yontem: Yuvarlama = Yuvarlama.YARIM_YUKARI) -> Decimal:
    """Kesirli sayıyı istenen basamağa tam aritmetikle yuvarlar (kayan nokta kullanılmaz).

    Yarım yukarı: sıfırdan uzağa (eksi sayılarda simetrik). Aşağı ve yukarı: taban ve tavan.
    """
    olcekli = Fraction(deger) * (10**ondalik)
    if yontem == Yuvarlama.ASAGI:
        n = math.floor(olcekli)
    elif yontem == Yuvarlama.YUKARI:
        n = math.ceil(olcekli)
    elif olcekli >= 0:
        n = math.floor(olcekli + Fraction(1, 2))
    else:
        n = -math.floor(-olcekli + Fraction(1, 2))
    return Decimal(n).scaleb(-ondalik) if ondalik else Decimal(n)


def soru_puanlari(anahtar: CevapAnahtari, ayarlar: PuanlamaAyarlari) -> list[Fraction]:
    n = anahtar.soru_sayisi
    if n == 0:
        return []
    if ayarlar.yontem == PuanYontemi.ESIT:
        return [fraction_decimal(ayarlar.toplam_puan) / n] * n
    return [fraction_decimal(s.puan) if s.puan not in (None, "") else Fraction(0) for s in anahtar.sorular]


def soru_degerlendir(isaret: str, soru: Soru, ayarlar: PuanlamaAyarlari) -> SoruSonucuDurumu:
    if soru.durum == SoruDurumu.IPTAL:
        return SoruSonucuDurumu.IPTAL
    dogrular = soru.dogru_kume()
    if not dogrular:
        return SoruSonucuDurumu.ANAHTARSIZ
    if isaret == CIFT_ISARET:
        return SoruSonucuDurumu.YANLIS if ayarlar.cift_isaret == CiftIsaretKurali.YANLIS else SoruSonucuDurumu.BOS
    if isaret not in SIKLAR:
        return SoruSonucuDurumu.BOS  # boşluk ve geçersiz işaretler
    if soru.durum == SoruDurumu.COKLU:
        return SoruSonucuDurumu.DOGRU if isaret in dogrular else SoruSonucuDurumu.YANLIS
    return SoruSonucuDurumu.DOGRU if isaret in dogrular else SoruSonucuDurumu.YANLIS


def ogrenci_puanla(cevaplar: list[str], anahtar: CevapAnahtari, ayarlar: PuanlamaAyarlari, puanlar: list[Fraction] | None = None):
    """Bir öğrencinin cevaplarını puanlar.

    Döndürür: (soru sonuçları, doğru, yanlış, boş, ham puan, ceza, puan). Puanlar yuvarlanmamıştır.
    Cevap listesi anahtardan kısaysa eksik sorular boş sayılır.
    """
    puanlar = puanlar if puanlar is not None else soru_puanlari(anahtar, ayarlar)
    sonuclar: list[SoruSonucu] = []
    dogru = yanlis = bos = 0
    ham = Fraction(0)
    ceza = Fraction(0)
    for i, soru in enumerate(anahtar.sorular):
        isaret = cevaplar[i] if i < len(cevaplar) else " "
        durum = soru_degerlendir(isaret, soru, ayarlar)
        p = Fraction(0)
        if durum in (SoruSonucuDurumu.DOGRU, SoruSonucuDurumu.IPTAL):
            dogru += 1
            p = puanlar[i]
        elif durum == SoruSonucuDurumu.YANLIS:
            yanlis += 1
            if ayarlar.yanlis_cezasi and ayarlar.ceza_orani > 0:
                ceza += puanlar[i] / ayarlar.ceza_orani
        elif durum == SoruSonucuDurumu.BOS:
            bos += 1
        ham += p
        sonuclar.append(SoruSonucu(isaret=isaret, durum=durum, puan=p))
    puan = max(Fraction(0), ham - ceza)
    return sonuclar, dogru, yanlis, bos, ham, ceza, puan


def net(dogru: int, yanlis: int, ayarlar: PuanlamaAyarlari) -> Fraction:
    if not ayarlar.yanlis_cezasi or ayarlar.ceza_orani <= 0:
        return Fraction(dogru)
    return max(Fraction(0), Fraction(dogru) - Fraction(yanlis, ayarlar.ceza_orani))


def anahtar_eksikleri(anahtar: CevapAnahtari, ayarlar: PuanlamaAyarlari, klasik: bool = False) -> list[str]:
    """Puanlamaya engel eksikleri metin olarak döndürür (boşsa tamamdır). Klasik sınavda şık denetlenmez."""
    from .. import metinler as M

    eksik = []
    if anahtar.soru_sayisi == 0:
        eksik.append(M.EKSIK["soru_sayisi"])
        return eksik
    if klasik:
        anahtar = CevapAnahtari(sorular=[Soru(s.no, dogru="A", puan=s.puan) for s in anahtar.sorular])
    anahtarsiz = [s.no for s in anahtar.sorular if s.durum != SoruDurumu.IPTAL and not s.dogru_kume()]
    if anahtarsiz:
        eksik.append(M.EKSIK["anahtar"].format(sorular=", ".join(map(str, anahtarsiz))))
    coklu_tek = [s.no for s in anahtar.sorular if s.durum == SoruDurumu.COKLU and len(s.dogru_kume()) < 2]
    if coklu_tek:
        eksik.append(M.EKSIK["coklu_tek"].format(sorular=", ".join(map(str, coklu_tek))))
    if ayarlar.yontem == PuanYontemi.SORU_BAZLI:
        puansiz = [s.no for s in anahtar.sorular if s.puan in (None, "")]
        if puansiz:
            eksik.append(M.EKSIK["soru_puan_eksik"].format(sorular=", ".join(map(str, puansiz))))
        else:
            toplam = sum(soru_puanlari(anahtar, ayarlar), Fraction(0))
            beklenen = fraction_decimal(ayarlar.toplam_puan)
            if toplam != beklenen:
                eksik.append(M.EKSIK["soru_puan_toplam"].format(toplam=sayi_yaz(toplam), beklenen=sayi_yaz(beklenen)))
    return eksik


def esit_soru_puanlari(toplam: str, n: int, basamak: int = 2) -> list[str]:
    """Toplamı tam `toplam` olan, `basamak` ondalıklı eşit soru puanları (kuruş farkı baştaki sorulara)."""
    if n <= 0:
        return []
    birim = Fraction(1, 10**basamak)
    t = fraction_decimal(toplam)
    taban = math.floor(t / n / birim) * birim
    kalan = int((t - taban * n) / birim)
    degerler = [taban + (birim if i < kalan else 0) for i in range(n)]
    return [f"{Decimal(v.numerator) / Decimal(v.denominator):.{basamak}f}".rstrip("0").rstrip(".") for v in degerler]


def sayi_yaz(deger: Fraction | Decimal, ondalik: int = 2, ayirici: str = ",") -> str:
    """Gösterim için: yarım yukarı yuvarlar, gereksiz sıfırları atmaz."""
    if isinstance(deger, Fraction):
        deger = yuvarla(deger, ondalik)
    s = f"{deger:.{ondalik}f}" if ondalik > 0 else f"{deger:.0f}"
    return s.replace(".", ayirici)
