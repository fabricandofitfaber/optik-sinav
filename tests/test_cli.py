from optik_sinav.cli import main


def test_puanla_komutu(fix, tmp_path, capsys):
    kod = main(["puanla", "--dat", str(fix / "uydurma_1254_crlf.dat"), "--anahtar", "ABCDEABCDE",
                "--liste", str(fix / "uydurma_liste.xlsx"), "--cikti", str(tmp_path / "c"), "--ders-kodu", "UYD1001",
                "--sinav-turu", "Ara Sınav", "--tarih", "2026-11-10", "--pdfsiz", "--proje-kaydet", str(tmp_path / "s.osd")])
    cikti = capsys.readouterr().out
    assert kod == 0
    assert "Öğrenci: 11  soru: 10" in cikti and "sınava girmeyen: 2" in cikti
    assert (tmp_path / "c" / "UYD1001_AraSinav_2026-11-10_sonuc.xlsx").exists()
    # proje dosyasıyla yeniden çalıştır
    assert main(["puanla", "--proje", str(tmp_path / "s.osd")]) == 0


def test_eksik_anahtar_hata_verir(fix, capsys):
    assert main(["puanla", "--dat", str(fix / "uydurma_1254_crlf.dat"), "--anahtar", "ABC"]) == 2


def test_iptal_ve_coklu(fix, capsys):
    assert main(["puanla", "--dat", str(fix / "uydurma_1254_crlf.dat"), "--anahtar", "ABCDEABCDE", "--iptal", "2", "--coklu", "3=CD", "--ayrintili"]) == 0
