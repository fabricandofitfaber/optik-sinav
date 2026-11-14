"""Düzeltmeleri uygular, öğrenci listesiyle eşleştirir ve sınavı değerlendirir.

Özgün okuma (`HamKayit`) hiçbir zaman değiştirilmez. Düzeltmeler ayrı tutulur ve
her değerlendirmede baştan uygulanır.
"""
from __future__ import annotations

import getpass
from datetime import datetime

from .. import metinler as M
from .modeller import (
    CevapAnahtari,
    Duzeltme,
    HamKayit,
    Ogrenci,
    OgrenciListesi,
    OgrenciSonucu,
    PuanlamaAyarlari,
    SinavSonucu,
    Uyari,
    UyariTuru,
)
from .puanlama import ogrenci_puanla, soru_puanlari

# Düzeltme yapıldığında artık geçerli olmayan okuma uyarıları
_ALANA_GORE_KALKAN = {
    "no": {UyariTuru.NUMARA_BOS, UyariTuru.NUMARA_OKUNAMADI},
    "ad": {UyariTuru.AD_BOS, UyariTuru.AD_OKUNAMADI, UyariTuru.AD_BOZUK_KARAKTER},
    "kitapcik": {UyariTuru.KITAPCIK_OKUNAMADI},
}


def duzeltme_olustur(kayit: HamKayit, alan: str, yeni: str, onceki: list[Duzeltme] | None = None, kim: str | None = None) -> Duzeltme:
    """Geçerli değeri (önceki düzeltmeler uygulanmış) eski değer olarak kaydeden yeni düzeltme."""
    no, ad, cevaplar = duzeltilmis_degerler(kayit, onceki or [])
    if alan == "no":
        eski = no
    elif alan == "ad":
        eski = ad
    elif alan.startswith("cevap:"):
        eski = cevaplar[int(alan.split(":")[1]) - 1]
    elif alan == "kitapcik":
        eski = duzeltilmis_kitapcik(kayit, onceki or [])
        yeni = (yeni or "").strip().upper()[:1]
    else:
        raise ValueError(f"Bilinmeyen alan: {alan}")
    if alan.startswith("cevap:"):
        yeni = (yeni or " ").upper()[:1]
    if kim is None:
        try:
            kim = getpass.getuser()
        except Exception:  # pragma: no cover
            kim = ""
    return Duzeltme(satir_no=kayit.satir_no, alan=alan, eski=eski, yeni=yeni.strip() if alan != "ad" else yeni.strip(), kim=kim, zaman=datetime.now().isoformat(timespec="seconds"))


def duzeltilmis_degerler(kayit: HamKayit, duzeltmeler: list[Duzeltme]) -> tuple[str, str, list[str]]:
    no, ad, cevaplar = kayit.ogrenci_no, kayit.ad, list(kayit.cevaplar)
    for d in duzeltmeler:
        if d.satir_no != kayit.satir_no:
            continue
        if d.alan == "no":
            no = d.yeni
        elif d.alan == "ad":
            ad = d.yeni
        elif d.alan.startswith("cevap:"):
            i = int(d.alan.split(":")[1]) - 1
            while len(cevaplar) <= i:
                cevaplar.append(" ")
            cevaplar[i] = (d.yeni or " ")[:1]
    return no, ad, cevaplar


def duzeltilmis_kitapcik(kayit: HamKayit, duzeltmeler: list[Duzeltme]) -> str:
    k = kayit.kitapcik
    for d in duzeltmeler:
        if d.satir_no == kayit.satir_no and d.alan == "kitapcik":
            k = d.yeni
    return k


def numara_onerileri(no: str, adaylar: list[str], en_fazla: int = 3) -> list[str]:
    """Birebir eşleşmeyen numara için olası liste numaraları. Otomatik eşleştirme yapılmaz.

    Ölçüt: sondan ortak hane sayısı (9 ve 10 haneli numaralar için), ardından düzenleme uzaklığı.
    """
    if not no:
        return []
    puanli = []
    for a in adaylar:
        son_ortak = 0
        for x, y in zip(reversed(no), reversed(a)):
            if x != y:
                break
            son_ortak += 1
        uz = _duzenleme_uzakligi(no, a)
        icerir = no in a or a in no
        if icerir or uz <= 2 or son_ortak >= max(4, min(len(no), len(a)) - 3):
            puanli.append((-int(icerir), uz, -son_ortak, a))
    puanli.sort()
    return [a for *_, a in puanli[:en_fazla]]


def _duzenleme_uzakligi(a: str, b: str) -> int:
    onceki = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        simdi = [i]
        for j, cb in enumerate(b, 1):
            simdi.append(min(onceki[j] + 1, simdi[j - 1] + 1, onceki[j - 1] + (ca != cb)))
        onceki = simdi
    return onceki[-1]


def sinavi_degerlendir(
    kayitlar: list[HamKayit],
    anahtar: CevapAnahtari,
    ayarlar: PuanlamaAyarlari,
    liste: OgrenciListesi | None = None,
    duzeltmeler: list[Duzeltme] | None = None,
) -> SinavSonucu:
    duzeltmeler = duzeltmeler or []
    puanlar = soru_puanlari(anahtar, ayarlar)
    liste_sozluk: dict[str, Ogrenci] = {o.no: o for o in liste.ogrenciler} if liste else {}

    ogrenciler: list[OgrenciSonucu] = []
    for k in kayitlar:
        no, okunan_ad, cevaplar = duzeltilmis_degerler(k, duzeltmeler)
        duzeltilen_alanlar = {d.alan for d in duzeltmeler if d.satir_no == k.satir_no}
        kalkan = set().union(*(_ALANA_GORE_KALKAN.get(a, set()) for a in duzeltilen_alanlar)) if duzeltilen_alanlar else set()
        uyarilar = [u for u in k.uyarilar if u.tur not in kalkan and u.tur != UyariTuru.TEKRAR_NUMARA]
        # Kitapçık: cevaplar ana kitapçık sırasına çevrilir, o kitapçığın anahtarıyla puanlanır.
        kitapcik = duzeltilmis_kitapcik(k, duzeltmeler) or anahtar.ana_kitapcik
        if kitapcik not in anahtar.kitapciklar():
            if anahtar.kitapcik_anahtarlari:
                uyarilar.append(Uyari(UyariTuru.KITAPCIK_OKUNAMADI, M.UYARI["kitapcik_bilinmiyor"].format(k=kitapcik, ana=anahtar.ana_kitapcik), k.satir_no))
            kitapcik = anahtar.ana_kitapcik
        k_anahtar, ana_kendi = anahtar.kitapcik_icin(kitapcik)
        kaynak = [ana_kendi.get(s.no, s.no) for s in anahtar.sorular]
        kendi_cevaplar = cevaplar
        cevaplar = [kendi_cevaplar[j - 1] if j - 1 < len(kendi_cevaplar) else " " for j in kaynak]
        sonuclar, d, y, b, ham, ceza, puan = ogrenci_puanla(cevaplar, k_anahtar, ayarlar, puanlar)
        listede = True
        ad = okunan_ad
        oneriler: list[str] = []
        if liste is not None:
            if no in liste_sozluk:
                ad = liste_sozluk[no].ad or okunan_ad
                # Ad listeden geldiyse okunan addaki bozukluk önemsizdir.
                uyarilar = [u for u in uyarilar if u.tur not in (UyariTuru.AD_BOZUK_KARAKTER, UyariTuru.AD_OKUNAMADI, UyariTuru.AD_BOS)]
            else:
                listede = False
        ogrenciler.append(
            OgrenciSonucu(
                kayit=k, no=no, ad=ad, okunan_ad=okunan_ad, cevaplar=cevaplar, sorular=sonuclar,
                dogru=d, yanlis=y, bos=b, ham_puan=ham, ceza=ceza, puan=puan,
                listede=listede, uyarilar=uyarilar, oneriler=oneriler, kitapcik=kitapcik, kaynak_soru=kaynak,
            )
        )

    # Tekrar eden numaralar düzeltmelerden sonra yeniden denetlenir.
    sayac: dict[str, list[OgrenciSonucu]] = {}
    for o in ogrenciler:
        if o.no:
            sayac.setdefault(o.no, []).append(o)
    for grup in sayac.values():
        if len(grup) > 1:
            for o in grup:
                diger = ", ".join(str(x.kayit.satir_no) for x in grup if x is not o)
                o.uyarilar.append(Uyari(UyariTuru.TEKRAR_NUMARA, M.UYARI["tekrar_numara"].format(satirlar=diger), o.kayit.satir_no))

    girmeyenler: list[Ogrenci] = []
    listede_olmayanlar: list[OgrenciSonucu] = []
    if liste is not None:
        okunan = {o.no for o in ogrenciler}
        girmeyenler = [o for o in liste.ogrenciler if o.no not in okunan]
        bos_numaralar = [o.no for o in girmeyenler]
        for o in ogrenciler:
            if not o.listede:
                o.oneriler = numara_onerileri(o.no, bos_numaralar)
                mesaj = M.UYARI["listede_yok_oneri"].format(oneriler=", ".join(o.oneriler)) if o.oneriler else M.UYARI["listede_yok"]
                o.uyarilar.append(Uyari(UyariTuru.LISTEDE_YOK, mesaj, o.kayit.satir_no, o.oneriler))
                listede_olmayanlar.append(o)

    return SinavSonucu(
        ogrenciler=ogrenciler, girmeyenler=girmeyenler, listede_olmayanlar=listede_olmayanlar,
        soru_puanlari=puanlar, anahtar=anahtar, ayarlar=ayarlar, liste_var=liste is not None, liste=liste,
    )
