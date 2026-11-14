"""Arayüz duman testi: ekransız kipte bütün adımlardan geçer."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


@pytest.fixture
def pencere(qapp_):
    from optik_sinav.ui.ana_pencere import AnaPencere

    p = AnaPencere()
    yield p
    p.close()


@pytest.fixture(scope="module")
def qapp_():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_butun_adimlar(pencere, fix, tmp_path):
    from optik_sinav.ui.adimlar.kontrol import KontrolAdimi

    d = pencere.durum
    assert not pencere.sonraki.isEnabled()  # dosya ve ders kodu yok
    pencere.adimlar[0].ders_kodu.setText("UYD1001")
    pencere.adimlar[0]._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    pencere.adimlar[0]._liste_ac(str(fix / "uydurma_liste.xlsx"))
    assert d.proje.okuyucu.soru_sayisi == 10 and len(d.okuma.kayitlar) == 11
    assert pencere.sonraki.isEnabled()
    pencere.sonraki.click()
    a = pencere.adimlar[1]
    assert pencere.yigin.currentIndex() == 1 and not pencere.sonraki.isEnabled()
    a.hizli.setText("ABCDE ABCDE")
    a._hizli_uygula()
    assert d.proje.anahtar.metne() == "ABCDEABCDE" and pencere.sonraki.isEnabled()
    # yuvarlak şıklarla değiştirme
    a.satirlar[0].kabarciklar["B"].click()  # 1. soru B
    assert d.proje.anahtar.sorular[0].dogru == "B"
    a.satirlar[0].kabarciklar["A"].click()
    assert d.proje.anahtar.sorular[0].dogru == "A"
    # klavye: etkin satır 2. soru; "C" yazınca 2. soru C olur ve 3. soruya geçer
    a.etkin = 1
    a._tus("C")
    assert d.proje.anahtar.sorular[1].dogru == "C" and a.etkin == 2
    a._tus("B")
    assert d.proje.anahtar.sorular[2].dogru == "B"
    a.hizli.setText("ABCDE ABCDE")
    a._hizli_uygula()
    # öğrenme çıktısı: yazım "1, 2" -> Ö01 %50, Ö02 %50
    a.satirlar[0].oc.setText("1, 2")
    a._oc_degisti(0)
    assert d.proje.anahtar.sorular[0].cikti_dagilimi() == {"Ö01": 50, "Ö02": 50}
    assert not pencere.sonraki.isEnabled()  # öteki sorulara çıktı atanmadı
    for i in range(1, 10):
        a.satirlar[i].oc.setText("Ö01 %70, Ö03")
        a._oc_degisti(i)
    assert d.proje.anahtar.sorular[1].cikti_dagilimi() == {"Ö01": 70, "Ö03": 30}
    assert pencere.sonraki.isEnabled()
    # soru puanı değiştirilince soru bazlı puana geçilir, toplam korunur
    a.satirlar[0].puan.setValue(12)
    from optik_sinav.core.modeller import PuanYontemi

    assert d.proje.ayarlar.yontem == PuanYontemi.SORU_BAZLI and d.proje.anahtar.sorular[1].puan == "10"
    a._esit_puan()
    assert d.proje.ayarlar.yontem == PuanYontemi.ESIT
    pencere.sonraki.click()
    pencere.sonraki.click()
    k: KontrolAdimi = pencere.adimlar[3]
    assert pencere.yigin.currentIndex() == 3
    assert k.model.rowCount() == 11 and k.model.columnCount() == 3 + 10 + 5
    k.yalniz_uyarili.setChecked(True)
    assert k.suzgec.rowCount() < 11
    assert k.girmeyen_tablo.rowCount() == 4 and k.olmayan_tablo.rowCount() == 2
    # numara düzeltme (iletişim kutusu olmadan)
    satir = next(o.kayit.satir_no for o in d.sonuc.ogrenciler if o.no == "990000088")
    d.duzelt(satir, "no", "990000008")
    assert k.girmeyen_tablo.rowCount() == 3 and k.duzeltme_tablo.rowCount() == 1
    pencere.sonraki.click()
    ist = pencere.adimlar[4]
    assert pencere.yigin.currentIndex() == 4 and ist.madde.rowCount() == 10 and "Kısaca" in ist.yorum.text()
    assert ist.cikti.rowCount() == 3  # Ö01, Ö02, Ö03
    pencere.sonraki.click()
    e = pencere.adimlar[5]
    assert e.akr.count() >= 3 and e.onizleme.rowCount() == 12
    # proje kaydet ve yeniden aç
    d.kaydet(str(tmp_path / "s.osd"))
    from optik_sinav.ui.ana_pencere import AnaPencere

    p2 = AnaPencere()
    p2.proje_ac(str(tmp_path / "s.osd"))
    assert p2.durum.proje.anahtar.metne() == "ABCDEABCDE" and len(p2.durum.proje.duzeltmeler) == 1
    assert p2.adimlar[0].ders_kodu.text() == "UYD1001"
    p2.close()


def test_kitapcik_arayuzu(pencere, fix):
    d = pencere.durum
    pencere.adimlar[0].ders_kodu.setText("UYD1001")
    pencere.adimlar[0]._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    pencere.sonraki.click()
    a = pencere.adimlar[1]
    a.hizli.setText("ABCDEABCDE")
    a._hizli_uygula()
    d.proje.anahtar.kitapcik_anahtarlari["B"] = "-" * 10
    a._kurulu = None
    a.durumdan_yukle()
    assert a.sekmeler.count() == 2
    a.sekmeler.setCurrentIndex(1)
    assert a.kitapcik == "B" and a.satirlar[0].esleme is not None and a.satirlar[0].puan is None
    assert not pencere.sonraki.isEnabled()  # B anahtarı boş
    a.hizli.setText("EDCBAEDCBA")
    a._hizli_uygula()
    assert d.proje.anahtar.kitapcik_anahtarlari["B"] == "EDCBAEDCBA"
    a.satirlar[0].esleme.setValue(2)
    a.satirlar[1].esleme.setValue(1)
    assert d.proje.anahtar.esleme("B")[1] == 2 and pencere.sonraki.isEnabled()


def test_klasik_sinav_arayuzu(pencere, fix, tmp_path):
    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1.ders_kodu.setText("UYD1001")
    p1.bicim_klasik.setChecked(True)
    assert d.proje.klasik and not pencere.sonraki.isEnabled()  # liste yok
    p1._liste_ac(str(fix / "uydurma_liste.xlsx"))
    p1.klasik_sayi.setValue(4)
    assert d.proje.anahtar.soru_sayisi == 4 and pencere.sonraki.isEnabled()
    pencere.sonraki.click()
    a = pencere.adimlar[1]
    assert [s.puan for s in d.proje.anahtar.sorular] == ["25", "25", "25", "25"]
    assert a.satirlar[0].kabarciklar == {} and pencere.sonraki.isEnabled()
    a.satirlar[3].puan.setValue(40)
    a.satirlar[0].puan.setValue(10)
    pencere.sonraki.click()
    assert pencere.sonraki.isEnabled()  # 10 + 25 + 25 + 40 = 100
    pencere.sonraki.click()
    k = pencere.adimlar[3]
    m = k.klasik_model
    assert m.rowCount() == len(d.liste.ogrenciler) and m.columnCount() == 3 + 4 + 1
    assert not pencere.sonraki.isEnabled()  # puan yok
    m.setData(m.index(0, 3), "10")
    m.setData(m.index(0, 4), "12,5")
    m.setData(m.index(1, 6), "40")
    assert d.sonuc.klasik and len(d.sonuc.ogrenciler) == 2
    o = d.sonuc.no_ile()[d.liste.ogrenciler[0].no]
    assert float(o.puan) == 22.5
    assert pencere.sonraki.isEnabled()
    pencere.sonraki.click()
    pencere.sonraki.click()
    d.kaydet(str(tmp_path / "k.osd"))
    from optik_sinav.ui.ana_pencere import AnaPencere

    p2 = AnaPencere()
    p2.proje_ac(str(tmp_path / "k.osd"))
    assert p2.durum.proje.klasik and p2.durum.proje.klasik_puanlar[d.liste.ogrenciler[0].no][:2] == ["10", "12,5"]
    p2.close()
