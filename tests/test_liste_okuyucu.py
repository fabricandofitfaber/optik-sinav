from optik_sinav.io.liste_okuyucu import esleme_tahmin_et, liste_oku, numara_normalle


def test_eski_program_ciktisi(fix):
    l = liste_oku(fix / "uydurma_liste.xlsx")
    assert l.esleme.sayfa == "ktt"
    assert (l.esleme.baslik_satiri, l.esleme.no_sutun, l.esleme.ad_sutun) == (2, 3, 4)
    assert len(l.ogrenciler) == 12
    assert l.ogrenciler[0].no == "990000001"
    assert l.ogrenciler[0].ad == "ÇİĞDEM ÖZTÜRK"  # sondaki boşluklar atıldı


def test_ayri_ad_soyad_sutunlari(fix):
    l = liste_oku(fix / "uydurma_sablon.xlsx")
    assert (l.esleme.baslik_satiri, l.esleme.no_sutun, l.esleme.ad_sutun, l.esleme.soyad_sutun) == (3, 2, 3, 4)
    assert l.ogrenciler[0].ad == "İSMAİL KOÇ"


def test_basliksiz_csv(fix):
    l = liste_oku(fix / "uydurma_liste.csv")
    assert len(l.ogrenciler) == 12
    assert l.ogrenciler[1].ad == "ŞÜKRÜ IŞIK"


def test_numara_normalle():
    assert numara_normalle(990000001.0) == "990000001"
    assert numara_normalle(" 9900 000001 ") == "9900000001"
    assert numara_normalle("990000001.0") == "990000001"
    assert numara_normalle(None) == ""


def test_esleme_degistirilebilir(fix):
    from optik_sinav.core.modeller import ListeEslemesi

    l = liste_oku(fix / "uydurma_liste.xlsx", ListeEslemesi(sayfa="ktt", baslik_satiri=2, no_sutun=3, ad_sutun=None))
    assert l.ogrenciler[0].ad == ""


def test_baslik_turkce_buyuk_harf():
    e = esleme_tahmin_et([["ÖĞRENCİ NO", "ADI SOYADI"], ["123456789", "X"]])
    assert (e.no_sutun, e.ad_sutun) == (1, 2)
