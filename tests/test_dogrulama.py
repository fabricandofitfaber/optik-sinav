from optik_sinav.core.dogrulama import duzeltme_olustur, numara_onerileri, sinavi_degerlendir
from optik_sinav.core.modeller import CevapAnahtari, OkuyucuSablonu, PuanlamaAyarlari, UyariTuru
from optik_sinav.io.dat_okuyucu import dat_oku
from optik_sinav.io.liste_okuyucu import liste_oku

S10 = OkuyucuSablonu(soru_sayisi=10)
K = CevapAnahtari.metinden("ABCDEABCDE")


def degerlendir(fix, dat="uydurma_1254_crlf.dat", duzeltmeler=None, otomatik=False):
    """Varsayılan: otomatik numara düzeltmesi kapalı (listede olmayan numara yolunu sınamak için)."""
    okuma = dat_oku(fix / dat, S10)
    liste = liste_oku(fix / "uydurma_liste.xlsx")
    kapali = None if otomatik else [k.satir_no for k in okuma.kayitlar]
    return okuma, sinavi_degerlendir(okuma.kayitlar, K, PuanlamaAyarlari(), liste, duzeltmeler, kapali)


def test_girmeyenler_ve_listede_olmayanlar(fix):
    _, s = degerlendir(fix)
    girmeyen = {o.no for o in s.girmeyenler}
    # 990000004 numarası '*' ile okundu, 990000008 numarası 990000088 okundu
    assert girmeyen == {"990000004", "990000008", "990000011", "990000012"}
    olmayan = {o.no for o in s.listede_olmayanlar}
    assert olmayan == {"99000*004", "990000088"}
    o = next(x for x in s.ogrenciler if x.no == "990000088")
    assert "990000008" in o.oneriler
    assert any(u.tur == UyariTuru.LISTEDE_YOK for u in o.uyarilar)
    # otomatik eşleştirme yapılmaz
    assert not o.listede


def test_bozuk_adlar_listeden_duzeltilir(fix):
    _, s = degerlendir(fix, "uydurma_bozuk_utf8.dat")
    o = s.ogrenciler[0]
    assert "�" in o.okunan_ad and o.ad == "ÇİĞDEM ÖZTÜRK"
    assert not any(u.tur == UyariTuru.AD_BOZUK_KARAKTER for u in o.uyarilar)


def test_bos_ad_listeden_gelir(fix):
    _, s = degerlendir(fix)
    o = next(x for x in s.ogrenciler if x.no == "990000005")
    assert o.ad == "BURAK ERDOĞAN" and not o.uyarilar


def test_duzeltme_ozgun_okumayi_silmez(fix):
    okuma, _ = degerlendir(fix)
    k = okuma.kayitlar[3]  # numarası 99000*004
    d1 = duzeltme_olustur(k, "no", "990000004", kim="test")
    d2 = duzeltme_olustur(k, "cevap:1", "a", [d1], kim="test")
    assert (d1.eski, d1.yeni, d2.eski, d2.yeni) == ("99000*004", "990000004", "E", "A")
    _, s = degerlendir(fix, duzeltmeler=[d1, d2])
    o = next(x for x in s.ogrenciler if x.no == "990000004")
    assert o.listede and o.ad == "MEHMET ÇAKIR" and o.dogru == 3
    assert not any(u.tur == UyariTuru.NUMARA_OKUNAMADI for u in o.uyarilar)
    assert k.ogrenci_no == "99000*004" and k.cevaplar[0] == "E"  # özgün okuma aynı
    assert len(s.girmeyenler) == 3


def test_tekrar_numara_duzeltmeden_sonra_yeniden_denetlenir(fix):
    okuma, s = degerlendir(fix)
    tekrar = [o for o in s.ogrenciler if any(u.tur == UyariTuru.TEKRAR_NUMARA for u in o.uyarilar)]
    assert len(tekrar) == 2
    d = duzeltme_olustur(okuma.kayitlar[9], "no", "990000012", kim="t")
    _, s = degerlendir(fix, duzeltmeler=[d])
    assert not any(u.tur == UyariTuru.TEKRAR_NUMARA for o in s.ogrenciler for u in o.uyarilar)


def test_numara_onerileri_uzunluk_farki():
    assert numara_onerileri("990000006", ["9910000002", "0990000006", "111111111"])[0] == "0990000006"
    assert numara_onerileri("", ["1"]) == []


def test_otomatik_numara_duzeltme(fix):
    """Listede olmayan numara: okunan ad, kağıdı olmayan tek bir öğrenciyle güçlü eşleşiyorsa numara düzeltilir."""
    okuma, s = degerlendir(fix, otomatik=True)
    assert {o.no for o in s.girmeyenler} == {"990000011", "990000012"} and not s.listede_olmayanlar
    o = next(x for x in s.ogrenciler if x.kayit.ogrenci_no == "990000088")
    u = next(u for u in o.uyarilar if u.tur == UyariTuru.OTOMATIK_NUMARA)
    assert o.no == "990000008" and o.listede and o.ad == "HASAN KAYA" and u.ayrinti == "990000088" and "990000008" in u.mesaj
    y = next(x for x in s.ogrenciler if x.kayit.ogrenci_no == "99000*004")
    assert y.no == "990000004" and not any(u.tur == UyariTuru.NUMARA_OKUNAMADI for u in y.uyarilar)
    # hoca geri aldı: yalnızca o satır eski hâline döner
    kapali = [o.kayit.satir_no]
    s2 = sinavi_degerlendir(okuma.kayitlar, K, PuanlamaAyarlari(), liste_oku(fix / "uydurma_liste.xlsx"), None, kapali)
    o2 = next(x for x in s2.ogrenciler if x.kayit.satir_no == o.kayit.satir_no)
    assert o2.no == "990000088" and not o2.listede and "990000008" in o2.oneriler
    assert next(x for x in s2.ogrenciler if x.kayit.ogrenci_no == "99000*004").no == "990000004"


def test_ad_benzerligi_ve_uyusmazlik(fix):
    from optik_sinav.core.dogrulama import ad_benzerligi
    from optik_sinav.core.modeller import HamKayit, OgrenciListesi, Ogrenci

    assert ad_benzerligi("HASAN KAYA", "Hasan  Kaya") == 1.0
    assert ad_benzerligi("ZÜLFÜNUR  *LMAN", "ZÜLFÜNUR YALMAN") >= 0.8  # okunamayan harf
    assert ad_benzerligi("HASAN KA", "HASAN KAYA") == 1.0  # formda kesilmiş ad
    assert ad_benzerligi("ALİ", "ALİ VELİ") == 0.0  # çok kısa: karar verilmez
    assert ad_benzerligi("HASAN KAYA", "İSMAİL KOÇ") < 0.5
    okuma, s = degerlendir(fix, otomatik=True)
    assert not any(u.tur == UyariTuru.AD_UYUSMUYOR for o in s.ogrenciler for u in o.uyarilar)
    # başkasının numarası: numara listede, ad bambaşka
    liste = liste_oku(fix / "uydurma_liste.xlsx")
    k = okuma.kayitlar[0]
    sahte = HamKayit(**{**k.__dict__, "satir_no": 999, "ad": "ZEYNEP YILMAZER", "uyarilar": []})
    sahte.ogrenci_no = next(o.no for o in liste.ogrenciler if o.no not in {x.no for x in s.ogrenciler})
    s3 = sinavi_degerlendir([sahte], K, PuanlamaAyarlari(), liste)
    assert any(u.tur == UyariTuru.AD_UYUSMUYOR for u in s3.ogrenciler[0].uyarilar)


def test_baskasinin_numarasi_adla_duzeltilir(fix):
    """Öğrenci başkasının (sınava girmemiş) numarasını kodlamış: okunan ad listedeki tek öğrenciyle eşleşiyorsa düzeltilir."""
    import copy

    okuma, s = degerlendir(fix, otomatik=True)
    liste = liste_oku(fix / "uydurma_liste.xlsx")
    ks = copy.deepcopy(okuma.kayitlar)
    hedef = next(o for o in s.ogrenciler if o.listede and o.kayit.ogrenci_no == o.no)  # numarası doğru okunmuş biri
    bos = next(g.no for g in s.girmeyenler)  # sınava girmemiş birinin numarası
    k = next(x for x in ks if x.satir_no == hedef.kayit.satir_no)
    k.ogrenci_no = bos
    s2 = sinavi_degerlendir(ks, K, PuanlamaAyarlari(), liste)
    o = next(x for x in s2.ogrenciler if x.kayit.satir_no == k.satir_no)
    u = next(u for u in o.uyarilar if u.tur == UyariTuru.OTOMATIK_NUMARA)
    assert o.no == hedef.no and "başka öğrenciye" in u.mesaj and bos in {g.no for g in s2.girmeyenler}
    assert not any(x.tur == UyariTuru.AD_UYUSMUYOR for x in o.uyarilar)
