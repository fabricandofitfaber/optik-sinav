from optik_sinav.core.modeller import OkuyucuSablonu, UyariTuru
from optik_sinav.io.dat_okuyucu import dat_oku, satiri_coz, soru_sayisi_oner
from optik_sinav.io.kodlama import baytlari_coz, metin_dosyasi_oku, satirlara_bol

S10 = OkuyucuSablonu(soru_sayisi=10)


def turler(k):
    return {u.tur for u in k.uyarilar}


def test_kodlama_sirasi():
    assert baytlari_coz("ŞÜKRÜ".encode("utf-8"))[1] == "utf-8"
    assert baytlari_coz("ŞÜKRÜ".encode("cp1254")) == ("ŞÜKRÜ", "windows-1254")
    assert baytlari_coz(b"\xef\xbb\xbfAB")[0] == "AB"
    # Windows-1254'te tanımsız bayt (0x81): Latin-1'e düşer
    assert baytlari_coz(b"\x81\xdd")[1] == "latin-1"


def test_satir_sonlari():
    assert satirlara_bol("a\r\nb\r\n") == ["a", "b"]
    assert satirlara_bol("a\nb") == ["a", "b"]
    assert satirlara_bol("a\rb\r") == ["a", "b"]
    assert satirlara_bol("a\x0cb\n") == ["a\x0cb"]


def test_cp1254_crlf_ve_utf8_lf_ayni_sonucu_verir(fix):
    a = dat_oku(fix / "uydurma_1254_crlf.dat", S10)
    b = dat_oku(fix / "uydurma_utf8_lf.dat", S10)
    assert (a.kodlama, a.satir_sonu) == ("windows-1254", "CRLF")
    assert (b.kodlama, b.satir_sonu) == ("utf-8", "LF")
    assert [(k.ad, k.ogrenci_no, k.cevaplar) for k in a.kayitlar] == [(k.ad, k.ogrenci_no, k.cevaplar) for k in b.kayitlar]
    assert a.kayitlar[0].ad == "ÇİĞDEM ÖZTÜRK"
    assert len(a.kayitlar) == 11


def test_uyari_turleri(fix):
    k = dat_oku(fix / "uydurma_1254_crlf.dat", S10).kayitlar
    assert turler(k[0]) == set()
    assert UyariTuru.NUMARA_OKUNAMADI in turler(k[3])
    assert UyariTuru.AD_BOS in turler(k[4])
    assert UyariTuru.CIFT_ISARET in turler(k[5])
    assert UyariTuru.ALAN_DISI_ISARET in turler(k[6])
    assert k[6].uyarilar[0].ayrinti == [67]
    assert UyariTuru.TEKRAR_NUMARA in turler(k[8]) and UyariTuru.TEKRAR_NUMARA in turler(k[9])
    assert UyariTuru.KISA_SATIR in turler(k[10])
    assert k[10].cevaplar == list("ABCDE     ")


def test_bozuk_karakter_uyarisi(fix):
    k = dat_oku(fix / "uydurma_bozuk_utf8.dat", S10).kayitlar
    assert "�" in k[0].ad
    assert UyariTuru.AD_BOZUK_KARAKTER in turler(k[0])
    assert k[0].ogrenci_no == "990000001"  # sabit genişlik bozulmadı


def test_bos_satirlar_atlanir():
    from optik_sinav.io.dat_okuyucu import satirlari_oku

    satir = "AD".ljust(25) + "123456789" + "  " + "ABCDE"
    kayitlar, bos = satirlari_oku([satir, "", "   ", satir.replace("123456789", "123456780")], OkuyucuSablonu(soru_sayisi=5))
    assert len(kayitlar) == 2 and bos == 2
    assert kayitlar[1].satir_no == 4


def test_kucuk_harf_ve_gecersiz_isaret():
    k = satiri_coz("X".ljust(25) + "123456789" + "  " + "abZ", 1, OkuyucuSablonu(soru_sayisi=3))
    assert k.cevaplar == ["A", "B", "Z"]
    assert UyariTuru.CEVAPTA_GECERSIZ in turler(k)


def test_kitapcik_alani():
    s = OkuyucuSablonu(soru_sayisi=3, kitapcik_baslangic=35)
    k = satiri_coz("X".ljust(25) + "123456789" + "B " + "ABC", 1, s)
    assert k.kitapcik == "B" and not k.uyarilar


def test_soru_sayisi_onerisi_alan_disi_isarete_aldanmaz(fix):
    satirlar, _, _ = metin_dosyasi_oku(fix / "uydurma_1254_crlf.dat")
    assert soru_sayisi_oner(satirlar, 37) == 10
