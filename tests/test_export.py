"""Dışa aktarma profilleri. Metin çıktılarında bayt bayt altın dosya karşılaştırması yapılır.

xlsx dosyaları zip zaman damgası ve belge özellikleri taşıdığı için bayt bayt değil,
hücre değeri, türü ve sayı biçimi düzeyinde altın dosyayla karşılaştırılır.
Altın dosyaları yenilemek için: ALTIN_GUNCELLE=1 pytest tests/test_export.py
"""
import json
import os
from dataclasses import replace

import openpyxl
import pytest

from optik_sinav.core.dogrulama import sinavi_degerlendir
from optik_sinav.core.modeller import CevapAnahtari, OkuyucuSablonu, PuanlamaAyarlari, SinavBilgisi
from optik_sinav.export.csv_yazici import csv_yaz
from optik_sinav.export.pano import pano_metni
from optik_sinav.export.profil import Profil, profil_bul, profilleri_listele
from optik_sinav.export.raporlar import tum_raporlari_yaz
from optik_sinav.export.sablon_doldurucu import numara_sirasi, sablondan_profil_oner, sablonu_doldur
from optik_sinav.export.xlsx_yazici import profil_xlsx_yaz
from optik_sinav.io.dat_okuyucu import dat_oku
from optik_sinav.io.liste_okuyucu import liste_oku

from conftest import GOLDEN

GUNCELLE = os.environ.get("ALTIN_GUNCELLE") == "1"
SINAV = SinavBilgisi(ders_kodu="UYD1001", ders_adi="Uydurma Ders", sinav_turu="Ara Sınav", tarih="2026-11-10")


@pytest.fixture
def sonuc(fix):
    okuma = dat_oku(fix / "uydurma_1254_crlf.dat", OkuyucuSablonu(soru_sayisi=10))
    liste = liste_oku(fix / "uydurma_liste.xlsx")
    return sinavi_degerlendir(okuma.kayitlar, CevapAnahtari.metinden("ABCDEABCDE"), PuanlamaAyarlari(), liste)


def altin_bayt(ad, veri: bytes):
    yol = GOLDEN / ad
    if GUNCELLE or not yol.exists():
        yol.write_bytes(veri)
    assert veri == yol.read_bytes(), f"{ad} altın dosyadan farklı"


def xlsx_ozeti(yol):
    wb = openpyxl.load_workbook(yol)
    return {ws.title: [[(c.value, c.data_type, c.number_format) for c in r] for r in ws.iter_rows()] for ws in wb}


def altin_xlsx(ad, yol):
    ozet = json.loads(json.dumps(xlsx_ozeti(yol), ensure_ascii=False))
    altin = GOLDEN / (ad + ".json")
    if GUNCELLE or not altin.exists():
        altin.write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    assert ozet == json.loads(altin.read_text(encoding="utf-8"))


def test_varsayilan_profiller_var():
    p = profilleri_listele()
    assert {"akreditasyon_soru_bazli_varsayilan", "not_giris_varsayilan", "not_giris_csv_ornek"} <= set(p)


def test_profil_json_gidis_donus():
    p = profil_bul("akreditasyon_soru_bazli_varsayilan")
    assert Profil.from_dict(json.loads(json.dumps(p.to_dict()))) == p


def test_csv_altin(sonuc, tmp_path):
    yol = csv_yaz(profil_bul("not_giris_csv_ornek"), sonuc, tmp_path / "x.csv")
    veri = yol.read_bytes()
    assert b"\r\n" in veri and "Öğrenci No".encode("cp1254") in veri
    altin_bayt("not_giris_csv_ornek.csv", veri)


def test_csv_secenekleri(sonuc, tmp_path):
    p = replace(profil_bul("not_giris_csv_ornek"), kodlama="utf-8", ayrac="\\t", satir_sonu="LF", ondalik_ayirici=".",
                girmedi_gosterimi="-1", ogrenci_no_bicimi="sayi")
    metin = csv_yaz(p, sonuc, tmp_path / "y.txt").read_bytes().decode("utf-8")
    satirlar = metin.split("\n")
    assert "\r" not in metin and satirlar[0] == "Öğrenci No\tAd Soyad\tPuan"
    assert satirlar[1] == "990000001\tÇİĞDEM ÖZTÜRK\t100.00"
    assert "990000011\tGÜL ÖZDEMİR\t-1" in satirlar
    altin_bayt("not_giris_tab_lf_utf8.txt", metin.encode("utf-8"))


def test_akreditasyon_xlsx_altin(sonuc, tmp_path):
    yol = profil_xlsx_yaz(profil_bul("akreditasyon_soru_bazli_varsayilan"), sonuc, tmp_path / "a.xlsx", SINAV)
    ws = openpyxl.load_workbook(yol).active
    assert [c.value for c in ws[1]][:4] == ["Öğrenci No", "Ad Soyad", "S1", "S2"]
    assert ws["A2"].data_type == "s" and ws["A2"].value == "990000001"
    assert ws["C2"].value == 10 and ws["C2"].number_format == "0.00"
    altin_xlsx("akreditasyon_soru_bazli_varsayilan.xlsx", yol)


def test_not_giris_xlsx_altin(sonuc, tmp_path):
    yol = profil_xlsx_yaz(profil_bul("not_giris_varsayilan"), sonuc, tmp_path / "n.xlsx", SINAV)
    satirlar = list(openpyxl.load_workbook(yol).active.iter_rows(values_only=True))
    # Liste sırası; girmeyenlerde "G"; listede olmayanlar yazılmaz
    assert len(satirlar) == 13
    assert satirlar[4] == ("990000004", "MEHMET ÇAKIR", "G")
    altin_xlsx("not_giris_varsayilan.xlsx", yol)


def test_sablondan_profil_ve_doldurma(fix, sonuc, tmp_path):
    p = sablondan_profil_oner(fix / "uydurma_sablon.xlsx")
    assert p.sablon.baslik_satiri == 3 and p.sablon.no_sutun == 2
    assert p.sablon.soru_sutunlari == {k: k + 4 for k in range(1, 11)}
    assert p.sablon.puan_sutunu == 15
    p.girmedi_gosterimi = "G"
    rapor = sablonu_doldur(fix / "uydurma_sablon.xlsx", p, sonuc, tmp_path / "dolu.xlsx")
    ws = openpyxl.load_workbook(rapor.cikti)["Öğrenciler"]
    assert ws["A1"].value == "UYDURMA DERS - Soru Bazlı Not Girişi"  # şablonun geri kalanı korunur
    assert ws["B4"].value == "990000012" and ws["E4"].value == "G"  # ilk satır sınava girmedi
    assert ws["B5"].value == "990000001" and ws["O5"].value == 100
    assert ws["E6"].value == 10 and ws["N6"].value == 0  # 9 doğru, son soru yanlış
    assert set(rapor.girmedi) == {"990000004", "990000008", "990000011", "990000012"}
    assert set(rapor.sablonda_olmayan) == {"99000*004", "990000088"}
    # profil kaydedilip yeniden yüklenebilir
    p.kaydet(tmp_path / "p.json")
    assert Profil.yukle(tmp_path / "p.json").sablon.soru_sutunlari[10] == 14


def test_pano_sistem_sirasi(fix, sonuc):
    p = sablondan_profil_oner(fix / "uydurma_sablon.xlsx")
    sira = numara_sirasi(fix / "uydurma_sablon.xlsx", p)
    p2 = replace(profil_bul("akreditasyon_soru_bazli_varsayilan"), sutunlar=[s for s in profil_bul("akreditasyon_soru_bazli_varsayilan").sutunlar if s.alan == "soru_puanlari"])
    metin = pano_metni(p2, sonuc, sira)
    satirlar = metin.split("\n")
    assert len(satirlar) == 12
    assert satirlar[0] == "\t".join(["G"] * 10)
    assert satirlar[1] == "\t".join(["10,00"] * 10)


def test_tum_raporlar(sonuc, tmp_path):
    sonuc.anahtar.sorular[0].ogrenme_ciktilari = ["1"]
    t = tum_raporlari_yaz(sonuc, SINAV, tmp_path, [], profil_bul("akreditasyon_soru_bazli_varsayilan"), profil_bul("not_giris_varsayilan"), pdf=True)
    adlar = sorted(p.name for p in t.dosyalar)
    assert "UYD1001_AraSinav_2026-11-10_sonuc.xlsx" in adlar
    assert "UYD1001_AraSinav_2026-11-10_ogrenme_ciktisi.xlsx" in adlar
    wb = openpyxl.load_workbook(tmp_path / "UYD1001_AraSinav_2026-11-10_sonuc.xlsx")
    assert wb.sheetnames == ["Sonuç", "Cevaplar", "Uyarılar", "Düzeltme Kaydı", "Anahtar ve Ayarlar"]
    ws = wb["Sonuç"]
    assert ws.freeze_panes == "A2" and ws.auto_filter.ref


def test_sisteme_giris_dosyalari_ve_soru_tanimi(sonuc, tmp_path):
    """Varsayılan giriş seçimi yalnızca üç dosya yazar; soru tanımı dosyasının ilk sayfası panodaki metinle aynıdır."""
    import openpyxl

    from optik_sinav.export.profil import profil_bul
    from optik_sinav.export.raporlar import GIRIS_DOSYALARI, tum_raporlari_yaz
    from optik_sinav.export.soru_tanimi import soru_tanimi_metni

    for s in sonuc.anahtar.sorular:
        s.ogrenme_ciktilari = ["Ö01"] if s.no % 2 else ["Ö01", "Ö02"]
    t = tum_raporlari_yaz(sonuc, SINAV, tmp_path, [], profil_bul("akreditasyon_soru_bazli_varsayilan"),
                          profil_bul("not_giris_varsayilan"), secim=set(GIRIS_DOSYALARI))
    adlar = sorted(d.name.rsplit("_", 1)[-1] for d in t.dosyalar)
    assert len(t.dosyalar) == 3 and any(d.stem.endswith("_soru_tanimi") for d in t.dosyalar)
    st = next(d for d in t.dosyalar if d.stem.endswith("_soru_tanimi"))
    ws = openpyxl.load_workbook(st)["Aktarım"]
    metin = "\n".join("\t".join(str(c.value) for c in satir if c.value is not None) for satir in ws.iter_rows())
    assert metin == soru_tanimi_metni(sonuc.anahtar, sonuc.ayarlar)
    # çıktı yoksa soru tanımı yazılmaz, neden not olarak döner
    for s in sonuc.anahtar.sorular:
        s.ogrenme_ciktilari = []
    t = tum_raporlari_yaz(sonuc, SINAV, tmp_path / "b", [], None, None, secim={"soru_tanimi"})
    assert not t.dosyalar and "öğrenme çıktısı" in t.notlar[0]
    assert adlar
