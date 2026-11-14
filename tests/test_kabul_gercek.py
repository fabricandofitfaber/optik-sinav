"""PROJE_TANIMI.md bölüm 12: gerçek dosyalarla kabul testleri.

Gerçek dosyalar depoda değildir; `ornek_veri/` yoksa bu testler atlanır.
"""
import json
from decimal import Decimal

import openpyxl
import pytest

from optik_sinav.core.dogrulama import sinavi_degerlendir
from optik_sinav.core.modeller import CevapAnahtari, CiftIsaretKurali, Ogrenci, OgrenciListesi, PuanlamaAyarlari, UyariTuru
from optik_sinav.core.puanlama import yuvarla
from optik_sinav.io.dat_okuyucu import dat_oku, sablon_oner
from optik_sinav.io.kodlama import metin_dosyasi_oku
from optik_sinav.io.liste_okuyucu import liste_oku

from conftest import GERCEK

DAT = GERCEK / "YATIRIM_61.dat"
XLSX = GERCEK / "YATIRIM61.xlsx"
pytestmark = pytest.mark.skipif(not (DAT.exists() and XLSX.exists()), reason="gerçek örnek dosyalar yok (depoya girmez)")
ANAHTAR = "BEDACDEDBCBEAAC"
# Beklenen öğrenci numaraları gerçek veridir; depoya girmez, ornek_veri/kabul_beklenen.json içindedir.
BEKLENEN = json.loads((GERCEK / "kabul_beklenen.json").read_text(encoding="utf-8")) if (GERCEK / "kabul_beklenen.json").exists() else {}


@pytest.fixture(scope="module")
def okuma():
    satirlar, _, _ = metin_dosyasi_oku(DAT)
    return dat_oku(DAT, sablon_oner(satirlar))


@pytest.fixture(scope="module")
def eski():
    ws = openpyxl.load_workbook(XLSX)["ktt"]
    return {str(r[2]): r for r in ws.iter_rows(min_row=3, values_only=True)}


def degerlendir(okuma, liste=None, **ay):
    return sinavi_degerlendir(okuma.kayitlar, CevapAnahtari.metinden(ANAHTAR), PuanlamaAyarlari(**ay), liste)


def test_1_ogrenci_ve_soru_sayisi(okuma):
    assert len(okuma.kayitlar) == 61 and okuma.sablon.soru_sayisi == 15


def test_3_cift_isaret_yanlis_sayilinca_hepsi_tutar(okuma, eski):
    s = degerlendir(okuma, cift_isaret=CiftIsaretKurali.YANLIS)
    for o in s.ogrenciler:
        assert (o.dogru, o.yanlis) == (eski[o.no][9], eski[o.no][10]), o.no


def test_3_varsayilan_ayarda_tek_fark(okuma, eski):
    s = degerlendir(okuma)
    farkli = [o for o in s.ogrenciler if (o.dogru, o.yanlis) != (eski[o.no][9], eski[o.no][10])]
    assert len(farkli) == 1 and any(u.tur == UyariTuru.CIFT_ISARET for u in farkli[0].uyarilar)
    if "cift_isaretli" in BEKLENEN:
        assert farkli[0].no == BEKLENEN["cift_isaretli"]
    assert (farkli[0].yanlis, farkli[0].bos) == (7, 1)


def test_4_puan_farki_en_fazla_005(okuma, eski):
    s = degerlendir(okuma)
    for o in s.ogrenciler:
        assert abs(yuvarla(o.puan) - Decimal(str(eski[o.no][12]))) <= Decimal("0.05"), o.no
        if o.dogru == 14:
            assert yuvarla(o.puan) == Decimal("93.33") and eski[o.no][12] == 93.38
        if o.dogru == 15:
            assert o.puan == 100


def test_5_alan_disi_isaret(okuma):
    s = degerlendir(okuma)
    alan_disi = [x for x in s.ogrenciler if any(u.tur == UyariTuru.ALAN_DISI_ISARET for u in x.uyarilar)]
    assert len(alan_disi) == 1
    o = alan_disi[0]
    if "alan_disi" in BEKLENEN:
        assert o.no == BEKLENEN["alan_disi"]
    assert any(u.tur == UyariTuru.ALAN_DISI_ISARET and "67" in u.mesaj for u in o.uyarilar)
    assert any(u.mesaj.startswith("Soru alanı dışında işaret var") for u in o.uyarilar)


def test_6_iki_ogrenci_girmedi(okuma):
    l = liste_oku(XLSX)
    # 63 kişilik ders listesi gerçek dosyada yok; mevcut listeye iki uydurma öğrenci eklenir
    l63 = OgrenciListesi(l.ogrenciler + [Ogrenci("234700998", "UYDURMA BİR"), Ogrenci("234700999", "UYDURMA İKİ")], l.esleme)
    s = degerlendir(okuma, l63)
    assert len(l63.ogrenciler) == 63 and len(s.girmeyenler) == 2 and not s.listede_olmayanlar


def test_7_adlar_listeden(okuma):
    l = liste_oku(XLSX)
    s = degerlendir(okuma, l)
    adlar = {o.no: o.ad for o in l.ogrenciler}
    assert all(o.ad == adlar[o.no] for o in s.ogrenciler)
    assert all("�" not in o.ad for o in s.ogrenciler)
