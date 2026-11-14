"""Excel (xlsx) yazımı: profil tabanlı aktarım dosyası ve ortak biçim yardımcıları."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..core.modeller import SinavBilgisi, SinavSonucu
from .profil import Hucre, Profil, tablo_uret

RENK = {
    "D": "C6EFCE",  # doğru: yeşil
    "Y": "FFC7CE",  # yanlış: kırmızı
    "B": "FFEB9C",  # boş: sarı
    "I": "D9D9D9",  # iptal: gri
    "K": "DDEBF7",  # klasik sınavda kısmi puan: mavi
    "-": "EDEDED",
    "uyari": "FCD5B4",  # uyarılı satır: turuncu
    "baslik": "DDEBF7",
}


def dolgu(renk: str) -> PatternFill:
    return PatternFill("solid", start_color=renk, end_color=renk)


KALIN = Font(bold=True)


def sayi_bicimi(ondalik: int) -> str:
    return "0" if ondalik <= 0 else "0." + "0" * ondalik


def hucre_yaz(ws, satir: int, sutun: int, h: Hucre) -> None:
    c = ws.cell(row=satir, column=sutun)
    if h.tur == "sayi":
        c.value = float(h.deger)  # Decimal zaten yuvarlanmış; float gösterimi tam karşılığıdır
        c.number_format = sayi_bicimi(h.ondalik)
    elif h.tur == "tamsayi":
        c.value = int(h.deger)
        c.number_format = "0"
    elif h.tur == "girmedi":
        c.value = h.deger if h.deger != "" else None
    else:
        c.value = "" if h.deger is None else str(h.deger)
        if c.value == "":
            c.value = None
        c.number_format = "@"


def baslik_satiri(ws, satir: int, basliklar: list[str]) -> None:
    for j, b in enumerate(basliklar, start=1):
        c = ws.cell(row=satir, column=j, value=b)
        c.font = KALIN
        c.fill = dolgu(RENK["baslik"])
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def sutun_genislikleri(ws, genislikler: dict[int, float] | None = None, varsayilan: float = 8) -> None:
    for j in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(j)].width = (genislikler or {}).get(j, varsayilan)


def profil_xlsx_yaz(profil: Profil, sonuc: SinavSonucu, yol: str | Path, sinav: SinavBilgisi | None = None) -> Path:
    ust, basliklar, veri = tablo_uret(profil, sonuc, sinav)
    wb = Workbook()
    ws = wb.active
    ws.title = profil.sayfa_adi[:31] or "Sayfa1"
    r = 1
    for s in ust:
        for j, v in enumerate(s, start=1):
            ws.cell(row=r, column=j, value=v)
        r += 1
    if profil.baslik_satiri_yaz:
        for j, b in enumerate(basliklar, start=1):
            ws.cell(row=r, column=j, value=b).font = KALIN
        r += 1
    for satir in veri:
        for j, h in enumerate(satir, start=1):
            hucre_yaz(ws, r, j, h)
        r += 1
    genislik = {}
    for j, b in enumerate(basliklar, start=1):
        genislik[j] = max(8, min(40, len(b) + 2))
        if b.lower().startswith("ad"):
            genislik[j] = 30
        if "no" in b.lower():
            genislik[j] = 14
    sutun_genislikleri(ws, genislik)
    yol = Path(yol)
    wb.save(yol)
    return yol


def aktarim_yaz(profil: Profil, sonuc: SinavSonucu, yol: str | Path, sinav: SinavBilgisi | None = None) -> Path:
    """Profilin dosya türüne göre doğru yazıcıyı seçer."""
    from .csv_yazici import csv_yaz

    tur = profil.dosya_turu.lower()
    if tur == "xlsx":
        return profil_xlsx_yaz(profil, sonuc, yol, sinav)
    if tur in ("csv", "txt"):
        return csv_yaz(profil, sonuc, yol, sinav)
    if tur == "xls":
        raise ValueError("Eski .xls biçiminde yazma desteklenmiyor; profilde xlsx seçin ya da sistem şablonunu doldurun.")
    raise ValueError(f"Bu profil doğrudan dosya üretmez (tür: {profil.dosya_turu}); 'Sistem şablonunu doldur' kullanın.")


def uzanti(profil: Profil) -> str:
    return {"xlsx": ".xlsx", "csv": ".csv", "txt": ".txt"}.get(profil.dosya_turu.lower(), ".xlsx")
