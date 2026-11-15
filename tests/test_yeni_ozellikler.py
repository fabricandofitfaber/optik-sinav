"""Kitapçık, klasik sınav, öğrenme çıktısı yüzdeleri, ders paketi ve yeni istatistikler."""
import math
from fractions import Fraction

from optik_sinav.core.dogrulama import duzeltme_olustur, sinavi_degerlendir
from optik_sinav.core.klasik import klasik_degerlendir, tablodan_klasik_puanlar
from optik_sinav.core.madde_analizi import (
    cikti_dagilimi, cikti_denetimi, madde_analizi, ogrenme_ciktisi_raporu, tam_sayi_dagilim,
)
from optik_sinav.core.modeller import (
    CevapAnahtari, HamKayit, Ogrenci, OgrenciListesi, ListeEslemesi, PuanlamaAyarlari, PuanYontemi, Soru,
    SoruSonucuDurumu, esit_yuzdeler,
)
from optik_sinav.core.proje import SinavProjesi
from optik_sinav.io.ders_paketi import metinden_coz


def kayit(i, cevap, kitapcik=""):
    return HamKayit(i, "", f"O{i}", str(100 + i), list(cevap), kitapcik=kitapcik)


# ------------------------------------------------------------------ kitapçık
def test_b_kitapcigi_sirasi_ve_anahtari_ana_kitapciga_cevrilir():
    a = CevapAnahtari.metinden("ABC")
    a.sorular[2].puan = "50"
    # B'de sorular ters sırada: B1 = A3, B2 = A2, B3 = A1
    a.kitapcik_anahtarlari["B"] = "DBA"
    a.kitapcik_eslemesi["B"] = {1: 3, 2: 2, 3: 1}
    ayar = PuanlamaAyarlari(yontem=PuanYontemi.SORU_BAZLI)
    a.sorular[0].puan = "25"
    a.sorular[1].puan = "25"
    s = sinavi_degerlendir([kayit(1, "ABC", "A"), kayit(2, "DBA", "B"), kayit(3, "DBE", "B")], a, ayar)
    o1, o2, o3 = s.ogrenciler
    assert o1.puan == o2.puan == 100
    # B öğrencisinin cevapları ana sıraya çevrilmiş: A1 <- B3, A3 <- B1
    assert o2.cevaplar == ["A", "B", "D"] and o2.kaynak_soru == [3, 2, 1]
    # 3. öğrenci B3'ü (= A1) yanlış yaptı: ana kitapçığın 1. sorusu (25 puan) gitti
    assert o3.puan == 75 and o3.sorular[0].durum == SoruSonucuDurumu.YANLIS


def test_kitapcik_duzeltmesi_ve_bilinmeyen_kitapcik():
    a = CevapAnahtari.metinden("AB")
    a.kitapcik_anahtarlari["B"] = "BA"
    k = kayit(1, "BA", "")  # kitapçık okunmamış: ana sayılır
    s = sinavi_degerlendir([k], a, PuanlamaAyarlari())
    assert s.ogrenciler[0].kitapcik == "A" and s.ogrenciler[0].dogru == 0
    d = duzeltme_olustur(k, "kitapcik", "b")
    assert d.yeni == "B"
    s = sinavi_degerlendir([k], a, PuanlamaAyarlari(), duzeltmeler=[d])
    assert s.ogrenciler[0].kitapcik == "B" and s.ogrenciler[0].dogru == 2
    s = sinavi_degerlendir([kayit(1, "AB", "C")], a, PuanlamaAyarlari())
    assert any("Anahtarı girilmemiş kitapçık" in u.mesaj for u in s.ogrenciler[0].uyarilar)


def test_kitapcik_proje_dosyasinda_saklanir(tmp_path):
    p = SinavProjesi()
    p.anahtar = CevapAnahtari.metinden("AB")
    p.anahtar.kitapcik_anahtarlari["B"] = "BA"
    p.anahtar.kitapcik_eslemesi["B"] = {1: 2, 2: 1}
    p.anahtar.sorular[0].ogrenme_ciktilari = ["Ö01", "Ö02"]
    p.anahtar.sorular[0].cikti_yuzdeleri = {"Ö01": 70, "Ö02": 30}
    p.kaydet(tmp_path / "x.osd")
    q = SinavProjesi.ac(tmp_path / "x.osd")
    assert q.anahtar.kitapcik_anahtarlari == {"B": "BA"} and q.anahtar.esleme("B") == {1: 2, 2: 1}
    assert q.anahtar.sorular[0].cikti_dagilimi() == {"Ö01": 70, "Ö02": 30}


# ------------------------------------------------------------------ öğrenme çıktısı
def test_esit_yuzdeler_toplami_100():
    assert esit_yuzdeler(3) == [34, 33, 33] and sum(esit_yuzdeler(7)) == 100


def test_cikti_dagilimi_ve_denetim():
    a = CevapAnahtari.metinden("ABCD")
    a.sorular[0].ogrenme_ciktilari = ["Ö01"]
    a.sorular[1].ogrenme_ciktilari = ["Ö01", "Ö02"]
    a.sorular[2].ogrenme_ciktilari = ["Ö02", "Ö03", "Ö04"]
    hatalar, _ = cikti_denetimi(a, ["Ö01", "Ö02", "Ö03", "Ö04", "Ö05"])
    assert any("seçilmemiş sorular: 4" in h for h in hatalar)
    a.sorular[3].ogrenme_ciktilari = ["Ö05"]
    hatalar, bilgiler = cikti_denetimi(a, ["Ö01", "Ö02", "Ö03", "Ö04", "Ö05", "Ö06"])
    assert not hatalar and "Ö06" in bilgiler[0]
    d = cikti_dagilimi(a, [Fraction(25)] * 4)
    assert sum(d.values()) == 100
    assert d["Ö01"] == Fraction(25 + 12.5) * 100 / 100
    tam = tam_sayi_dagilim(d)
    assert sum(tam.values()) == 100
    a.sorular[1].cikti_yuzdeleri = {"Ö01": 60, "Ö02": 30}
    hatalar, _ = cikti_denetimi(a)
    assert any("100 etmeyen" in h and "2 (%90)" in h for h in hatalar)
    a.sorular[0].ogrenme_ciktilari = ["Ö09"]
    hatalar, _ = cikti_denetimi(a, ["Ö01"])
    assert any("Ö09" in h for h in hatalar)


def test_cikti_raporu_ulasma_orani_ve_agirlik():
    a = CevapAnahtari.metinden("AB")
    a.sorular[0].ogrenme_ciktilari = ["Ö01"]
    a.sorular[1].ogrenme_ciktilari = ["Ö02"]
    s = sinavi_degerlendir([kayit(1, "AB"), kayit(2, "AC"), kayit(3, "CC")], a, PuanlamaAyarlari())
    r = {c.kod: c for c in ogrenme_ciktisi_raporu(s)}
    assert math.isclose(r["Ö01"].ulasan_orani, 2 / 3) and math.isclose(r["Ö01"].sinav_agirligi, 50)


# ------------------------------------------------------------------ klasik sınav
def liste(*nolar):
    return OgrenciListesi([Ogrenci(no, f"Ad {no}") for no in nolar], ListeEslemesi())


def test_klasik_puanlama_kismi_eksik_fazla_girmedi():
    a = CevapAnahtari(sorular=[Soru(1, puan="40"), Soru(2, puan="60")])
    ayar = PuanlamaAyarlari(yontem=PuanYontemi.SORU_BAZLI)
    p = {"1": ["40", "30,5"], "2": ["0", None], "3": [None, None], "4": ["50", "60"]}
    s = klasik_degerlendir(liste("1", "2", "3", "4"), a, ayar, p)
    assert s.klasik and [g.no for g in s.girmeyenler] == ["3"]
    o1, o2, o4 = s.ogrenciler
    assert o1.puan == Fraction(705, 10) and o1.sorular[1].durum == SoruSonucuDurumu.KISMI and o1.dogru == 1
    assert o2.puan == 0 and o2.sorular[0].durum == SoruSonucuDurumu.YANLIS and o2.sorular[1].durum == SoruSonucuDurumu.BOS
    assert any("Puanı girilmemiş" in u.mesaj for u in o2.uyarilar)
    assert any("büyük" in u.mesaj for u in o4.uyarilar)
    m, g = madde_analizi(s)
    assert m[0].guclik is not None and g.kr20 is None


def test_klasik_istatistikleri_ve_alfa():
    a = CevapAnahtari(sorular=[Soru(1, puan="50"), Soru(2, puan="50")])
    ayar = PuanlamaAyarlari(yontem=PuanYontemi.SORU_BAZLI)
    p = {str(i): [str(x), str(y)] for i, (x, y) in enumerate([(50, 40), (40, 40), (30, 20), (10, 15), (0, 5), (20, 25)])}
    s = klasik_degerlendir(liste(*p), a, ayar, p)
    m, g = madde_analizi(s)
    x = [50, 40, 30, 10, 0, 20]
    y = [40, 40, 20, 15, 5, 25]
    t = [a + b for a, b in zip(x, y)]
    var = lambda v: sum((q - sum(v) / len(v)) ** 2 for q in v) / len(v)
    assert math.isclose(g.alfa, 2 * (1 - (var(x) + var(y)) / var(t)))
    assert math.isclose(m[0].guclik, sum(x) / 6 / 50)


def test_excelden_klasik_puan_alma():
    tablo = [["Öğrenci No", "Adı Soyadı", "S1", "S2"], ["990000001", "A", 10, "7,5"], [990000002.0, "B", None, 3]]
    p, notlar = tablodan_klasik_puanlar(tablo, 2)
    assert p == {"990000001": ["10", "7,5"], "990000002": [None, "3"]} and not notlar


# ------------------------------------------------------------------ istatistikler
def test_alfa_esit_puanli_testte_kr20_ye_esit_ve_betimleyiciler():
    a = CevapAnahtari.metinden("ABCD")
    cev = ["ABCD", "ABCA", "ABAA", "AAAA", "CCCC", "ABCD", "BBCD", "AACA"]
    s = sinavi_degerlendir([kayit(i, c) for i, c in enumerate(cev, 1)], a, PuanlamaAyarlari())
    m, g = madde_analizi(s)
    assert math.isclose(g.alfa, g.kr20)
    assert g.olcme_hatasi is not None and g.birinci_ceyrek <= g.medyan <= g.ucuncu_ceyrek
    assert all(len(x.bes_grup) == 5 for x in m if not x.analiz_disi)
    assert g.yorumlar


def test_hiz_uyarisi_son_sorularda_bos_artisi():
    a = CevapAnahtari.metinden("AAAAAAAA")
    cev = ["AAAAAA  ", "AAAAA   ", "AAAAAAA ", "AAAAAA  ", "AAAAAAAA"]
    s = sinavi_degerlendir([kayit(i, c) for i, c in enumerate(cev, 1)], a, PuanlamaAyarlari())
    _, g = madde_analizi(s)
    assert g.bos_orani_sirayla[-1] == 0.8 and "Süre yetmemiş" in g.hiz_uyarisi


def test_kisi_uyumu_ters_oruntu():
    a = CevapAnahtari.metinden("AAAAAA")
    cev = ["AAAAAA", "AAAAAB", "AAAABB", "AAABBB", "AABBBB", "ABBBBB", "BBBBBB", "AABBBB", "AAABBB",
           "BBBBAA"]  # son öğrenci kolayları kaçırıp en zor ikisini bilmiş
    s = sinavi_degerlendir([kayit(i, c) for i, c in enumerate(cev, 1)], a, PuanlamaAyarlari())
    _, g = madde_analizi(s)
    assert g.kisi_uyumu and g.kisi_uyumu[0].no == "110" and g.kisi_uyumu[0].indeks > 0.9


def test_benzer_yanlis_oruntusu():
    import random

    rnd = random.Random(3)
    n = 20
    a = CevapAnahtari.metinden("A" * n)
    cev = ["".join(rnd.choice("AAABCDE") for _ in range(n)) for _ in range(30)]
    ortak = "".join("A" if i % 2 else "E" for i in range(n))
    cev[3] = ortak
    cev[17] = ortak
    s = sinavi_degerlendir([kayit(i, c) for i, c in enumerate(cev, 1)], a, PuanlamaAyarlari())
    _, g = madde_analizi(s)
    assert g.benzer_ciftler and {g.benzer_ciftler[0].no1, g.benzer_ciftler[0].no2} == {"104", "118"}


# ------------------------------------------------------------------ ders paketi
DERS_METNI = """XYZ1001 Uydurma Ders
 Kredi  AKTS
Bölümü/Programı:
Uydurma Bölüm
Sıra No Açıklama
 Dersin Öğrenme Çıktıları
Ö01  Birinci çıktı
Ö02 İkinci çıktı uzun
devam eden satır
 Programın Öğrenme Çıktıları
Sıra No Açıklama
P02 Program iki
P01 Program bir
 Dersin Öğrenme Çıktılarının Programın Öğrenme Çıktılarına Katkıları
 Ara Sınav 0 %40
 Yarıyıl Sonu Sınavı 0 %60
P01 P02
 Tüm 3 5
"""


def test_ders_paketi_metinden_cozulur():
    p = metinden_coz(DERS_METNI)
    assert p.kod == "XYZ1001" and p.ad == "Uydurma Ders" and p.program == "Uydurma Bölüm"
    assert p.ogrenme_kodlari() == ["Ö01", "Ö02"] and p.ogrenme_ciktilari[1].aciklama == "İkinci çıktı uzun devam eden satır"
    assert [c.kod for c in p.program_ciktilari] == ["P01", "P02"]
    assert p.katki == {"P01": 3, "P02": 5} and p.degerlendirme == {"Ara Sınav": 40, "Yarıyıl Sonu Sınavı": 60}


def test_paketle_gelen_dersler():
    from optik_sinav.io.ders_paketi import ders_bul

    d = ders_bul("utl4513")
    assert d and d.ad == "Yatırım Analizi" and d.ogrenme_kodlari() == ["Ö01", "Ö02", "Ö03", "Ö04", "Ö05"]


def test_sistem_soru_tanimi_metni():
    from optik_sinav.export.soru_tanimi import soru_tanimi_metni

    a = CevapAnahtari.metinden("ABC")
    a.sorular[0].ogrenme_ciktilari = ["Ö05", "Ö07"]
    a.sorular[1].ogrenme_ciktilari = ["Ö03"]
    a.sorular[2].ogrenme_ciktilari = ["Ö03", "Ö04"]
    a.sorular[2].cikti_yuzdeleri = {"Ö03": 60, "Ö04": 40}
    m = soru_tanimi_metni(a, PuanlamaAyarlari())
    assert m.split("\n") == ["1\t33,34\tSoru 1\t5\t50\t7\t50", "2\t33,33\tSoru 2\t3\t100", "3\t33,33\tSoru 3\t3\t60\t4\t40"]
    a.sorular[0].puan, a.sorular[1].puan, a.sorular[2].puan = "25", "35", "40"
    m = soru_tanimi_metni(a, PuanlamaAyarlari(yontem=PuanYontemi.SORU_BAZLI), ["Ö03", "Ö04", "Ö05", "Ö07"])
    assert m.split("\n")[0] == "1\t25\tSoru 1\t3\t50\t4\t50"


# ------------------------------------------------------------------ ek istatistikler
def test_ek_istatistikler():
    from optik_sinav.core import ek_istatistik as E

    a = CevapAnahtari.metinden("ABCDE")
    cev = ["ABCDE", "ABCDA", "ABCAA", "ABAAA", "AAAAA", "EEEEE", "ABCDE", "BBCDE"]
    s = sinavi_degerlendir([kayit(i, c) for i, c in enumerate(cev, 1)], a, PuanlamaAyarlari())
    assert E.sans_puani(s) == 20.0
    f = {x.no: x.gereken for x in E.final_gereken(s, 40, 50, 50)}
    assert f["101"] == 50.0  # 100 alan: alt sınır 50
    assert f["106"] == 70.0  # 20 alan: (50 - 20 × 0,4) / 0,6 = 70
    t = E.tasarim_denetimi(s, [0.9, 0.7, 0.6, 0.4, 0.3])
    assert t.sik_sayilari == {"A": 1, "B": 1, "C": 1, "D": 1, "E": 1} and t.sira_guclik_korelasyonu == -1.0
    assert math.isclose(E.t_iki_yonlu_p(2.0, 10), 0.0734, abs_tol=1e-4)
    r = E.rasch(s)
    assert r is not None and abs(sum(r.soru_zorluklari.values())) < 1e-9
    assert r.soru_zorluklari[1] < r.soru_zorluklari[5]  # 1. soru en kolay


def test_arsiv(tmp_path):
    from optik_sinav.core import ek_istatistik as E
    from optik_sinav.core.modeller import SinavBilgisi

    a = CevapAnahtari.metinden("AB")
    a.sorular[0].ogrenme_ciktilari = ["Ö01"]
    a.sorular[1].ogrenme_ciktilari = ["Ö02"]
    s = sinavi_degerlendir([kayit(1, "AB"), kayit(2, "AC")], a, PuanlamaAyarlari())
    _, g = madde_analizi(s)
    for tarih in ("2025-11-10", "2026-11-10"):
        k = E.arsiv_kaydi_olustur(s, SinavBilgisi("UYD1001", "", "Ara Sınav", tarih), g, ogrenme_ciktisi_raporu(s))
        E.arsive_yaz(tmp_path, k)
    kayitlar = E.arsivi_oku(tmp_path, "UYD1001")
    assert [k.tarih for k in kayitlar] == ["2025-11-10", "2026-11-10"] and kayitlar[0].cikti_basarilari["Ö02"] == 50.0


# ------------------------------------------------------------------ dört yeni analiz
def test_kavram_yanilgisi_ve_fisher():
    from optik_sinav.core import ek_istatistik as E

    assert math.isclose(E.fisher_ust(5, 11, 8, 61), 0.0032727941221379437, rel_tol=1e-9)
    a = CevapAnahtari.metinden("AAAA")
    cev = ["BCAA"] * 6 + ["AAAA"] * 10 + ["BAAA", "ACAA", "AAAB", "AAAA"]
    s = sinavi_degerlendir([kayit(i, c) for i, c in enumerate(cev, 1)], a, PuanlamaAyarlari())
    k = E.kavram_yanilgilari(s)
    assert k and (k[0].soru1, k[0].sik1, k[0].soru2, k[0].sik2) == (1, "B", 2, "C") and k[0].birlikte == 6


def test_sinav_yapisi_tek_boyut():
    from optik_sinav.core import ek_istatistik as E

    import random

    rnd = random.Random(5)
    a = CevapAnahtari.metinden("A" * 8)
    for s_ in a.sorular:
        s_.ogrenme_ciktilari = ["Ö01"] if s_.no <= 4 else ["Ö02"]
    cev = []
    for _ in range(80):
        yetenek = rnd.random()
        cev.append("".join("A" if rnd.random() < yetenek else "B" for _ in range(8)))
    s = sinavi_degerlendir([kayit(i, c) for i, c in enumerate(cev, 1)], a, PuanlamaAyarlari())
    y = E.sinav_yapisi(s)
    assert y.oran_1_2 > 3 and abs(sum(y.ozdegerler) - 8) < 1e-9 and "tek bir beceriyi" in y.yorum
    assert all(v > 0.2 for v in y.yukler.values()) and len(y.cikti_uyumu) == 2


def test_donem_sonu_mutlak_bagil():
    from optik_sinav.core.donem_sonu import HarfAyarlari, donem_sonu, tablodan_final_puanlari

    a = CevapAnahtari.metinden("AB")
    s = sinavi_degerlendir([kayit(1, "AB"), kayit(2, "AC"), kayit(3, "CC")], a, PuanlamaAyarlari())
    f = {"101": "90", "102": "40", "103": None}
    d = donem_sonu(s, f, 40, 50, 50, HarfAyarlari())
    n = {x.no: x for x in d.notlar}
    assert math.isclose(n["101"].ham, 94) and n["101"].harf == "AA" and n["101"].gecti
    assert n["102"].harf == "FF" and not n["102"].gecti and "final" in n["102"].aciklama
    assert n["103"].harf == "" and n["103"].aciklama == "final girilmedi"
    d2 = donem_sonu(s, {"101": "90", "102": "60", "103": "70"}, 40, 50, 50, HarfAyarlari(yontem="bagil", bagil_en_az=3))
    assert d2.uygulanan == "bagil" and all(x.t is not None for x in d2.notlar)
    d3 = donem_sonu(s, {"101": "90", "102": "60", "103": "70"}, 40, 50, 50, HarfAyarlari(yontem="bagil", bagil_en_az=30))
    assert d3.uygulanan == "mutlak" and d3.notlar_metin
    p, _ = tablodan_final_puanlari([["Öğrenci No", "Ad", "Final"], ["990000001", "X", 75], [990000002.0, "Y", "62,5"]])
    assert p == {"990000001": "75", "990000002": "62,5"}


def test_karne():
    from optik_sinav.core.donem_sonu import karneler

    a = CevapAnahtari.metinden("ABCD")
    for s_, c in zip(a.sorular, (["Ö01"], ["Ö01"], ["Ö02"], ["Ö02"])):
        s_.ogrenme_ciktilari = c
    s = sinavi_degerlendir([kayit(1, "ABCD"), kayit(2, "ABAA"), kayit(3, "CCCD")], a, PuanlamaAyarlari())
    k = {x.no: x for x in karneler(s, ogrenme_ciktisi_raporu(s))}
    assert k["101"].sira == 1 and k["102"].ciktilar[0][2] == 100.0 and "Ö01" in k["102"].guclu and "Ö02" in k["102"].gelismeli


def test_puan_listesi_coz():
    import pytest

    from optik_sinav.core.klasik import puan_listesi_coz

    assert puan_listesi_coz("10 10 10 10 20 40") == ["10", "10", "10", "10", "20", "40"]
    assert puan_listesi_coz("10, 10, 20, 12,5") == ["10", "10", "20", "12.5"]
    assert puan_listesi_coz("10,10,20") == ["10", "10", "20"]
    assert puan_listesi_coz("7,5;12.5+5") == ["7.5", "12.5", "5"]
    assert puan_listesi_coz("  ") == []
    with pytest.raises(ValueError):
        puan_listesi_coz("10 -5")
    with pytest.raises(ValueError):
        puan_listesi_coz("10 abc")


# ------------------------------------------------------------------ notu belirleyen sorular, kısmi puan, okuma sırası
def _klasik_sinav(puanlar_listesi, tam):
    from optik_sinav.core.modeller import CevapAnahtari, PuanlamaAyarlari, PuanYontemi, Soru

    a = CevapAnahtari(sorular=[Soru(i + 1, puan=str(t)) for i, t in enumerate(tam)])
    p = {str(100 + i): [None if x is None else str(x) for x in r] for i, r in enumerate(puanlar_listesi)}
    return klasik_degerlendir(liste(*p), a, PuanlamaAyarlari(yontem=PuanYontemi.SORU_BAZLI), p), list(p)


def test_notu_belirleyen_sorular():
    from optik_sinav.core import ek_istatistik as E

    # 1. soru (40 puan) öğrencileri ayırıyor; 2. ve 3. soruda herkes neredeyse aynı puanı almış
    s, _ = _klasik_sinav([[40, 20, 20], [30, 20, 21], [20, 21, 20], [10, 20, 20], [0, 21, 21], [35, 20, 20]], [40, 30, 30])
    nb = E.notu_belirleyen_sorular(s)
    assert math.isclose(sum(k.katki_payi for k in nb.sorular), 1.0)
    k1, k2, k3 = nb.sorular
    assert k1.durum == "fazla_belirleyici" and k1.katki_payi > 0.9 and math.isclose(k1.puan_payi, 0.4)
    assert k2.durum == "az_etkili" and k3.durum == "az_etkili"
    assert "1. sorudan" in nb.yorum and "Notu puanından çok daha fazla belirleyen soru: 1" in nb.yorum
    # herkes aynı toplamı almışsa hesaplanmaz
    s, _ = _klasik_sinav([[10, 10]] * 6, [50, 50])
    assert E.notu_belirleyen_sorular(s) is None


def test_kismi_puan_profili():
    from optik_sinav.core import ek_istatistik as E

    s, _ = _klasik_sinav([[5, 50, 10], [7, 50, None], [6, 50, 0], [10, 50, 3]], [10, 50, 20])
    k1, k2, k3 = E.kismi_puan_profili(s)
    assert (k1.tam, k1.kismi, k1.sifir, k1.bos) == (1, 3, 0, 0) and "çoğu kısmi" in k1.notlar[0]
    assert k2.tam == 4 and "herkes tam" in k2.notlar[0]
    assert (k3.kismi, k3.sifir, k3.bos) == (2, 1, 1) and any("kimse tam" in n for n in k3.notlar)
    assert math.isclose(k1.ortalama_oran, 0.7)


def test_okuma_sirasi_etkisi():
    from optik_sinav.core import ek_istatistik as E

    # girildikçe düşen puanlar: yorulma
    s, nolar = _klasik_sinav([[100 - 7 * i] for i in range(12)], [100])
    ok = E.okuma_sirasi_etkisi(s, nolar)
    assert ok.n == 12 and math.isclose(ok.rho, -1.0) and ok.p == 0.0 and "düşüyor" in ok.yorum and ok.ilk_ortalama > ok.son_ortalama
    karisik = [nolar[i] for i in (5, 0, 9, 3, 11, 1, 7, 2, 10, 4, 8, 6)]
    assert "belirgin bir kayma yok" in E.okuma_sirasi_etkisi(s, karisik).yorum
    assert E.okuma_sirasi_etkisi(s, nolar[:9]) is None  # en az 10 kâğıt
