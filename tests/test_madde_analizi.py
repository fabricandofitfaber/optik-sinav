import math

from optik_sinav.core.dogrulama import sinavi_degerlendir
from optik_sinav.core.madde_analizi import madde_analizi, ogrenme_ciktisi_raporu
from optik_sinav.core.modeller import CevapAnahtari, HamKayit, PuanlamaAyarlari, SoruDurumu


def kayitlar(cevaplar):
    return [HamKayit(i + 1, "", f"O{i}", str(100 + i), list(c)) for i, c in enumerate(cevaplar)]


def test_bilinen_degerler():
    k = CevapAnahtari.metinden("AB")
    cev = ["AB", "AB", "AC", "CB", "CC"]
    s = sinavi_degerlendir(kayitlar(cev), k, PuanlamaAyarlari())
    m, g = madde_analizi(s)
    assert math.isclose(m[0].guclik, 0.6) and math.isclose(m[1].guclik, 0.6)
    # 5 öğrencide %27 grup = 1 kişi; üstte AB, altta CC
    assert m[0].ayirt_edicilik == 1.0
    assert math.isclose(m[0].sik_oranlari["C"], 0.4)
    # Kuder-Richardson 20: k=2, p=q, toplamlar [2,2,1,1,0] -> varyans 0,56
    var = sum((x - 1.2) ** 2 for x in [2, 2, 1, 1, 0]) / 5
    beklenen = 2 * (1 - 2 * 0.24 / var)
    assert math.isclose(g.kr20, beklenen)
    assert g.ogrenci_sayisi == 5 and math.isclose(g.ortalama, 60)


def test_iptal_soru_analiz_disi_ve_celdirici_uyarisi():
    k = CevapAnahtari.metinden("ABC")
    k.sorular[1].durum = SoruDurumu.IPTAL
    s = sinavi_degerlendir(kayitlar(["DBC", "DAC", "AAA", "DCC"]), k, PuanlamaAyarlari())
    m, g = madde_analizi(s)
    assert m[1].analiz_disi and m[1].guclik is None
    assert g.analizdeki_soru_sayisi == 2
    assert any("Yanlış şık" in x for x in m[0].sorunlar)


def test_ogrenme_ciktisi_raporu():
    k = CevapAnahtari.metinden("AB")
    k.sorular[0].ogrenme_ciktilari = ["1"]
    k.sorular[1].ogrenme_ciktilari = ["1", "2"]
    k.sorular[1].program_ciktilari = ["3"]
    s = sinavi_degerlendir(kayitlar(["AB", "AC"]), k, PuanlamaAyarlari())
    r = {(c.tur, c.kod): c for c in ogrenme_ciktisi_raporu(s)}
    # 2. sorunun puanı iki çıktıya yarı yarıya dağılır: 101 için (50 + 0) / (50 + 25)
    assert r[("Öğrenme çıktısı", "1")].ogrenci_yuzdeleri == {"100": 100.0, "101": 200 / 3}
    assert r[("Öğrenme çıktısı", "2")].sinif_yuzdesi == 50.0
    assert r[("Program çıktısı", "3")].sorular == [2]
