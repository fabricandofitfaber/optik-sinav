"""Profil tanımına göre csv ya da txt aktarım dosyası yazar (bayt bayt belirlenmiş çıktı)."""
from __future__ import annotations

from pathlib import Path

from ..core.modeller import SinavBilgisi, SinavSonucu
from .profil import Profil, hucre_metni, tablo_uret


def _alan(metin: str, ayrac: str) -> str:
    if ayrac and (ayrac in metin or '"' in metin or "\n" in metin or "\r" in metin):
        return '"' + metin.replace('"', '""') + '"'
    return metin


def metin_uret(profil: Profil, sonuc: SinavSonucu, sinav: SinavBilgisi | None = None, sira: list[str] | None = None) -> str:
    ust, basliklar, veri = tablo_uret(profil, sonuc, sinav, sira)
    ayrac = "\t" if profil.ayrac in ("\\t", "tab", "sekme") else profil.ayrac
    satirlar = [ayrac.join(_alan(h, ayrac) for h in s) for s in ust]
    if profil.baslik_satiri_yaz:
        satirlar.append(ayrac.join(_alan(b, ayrac) for b in basliklar))
    for s in veri:
        satirlar.append(ayrac.join(_alan(hucre_metni(h, profil), ayrac) for h in s))
    son = profil.satir_sonu_karakteri
    return son.join(satirlar) + son


def csv_yaz(profil: Profil, sonuc: SinavSonucu, yol: str | Path, sinav: SinavBilgisi | None = None) -> Path:
    yol = Path(yol)
    kodlama = {"windows-1254": "cp1254"}.get(profil.kodlama.lower(), profil.kodlama)
    yol.write_bytes(metin_uret(profil, sonuc, sinav).encode(kodlama, errors="replace"))
    return yol
