from decimal import Decimal
from fractions import Fraction

from optik_sinav.core.modeller import (
    CevapAnahtari, CiftIsaretKurali, PuanlamaAyarlari, PuanYontemi, SoruDurumu, SoruSonucuDurumu, Yuvarlama,
)
from optik_sinav.core.puanlama import anahtar_eksikleri, net, ogrenci_puanla, soru_puanlari, yuvarla

K15 = CevapAnahtari.metinden("BEDACDEDBCBEAAC")


def puanla(cevap, anahtar=K15, **ay):
    return ogrenci_puanla(list(cevap), anahtar, PuanlamaAyarlari(**ay))


def test_yuvarlama_yalniz_sonda():
    _, d, y, b, ham, ceza, puan = puanla("BEDACDEDBCBEAAC")
    assert (d, y, b) == (15, 0, 0) and puan == 100
    assert yuvarla(puan) == Decimal("100.00")
    _, d, *_, puan = puanla("BEDACDEDBCBEAAA")
    assert d == 14 and yuvarla(puan) == Decimal("93.33")


def test_yuvarlama_yontemleri():
    x = Fraction(280, 3)  # 93,333...
    assert yuvarla(x, 0, Yuvarlama.YARIM_YUKARI) == 93
    assert yuvarla(x, 0, Yuvarlama.YUKARI) == 94
    assert yuvarla(x, 0, Yuvarlama.ASAGI) == 93
    assert yuvarla(Fraction(185, 2), 0) == 93  # 92,5 -> 93
    assert yuvarla(Fraction(1, 200), 2) == Decimal("0.01")  # 0,005 yarım yukarı
    assert yuvarla(Fraction(200, 3), 2, Yuvarlama.ASAGI) == Decimal("66.66")


def test_hizli_giris():
    k = CevapAnahtari.metinden("ab c-e", 6)
    assert [s.dogru for s in k.sorular] == ["A", "B", "C", "", "E", ""]
    assert k.metne() == "ABC-E-"


def test_cift_isaret_kurali():
    cevap = "BAAAA*CDECBBBAC"
    _, d, y, b, *_ = puanla(cevap)
    assert (d, y, b) == (7, 7, 1)
    _, d, y, b, *_ = puanla(cevap, cift_isaret=CiftIsaretKurali.YANLIS)
    assert (d, y, b) == (7, 8, 0)


def test_iptal_soru_herkese_tam_puan():
    k = CevapAnahtari.metinden("ABCDE")
    k.sorular[2].durum = SoruDurumu.IPTAL
    s, d, y, b, ham, ceza, puan = ogrenci_puanla(list("     "), k, PuanlamaAyarlari())
    assert puan == 20 and d == 1 and b == 4
    assert s[2].durum == SoruSonucuDurumu.IPTAL
    # iptal soru sayıya dahil: soru puanı 100/5
    assert soru_puanlari(k, PuanlamaAyarlari()) == [Fraction(20)] * 5


def test_birden_fazla_dogru():
    k = CevapAnahtari.metinden("ABCDE")
    k.sorular[0].durum, k.sorular[0].dogru = SoruDurumu.COKLU, "AC"
    for isaret, beklenen in (("A", 1), ("C", 1), ("B", 0)):
        _, d, *_ = ogrenci_puanla([isaret, " ", " ", " ", " "], k, PuanlamaAyarlari())
        assert d == beklenen


def test_yanlis_cezasi_ve_sifirin_alti():
    k = CevapAnahtari.metinden("AAAAAAAAAA")  # 10 soru, soru başı 10
    _, d, y, b, ham, ceza, puan = ogrenci_puanla(list("AAAAAABBBB"), k, PuanlamaAyarlari(yanlis_cezasi=True, ceza_orani=4))
    assert (d, y) == (6, 4) and ham == 60 and ceza == 10 and puan == 50
    assert net(d, y, PuanlamaAyarlari(yanlis_cezasi=True, ceza_orani=4)) == 5
    _, d, y, b, ham, ceza, puan = ogrenci_puanla(list("ABBBBBBBBB"), k, PuanlamaAyarlari(yanlis_cezasi=True, ceza_orani=3))
    assert ham == 10 and ceza == 30 and puan == 0  # sıfırın altına düşmez
    # Soru bazında ham puan korunur, ceza dağıtılmaz
    s, *_ = ogrenci_puanla(list("ABBBBBBBBB"), k, PuanlamaAyarlari(yanlis_cezasi=True, ceza_orani=3))
    assert s[0].puan == 10 and all(x.puan == 0 for x in s[1:])


def test_soru_bazli_puan():
    k = CevapAnahtari.metinden("ABCD")
    for s, p in zip(k.sorular, ["10", "20", "30", "40"]):
        s.puan = p
    ay = PuanlamaAyarlari(yontem=PuanYontemi.SORU_BAZLI)
    assert anahtar_eksikleri(k, ay) == []
    *_, puan = ogrenci_puanla(list("AB D"), k, ay)
    assert puan == 70
    k.sorular[3].puan = "39,5"
    eksik = anahtar_eksikleri(k, ay)
    assert len(eksik) == 1 and "99,50" in eksik[0]


def test_anahtar_eksikleri():
    k = CevapAnahtari.metinden("A-C")
    assert "2" in anahtar_eksikleri(k, PuanlamaAyarlari())[0]
    k.sorular[1].durum = SoruDurumu.IPTAL
    assert anahtar_eksikleri(k, PuanlamaAyarlari()) == []
    k.sorular[0].durum = SoruDurumu.COKLU
    assert anahtar_eksikleri(k, PuanlamaAyarlari())


def test_kisa_cevap_listesi_bos_sayilir():
    _, d, y, b, *_ = puanla("BED")
    assert (d, y, b) == (3, 0, 12)
