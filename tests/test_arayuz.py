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



def _hazir(pencere):
    """Bulunulan adımın zorunlu bilgileri tam mı (eksikler artık gezinmeyi engellemez, yalnızca gösterilir)."""
    return not pencere.adimlar[pencere.yigin.currentIndex()].eksikler()

def test_butun_adimlar(pencere, fix, tmp_path):
    from optik_sinav.ui.adimlar.kontrol import KontrolAdimi

    d = pencere.durum
    assert not _hazir(pencere)  # dosya yok (ders kodu isteğe bağlı)
    assert pencere.sonraki.isEnabled()  # eksik olsa da ileri geçilebilir
    pencere.adimlar[0].ders_kodu.setText("UYD1001")
    pencere.adimlar[0]._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    pencere.adimlar[0]._liste_ac(str(fix / "uydurma_liste.xlsx"))
    assert d.proje.okuyucu.soru_sayisi == 10 and len(d.okuma.kayitlar) == 11
    assert _hazir(pencere)
    pencere.sonraki.click()
    a = pencere.adimlar[1]
    assert pencere.yigin.currentIndex() == 1 and not _hazir(pencere)
    a.hizli.setText("ABCDE ABCDE")
    a._hizli_uygula()
    assert d.proje.anahtar.metne() == "ABCDEABCDE" and _hazir(pencere)
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
    assert not _hazir(pencere)  # öteki sorulara çıktı atanmadı
    for i in range(1, 10):
        a.satirlar[i].oc.setText("Ö01 %70, Ö03")
        a._oc_degisti(i)
    assert d.proje.anahtar.sorular[1].cikti_dagilimi() == {"Ö01": 70, "Ö03": 30}
    assert _hazir(pencere)
    # soru puanı değiştirilince soru bazlı puana geçilir, toplam korunur
    a.satirlar[0].puan.setValue(12)
    from optik_sinav.core.modeller import PuanYontemi

    assert d.proje.ayarlar.yontem == PuanYontemi.SORU_BAZLI and d.proje.anahtar.sorular[1].puan == "10"
    a._esit_puan()
    assert d.proje.ayarlar.yontem == PuanYontemi.ESIT
    assert not a.baslik_w["Puan"].isVisibleTo(a)  # eşit puanda puan sütunu gizli
    d.proje.otomatik_kapali = [x.satir_no for x in d.okuma.kayitlar]  # elle düzeltme yolunu sınamak için otomatik kapalı
    pencere.sonraki.click()
    k: KontrolAdimi = pencere.adimlar[2]
    assert pencere.yigin.currentIndex() == 2
    assert k.model.rowCount() == 11 and k.model.columnCount() == 3 + 10 + 5
    k.yalniz_uyarili.setChecked(True)
    assert k.suzgec.rowCount() < 11
    assert k.girmeyen_tablo.rowCount() == 4 and k.olmayan_tablo.rowCount() == 2
    # numara düzeltme (iletişim kutusu olmadan)
    satir = next(o.kayit.satir_no for o in d.sonuc.ogrenciler if o.no == "990000088")
    d.duzelt(satir, "no", "990000008")
    assert k.girmeyen_tablo.rowCount() == 3 and k.duzeltme_tablo.rowCount() == 1
    pencere.adim_listesi.setCurrentRow(4)
    ist = pencere.adimlar[4]
    assert pencere.yigin.currentIndex() == 4 and ist.madde.rowCount() == 10 and "Kısaca" in ist.yorum.text()
    assert ist.cikti.rowCount() == 3  # Ö01, Ö02, Ö03
    pencere.adim_listesi.setCurrentRow(3)
    e = pencere.adimlar[3]
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
    assert not _hazir(pencere)  # B anahtarı boş
    a.hizli.setText("EDCBAEDCBA")
    a._hizli_uygula()
    assert d.proje.anahtar.kitapcik_anahtarlari["B"] == "EDCBAEDCBA"
    a.satirlar[0].esleme.setValue(2)
    a.satirlar[1].esleme.setValue(1)
    assert d.proje.anahtar.esleme("B")[1] == 2 and _hazir(pencere)


def test_klasik_sinav_arayuzu(pencere, fix, tmp_path):
    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1.ders_kodu.setText("UYD1001")
    p1.bicim_klasik.setChecked(True)
    assert d.proje.klasik and not _hazir(pencere)  # liste yok
    p1._liste_ac(str(fix / "uydurma_liste.xlsx"))
    p1.klasik_sayi.setValue(4)
    assert d.proje.anahtar.soru_sayisi == 4 and _hazir(pencere)
    pencere.sonraki.click()
    a = pencere.adimlar[1]
    assert [s.puan for s in d.proje.anahtar.sorular] == ["25", "25", "25", "25"]
    assert a.satirlar[0].kabarciklar == {} and _hazir(pencere)
    a.satirlar[3].puan.setValue(40)
    a.satirlar[0].puan.setValue(10)
    assert _hazir(pencere)  # 10 + 25 + 25 + 40 = 100
    pencere.sonraki.click()
    k = pencere.adimlar[2]
    assert "Puan girişi" in k.baslik_etiketi.text() and pencere.adim_listesi.item(2).text().startswith("3. Puan girişi")
    m = k.klasik_model
    assert m.rowCount() == len(d.liste.ogrenciler) and m.columnCount() == 3 + 4 + 3  # + Toplam, Kâğıttaki toplam, Girmedi
    assert not _hazir(pencere)  # puan yok
    m.setData(m.index(0, 3), "10")
    m.setData(m.index(0, 4), "12,5")
    m.setData(m.index(1, 6), "40")
    assert d.sonuc.klasik and len(d.sonuc.ogrenciler) == 2
    o = d.sonuc.no_ile()[d.liste.ogrenciler[0].no]
    assert float(o.puan) == 22.5
    assert _hazir(pencere)
    pencere.sonraki.click()
    pencere.sonraki.click()
    d.kaydet(str(tmp_path / "k.osd"))
    from optik_sinav.ui.ana_pencere import AnaPencere

    p2 = AnaPencere()
    p2.proje_ac(str(tmp_path / "k.osd"))
    assert p2.durum.proje.klasik and p2.durum.proje.klasik_puanlar[d.liste.ogrenciler[0].no][:2] == ["10", "12,5"]
    p2.close()


def test_istatistik_yeni_sekmeler(pencere, fix):
    d = pencere.durum
    pencere.adimlar[0].ders_kodu.setText("UYD1001")
    pencere.adimlar[0]._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    pencere.adimlar[0]._liste_ac(str(fix / "uydurma_liste.xlsx"))
    pencere.sonraki.click()
    a = pencere.adimlar[1]
    a.hizli.setText("ABCDEABCDE")
    a._hizli_uygula()
    for _ in range(3):
        pencere.sonraki.click()
    ist = pencere.adimlar[4]
    assert "Sınav" in ist.yapi.toPlainText() or "en az 10" in ist.yapi.toPlainText()
    d.proje.final_puanlar = {o.no: "70" for o in d.sonuc.ogrenciler}
    ist.donem.yenile()
    assert ist.donem.tablo.rowCount() == len(d.sonuc.ogrenciler) and "Uygulanan" in ist.donem.ozet.text()
    ist.donem.tablo.item(0, 3).setText("20")
    assert d.proje.final_puanlar[ist.donem.tablo.item(0, 0).text()] == "20"
    assert ist.donem.donem() is not None


def test_kagit_sirasiyla_giris(pencere, fix):
    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1.ders_kodu.setText("UYD1001")
    p1.bicim_klasik.setChecked(True)
    p1._liste_ac(str(fix / "uydurma_liste.xlsx"))
    p1.klasik_sayi.setValue(3)
    pencere.sonraki.click()
    pencere.sonraki.click()
    k = pencere.adimlar[2]
    panel = k.kagit
    assert len(panel.kutular) == 3
    hedef = d.liste.ogrenciler[2]
    bulunan = panel.bul(hedef.ad.split()[0][:3].lower())
    assert hedef in bulunan
    panel.sec(hedef)
    for e, x in zip(panel.kutular, ["30", "20,5", "10"]):
        e.setText(x)
    panel.toplam.setText("61")
    panel.kaydet()
    o = d.sonuc.no_ile()[hedef.no]
    assert float(o.puan) == 60.5 and any("tutmuyor" in u.mesaj for u in o.uyarilar)
    assert panel.secili is None and "Girilen: 1 ·" in panel.kalan.text()
    m = k.klasik_model
    assert m.data(m.index(2, 3 + 3 + 1)) == "61"


def test_serbest_gezinme_ve_eksik_seridi(pencere):
    """Boş projede 6. adıma doğrudan gidilir; sonuç hesaplanmaz, üstteki şerit eksikleri ve adımlarını gösterir."""
    pencere.adim_listesi.setCurrentRow(4)
    assert pencere.yigin.currentIndex() == 4
    assert pencere.durum.sonuc is None
    assert not pencere.serit.isHidden() and "1. adım" in pencere.serit.text()
    pencere.adim_listesi.setCurrentRow(0)
    assert pencere.serit.isHidden()
    assert pencere.adimlar[0].dat_dugmesi.styleSheet()  # zorunlu dosya düğmesi vurgulu


def test_otomatik_kayit_ve_kurtarma(pencere, fix, tmp_path, monkeypatch):
    """Klasik sınavda girilen puanlar kendiliğinden kaydedilir; liste dosyası silinse bile açılışta geri gelir."""
    import shutil

    from PySide6.QtWidgets import QMessageBox

    from optik_sinav.ui.ana_pencere import AnaPencere
    from optik_sinav.ui.durum import kurtarma_ozeti, kurtarma_yolu

    liste = tmp_path / "sinif.xlsx"
    shutil.copy(fix / "uydurma_liste.xlsx", liste)
    d = pencere.durum
    assert not d.otomatik_kaydet()  # boş proje kaydedilmez
    p1 = pencere.adimlar[0]
    p1.bicim_klasik.setChecked(True)
    p1._liste_ac(str(liste))
    p1.klasik_sayi.setValue(3)
    pencere.adim_listesi.setCurrentRow(2)
    m = pencere.adimlar[2].klasik_model
    m.setData(m.index(0, 3), "20")
    m.setData(m.index(1, 5), "7,5")
    pencere.otomatik_kaydet()
    assert kurtarma_yolu().exists()
    assert not d.otomatik_kaydet()  # değişiklik yoksa yeniden yazmaz
    o = kurtarma_ozeti()
    assert o["klasik"] and o["puanli"] == 2
    ilk_no = d.liste.ogrenciler[0].no

    liste.unlink()  # özgün liste kayboldu: gömülü kopyadan açılmalı
    yeni = AnaPencere()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    assert yeni.kurtarmayi_sor()
    d2 = yeni.durum
    assert d2.proje.klasik and d2.liste is not None and len(d2.liste.ogrenciler) == len(d.liste.ogrenciler)
    assert d2.proje.klasik_puanlar[ilk_no][0] == "20"
    assert yeni.yigin.currentIndex() == 2  # doğrudan puan girişine
    assert d2.proje_yolu is None  # kurtarma dosyası "Kaydet" hedefi olmaz
    yeni.close()

    # "Hayır": çalışma silinmez, yedeklenir
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    ucuncu = AnaPencere()
    assert not ucuncu.kurtarmayi_sor()
    assert not kurtarma_yolu().exists()
    assert list((kurtarma_yolu().parent / "yedekler").glob("son_calisma_*.osd"))
    ucuncu.close()


def test_kayitli_dosyaya_otomatik_yazar(pencere, fix, tmp_path):
    """Sınav bir dosyaya kaydedildiyse sonraki değişiklikler o dosyaya da kendiliğinden yazılır."""
    import json

    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1.bicim_klasik.setChecked(True)
    p1._liste_ac(str(fix / "uydurma_liste.xlsx"))
    hedef = d.kaydet(str(tmp_path / "ara.osd"))
    d.klasik_puan_yaz(d.liste.ogrenciler[0].no, 0, "15")
    assert d.otomatik_kaydet()
    v = json.loads(hedef.read_text(encoding="utf-8"))
    assert v["klasik_puanlar"][d.liste.ogrenciler[0].no][0] == "15"
    assert v["gomulu_dosyalar"]["liste"]


def test_birakilan_pdf_liste_olarak_okunur(pencere, fix):
    """Ders bilgi paketi olmayan PDF öğrenci listesi sayılır; klasik sınavda puan girişine geç düğmesi çıkar."""
    p1 = pencere.adimlar[0]
    p1.bicim_klasik.setChecked(True)
    p1._pdf_ac(str(fix / "uydurma_liste.pdf"))
    assert pencere.durum.liste is not None and len(pencere.durum.liste.ogrenciler) == 12
    assert not p1.giris_dugmesi.isHidden()
    p1.giris_dugmesi.click()
    assert pencere.yigin.currentIndex() == 2


def test_klasik_sorular_ve_puanlar(pencere, fix, monkeypatch):
    """Klasik sınavda puan dizisi tek satırdan girilir; soru eklenir ve çıkarılır, girilmiş puanlar silinmez."""
    from PySide6.QtWidgets import QMessageBox

    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1.bicim_klasik.setChecked(True)
    p1._liste_ac(str(fix / "uydurma_liste.xlsx"))
    pencere.adim_listesi.setCurrentRow(1)
    a = pencere.adimlar[1]
    assert "Sorular ve puanlar" in a.baslik_etiketi.text()
    assert pencere.adim_listesi.item(1).text().startswith("2. Sorular ve puanlar")
    a.hizli.setText("10 10 10 10 20 40")
    a._hizli_uygula()
    assert d.proje.klasik_soru_sayisi == 6 and p1.klasik_sayi.value() == 6
    assert [s.puan for s in d.proje.anahtar.sorular] == ["10", "10", "10", "10", "20", "40"]
    assert "✓" in a.puan_ozeti.text()
    a._soru_ekle()
    assert d.proje.anahtar.soru_sayisi == 7 and "puanı girilmemiş soru: 7" in a.puan_ozeti.text()
    a._soru_cikar()
    no = d.liste.ogrenciler[0].no
    d.klasik_puan_yaz(no, 5, "35")
    monkeypatch.setattr(QMessageBox, "question", lambda *x, **k: QMessageBox.StandardButton.No)
    a._soru_cikar()  # 6. soruda puan var, vazgeçildi
    assert d.proje.anahtar.soru_sayisi == 6
    monkeypatch.setattr(QMessageBox, "question", lambda *x, **k: QMessageBox.StandardButton.Yes)
    a._soru_cikar()
    assert d.proje.anahtar.soru_sayisi == 5 and d.proje.klasik_puanlar[no][5] == "35"  # silinmedi
    a.hizli.setText("10 abc")
    monkeypatch.setattr(QMessageBox, "warning", lambda *x, **k: None)
    a._hizli_uygula()
    assert d.proje.anahtar.soru_sayisi == 5


def test_klasik_yeni_istatistik_sekmeleri(pencere, fix):
    """Puan girildikçe giriş sırası kaydedilir; 5. adımda notu belirleyen sorular ve klasik puanlama sekmeleri dolar."""
    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1.bicim_klasik.setChecked(True)
    p1._pdf_ac(str(fix / "uydurma_liste.pdf"))
    d.klasik_puanlarini_yaz(["40", "30", "30"])
    nolar = [o.no for o in d.liste.ogrenciler]
    sira = list(reversed(nolar))
    for i, no in enumerate(sira):
        d.klasik_puan_yaz(no, 0, str(40 - 3 * i))
        d.klasik_puan_yaz(no, 1, "20")
        d.klasik_puan_yaz(no, 2, str(10 + (i % 3)))
    d.klasik_puan_yaz(sira[0], 0, "39")  # düzeltme sırayı değiştirmez
    assert d.proje.klasik_giris_sirasi == sira
    pencere.adim_listesi.setCurrentRow(4)
    ist = pencere.adimlar[4]
    assert "en büyük katkı 1. sorudan" in ist.belirleyen.toPlainText()
    assert ist.uygun[id(ist.puanlama)] and not ist.uygun[id(ist.kavram)]  # klasikte menüde puanlama var, kavram yok
    ist._diger_menuyu_doldur()
    assert "Puanlama (klasik)" in [e.text() for e in ist.diger_menu.actions()]
    ist.analiz_ac(ist.puanlama)
    assert ist.sekmeler.currentWidget() is ist.puanlama and ist.sekmeler.isTabVisible(ist.sekmeler.indexOf(ist.puanlama))
    assert [ist.sekmeler.tabText(i) for i in range(3)] == ["Madde analizi", "Öğrenme çıktıları", "Dönem sonu notu"]
    metin = ist.puanlama.toPlainText()
    assert "Okuma ilerledikçe puanlar düşüyor" in metin and "Kısmi puan profili" in metin


def test_sinava_girmedi_isareti(pencere, fix, tmp_path, monkeypatch):
    """Puan tablosunda "Girmedi" kutusu; işaretli öğrenci puanı olsa bile girmeyen sayılır, Excel'e yazılır ve geri okunur."""
    import openpyxl
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1.bicim_klasik.setChecked(True)
    p1._liste_ac(str(fix / "uydurma_liste.xlsx"))
    d.klasik_puanlarini_yaz(["50", "50"])
    pencere.adim_listesi.setCurrentRow(2)
    k = pencere.adimlar[2]
    m = k.klasik_model
    no0, no1 = d.liste.ogrenciler[0].no, d.liste.ogrenciler[1].no
    m.setData(m.index(0, 3), "40")
    m.setData(m.index(1, 3), "30")
    assert m.data(m.index(2, 3 + 2)) == "—"  # henüz girilmedi
    m.setData(m.index(1, m.girmedi_sutunu), Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole)
    assert d.proje.klasik_girmedi == [no1]
    assert m.data(m.index(1, 3 + 2)) == "sınava girmedi"
    for j in range(m.columnCount()):  # gri satırın bütün hücreleri hatasız çizilebilmeli
        m.data(m.index(1, j), Qt.ItemDataRole.BackgroundRole)
        m.data(m.index(1, j), Qt.ItemDataRole.ForegroundRole)
    assert m.data(m.index(1, 0), Qt.ItemDataRole.BackgroundRole) is not None
    assert no1 in [g.no for g in d.sonuc.girmeyenler] and [o.no for o in d.sonuc.ogrenciler] == [no0]
    assert d.proje.klasik_puanlar[no1][0] == "30"  # puan silinmedi
    # kâğıt paneliyle işaretleme
    panel = k.kagit
    panel.sec(d.liste.ogrenciler[2])
    panel.girmedi()
    assert d.liste.ogrenciler[2].no in d.proje.klasik_girmedi and "Girmedi: 2" in panel.kalan.text()
    # Excel'e kaydet ve geri oku
    yol = tmp_path / "puanlar.xlsx"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **kw: (str(yol), "")))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **kw: (str(yol), "")))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **kw: None))
    k._sablon_yaz()
    ws = openpyxl.load_workbook(yol).active
    basliklar = [c.value for c in ws[1]]
    assert basliklar[-2:] == ["Toplam", "Girmedi"] and basliklar[2] == "S1 (50)"
    assert ws.cell(row=2, column=3).value == 40 and ws.cell(row=2, column=5).value == 40
    assert ws.cell(row=3, column=6).value == "girmedi"
    d.proje.klasik_girmedi.clear()
    k._excelden_al()
    assert sorted(d.proje.klasik_girmedi) == sorted([no1, d.liste.ogrenciler[2].no])


def test_sisteme_aktar_adimi(pencere, fix, monkeypatch):
    """4. adım: öğrenci puanları ve not girişi için panoya kopyalama; uyarılar en üstte; gelişmiş bölüm katlı."""
    from PySide6.QtGui import QGuiApplication

    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    p1._liste_ac(str(fix / "uydurma_liste.xlsx"))
    pencere.adim_listesi.setCurrentRow(1)
    a = pencere.adimlar[1]
    a.hizli.setText("ABCDEABCDE")
    a._hizli_uygula()
    pencere.adim_listesi.setCurrentRow(2)
    k = pencere.adimlar[2]
    assert k.duzeltilecek_kutusu.isVisibleTo(k) and k.duzeltilecekler.count() == sum(1 for o in d.sonuc.ogrenciler if o.uyarilar)
    k._duzeltilecege_git(k.duzeltilecekler.item(0))
    assert k.sekmeler.currentWidget() is k.tablo and k.tablo.selectionModel().hasSelection()
    pencere.adim_listesi.setCurrentRow(3)
    e = pencere.adimlar[3]
    assert not e.gelismis.isVisibleTo(e) and e.bilgi.isVisibleTo(e)  # aynı numara iki satırda: uyarı üstte
    from PySide6.QtWidgets import QMessageBox

    from optik_sinav.export.sistem_puan_dosyasi import akreditasyon_satirlari

    monkeypatch.setattr(QMessageBox, "information", lambda *x, **k: None)
    e._ogrenci_puanlarini_kopyala()
    satirlar = QGuiApplication.clipboard().text().splitlines()
    assert [x.split("\t") for x in satirlar] == akreditasyon_satirlari(d.sonuc) and len(satirlar[0].split("\t")) == 1 + 10
    e._notlari_kopyala()
    assert len(QGuiApplication.clipboard().text().splitlines()[0].split("\t")) == 2
    assert "kopyalandı" in e.durum_satiri.text()


def test_ogrenme_ciktilari_varsayilan_esit(pencere, fix, monkeypatch):
    """Ders çıktıları biliniyorsa sorulara kendiliğinden eşit dağıtılır; soru sayısı değişse de eşit kalır;
    hoca bir soruyu değiştirince dokunulmaz; "Yeniden eşit dağıt" eşit dağıtıma döner."""
    from PySide6.QtWidgets import QMessageBox

    from optik_sinav.core.madde_analizi import cikti_atamasi_esit_mi
    from optik_sinav.core.proje import SinavProjesi

    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1.bicim_klasik.setChecked(True)
    p1.ders_kodu.setText("EKF4507")  # programla gelen ders paketi: 6 öğrenme çıktısı
    p1._liste_ac(str(fix / "uydurma_liste.xlsx"))
    pencere.adim_listesi.setCurrentRow(1)
    a = pencere.adimlar[1]
    kodlar = d.ogrenme_kodlari()
    assert len(kodlar) == 6 and cikti_atamasi_esit_mi(d.proje.anahtar, kodlar)
    assert "eşit dağıtıldı" in a.cikti_bilgi.text() and not a.esit_dagit_dugmesi.isVisibleTo(a)
    a.hizli.setText("10 10 10 10 20 40")
    a._hizli_uygula()  # 6 soru: her soru bir çıktıya
    assert [s.ogrenme_ciktilari for s in d.proje.anahtar.sorular] == [[k] for k in kodlar]
    a._soru_ekle()  # 7 soru: yine eşit
    assert d.proje.anahtar.soru_sayisi == 7 and cikti_atamasi_esit_mi(d.proje.anahtar, kodlar)
    a.satirlar[0].oc.setText("2")
    a._oc_degisti(0)  # hoca değiştirdi
    assert d.proje.cikti_elle and d.proje.anahtar.sorular[0].ogrenme_ciktilari == ["Ö02"]
    a._soru_cikar()
    assert d.proje.anahtar.sorular[0].ogrenme_ciktilari == ["Ö02"]  # dokunulmadı
    assert "elle düzenlendi" in a.cikti_bilgi.text() and a.esit_dagit_dugmesi.isVisibleTo(a)
    monkeypatch.setattr(QMessageBox, "question", lambda *x, **k: QMessageBox.StandardButton.Yes)
    a._sirayla_dagit()
    assert not d.proje.cikti_elle and cikti_atamasi_esit_mi(d.proje.anahtar, kodlar)
    # eski dosya (alan yok, çıktı girilmiş): hocanın girdiği sayılır
    sozluk = d.proje.to_dict()
    sozluk.pop("cikti_elle")
    assert SinavProjesi.from_dict(sozluk).cikti_elle


def test_sinav_kimligi_seridi(pencere, fix, tmp_path):
    """Her adımın üstünde sınav kimliği; pencere başlığında kısa ad; son açılanlarda okunur ad; ders değişince güncellenir."""
    from optik_sinav.ui.durum import osd_okunur_adi

    d = pencere.durum
    assert "Yeni sınav" in pencere.kimlik.text() and pencere.windowTitle().startswith("Yeni sınav")
    p1 = pencere.adimlar[0]
    p1._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    assert "Adsız sınav · uydurma_1254_crlf.dat" in pencere.kimlik.text() and "11 öğrenci, 10 soru" in pencere.kimlik.text()
    p1.ders_kodu.setText("EKF4507")
    assert "<b>EKF4507 Sermaye Piyasası ve Portföy Yönetimi</b>" in pencere.kimlik.text()
    assert pencere.windowTitle().startswith("EKF4507 Ara Sınav")
    pencere.adim_listesi.setCurrentRow(3)
    assert pencere.kimlik.isVisibleTo(pencere)  # her adımda görünür
    yol = d.kaydet(str(tmp_path / "s.osd"))
    assert osd_okunur_adi(str(yol)).startswith("EKF4507 Ara Sınav (") and osd_okunur_adi(str(yol)).endswith("— s.osd")
    p1.ders_kodu.setText("UTL4513")  # başka derse geçildi
    assert "UTL4513" in pencere.kimlik.text() and pencere.windowTitle().startswith("UTL4513")


def test_ders_paketi_yokken_cikti_sayisi(pencere, fix, monkeypatch, tmp_path):
    """Ders bilgi paketi yokken (ders kodu boş) sisteme giriş dosyaları istenince öğrenme çıktısı sayısı sorulur,
    çıktılar eşit dağıtılır ve soru tanımı yazılır; 2. adımdaki sayı kutusu aynı işi görür ve dosyaya kaydedilir."""
    from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

    from optik_sinav.core.madde_analizi import cikti_atamasi_esit_mi, sayidan_cikti_kodlari
    from optik_sinav.core.proje import SinavProjesi

    assert sayidan_cikti_kodlari(3) == ["Ö01", "Ö02", "Ö03"] and sayidan_cikti_kodlari(0) == []
    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    p1._liste_ac(str(fix / "uydurma_liste.xlsx"))
    pencere.adim_listesi.setCurrentRow(1)
    a = pencere.adimlar[1]
    a.hizli.setText("ABCDEABCDE")
    a._hizli_uygula()
    assert d.ders is None and d.ogrenme_kodlari() == [] and a.cikti_sayisi_kutusu.isVisibleTo(a)
    assert "bilinmiyor" in a.cikti_bilgi.text()
    pencere.adim_listesi.setCurrentRow(3)
    e = pencere.adimlar[3]
    assert "öğrenme çıktısı sayısı sorulacak" in e.bilgi.text()
    monkeypatch.setattr(QInputDialog, "getInt", lambda *x, **k: (4, True))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *x, **k: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "information", lambda *x, **k: None)
    e._giris_dosyalari()
    assert d.proje.cikti_sayisi == 4 and cikti_atamasi_esit_mi(d.proje.anahtar, ["Ö01", "Ö02", "Ö03", "Ö04"])
    st = list(tmp_path.glob("*_soru_tanimi.xlsx"))
    assert len(st) == 1
    from openpyxl import load_workbook

    satirlar = [[c.value for c in r] for r in load_workbook(st[0])["Aktarım"].iter_rows()]
    assert len(satirlar) == 10 and satirlar[0][3] == "1" and satirlar[-1][3] == "4" and satirlar[0][4] == "100"
    assert SinavProjesi.from_dict(d.proje.to_dict()).cikti_sayisi == 4
    # 2. adımdaki kutu: sayı değişince yeniden eşit dağıtılır
    pencere.adim_listesi.setCurrentRow(1)
    assert a.cikti_sayisi_kutusu.value() == 4
    a.cikti_sayisi_kutusu.setValue(2)
    assert cikti_atamasi_esit_mi(d.proje.anahtar, ["Ö01", "Ö02"]) and "eşit dağıtıldı" in a.cikti_bilgi.text()


def test_sistem_puan_dosyasi_doldurma(pencere, fix, monkeypatch, tmp_path):
    """4. adım "2. Sistemin puan dosyasını doldur…": sistemden indirilen CSV seçilir, doldurulmuş hâli aynı biçimde kaydedilir."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    p1 = pencere.adimlar[0]
    p1._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    p1._liste_ac(str(fix / "uydurma_liste.xlsx"))
    pencere.adim_listesi.setCurrentRow(1)
    a = pencere.adimlar[1]
    a.hizli.setText("ABCDEABCDE")
    a._hizli_uygula()
    pencere.adim_listesi.setCurrentRow(3)
    e = pencere.adimlar[3]
    nolar = [o.no for o in pencere.durum.sonuc.ogrenciler if o.listede][:3]
    girdi = tmp_path / "FILE_x.csv"
    girdi.write_bytes(("Öğrenci No;Adı;Girme Durum;" + ";".join(f"Soru{i}(%10)" for i in range(1, 11)) + ";Sınav Notu\r\n"
                       + "".join(f"{n}\xa0;AD;Girdi;" + ";" * 10 + "\r\n" for n in nolar)).encode("cp1254"))
    cikti = tmp_path / "dolu.csv"
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *x, **k: (str(girdi), ""))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *x, **k: (str(cikti), ""))
    mesaj = []
    monkeypatch.setattr(QMessageBox, "information", lambda *x, **k: mesaj.append(x[2]))
    e._sistem_dosyasi()
    satir = cikti.read_bytes().decode("cp1254").split("\r\n")[1].split(";")
    assert satir[0] == nolar[0] + "\xa0" and satir[2] == "Girdi" and all(x in ("0", "10") for x in satir[3:13])
    assert "Puanı yazılan öğrenci: 3" in mesaj[0]


def test_bonus_soru_numarayla(pencere, fix):
    """Bonus soru, açılır kutu yerine "Bonus soru" alanına numara yazılarak da seçilir; boşaltınca kalkar."""
    from optik_sinav.core.modeller import SoruDurumu

    d = pencere.durum
    pencere.adimlar[0]._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    pencere.adim_listesi.setCurrentRow(1)
    a = pencere.adimlar[1]
    a.hizli.setText("ABCDEABCDE")
    a._hizli_uygula()
    assert a.bonus_satiri.isVisibleTo(a)
    a.bonus.setText("10")
    a._bonus_degisti()
    assert d.proje.anahtar.sorular[9].durum == SoruDurumu.BONUS and len(d.proje.anahtar.aktarim_sorulari()) == 9
    assert a.satirlar[9].durum.deger() == "bonus" and "bonus" in pencere.kimlik.text().lower()
    a.bonus.setText("")
    a._bonus_degisti()
    assert all(s.durum == SoruDurumu.NORMAL for s in d.proje.anahtar.sorular)


def test_soru_durumu_dugmesi(pencere, fix):
    """Soru durumu açılır liste değil, tıkladıkça değişen düğme (macOS'ta görünmeyen açılır liste sorunu)."""
    from optik_sinav.core.modeller import SoruDurumu

    d = pencere.durum
    pencere.adimlar[0]._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    pencere.adim_listesi.setCurrentRow(1)
    a = pencere.adimlar[1]
    a.hizli.setText("ABCDEABCDE")
    a._hizli_uygula()
    b = a.satirlar[3].durum
    assert b.text() == "Normal"
    sira = []
    for _ in range(4):
        b = a.satirlar[3].durum
        b.click()
        sira.append(d.proje.anahtar.sorular[3].durum)
    assert sira == [SoruDurumu.IPTAL, SoruDurumu.COKLU, SoruDurumu.BONUS, SoruDurumu.NORMAL]
    a.satirlar[3].durum.click()
    assert a.satirlar[3].durum.text().startswith("İptal")


def test_sistemden_liste_ve_otomatik_numara(pencere, fix, monkeypatch):
    """1. adımda sistemin öğrenci tablosu yapıştırılır; listede olmayan numara adla düzeltilir; 3. adımda geri alınır."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "information", lambda *x, **k: None)
    d = pencere.durum
    p1 = pencere.adimlar[0]
    p1._dat_ac(str(fix / "uydurma_1254_crlf.dat"))
    from optik_sinav.io.liste_okuyucu import liste_oku

    l = liste_oku(fix / "uydurma_liste.xlsx")
    tablo = "#\t Öğrenci No\tAdı\tSoyadı\tSnf\n" + "".join(
        f"{i}\t{o.no}\t{' '.join(o.ad.split()[:-1])}\t{o.ad.split()[-1]}\t4\t\nGirdi\n6,25\n" for i, o in enumerate(l.ogrenciler, 1))
    p1._listeyi_yapistir(tablo)
    assert d.liste is not None and len(d.liste.ogrenciler) == len(l.ogrenciler)
    assert d.proje.liste_yolu.endswith(".txt") and "sistem_listesi" in d.proje.liste_yolu
    pencere.adim_listesi.setCurrentRow(1)
    a = pencere.adimlar[1]
    a.hizli.setText("ABCDEABCDE")
    a._hizli_uygula()
    pencere.adim_listesi.setCurrentRow(2)
    k = pencere.adimlar[2]
    s = d.sonuc
    o = next(x for x in s.ogrenciler if x.kayit.ogrenci_no == "990000088")
    assert o.no == "990000008" and not s.listede_olmayanlar
    sira = next(i for i in range(k.duzeltilecekler.count()) if "990000008 " in k.duzeltilecekler.item(i).text())
    k.duzeltilecekler.setCurrentRow(sira)
    k._duzeltilecege_git(k.duzeltilecekler.item(sira))
    assert k.geri_al.isVisibleTo(k)
    k._otomatigi_geri_al()
    assert o.kayit.satir_no in d.proje.otomatik_kapali
    assert next(x for x in d.sonuc.ogrenciler if x.kayit.ogrenci_no == "990000088").no == "990000088"
