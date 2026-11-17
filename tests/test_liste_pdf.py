"""PDF öğrenci listesi (sınav yoklama listesi) okuma. Bütün veriler uydurmadır (tools/fixture_uret.py)."""
import json
from pathlib import Path

from optik_sinav.io.liste_okuyucu import liste_oku, pdf_hucrelerinden_tablo

KOK = Path(__file__).resolve().parents[1]


def test_pdf_listesi_okunur(fix):
    l = liste_oku(fix / "uydurma_liste.pdf")
    assert len(l.ogrenciler) == 12
    assert (l.ogrenciler[0].no, l.ogrenciler[0].ad) == ("990000001", "ÇİĞDEM ÖZTÜRK")
    assert l.ogrenciler[-1].ad == "İSMAİL KOÇ"  # program sütunu ada karışmaz
    assert all("İŞLETME" not in o.ad for o in l.ogrenciler)


def test_pdf_ornekleri_tarayici_ile_ortak():
    """tests/web/liste_pdf.json tarayıcı sürümünde de (web/test/parite.mjs) aynı sonucu vermeli."""
    for o in json.loads((KOK / "tests/web/liste_pdf.json").read_text(encoding="utf-8")):
        assert pdf_hucrelerinden_tablo(o["girdi"]) == o["beklenen"]


def test_ayri_ad_soyad_ve_tekrar():
    t = pdf_hucrelerinden_tablo([["No", "Öğrenci No", "Adı", "Soyadı"], ["1", "220101001", "Ayşe", "Yılmaz"],
                                 ["2", "220101001", "Ayşe", "Yılmaz"], ["Toplam: 2"]])
    assert t == [["Öğrenci No", "Adı Soyadı"], ["220101001", "Ayşe Yılmaz"]]


def test_resim_pdf_anlasilir_hata(tmp_path):
    import pytest
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    yol = tmp_path / "bos.pdf"
    with open(yol, "wb") as f:
        w.write(f)
    with pytest.raises(ValueError, match="öğrenci numarası bulunamadı"):
        liste_oku(yol)


def test_sistem_tablosundan_liste():
    """Akademik Bilgi Sistemi'nin ekrandan kopyalanan öğrenci tablosu (puan satırları araya karışmış) listeye çevrilir."""
    from optik_sinav.io.liste_okuyucu import sistem_tablosu_coz

    m = ('Ad Soyad \n \n  \n#\t Öğrenci No\tAdı\tSoyadı\tSnf\tGirme Durum\tSoru1\n(%6,25)\tSoru2\n(%6,25)\tSınav Notu\n1\t990000001\tÇİĞDEM\tÖZTÜRK\t4\t\nGirdi\n6,25\n6,25\n12,5\n2\t990000002\tŞÜKRÜ\tIŞIK\t4\t\nGirdi\n \n3\t2641064003\tAHMET YUSUF\tPEKER\t1\t\nGirmedi\n0\n4\t990000002\tŞÜKRÜ\tIŞIK\t4\t\n')
    assert sistem_tablosu_coz(m) == [["Öğrenci No", "Adı Soyadı"], ["990000001", "ÇİĞDEM ÖZTÜRK"], ["990000002", "ŞÜKRÜ IŞIK"],
                                     ["2641064003", "AHMET YUSUF PEKER"]]
    assert sistem_tablosu_coz("990000005;AYŞE;KARA;2")[1] == ["990000005", "AYŞE KARA"]
    assert sistem_tablosu_coz("") == [["Öğrenci No", "Adı Soyadı"]]
