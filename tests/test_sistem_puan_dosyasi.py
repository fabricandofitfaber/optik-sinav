"""Sistemden indirilen soru bazlı puan dosyası (Windows-1254, noktalı virgül, CRLF, numarada bölünmez boşluk)
doldurulur; dosyanın geri kalanı bayt bayt korunur."""
from fractions import Fraction

import pytest

from optik_sinav.core.dogrulama import sinavi_degerlendir
from optik_sinav.core.modeller import CevapAnahtari, PuanlamaAyarlari, SoruDurumu
from optik_sinav.export.sistem_puan_dosyasi import sistem_dosyasini_doldur
from optik_sinav.io.dat_okuyucu import dat_oku
from optik_sinav.io.liste_okuyucu import liste_oku


def _sonuc(fix, anahtar="ABCDEABCDE"):
    okuma = dat_oku(fix / "uydurma_1254_crlf.dat")
    liste = liste_oku(fix / "uydurma_liste.xlsx")
    return sinavi_degerlendir(okuma.kayitlar, CevapAnahtari.metinden(anahtar), PuanlamaAyarlari(), liste)


def _dosya(nolar, agirliklar, fazla=("99999999",)):
    bas = ["Öğrenci No", "Adı", "Soyadı", "Snf", "Girme Durum"] + [f"Soru{i}(%{w})" for i, w in enumerate(agirliklar, 1)] + ["Sınav Notu"]
    satir = [";".join(bas)]
    for no in list(nolar) + list(fazla):
        satir.append(";".join([no + "\xa0", "AD", "SOYADĞŞ", "4", "Girdi"] + [""] * len(agirliklar) + [""]))
    return ("\r\n".join(satir) + "\r\n").encode("cp1254")


def test_doldurma_ve_bicim_korunur(fix):
    s = _sonuc(fix)
    nolar = [o.no for o in s.ogrenciler if o.listede][:5]
    w = ["10"] * 10
    veri = _dosya(nolar, w)
    cikti, rapor = sistem_dosyasini_doldur(veri, s)
    assert cikti.endswith(b"\r\n") and cikti.count(b"\r\n") == veri.count(b"\r\n")
    metin = cikti.decode("cp1254")
    satirlar = metin.split("\r\n")
    assert satirlar[0] == veri.decode("cp1254").split("\r\n")[0]  # başlık aynı
    o = s.no_ile()[nolar[0]]
    h = satirlar[1].split(";")
    assert h[0] == nolar[0] + "\xa0" and h[2] == "SOYADĞŞ" and h[4] == "Girdi"
    beklenen = [("10" if r.puan else "0") for r in o.sorular]
    assert h[5:15] == beklenen
    assert h[15] == str(int(o.puan)) if o.puan.denominator == 1 else True
    assert rapor.yazilan == 5 and rapor.girmedi == ["99999999"]
    son = satirlar[-2].split(";")
    assert son[4] == "Girmedi" and son[5:16] == [""] * 11


def test_esit_olmayan_agirlik_ve_bonus(fix):
    s = _sonuc(fix, "ABCDEABCDE")
    s.anahtar.sorular[9].durum = SoruDurumu.BONUS  # aktarımda 9 soru
    with pytest.raises(ValueError, match="10 soru var"):
        sistem_dosyasini_doldur(_dosya([], ["10"] * 10), s)
    from optik_sinav.core.dogrulama import sinavi_degerlendir as sd
    from optik_sinav.io.dat_okuyucu import dat_oku as do
    from optik_sinav.io.liste_okuyucu import liste_oku as lo

    s = sd(do(fix / "uydurma_1254_crlf.dat").kayitlar, s.anahtar, PuanlamaAyarlari(), lo(fix / "uydurma_liste.xlsx"))
    w = ["11,12"] * 8 + ["11,04"]
    no = next(o.no for o in s.ogrenciler if o.listede)
    cikti, _ = sistem_dosyasini_doldur(_dosya([no], w, ()), s)
    h = cikti.decode("cp1254").split("\r\n")[1].split(";")
    o = s.no_ile()[no]
    sira = s.anahtar.aktarim_sorulari()
    for k, i in enumerate(sira):
        dogru = o.sorular[i].puan > 0
        assert h[5 + k] == ((w[k]) if dogru else "0")
    toplam = sum(Fraction(x.replace(",", ".")) for x in h[5:14])
    assert Fraction(h[14].replace(",", ".")) == toplam


def test_basliksiz_dosya_reddedilir(fix):
    with pytest.raises(ValueError, match="soru sütunu"):
        sistem_dosyasini_doldur("Öğrenci No;Adı\r\n1;A\r\n".encode("cp1254"), _sonuc(fix))


def test_baska_dersin_dosyasi_reddedilir(fix):
    with pytest.raises(ValueError, match="hiçbiri bu sınavda yok"):
        sistem_dosyasini_doldur(_dosya([], ["10"] * 10, ("11111111", "22222222")), _sonuc(fix))


def test_aktarim_kutusu_girmeyen_G(fix):
    """Sistemin örneği: A numara, B.. soru puanları; girmeyende B'de yalnızca G. Liste sırasıyla herkes."""
    from optik_sinav.export.sistem_puan_dosyasi import akreditasyon_satirlari

    s = _sonuc(fix)
    satirlar = akreditasyon_satirlari(s)
    assert [r[0] for r in satirlar] == list(dict.fromkeys(o.no for o in s.liste.ogrenciler))
    girmeyen = {g.no for g in s.girmeyenler}
    assert girmeyen and all((r[1:] == ["G"] + [""] * 9) == (r[0] in girmeyen) for r in satirlar)
    assert all(len(r) == 11 for r in satirlar)  # G satırı da tam sütun (sistem kısa satırı tanımıyor)
    assert all(len(r) == 11 for r in satirlar if r[0] not in girmeyen)


def test_ondalik_nokta_secenegi(fix):
    from optik_sinav.export.sistem_puan_dosyasi import akreditasyon_metni

    s = _sonuc(fix)
    s.ayarlar.toplam_puan = "95"  # 9,5 puanlık sorular: ondalık çıksın
    v, n = akreditasyon_metni(s), akreditasyon_metni(s, ".")
    assert "9,5" in v and "9.5" in n and v.replace(",", ".") == n
