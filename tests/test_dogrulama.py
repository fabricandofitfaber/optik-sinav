from optik_sinav.core.dogrulama import duzeltme_olustur, numara_onerileri, sinavi_degerlendir
from optik_sinav.core.modeller import CevapAnahtari, OkuyucuSablonu, PuanlamaAyarlari, UyariTuru
from optik_sinav.io.dat_okuyucu import dat_oku
from optik_sinav.io.liste_okuyucu import liste_oku

S10 = OkuyucuSablonu(soru_sayisi=10)
K = CevapAnahtari.metinden("ABCDEABCDE")


def degerlendir(fix, dat="uydurma_1254_crlf.dat", duzeltmeler=None):
    okuma = dat_oku(fix / dat, S10)
    liste = liste_oku(fix / "uydurma_liste.xlsx")
    return okuma, sinavi_degerlendir(okuma.kayitlar, K, PuanlamaAyarlari(), liste, duzeltmeler)


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
