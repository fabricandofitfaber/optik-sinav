"""tests/fixtures/ altındaki uydurma test dosyalarını üretir. Bütün ad ve numaralar uydurmadır.

Çalıştırma: python tools/fixture_uret.py
"""
from __future__ import annotations

from pathlib import Path

import openpyxl

KOK = Path(__file__).resolve().parents[1]
F = KOK / "tests" / "fixtures"

ANAHTAR = "ABCDEABCDE"  # 10 soru


def satir(ad: str, no: str, cevap: str, ek: dict[int, str] | None = None, uzunluk: int = 136) -> str:
    s = list(ad.ljust(25)[:25] + no.ljust(9)[:9] + "  " + cevap.ljust(10)[:10])
    s += [" "] * (uzunluk - len(s))
    for konum, c in (ek or {}).items():
        s[konum - 1] = c
    return "".join(s)


def dat_satirlari() -> list[str]:
    return [
        satir("ÇİĞDEM ÖZTÜRK", "990000001", "ABCDEABCDE"),                 # 10 doğru
        satir("ŞÜKRÜ IŞIK", "990000002", "ABCDEABCDA"),                    # 9 doğru 1 yanlış
        satir("AYŞE GÜNEŞ", "990000003", "ABC  ABC  "),                    # 6 doğru 4 boş
        satir("MEHMET ÇAKIR", "99000*004", "EEEEEEEEEE"),                  # numarada okunamayan karakter
        satir("", "990000005", "ABCDEABCDE"),                              # boş ad
        satir("ZEYNEP DEMİR", "990000006", "AB*DEABCDE"),                  # çift işaret
        satir("ALİ VELİ", "990000007", "ABCDEABCDE", {67: "A"}),          # alan dışı işaret
        satir("HASAN KAYA", "990000088", "BBBBBBBBBB"),                    # listede olmayan numara (öneri: 990000008)
        satir("FATMA YILDIZ", "990000009", "ABCDEABCDE"),                  # aynı numara
        satir("FATMA YILDIZ", "990000009", "ABCDEABCDE"),                  # aynı numara (ikinci kez)
        ("EMRE ŞAHİN".ljust(25) + "990000010" + "  " + "ABCDE"),          # kısa satır: son 5 cevap boş
    ]


LISTE = [
    ("990000001", "ÇİĞDEM ÖZTÜRK"),
    ("990000002", "ŞÜKRÜ IŞIK"),
    ("990000003", "AYŞE GÜNEŞ"),
    ("990000004", "MEHMET ÇAKIR"),
    ("990000005", "BURAK ERDOĞAN"),
    ("990000006", "ZEYNEP DEMİR"),
    ("990000007", "ALİ VELİ"),
    ("990000008", "HASAN KAYA"),
    ("990000009", "FATMA YILDIZ"),
    ("990000010", "EMRE ŞAHİN"),
    ("990000011", "GÜL ÖZDEMİR"),       # sınava girmedi
    ("990000012", "İSMAİL KOÇ"),        # sınava girmedi
]


def main() -> None:
    F.mkdir(parents=True, exist_ok=True)
    satirlar = dat_satirlari()
    (F / "uydurma_1254_crlf.dat").write_bytes(("\r\n".join(satirlar) + "\r\n").encode("cp1254"))
    (F / "uydurma_utf8_lf.dat").write_bytes(("\n".join(satirlar) + "\n").encode("utf-8"))
    # Aktarım sırasında bozulmuş dosya: Türkçe harfler yerine U+FFFD
    bozuk = [s.translate(str.maketrans({c: "�" for c in "ÇİĞÖŞÜIçığöşü" if c not in "I"})) for s in satirlar]
    (F / "uydurma_bozuk_utf8.dat").write_bytes(("\r\n".join(bozuk) + "\r\n").encode("utf-8"))

    # Eski okuma programının Excel çıktısını taklit eden liste
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ktt"
    ws["J1"] = "AWRG"
    ws.append(["Sınıf", None, "Öğr.No", "Adı Soyadı", "Telefon", "TEORİK", "Pratik", "PDÖ", "TOPLAM", "1D", "1Y", "1N", "1puan"])
    # append ilk boş satırdan sonra eklediği için başlığı 2. satıra taşı
    ws.delete_rows(2, ws.max_row)
    basliklar = ["Sınıf", None, "Öğr.No", "Adı Soyadı", "Telefon", "TEORİK", "Pratik", "PDÖ", "TOPLAM", "1D", "1Y", "1N", "1puan"]
    for j, b in enumerate(basliklar, start=1):
        ws.cell(row=2, column=j, value=b)
    for i, (no, ad) in enumerate(LISTE, start=3):
        ws.cell(row=i, column=1, value=" ")
        ws.cell(row=i, column=3, value=int(no))
        ws.cell(row=i, column=4, value=ad.ljust(25))
        ws.cell(row=i, column=5, value=" ")
    wb.save(F / "uydurma_liste.xlsx")

    # Sistem şablonunu taklit eden dosya (gerçek biçim bilinmiyor; şablon doldurma testi için)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Öğrenciler"
    ws["A1"] = "UYDURMA DERS - Soru Bazlı Not Girişi"
    basliklar = ["Sıra", "Öğrenci No", "Adı", "Soyadı"] + [f"S{k}" for k in range(1, 11)] + ["Toplam"]
    for j, b in enumerate(basliklar, start=1):
        ws.cell(row=3, column=j, value=b)
    sira = [LISTE[i] for i in (11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)]  # sistem sırası farklı
    for i, (no, ad) in enumerate(sira, start=4):
        ws.cell(row=i, column=1, value=i - 3)
        ws.cell(row=i, column=2, value=no)  # metin olarak
        parcalar = ad.split()
        ws.cell(row=i, column=3, value=" ".join(parcalar[:-1]))
        ws.cell(row=i, column=4, value=parcalar[-1])
    wb.save(F / "uydurma_sablon.xlsx")

    # Başlıksız csv liste
    (F / "uydurma_liste.csv").write_bytes(("\r\n".join(f"{no};{ad}" for no, ad in LISTE) + "\r\n").encode("cp1254"))
    liste_pdf_uret(F / "uydurma_liste.pdf")
    print("Üretildi:", *sorted(p.name for p in F.iterdir()))


def liste_pdf_uret(hedef: Path) -> None:
    """Sınav yoklama listesine benzeyen uydurma PDF: sıra, numara, ad soyad, program ve imza sütunları."""
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["pdf.fonttype"] = 42  # metin seçilebilir ve okunabilir kalsın
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.06, 0.95, "UYDURMA ÜNİVERSİTESİ - SINAV YOKLAMA LİSTESİ", fontsize=12, weight="bold")
    fig.text(0.06, 0.925, "Ders: UYD1001 Uydurma Ders    Sınav: Ara Sınav", fontsize=9)
    sutunlar = [(0.06, "Sıra"), (0.13, "Öğrenci No"), (0.32, "Adı Soyadı"), (0.62, "Program"), (0.85, "İmza")]
    y = 0.89
    for x, t in sutunlar:
        fig.text(x, y, t, fontsize=9, weight="bold")
    for i, (no, ad) in enumerate(LISTE, start=1):
        y -= 0.025
        for x, t in zip((c[0] for c in sutunlar), (str(i), no, ad, "İŞLETME (İÖ)")):
            fig.text(x, y, t, fontsize=9)
    fig.text(0.06, y - 0.05, f"Toplam öğrenci: {len(LISTE)}", fontsize=9)
    fig.savefig(hedef, format="pdf", metadata={"CreationDate": None, "Creator": None, "Producer": None})
    plt.close(fig)


if __name__ == "__main__":
    main()
