"""Akademik Bilgi Sistemi > Sınav Akreditasyon İşlemleri > "Toplu Aktarım Yap" için soru tanımı metni.

Sistemin örnek aktarım biçimi (13 Kasım 2026'da ekran görüntüsünden): her satır bir soru, sütunlar
    Soru No, Soru Puan, Soru metni, DÇ Sıra, Etki Oran, DÇ Sıra, Etki Oran, ...
Kolon ayracı "Excel'den Kopyalandı" (sekme). DÇ Sıra, dersin bilgi paketindeki öğrenme çıktısı sırasıdır
(Ö05 için 5). Sistem soru puanlarının toplamının ve her sorunun etki oranlarının toplamının %100 olmasını ister.
"""
from __future__ import annotations

import re

from ..core.modeller import CevapAnahtari, PuanlamaAyarlari, PuanYontemi
from ..core.puanlama import esit_soru_puanlari, soru_puanlari


def _cikti_sirasi(kod: str, ders_kodlari: list[str] | None) -> str:
    if ders_kodlari and kod in ders_kodlari:
        return str(ders_kodlari.index(kod) + 1)
    sayi = re.sub(r"\D", "", kod)
    return str(int(sayi)) if sayi else kod


def _puan_metni(deger: str, ayirici: str) -> str:
    s = deger.strip().replace(",", ".")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ayirici)


def soru_tanimi_satirlari(anahtar: CevapAnahtari, ayarlar: PuanlamaAyarlari, ders_kodlari: list[str] | None = None,
                          ondalik_ayirici: str = ",") -> list[list[str]]:
    """Sistemin toplu aktarım tablosu: [Soru No, Soru Puan, Soru metni, DÇ Sıra, Etki Oran, ...]."""
    n = anahtar.soru_sayisi
    if ayarlar.yontem == PuanYontemi.ESIT:
        puanlar = esit_soru_puanlari(ayarlar.toplam_puan, n)  # iki ondalıklı, toplamı tam 100
    else:
        puanlar = [s.puan or "0" for s in anahtar.sorular]
        soru_puanlari(anahtar, ayarlar)  # geçersiz değer varsa burada hata verir
    satirlar = []
    for s, p in zip(anahtar.sorular, puanlar):
        satir = [str(s.no), _puan_metni(p, ondalik_ayirici), f"Soru {s.no}"]
        for kod, yuzde in s.cikti_dagilimi().items():
            satir += [_cikti_sirasi(kod, ders_kodlari), str(yuzde)]
        satirlar.append(satir)
    return satirlar


def soru_tanimi_metni(anahtar: CevapAnahtari, ayarlar: PuanlamaAyarlari, ders_kodlari: list[str] | None = None,
                      ondalik_ayirici: str = ",") -> str:
    """Sistemdeki "Aktarım Kutusu"na yapıştırılacak sekmeyle ayrılmış metin (başlık satırı yok)."""
    return "\n".join("\t".join(s) for s in soru_tanimi_satirlari(anahtar, ayarlar, ders_kodlari, ondalik_ayirici))
