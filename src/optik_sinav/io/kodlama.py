"""Metin dosyalarının kodlamasını ve satır sonunu algılar.

Okuma sırası: katı UTF-8 (başta BOM varsa atılır), olmazsa Windows-1254, olmazsa Latin-1.
"""
from __future__ import annotations

from pathlib import Path

BOZUK_KARAKTER = "�"


def baytlari_coz(veri: bytes) -> tuple[str, str]:
    """(metin, kodlama adı) döndürür."""
    if veri.startswith(b"\xef\xbb\xbf"):
        return veri[3:].decode("utf-8", errors="replace"), "utf-8-sig"
    try:
        return veri.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return veri.decode("cp1254"), "windows-1254"
    except UnicodeDecodeError:
        return veri.decode("latin-1"), "latin-1"


def satir_sonu_algila(metin: str) -> str:
    crlf = metin.count("\r\n")
    cr = metin.count("\r") - crlf
    lf = metin.count("\n") - crlf
    turler = [ad for ad, n in (("CRLF", crlf), ("LF", lf), ("CR", cr)) if n]
    if not turler:
        return "LF"
    return turler[0] if len(turler) == 1 else "karışık"


def satirlara_bol(metin: str) -> list[str]:
    """CRLF, LF ve CR satır sonlarını tanır. Sondaki tek boş satır atılır.

    `str.splitlines` kullanılmaz; o, sayfa sonu gibi başka karakterlerde de böler.
    """
    satirlar = metin.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if satirlar and satirlar[-1] == "":
        satirlar.pop()
    return satirlar


def metin_dosyasi_oku(yol: str | Path) -> tuple[list[str], str, str]:
    """(satırlar, kodlama, satır sonu) döndürür."""
    metin, kodlama = baytlari_coz(Path(yol).read_bytes())
    return satirlara_bol(metin), kodlama, satir_sonu_algila(metin)
