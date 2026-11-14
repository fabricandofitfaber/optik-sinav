"""Kopyala-yapıştır modu: seçili sütunları, sistemdeki öğrenci sırasıyla, sekmeyle ayrılmış metin olarak hazırlar.

Panoya yazma işi arayüzdedir; burada yalnızca metin üretilir.
"""
from __future__ import annotations

from dataclasses import replace

from ..core.modeller import SinavSonucu
from .profil import Profil, hucre_metni, tablo_uret


def pano_metni(profil: Profil, sonuc: SinavSonucu, sira: list[str] | None = None, basliklarla: bool = False) -> str:
    """Web ekranındaki tabloya yapıştırmak için: satır sonu LF, ayraç sekme, üst satır yok."""
    p = replace(profil, ust_satirlar=[], baslik_satiri_yaz=basliklarla)
    _, basliklar, veri = tablo_uret(p, sonuc, None, sira)
    satirlar = ["\t".join(basliklar)] if basliklarla else []
    satirlar += ["\t".join(hucre_metni(h, p) for h in s) for s in veri]
    return "\n".join(satirlar)
