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
