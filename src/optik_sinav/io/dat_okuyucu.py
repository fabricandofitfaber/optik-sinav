"""Optik okuyucunun sabit genişlikli `.dat` dosyasını okur.

Okuma özgündür: hiçbir alan düzeltilmez, yalnızca uyarı üretilir.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from .. import metinler as M
from ..core.modeller import (
    CIFT_ISARET,
    SIKLAR,
    DatOkumaSonucu,
    HamKayit,
    OkuyucuSablonu,
    Uyari,
    UyariTuru,
)
from .kodlama import BOZUK_KARAKTER, metin_dosyasi_oku


def okuyucu_sablonu_yukle(yol: str | Path) -> OkuyucuSablonu:
    return OkuyucuSablonu.from_dict(json.loads(Path(yol).read_text(encoding="utf-8")))


def _alan(satir: str, baslangic: int, uzunluk: int) -> str:
    return satir[baslangic - 1 : baslangic - 1 + uzunluk]


def satiri_coz(satir: str, satir_no: int, s: OkuyucuSablonu) -> HamKayit:
    uyarilar: list[Uyari] = []
    ad = _alan(satir, s.ad_baslangic, s.ad_uzunluk).strip()
    no = _alan(satir, s.no_baslangic, s.no_uzunluk).strip()
    cevap_ham = _alan(satir, s.cevap_baslangic, s.soru_sayisi)

    # Kısa satır: cevap alanı kesikse eksik kısım boş sayılır.
    if len(satir) < s.cevap_bitis:
        eksik = s.cevap_bitis - max(len(satir), s.cevap_baslangic - 1)
        uyarilar.append(Uyari(UyariTuru.KISA_SATIR, M.UYARI["kisa_satir"].format(uzunluk=len(satir), eksik=eksik), satir_no))
    cevap_ham = cevap_ham.ljust(s.soru_sayisi)
    cevaplar = [c.upper() for c in cevap_ham]

    # Numara
    if not no:
        uyarilar.append(Uyari(UyariTuru.NUMARA_BOS, M.UYARI["numara_bos"], satir_no))
    elif not no.isdigit():
        uyarilar.append(Uyari(UyariTuru.NUMARA_OKUNAMADI, M.UYARI["numara_okunamadi"].format(no=no), satir_no))
    # Ad
    if not ad:
        uyarilar.append(Uyari(UyariTuru.AD_BOS, M.UYARI["ad_bos"], satir_no))
    else:
        if BOZUK_KARAKTER in ad:
            uyarilar.append(Uyari(UyariTuru.AD_BOZUK_KARAKTER, M.UYARI["ad_bozuk_karakter"], satir_no))
        if any(c == "*" or (not c.isalpha() and c not in " .'-") for c in ad.replace(BOZUK_KARAKTER, "")):
            uyarilar.append(Uyari(UyariTuru.AD_OKUNAMADI, M.UYARI["ad_okunamadi"].format(ad=ad), satir_no))
    # Cevaplar
    gecersiz = [i + 1 for i, c in enumerate(cevaplar) if c not in SIKLAR and c not in (" ", CIFT_ISARET)]
    if gecersiz:
        uyarilar.append(Uyari(UyariTuru.CEVAPTA_GECERSIZ, M.UYARI["cevapta_gecersiz"].format(sorular=_liste(gecersiz)), satir_no, gecersiz))
    cift = [i + 1 for i, c in enumerate(cevaplar) if c == CIFT_ISARET]
    if cift:
        uyarilar.append(Uyari(UyariTuru.CIFT_ISARET, M.UYARI["cift_isaret"].format(sorular=_liste(cift)), satir_no, cift))
    # Kitapçık
    kitapcik = ""
    if s.kitapcik_baslangic:
        kitapcik = _alan(satir, s.kitapcik_baslangic, s.kitapcik_uzunluk).strip().upper()
        if not kitapcik or not kitapcik.isalpha():
            uyarilar.append(Uyari(UyariTuru.KITAPCIK_OKUNAMADI, M.UYARI["kitapcik_okunamadi"].format(k=kitapcik), satir_no))
    # Alan dışı işaret: tanımlı alanların dışında boşluk olmayan karakter
    tanimli = set()
    for _, bas, uz in s.alanlar():
        tanimli.update(range(bas, bas + uz))
    disarida = [i + 1 for i, c in enumerate(satir) if (i + 1) not in tanimli and not c.isspace()]
    if disarida:
        uyarilar.append(Uyari(UyariTuru.ALAN_DISI_ISARET, M.UYARI["alan_disi_isaret"].format(konumlar=_liste(disarida)), satir_no, disarida))

    return HamKayit(satir_no=satir_no, ham_satir=satir, ad=ad, ogrenci_no=no, cevaplar=cevaplar, kitapcik=kitapcik, uyarilar=uyarilar)


def _liste(sayilar: list[int]) -> str:
    return ", ".join(str(n) for n in sayilar)


def tekrar_numaralari_isaretle(kayitlar: list[HamKayit], numara=lambda k: k.ogrenci_no) -> dict[str, list[int]]:
    """Aynı numaralı kayıtları bulur: {numara: [satır no, ...]}."""
    gruplar: dict[str, list[int]] = defaultdict(list)
    for k in kayitlar:
        n = numara(k)
        if n:
            gruplar[n].append(k.satir_no)
    return {n: s for n, s in gruplar.items() if len(s) > 1}


def satirlari_oku(satirlar: list[str], sablon: OkuyucuSablonu) -> tuple[list[HamKayit], int]:
    kayitlar = []
    bos = 0
    for i, satir in enumerate(satirlar, start=1):
        if not satir.strip():
            bos += 1
            continue
        kayitlar.append(satiri_coz(satir, i, sablon))
    for no, satir_nolar in tekrar_numaralari_isaretle(kayitlar).items():
        for k in kayitlar:
            if k.ogrenci_no == no:
                diger = [s for s in satir_nolar if s != k.satir_no]
                k.uyarilar.append(Uyari(UyariTuru.TEKRAR_NUMARA, M.UYARI["tekrar_numara"].format(satirlar=_liste(diger)), k.satir_no))
    return kayitlar, bos


def dat_oku(yol: str | Path, sablon: OkuyucuSablonu | None = None) -> DatOkumaSonucu:
    satirlar, kodlama, satir_sonu = metin_dosyasi_oku(yol)
    sablon = sablon or OkuyucuSablonu()
    kayitlar, bos = satirlari_oku(satirlar, sablon)
    return DatOkumaSonucu(kayitlar=kayitlar, kodlama=kodlama, satir_sonu=satir_sonu, sablon=sablon, bos_satir_sayisi=bos)


def soru_sayisi_oner(satirlar: list[str], cevap_baslangic: int, en_az_oran: float = 0.10) -> int:
    """Cevap alanında şık harfi ya da çift işaret görülen en son sütuna bakarak soru sayısı önerir.

    Tek tük alan dışı işaretlerin soru sayısını şişirmemesi için bir sütunun sayılması
    için satırların en az `en_az_oran` kadarında (ve en az iki satırda) işaret olmalıdır.
    """
    dolu = [s for s in satirlar if s.strip()]
    if not dolu:
        return 0
    sayac: Counter[int] = Counter()
    for s in dolu:
        for i in range(cevap_baslangic - 1, len(s)):
            if s[i].upper() in SIKLAR or s[i] == CIFT_ISARET:
                sayac[i] += 1
    esik = max(2, int(len(dolu) * en_az_oran)) if len(dolu) > 2 else 1
    son = [i for i, n in sayac.items() if n >= esik]
    if not son:
        return 0
    return max(son) - (cevap_baslangic - 1) + 1


def sablon_oner(satirlar: list[str], temel: OkuyucuSablonu | None = None) -> OkuyucuSablonu:
    """Temel şablonu alır, soru sayısını ve satır uzunluğunu dosyaya göre önerir."""
    s = OkuyucuSablonu.from_dict((temel or OkuyucuSablonu()).to_dict())
    n = soru_sayisi_oner(satirlar, s.cevap_baslangic)
    if n:
        s.soru_sayisi = n
    uzunluklar = Counter(len(x) for x in satirlar if x.strip())
    if uzunluklar:
        s.satir_uzunlugu = uzunluklar.most_common(1)[0][0]
    return s
