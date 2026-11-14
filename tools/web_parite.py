"""Tarayıcı sürümünün motoru ile Python motorunun aynı sonucu verdiğini denetlemek için beklenen değerleri yazar.

Senaryolar uydurma test dosyalarıyla kurulur (tests/web/*.json, depoya girer). `ornek_veri/` varsa gerçek sınav
için de bir senaryo yazılır (ornek_veri/web_parite_gercek.json, depoya girmez).
Karşılaştırma: `node web/test/parite.mjs`.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))

from optik_sinav.core import ek_istatistik as E  # noqa: E402
from optik_sinav.core.dogrulama import duzeltme_olustur, sinavi_degerlendir  # noqa: E402
from optik_sinav.core.klasik import klasik_degerlendir  # noqa: E402
from optik_sinav.core.madde_analizi import (  # noqa: E402
    MaddeEsikleri, cikti_dagilimi, cikti_denetimi, madde_analizi, ogrenme_ciktisi_raporu, tam_sayi_dagilim,
)
from optik_sinav.core.donem_sonu import HarfAyarlari, donem_sonu, karneler  # noqa: E402
from optik_sinav.core.modeller import CevapAnahtari, PuanlamaAyarlari  # noqa: E402
from optik_sinav.core.proje import SinavProjesi  # noqa: E402
from optik_sinav.core.puanlama import anahtar_eksikleri  # noqa: E402
from optik_sinav.export.soru_tanimi import soru_tanimi_metni  # noqa: E402
from optik_sinav.io.dat_okuyucu import dat_oku, sablon_oner  # noqa: E402
from optik_sinav.io.kodlama import metin_dosyasi_oku  # noqa: E402
from optik_sinav.io.liste_okuyucu import liste_oku  # noqa: E402

F = KOK / "tests" / "fixtures"


def kesir(x) -> str:
    return f"{x.numerator}/{x.denominator}"


def ciktilar(proje: SinavProjesi, sonuc, ders_kodlari=None) -> dict:
    esik = float(proje.ayarlar.basari_esigi)
    m, g = madde_analizi(sonuc, MaddeEsikleri(basari_esigi=esik, cikti_esigi=esik))
    rapor = ogrenme_ciktisi_raporu(sonuc, esik)
    dag = cikti_dagilimi(sonuc)
    rs = E.rasch(sonuc)
    kk = E.kitapcik_karsilastirma(sonuc)
    t = E.tasarim_denetimi(sonuc, [x.guclik for x in m])
    return {
        "ogrenciler": [{
            "no": o.no, "ad": o.ad, "puan": kesir(o.puan), "ham": kesir(o.ham_puan), "ceza": kesir(o.ceza),
            "durum": "".join(s.durum.value for s in o.sorular), "cevaplar": o.cevaplar, "dogru": o.dogru, "yanlis": o.yanlis,
            "bos": o.bos, "kitapcik": o.kitapcik, "kaynak": o.kaynak_soru, "listede": o.listede, "oneriler": o.oneriler,
            "uyarilar": [[u.tur.value, u.mesaj] for u in o.uyarilar],
        } for o in sonuc.ogrenciler],
        "girmeyenler": [x.no for x in sonuc.girmeyenler],
        "soru_puanlari": [kesir(p) for p in sonuc.soru_puanlari],
        "maddeler": [{
            "soru_no": x.soru_no, "analiz_disi": x.analiz_disi, "guclik": x.guclik, "ayirt": x.ayirt_edicilik,
            "r": x.nokta_cift_serili, "r_duz": x.duzeltilmis_r, "alfa_c": x.alfa_cikarilirsa, "bes": x.bes_grup,
            "sik": x.sik_oranlari, "sorunlar": x.sorunlar, "celdirici": [[c.sik, c.oran, c.ust, c.alt, c.sorunlar] for c in x.celdiriciler],
        } for x in m],
        "genel": {k: getattr(g, k) for k in ("ogrenci_sayisi", "ortalama", "standart_sapma", "en_dusuk", "en_yuksek", "medyan", "kr20",
                                             "birinci_ceyrek", "ucuncu_ceyrek", "carpiklik", "basiklik", "alfa", "olcme_hatasi",
                                             "basari_orani", "ortalama_guclik", "ortalama_ayirt_edicilik", "bos_orani_sirayla",
                                             "hiz_uyarisi", "yorumlar")},
        "kisi_uyumu": [[k.no, k.indeks, k.beklenmedik] for k in g.kisi_uyumu],
        "benzer": [[c.no1, c.no2, c.ayni_yanlis, c.ikisi_yanlis, c.ayni_cevap, c.z] for c in g.benzer_ciftler],
        "cikti_raporu": [[c.tur, c.kod, c.sorular, c.sinif_yuzdesi, c.sinav_agirligi, c.ulasan_orani, c.ogrenci_yuzdeleri] for c in rapor],
        "cikti_dagilimi": {k: kesir(v) for k, v in dag.items()},
        "tam_sayi_dagilim": tam_sayi_dagilim(dag),
        "cikti_denetimi": list(cikti_denetimi(proje.anahtar, ders_kodlari)),
        "anahtar_eksikleri": anahtar_eksikleri(proje.anahtar, proje.ayarlar, proje.klasik),
        "soru_tanimi": soru_tanimi_metni(proje.anahtar, proje.ayarlar, ders_kodlari) if any(s.ogrenme_ciktilari for s in proje.anahtar.sorular) else "",
        "sinir": [[x.no, x.fark] for x in E.sinirdaki_ogrenciler(sonuc, esik, g.olcme_hatasi)],
        "final": [[x.no, x.gereken] for x in E.final_gereken(sonuc, 40, proje.ayarlar.gecme_ortalamasi, proje.ayarlar.final_alt_siniri)],
        "sans": E.sans_puani(sonuc),
        "tasarim": None if t is None else [t.sik_sayilari, t.en_uzun_seri, t.seri_harfi, t.sira_guclik_korelasyonu, t.notlar],
        "kitapcik": None if kk is None else [kk.ortalama1, kk.ortalama2, kk.t, kk.serbestlik, kk.p, kk.etki],
        "rasch": None if rs is None else [rs.soru_zorluklari, rs.en_iyi_olctugu, rs.en_iyi_puan, rs.disarida_kalan_ogrenci, rs.disarida_kalan_soru],
        "kavram": [[k.soru1, k.sik1, k.soru2, k.sik2, k.birlikte, k.secen1, k.secen2, k.kosullu, k.taban, k.phi, k.p] for k in E.kavram_yanilgilari(sonuc)],
        "yapi": None if (y := E.sinav_yapisi(sonuc)) is None else [y.sorular, y.ozdegerler, y.ilk_pay, y.oran_1_2, y.ortalama_korelasyon,
                                                                    {str(k): v for k, v in y.yukler.items()}, y.zayif_sorular, [list(u) for u in y.cikti_uyumu], y.yorum],
        "donem": {yon: _donem(sonuc, proje, yon) for yon in ("mutlak", "bagil")},
        "karne": [[k.no, k.sira, k.yuzdelik, k.ciktilar, k.guclu, k.gelismeli] for k in karneler(sonuc, rapor)],
    }


def _donem(sonuc, proje, yontem):
    finaller = {o.no: (None if i % 7 == 3 else str((i * 37) % 101)) for i, o in enumerate(sonuc.ogrenciler)}
    proje.final_puanlar = finaller
    d = donem_sonu(sonuc, finaller, 40, 50, 50, HarfAyarlari(yontem=yontem, bagil_en_az=3))
    return [d.uygulanan, d.ortalama, d.standart_sapma, d.dagilim, d.notlar_metin,
            [[n.no, n.ham, n.t, n.harf, n.gecti, n.aciklama, n.sinirda] for n in d.notlar]]


def optik_senaryo(ad: str, dat: Path, liste: Path | None, proje: SinavProjesi, duzelt=None, ders_kodlari=None) -> dict:
    satirlar, _, _ = metin_dosyasi_oku(dat)
    proje.okuyucu = sablon_oner(satirlar, proje.okuyucu)
    okuma = dat_oku(dat, proje.okuyucu)
    lst = liste_oku(liste) if liste else None
    if duzelt:
        for satir_no, alan, yeni in duzelt:
            k = next(x for x in okuma.kayitlar if x.satir_no == satir_no)
            d = duzeltme_olustur(k, alan, yeni, proje.duzeltmeler, kim="test")
            d.zaman = ""
            proje.duzeltmeler.append(d)
    sonuc = sinavi_degerlendir(okuma.kayitlar, proje.anahtar, proje.ayarlar, lst, proje.duzeltmeler)
    return {"ad": ad, "dat": str(dat.relative_to(KOK)), "liste": str(liste.relative_to(KOK)) if liste else None,
            "proje": proje.to_dict(), "ders_kodlari": ders_kodlari, "okuyucu_onerisi": proje.okuyucu.to_dict(),
            "kodlama": okuma.kodlama, "beklenen": ciktilar(proje, sonuc, ders_kodlari)}


def anahtar_kur(metin: str, n: int) -> CevapAnahtari:
    return CevapAnahtari.metinden(metin, n)


def main():
    cikis = KOK / "tests" / "web"
    cikis.mkdir(parents=True, exist_ok=True)
    senaryolar = []
    dat, liste = F / "uydurma_1254_crlf.dat", F / "uydurma_liste.xlsx"
    oc = ["Ö01"], ["Ö01", "Ö02"], ["Ö02"], ["Ö03"], ["Ö03", "Ö04"], ["Ö04"], ["Ö05"], ["Ö05"], ["Ö01", "Ö05"], ["Ö02"]

    # 1) Eşit puan, öğrenme çıktıları, düzeltme
    p = SinavProjesi()
    p.anahtar = anahtar_kur("ABCDEABCDE", 10)
    for s, c in zip(p.anahtar.sorular, oc):
        s.ogrenme_ciktilari = list(c)
    p.anahtar.sorular[4].cikti_yuzdeleri = {"Ö03": 70, "Ö04": 30}
    p.anahtar.sorular[0].program_ciktilari = ["P01"]
    senaryolar.append(optik_senaryo("esit", dat, liste, p, [(3, "no", "990000008"), (4, "cevap:2", "B")], ["Ö01", "Ö02", "Ö03", "Ö04", "Ö05"]))

    # 2) Soru bazlı puan, yanlış cezası, çift işaret yanlış, iptal ve çoklu doğru
    p = SinavProjesi()
    p.anahtar = anahtar_kur("ABCDEABCDE", 10)
    p.ayarlar = PuanlamaAyarlari.from_dict({"yontem": "soru_bazli", "yanlis_cezasi": True, "ceza_orani": 4, "cift_isaret": "yanlis",
                                            "yuvarlama": "asagi", "ondalik": 1})
    for s, puan in zip(p.anahtar.sorular, ["5", "5", "7.5", "7.5", "10", "10", "12.5", "12.5", "15", "15"]):
        s.puan = puan
    p.anahtar.sorular[2].durum = p.anahtar.sorular[2].durum.__class__("iptal")
    p.anahtar.sorular[5].durum = p.anahtar.sorular[5].durum.__class__("coklu")
    p.anahtar.sorular[5].dogru = "AB"
    senaryolar.append(optik_senaryo("soru_bazli_ceza", dat, liste, p))

    # 3) Kitapçık: B ters sırada, bazı öğrenciler B
    p = SinavProjesi()
    p.anahtar = anahtar_kur("ABCDEABCDE", 10)
    p.anahtar.kitapcik_anahtarlari = {"B": "EDCBAEDCBA"}
    p.anahtar.kitapcik_eslemesi = {"B": {1: 10, 10: 1, 2: 9, 9: 2}}
    senaryolar.append(optik_senaryo("kitapcik", dat, liste, p, [(1, "kitapcik", "B"), (2, "kitapcik", "B"), (5, "kitapcik", "C")]))

    # 4) Klasik sınav
    p = SinavProjesi()
    p.bicim = "klasik"
    p.klasik_soru_sayisi = 4
    p.anahtar = CevapAnahtari.metinden("----", 4)
    p.ayarlar = PuanlamaAyarlari.from_dict({"yontem": "soru_bazli"})
    for s, puan, c in zip(p.anahtar.sorular, ["10", "25", "25", "40"], (["Ö01"], ["Ö02"], ["Ö02", "Ö03"], ["Ö04"])):
        s.puan, s.ogrenme_ciktilari = puan, list(c)
    lst = liste_oku(liste)
    rnd = random.Random(7)
    for i, og in enumerate(lst.ogrenciler[:-2]):
        p.klasik_puanlar[og.no] = [str(rnd.randint(0, 10)), f"{rnd.randint(0, 50) / 2:g}".replace(".", ","), None if i == 3 else str(rnd.randint(0, 25)), str(rnd.randint(0, 45))]
    nolar = list(p.klasik_puanlar)
    p.klasik_toplamlar = {nolar[0]: "999", nolar[1]: "abc"}
    sonuc = klasik_degerlendir(lst, p.anahtar, p.ayarlar, p.klasik_puanlar, p.klasik_toplamlar)
    senaryolar.append({"ad": "klasik", "dat": None, "liste": str(liste.relative_to(KOK)), "proje": p.to_dict(), "ders_kodlari": None,
                       "beklenen": ciktilar(p, sonuc)})

    for s in senaryolar:
        (cikis / f"parite_{s['ad']}.json").write_text(json.dumps(s, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("Yazıldı:", ", ".join(s["ad"] for s in senaryolar))

    gercek = KOK / "ornek_veri"
    if (gercek / "YATIRIM_61.dat").exists():
        p = SinavProjesi()
        p.anahtar = anahtar_kur("BEDACDEDBCBEAAC", 15)
        kod = [["Ö01"], ["Ö01"], ["Ö02"], ["Ö02"], ["Ö02", "Ö03"], ["Ö03"], ["Ö03"], ["Ö04"], ["Ö04"], ["Ö04"], ["Ö01", "Ö04"], ["Ö05"], ["Ö05"], ["Ö05"], ["Ö01"]]
        for s, c in zip(p.anahtar.sorular, kod):
            s.ogrenme_ciktilari = c
        s = optik_senaryo("gercek", gercek / "YATIRIM_61.dat", gercek / "YATIRIM61.xlsx", p, None, ["Ö01", "Ö02", "Ö03", "Ö04", "Ö05"])
        (gercek / "web_parite_gercek.json").write_text(json.dumps(s, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print("Gerçek sınav senaryosu yazıldı (ornek_veri/, depoya girmez).")


if __name__ == "__main__":
    main()
