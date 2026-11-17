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
    sorular = [anahtar.sorular[i] for i in anahtar.aktarim_sorulari()]  # bonus soru sisteme gitmez
    n = len(sorular)
    if ayarlar.yontem == PuanYontemi.ESIT:
        puanlar = esit_soru_puanlari(ayarlar.toplam_puan, n)  # iki ondalıklı, toplamı tam 100
    else:
        puanlar = [s.puan or "0" for s in sorular]
        soru_puanlari(anahtar, ayarlar)  # geçersiz değer varsa burada hata verir
    satirlar = []
    for no, (s, p) in enumerate(zip(sorular, puanlar), start=1):
        satir = [str(no), _puan_metni(p, ondalik_ayirici), f"Soru {no}"]
        for kod, yuzde in s.cikti_dagilimi().items():
            satir += [_cikti_sirasi(kod, ders_kodlari), str(yuzde)]
        satirlar.append(satir)
    return satirlar


def soru_tanimi_metni(anahtar: CevapAnahtari, ayarlar: PuanlamaAyarlari, ders_kodlari: list[str] | None = None,
                      ondalik_ayirici: str = ",") -> str:
    """Sistemdeki "Aktarım Kutusu"na yapıştırılacak sekmeyle ayrılmış metin (başlık satırı yok)."""
    return "\n".join("\t".join(s) for s in soru_tanimi_satirlari(anahtar, ayarlar, ders_kodlari, ondalik_ayirici))


SORU_TANIMI_ADIMLARI = [
    "Akademik Bilgi Sistemi'nde Sınav Akreditasyon İşlemleri'nde dersi ve sınavı açın.",
    "\"Toplu Sınav Soru Tanım\" kutusunda \"Toplu Aktarım Yap\" seçin.",
    "\"Kolon Ayracı\" \"Excel'den Kopyalandı\" olsun.",
    "Bu dosyanın ilk sayfasında (Aktarım) bütün hücreleri seçip kopyalayın (Cmd+A, Cmd+C ya da Ctrl+A, Ctrl+C).",
    "Sistemdeki Aktarım Kutusu'na tıklayıp yapıştırın ve \"Aktar\" düğmesine basın.",
]


def soru_tanimi_yaz(anahtar: CevapAnahtari, ayarlar: PuanlamaAyarlari, ders_kodlari: list[str] | None, yol) -> "Path":
    """Soru tanımını Excel dosyası olarak yazar: ilk sayfa yalnızca aktarılacak satırlar (başlıksız; hepsini seçip
    kopyalayıp sistemin Aktarım Kutusu'na yapıştırmak için), ikinci sayfa sütunların anlamı ve adımlar.
    Değerler metin olarak yazılır: kopyalanınca panodaki metinle (soru_tanimi_metni) birebir aynı olur."""
    from pathlib import Path

    from openpyxl import Workbook
    from openpyxl.styles import Font

    satirlar = soru_tanimi_satirlari(anahtar, ayarlar, ders_kodlari)
    wb = Workbook()
    ws = wb.active
    ws.title = "Aktarım"
    for r, satir in enumerate(satirlar, start=1):
        for c, v in enumerate(satir, start=1):
            h = ws.cell(row=r, column=c, value=v)
            h.number_format = "@"
    ws.column_dimensions["C"].width = 12
    a = wb.create_sheet("Açıklama")
    a.cell(row=1, column=1, value="Soru tanımı: Akademik Bilgi Sistemi'ne nasıl aktarılır?").font = Font(bold=True, size=13)
    for i, adim in enumerate(SORU_TANIMI_ADIMLARI, start=1):
        a.cell(row=2 + i, column=1, value=f"{i}. {adim}")
    a.cell(row=9, column=1, value="Aktarım sayfasındaki sütunlar").font = Font(bold=True)
    for i, (b, m) in enumerate((("Soru No", "1'den başlar; bonus soru gönderilmez."), ("Soru Puan", "Soru puanlarının toplamı 100."),
                                ("Soru metni", "\"Soru 1\", \"Soru 2\" … (sistemde değiştirebilirsiniz)."),
                                ("DÇ Sıra", "Dersin öğrenme çıktısının sırası (Ö05 için 5)."),
                                ("Etki Oran", "Sorunun o çıktıya katkı yüzdesi; her sorunun oranları toplamı 100."),
                                ("…", "Soru birden çok çıktıya bağlıysa DÇ Sıra ve Etki Oran çiftleri sağa doğru devam eder.")), start=10):
        a.cell(row=i, column=1, value=b).font = Font(bold=True)
        a.cell(row=i, column=2, value=m)
    a.column_dimensions["A"].width = 30
    a.column_dimensions["B"].width = 80
    Path(yol).parent.mkdir(parents=True, exist_ok=True)
    wb.save(yol)
    return Path(yol)
