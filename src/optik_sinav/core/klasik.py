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


def puan_listesi_coz(metin: str) -> list[str]:
    """"10 10 10 10 20 40" gibi soru puanı dizisini çözer; her puanı "12.5" biçiminde döndürür.

    Ayırıcı: boşluk, noktalı virgül, artı ya da eğik çizgi. Virgül ondalık işaretidir ("12,5"); ancak sonunda
    duran virgül ("10, 20") ya da birden çok virgül içeren parça ("10,10,20") ayırıcı sayılır.
    Sayı olmayan ya da eksi parça için ValueError.
    """
    import re

    parcalar = []
    for p in re.split(r"[\s;+/|]+", str(metin or "").strip()):
        p = p.strip(",")
        if not p:
            continue
        parcalar.extend(x for x in p.split(",") if x) if p.count(",") > 1 else parcalar.append(p)
    sonuc = []
    for p in parcalar:
        try:
            v = puan_coz(p)
        except (ValueError, ArithmeticError):
            raise ValueError(f"Sayı değil: {p!r}") from None
        if v is None or v < 0:
            raise ValueError(f"Puan sıfır ya da daha büyük olmalı: {p!r}")
        sonuc.append(str(v.numerator) if v.denominator == 1 else p.replace(",", "."))
    return sonuc


def klasik_degerlendir(liste: OgrenciListesi, anahtar: CevapAnahtari, ayarlar: PuanlamaAyarlari,
                       puanlar: dict[str, list[str | None]], toplamlar: dict[str, str | None] | None = None,
                       girmedi: list[str] | set[str] | None = None) -> SinavSonucu:
    """`toplamlar`: kâğıdın üstüne yazılan toplam (isteğe bağlı); soru puanlarının toplamıyla tutmazsa uyarı verilir.
    `girmedi`: "sınava girmedi" diye işaretlenen öğrenci numaraları; puanları girilmiş olsa bile hesaba katılmaz."""
    toplamlar = toplamlar or {}
    girmedi = set(girmedi or ())
    en_fazla = soru_puanlari(anahtar, ayarlar)
    n = anahtar.soru_sayisi
    ogrenciler: list[OgrenciSonucu] = []
    girmeyenler = []
    for sira, ogr in enumerate(liste.ogrenciler, start=1):
        if ogr.no in girmedi:
            girmeyenler.append(ogr)
            continue
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
        kagit = toplamlar.get(ogr.no)
        if kagit not in (None, ""):
            try:
                kt = puan_coz(kagit)
            except (ValueError, ArithmeticError):
                kt = None
            if kt is None:
                uyarilar.append(Uyari(UyariTuru.CEVAPTA_GECERSIZ, f"Kâğıttaki toplam sayı değil: {kagit!r}", sira))
            elif kt != ham:
                uyarilar.append(Uyari(UyariTuru.CEVAPTA_GECERSIZ, M.UYARI["klasik_toplam"].format(kagit=_yaz(kt), hesap=_yaz(ham)), sira))
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


def tablodan_girmedi(tablo: list[list[object]]) -> list[str]:
    """Excel'den puan alırken "Girmedi" sütunu doluysa (herhangi bir işaret) o öğrenci sınava girmedi sayılır."""
    from ..io.liste_okuyucu import _sade, esleme_tahmin_et, numara_normalle

    e = esleme_tahmin_et(tablo)
    if e.no_sutun is None or not e.baslik_satiri:
        return []
    baslik = [_sade(h) for h in tablo[e.baslik_satiri - 1]]
    j = next((i for i, h in enumerate(baslik) if h in ("girmedi", "sinavagirmedi", "girmeyen")), None)
    if j is None:
        return []
    sonuc = []
    for satir in tablo[e.baslik_satiri:]:
        no = numara_normalle(satir[e.no_sutun - 1] if e.no_sutun - 1 < len(satir) else None)
        v = satir[j] if j < len(satir) else None
        if no and no.isdigit() and v not in (None, "") and str(v).strip():
            sonuc.append(no)
    return sonuc


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
