"""Arayüzsüz komut satırı girişi.

Örnek:
    python -m optik_sinav puanla --dat x.dat --anahtar BEDAC... --liste y.xlsx --cikti klasor/
    python -m optik_sinav puanla --proje sinav.osd --cikti klasor/
    python -m optik_sinav onizle --dat x.dat
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import metinler as M
from .core.dogrulama import sinavi_degerlendir
from .core.modeller import CevapAnahtari, CiftIsaretKurali, PuanlamaAyarlari, SoruDurumu, Yuvarlama
from .core.proje import SinavProjesi
from .core.puanlama import anahtar_eksikleri, sayi_yaz
from .export.profil import profil_bul
from .export.raporlar import tum_raporlari_yaz
from .io.dat_okuyucu import dat_oku, okuyucu_sablonu_yukle, sablon_oner
from .io.kodlama import metin_dosyasi_oku
from .io.liste_okuyucu import liste_oku


def _sayi_listesi(metin: str | None) -> list[int]:
    if not metin:
        return []
    return [int(x) for x in metin.replace(";", ",").split(",") if x.strip()]


def puanla(a: argparse.Namespace) -> int:
    proje = SinavProjesi.ac(a.proje) if a.proje else SinavProjesi()
    if a.dat:
        proje.dat_yolu = a.dat
    if a.liste:
        proje.liste_yolu = a.liste
    if not proje.dat_yolu:
        print("Hata: --dat ya da --proje verilmeli.", file=sys.stderr)
        return 2
    s = proje.sinav
    for alan in ("ders_kodu", "ders_adi", "sinav_turu", "tarih", "saat", "etki_orani"):
        v = getattr(a, alan)
        if v:
            setattr(s, alan, v)

    # Okuyucu şablonu
    if a.okuyucu:
        okuyucu = okuyucu_sablonu_yukle(a.okuyucu)
    else:
        okuyucu = proje.okuyucu
        if not a.proje:
            satirlar, _, _ = metin_dosyasi_oku(proje.dat_yolu)
            okuyucu = sablon_oner(satirlar, okuyucu)
    if a.soru_sayisi:
        okuyucu.soru_sayisi = a.soru_sayisi
    proje.okuyucu = okuyucu

    # Anahtar ve ayarlar
    if a.anahtar:
        eski = {x.no: x for x in proje.anahtar.sorular}
        proje.anahtar = CevapAnahtari.metinden(a.anahtar, okuyucu.soru_sayisi)
        for x in proje.anahtar.sorular:  # proje dosyasındaki eşlemeleri koru
            if x.no in eski:
                x.ogrenme_ciktilari, x.program_ciktilari, x.puan = eski[x.no].ogrenme_ciktilari, eski[x.no].program_ciktilari, eski[x.no].puan
    for k in _sayi_listesi(a.iptal):
        proje.anahtar.sorular[k - 1].durum = SoruDurumu.IPTAL
    for parca in a.coklu or []:
        no, siklar = parca.split("=")
        q = proje.anahtar.sorular[int(no) - 1]
        q.durum, q.dogru = SoruDurumu.COKLU, siklar.upper()
    ay: PuanlamaAyarlari = proje.ayarlar
    if a.cift_isaret:
        ay.cift_isaret = CiftIsaretKurali(a.cift_isaret)
    if a.ceza:
        ay.yanlis_cezasi, ay.ceza_orani = True, a.ceza
    if a.yuvarlama:
        ay.yuvarlama = Yuvarlama(a.yuvarlama)
    eksik = anahtar_eksikleri(proje.anahtar, ay)
    if eksik:
        print("Hata: " + " ".join(eksik), file=sys.stderr)
        return 2

    okuma = dat_oku(proje.dat_yolu, okuyucu)
    liste = liste_oku(proje.liste_yolu, proje.liste_esleme if proje.liste_esleme.no_sutun else None) if proje.liste_yolu else None
    sonuc = sinavi_degerlendir(okuma.kayitlar, proje.anahtar, ay, liste, proje.duzeltmeler, proje.otomatik_kapali)

    print(f"Dosya: {proje.dat_yolu}  kodlama: {okuma.kodlama}  satır sonu: {okuma.satir_sonu}")
    print(f"Öğrenci: {len(sonuc.ogrenciler)}  soru: {proje.anahtar.soru_sayisi}  anahtar: {proje.anahtar.metne()}")
    if liste:
        print(f"Liste: {len(liste.ogrenciler)} öğrenci  sınava girmeyen: {len(sonuc.girmeyenler)}  listede olmayan: {len(sonuc.listede_olmayanlar)}")
    if a.ayrintili:
        for o in sonuc.ogrenciler:
            print(f"{o.no:>11}  {o.ad[:28]:<28} D{o.dogru:>3} Y{o.yanlis:>3} B{o.bos:>3}  {sayi_yaz(o.puan, ay.ondalik):>7}  {'; '.join(u.mesaj for u in o.uyarilar)}")
        for g in sonuc.girmeyenler:
            print(f"{g.no:>11}  {g.ad[:28]:<28} {M.GIRMEDI}")
    uyarili = [o for o in sonuc.ogrenciler if o.uyarili]
    print(f"Uyarılı satır: {len(uyarili)}")
    for o in uyarili if not a.ayrintili else []:
        print(f"  satır {o.kayit.satir_no:>3}  {o.no}: {'; '.join(u.mesaj for u in o.uyarilar)}")

    if a.cikti:
        akr = profil_bul(a.akreditasyon_profili or proje.profil_akreditasyon)
        ng = profil_bul(a.not_giris_profili or proje.profil_not_giris)
        t = tum_raporlari_yaz(sonuc, s, a.cikti, proje.duzeltmeler, akr, ng, a.sablon or proje.sistem_sablonu_yolu or None,
                              pdf=not a.pdfsiz, kaynaklar={"Optik dosya": Path(proje.dat_yolu).name, "Öğrenci listesi": Path(proje.liste_yolu).name if proje.liste_yolu else ""})
        print("Yazılan dosyalar:")
        for d in t.dosyalar:
            print(f"  {d}")
        for n in t.notlar:
            print(f"Not: {n}")
    if a.proje_kaydet:
        proje.kaydet(a.proje_kaydet)
        print(f"Proje kaydedildi: {a.proje_kaydet}")
    return 0


def onizle(a: argparse.Namespace) -> int:
    satirlar, kodlama, satir_sonu = metin_dosyasi_oku(a.dat)
    s = sablon_oner(satirlar)
    print(f"Kodlama: {kodlama}  satır sonu: {satir_sonu}  satır: {len(satirlar)}  önerilen soru sayısı: {s.soru_sayisi}  satır uzunluğu: {s.satir_uzunlugu}")
    cetvel = "".join(str(i % 10) for i in range(1, s.cevap_bitis + 1))
    print(cetvel)
    for x in satirlar[: a.satir]:
        print(x[: s.cevap_bitis])
    return 0


def ayristirici() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="optik_sinav", description=M.UYGULAMA_ADI)
    alt = p.add_subparsers(dest="komut")
    q = alt.add_parser("puanla", help="Optik dosyayı puanla ve raporları yaz")
    q.add_argument("--proje", help="Sınav proje dosyası (.osd)")
    q.add_argument("--dat", help="Optik okuyucu dosyası")
    q.add_argument("--anahtar", help="Cevap anahtarı, örneğin BEDACDEDBCBEAAC ('-' soruyu atlar)")
    q.add_argument("--liste", help="Öğrenci listesi (xlsx, xls, csv)")
    q.add_argument("--cikti", help="Raporların yazılacağı klasör")
    q.add_argument("--okuyucu", help="Okuyucu şablonu (readers/*.json)")
    q.add_argument("--soru-sayisi", type=int)
    q.add_argument("--iptal", help="İptal edilen sorular, örneğin 3,7")
    q.add_argument("--coklu", action="append", help="Birden fazla doğru, örneğin 5=AC (tekrarlanabilir)")
    q.add_argument("--cift-isaret", choices=["bos", "yanlis"])
    q.add_argument("--ceza", type=int, help="Yanlış cezası: bu kadar yanlış bir doğruyu götürür")
    q.add_argument("--yuvarlama", choices=["yarim_yukari", "asagi", "yukari"])
    q.add_argument("--akreditasyon-profili")
    q.add_argument("--not-giris-profili")
    q.add_argument("--sablon", help="Sistemden indirilen akreditasyon şablonu; puanlar içine yazılır")
    q.add_argument("--ders-kodu")
    q.add_argument("--ders-adi")
    q.add_argument("--sinav-turu")
    q.add_argument("--tarih")
    q.add_argument("--saat")
    q.add_argument("--etki-orani")
    q.add_argument("--pdfsiz", action="store_true", help="Özet dosyasını yazma")
    q.add_argument("--ayrintili", action="store_true", help="Her öğrenciyi yazdır")
    q.add_argument("--proje-kaydet", help="Ayarları .osd proje dosyasına kaydet")
    q.set_defaults(islev=puanla)
    o = alt.add_parser("onizle", help="Dosyanın ilk satırlarını ve önerilen soru sayısını göster")
    o.add_argument("--dat", required=True)
    o.add_argument("--satir", type=int, default=5)
    o.set_defaults(islev=onizle)
    return p


def main(argv: list[str] | None = None) -> int:
    for akim in (sys.stdout, sys.stderr):  # Windows konsolunda Türkçe harfler hata vermesin
        try:
            akim.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    a = ayristirici().parse_args(argv)
    if not getattr(a, "komut", None):
        ayristirici().print_help()
        return 1
    return a.islev(a)


