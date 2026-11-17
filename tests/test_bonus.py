"""Bonus soru: puanı öteki sorularla aynı ama toplama girmez; doğruysa öğrencinin bir yanlışını (yoksa bir boşunu)
doğru sayar; Akademik Bilgi Sistemi'ne giden soru tanımında ve aktarım dosyasında görünmez."""
from fractions import Fraction

from optik_sinav.core.modeller import CevapAnahtari, PuanlamaAyarlari, PuanYontemi, SoruDurumu
from optik_sinav.core.puanlama import anahtar_eksikleri, ogrenci_puanla, soru_puanlari
from optik_sinav.export.soru_tanimi import soru_tanimi_satirlari


def _anahtar(n=17, bonus=(17,)):
    a = CevapAnahtari.metinden("A" * n, n)
    for b in bonus:
        a.sorular[b - 1].durum = SoruDurumu.BONUS
    return a


def _puan(cevap, a, ayar=None):
    s, d, y, b, ham, ceza, puan = ogrenci_puanla(list(cevap), a, ayar or PuanlamaAyarlari())
    return puan, (d, y, b), [i + 1 for i, r in enumerate(s) if r.bonus_ile]


def test_esit_puanda_bonus_toplama_girmez():
    a = _anahtar()
    p = soru_puanlari(a, PuanlamaAyarlari())
    assert p[:16] == [Fraction(25, 4)] * 16 and p[16] == 0  # 16 × 6,25 = 100
    assert sum(p) == 100 and not anahtar_eksikleri(a, PuanlamaAyarlari())


def test_bonus_kurallari():
    a = _anahtar()
    assert _puan("A" * 17, a) == (100, (16, 0, 0), [])  # hepsi doğru: bonus sayılmaz, 106,25 olmaz
    assert _puan("B" + "A" * 16, a) == (100, (16, 0, 0), [1])  # bir yanlış bonusla silinir
    assert _puan("BB" + "A" * 15, a) == (Fraction(375, 4), (15, 1, 0), [1])  # 93,75: yalnızca biri
    assert _puan("B" + "A" * 15 + "B", a) == (Fraction(375, 4), (15, 1, 0), [])  # bonus yanlış: değişiklik yok
    assert _puan(" " + "A" * 16, a) == (100, (16, 0, 0), [1])  # boş da silinir
    assert _puan("A" * 16 + " ", a)[2] == []  # bonus boş


def test_cezada_once_yanlis_duzeltilir():
    a = _anahtar()
    ayar = PuanlamaAyarlari(yanlis_cezasi=True, ceza_orani=4)
    puan, sayilar, duzelen = _puan(" B" + "A" * 15, a, ayar)  # 1. boş, 2. yanlış, bonus doğru
    assert duzelen == [2] and sayilar == (15, 0, 1) and puan == Fraction(375, 4)
    puan, _, _ = _puan("A" * 16 + "B", a, ayar)  # bonus yanlış: cezası yok
    assert puan == 100


def test_soru_bazli_ve_birden_cok_bonus():
    a = _anahtar(6, bonus=(5, 6))
    ayar = PuanlamaAyarlari(yontem=PuanYontemi.SORU_BAZLI)
    for s, p in zip(a.sorular, ["10", "20", "30", "40", "10", "10"]):
        s.puan = p
    assert not anahtar_eksikleri(a, ayar)  # toplam bonuslar hariç 100
    puan, _, duzelen = _puan("BBAAAA", a, ayar)  # iki doğru bonus iki yanlışı siler
    assert puan == 100 and duzelen == [1, 2]
    puan, _, duzelen = _puan("BBBAAB", a, ayar)  # bir doğru bonus: en çok kazandıran (30 puanlık) silinir
    assert duzelen == [3] and puan == 70


def test_soru_tanimi_bonusu_gostermez():
    a = _anahtar()
    a.sorular[16].ogrenme_ciktilari = ["Ö01"]
    for s in a.sorular[:16]:
        s.ogrenme_ciktilari = ["Ö02"]
    satirlar = soru_tanimi_satirlari(a, PuanlamaAyarlari())
    assert len(satirlar) == 16 and satirlar[-1][:3] == ["16", "6,25", "Soru 16"]
    assert all(s[3:] == ["2", "100"] for s in satirlar)  # bonusun çıktısı yok sayılır
    assert a.sorular[16].cikti_dagilimi() == {}


def test_aktarim_dosyasi_bonusu_gostermez(tmp_path):
    from optik_sinav.core.dogrulama import sinavi_degerlendir
    from optik_sinav.core.modeller import HamKayit
    from optik_sinav.export.profil import profil_bul, tablo_uret

    a = _anahtar(4, bonus=(2,))  # bonus ortada: 1, 3, 4 → aktarımda 1, 2, 3
    kayitlar = [HamKayit(satir_no=1, ham_satir="", ad="X", ogrenci_no="990000001", cevaplar=list("ABAA")),
                HamKayit(satir_no=2, ham_satir="", ad="Y", ogrenci_no="990000002", cevaplar=list("AAAA"))]
    s = sinavi_degerlendir(kayitlar, a, PuanlamaAyarlari(), None, [])
    _, bas, veri = tablo_uret(profil_bul("akreditasyon_soru_bazli_varsayilan"), s)
    assert [b for b in bas if b.startswith("S")] == ["S1", "S2", "S3"]
    assert len(veri[0]) == 2 + 3
    o1, o2 = s.ogrenciler
    assert o1.puan == 100 and not any(r.bonus_ile for r in o1.sorular)  # bonus yanlış, öteki hepsi doğru
    assert o2.puan == 100
