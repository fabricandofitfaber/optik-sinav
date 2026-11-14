"""Çıktı dosya adları ve rapor tablolarının içerik kuralları (yazımdan bağımsız)."""
from __future__ import annotations

import re
import unicodedata

from .modeller import SinavBilgisi


def dosya_adi_parcasi(metin: str) -> str:
    """Türkçe harfleri sadeleştirir, boşlukları atar: 'Ara Sınav' -> 'AraSinav'."""
    s = metin.translate(str.maketrans("ıİğĞüÜşŞöÖçÇ", "iIgGuUsSoOcC"))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9_-]", "", s.title().replace(" ", "")) if " " in s else re.sub(r"[^A-Za-z0-9_-]", "", s)


def cikti_adi(sinav: SinavBilgisi, ek: str, uzanti: str = ".xlsx") -> str:
    """Örnek: UTL4513_AraSinav_2026-11-10_sonuc.xlsx"""
    parcalar = [dosya_adi_parcasi(sinav.ders_kodu) or "SINAV", dosya_adi_parcasi(sinav.sinav_turu) or "Sinav"]
    if sinav.tarih:
        parcalar.append(re.sub(r"[^0-9-]", "", sinav.tarih))
    parcalar.append(ek)
    return "_".join(p for p in parcalar if p) + uzanti
