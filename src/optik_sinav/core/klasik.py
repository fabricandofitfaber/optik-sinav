"""Klasik (yazılı) sınav: soru bazlı puanlar elle ya da Excel'den girilir, optik dosya yoktur.

Puanlar öğrenci numarasına göre metin olarak tutulur ("7,5" ya da "7.5"); boş hücre "girilmedi" demektir.
Bir öğrencinin hiçbir sorusuna puan girilmemişse öğrenci sınava girmemiş sayılır.
"""
from __future__ import annotations

from fractions import Fraction

from .. import metinler as M
from .modeller import (
    CevapAnahtari,
    HamKayit,
    OgrenciListesi,
    OgrenciSonucu,
    PuanlamaAyarlari,
    SinavSonucu,
    SoruSonucu,
    SoruSonucuDurumu,
    Uyari,
    UyariTuru,
    fraction_decimal,
)
from .puanlama import soru_puanlari


def puan_coz(metin: object) -> Fraction | None:
    """Hücre değerini puana çevirir. Boşsa None; sayı değilse ValueError."""
    if metin is None:
        return None
    if isinstance(metin, (int, float)):
        return Fraction(str(metin))
    s = str(metin).strip().replace(" ", "")
    if not s:
        return None
    return fraction_decimal(s)


def klasik_degerlendir(liste: OgrenciListesi, anahtar: CevapAnahtari, ayarlar: PuanlamaAyarlari,
                       puanlar: dict[str, list[str | None]]) -> SinavSonucu:
    en_fazla = soru_puanlari(anahtar, ayarlar)
    n = anahtar.soru_sayisi
    ogrenciler: list[OgrenciSonucu] = []
    girmeyenler = []
    for sira, ogr in enumerate(liste.ogrenciler, start=1):
        satir = list(puanlar.get(ogr.no) or [])
        satir += [None] * (n - len(satir))
        degerler: list[Fraction | None] = []
        uyarilar: list[Uyari] = []
        for k in range(n):
            try:
                degerler.append(puan_coz(satir[k]))
            except (ValueError, ArithmeticError):
                degerler.append(None)
                uyarilar.append(Uyari(UyariTuru.CEVAPTA_GECERSIZ, f"{k + 1}. soruda sayı olmayan değer: {satir[k]!r}", sira))
        if all(v is None for v in degerler) and not uyarilar:
            girmeyenler.append(ogr)
            continue
        sonuclar = []
        dogru = yanlis = bos = 0
        ham = Fraction(0)
        eksik = []
        for k, v in enumerate(degerler):
            tam = en_fazla[k]
            if v is None:
                eksik.append(k + 1)
                durum, p = SoruSonucuDurumu.BOS, Fraction(0)
                bos += 1
            else:
                p = v
                if v < 0:
                    uyarilar.append(Uyari(UyariTuru.CEVAPTA_GECERSIZ, M.UYARI["klasik_eksi"].format(soru=k + 1), sira))
                    p = Fraction(0)
                elif v > tam:
                    uyarilar.append(Uyari(UyariTuru.CEVAPTA_GECERSIZ, M.UYARI["klasik_fazla"].format(
                        soru=k + 1, puan=_yaz(v), en_fazla=_yaz(tam)), sira))
                if p >= tam and tam > 0:
                    durum = SoruSonucuDurumu.DOGRU
                    dogru += 1
                elif p == 0:
                    durum = SoruSonucuDurumu.YANLIS
                    yanlis += 1
                else:
                    durum = SoruSonucuDurumu.KISMI
            ham += p
            sonuclar.append(SoruSonucu(isaret=_yaz(v) if v is not None else "", durum=durum, puan=p))
        if eksik and len(eksik) < n:
            uyarilar.append(Uyari(UyariTuru.CEVAPTA_GECERSIZ, M.UYARI["klasik_eksik"].format(sorular=", ".join(map(str, eksik))), sira))
        kayit = HamKayit(satir_no=sira, ham_satir="", ad=ogr.ad, ogrenci_no=ogr.no, cevaplar=[s.isaret for s in sonuclar])
        ogrenciler.append(OgrenciSonucu(
            kayit=kayit, no=ogr.no, ad=ogr.ad, okunan_ad=ogr.ad, cevaplar=[s.isaret for s in sonuclar], sorular=sonuclar,
            dogru=dogru, yanlis=yanlis, bos=bos, ham_puan=ham, ceza=Fraction(0), puan=max(Fraction(0), ham),
            listede=True, uyarilar=uyarilar, kaynak_soru=list(range(1, n + 1)),
        ))
    return SinavSonucu(ogrenciler=ogrenciler, girmeyenler=girmeyenler, listede_olmayanlar=[], soru_puanlari=en_fazla,
                       anahtar=anahtar, ayarlar=ayarlar, liste_var=True, liste=liste, klasik=True)


def _yaz(x: Fraction | None) -> str:
    if x is None:
        return ""
    if x.denominator == 1:
        return str(x.numerator)
    from .puanlama import sayi_yaz

    return sayi_yaz(x, 2).rstrip("0").rstrip(",")


def tablodan_klasik_puanlar(tablo: list[list[object]], soru_sayisi: int) -> tuple[dict[str, list[str | None]], list[str]]:
    """Excel'den puan alma: numara sütununu ve onu izleyen soru sütunlarını bulur.

    Başlıkta "1", "S1", "Soru 1" gibi soru başlıkları aranır; bulunamazsa numara ve ad sütunlarından sonraki
    sayısal sütunlar sırayla soru sayılır. Döndürür: (puanlar, notlar).
    """
    import re

    from ..io.liste_okuyucu import _sade, esleme_tahmin_et, numara_normalle

    e = esleme_tahmin_et(tablo)
    notlar: list[str] = []
    if e.no_sutun is None:
        return {}, ["Numara sütunu bulunamadı."]
    baslik = tablo[e.baslik_satiri - 1] if e.baslik_satiri else []
    soru_sutun: dict[int, int] = {}
    for j, h in enumerate(baslik):
        m = re.fullmatch(r"(?:s|soru|q)?(\d{1,3})(?:puan|p)?", _sade(h))
        if m and j + 1 != e.no_sutun:
            k = int(m.group(1))
            if 1 <= k <= soru_sayisi and k not in soru_sutun:
                soru_sutun[k] = j
    if not soru_sutun:
        bas = max(e.no_sutun, e.ad_sutun or 0, e.soyad_sutun or 0)
        soru_sutun = {k: bas + k - 1 for k in range(1, soru_sayisi + 1)}
        notlar.append(f"Soru başlıkları bulunamadı; {bas + 1}. sütundan başlayan {soru_sayisi} sütun soru sayıldı.")
    puanlar: dict[str, list[str | None]] = {}
    for satir in tablo[(e.baslik_satiri or 0):]:
        no = numara_normalle(satir[e.no_sutun - 1] if e.no_sutun - 1 < len(satir) else None)
        if not no or not no.isdigit():
            continue
        degerler = []
        for k in range(1, soru_sayisi + 1):
            j = soru_sutun.get(k)
            v = satir[j] if j is not None and j < len(satir) else None
            if isinstance(v, float) and v.is_integer():
                v = int(v)
            degerler.append(None if v in (None, "") else str(v))
        puanlar[no] = degerler
    eksik = [k for k in range(1, soru_sayisi + 1) if k not in soru_sutun]
    if eksik:
        notlar.append("Sütunu bulunamayan sorular: " + ", ".join(map(str, eksik)))
    return puanlar, notlar
