"""Paketle gelen dosyaların (profiller, okuyucu şablonları, simge) ve kullanıcı klasörlerinin yerini bulur.

Kaynak ağacında depo kökündeki `profiles/`, `readers/` ve `assets/` klasörleri; PyInstaller paketinde
`sys._MEIPASS` altındaki kopyaları kullanılır. Kullanıcının kaydettiği profiller uygulama veri klasöründedir.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def kok() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def paket_klasoru(ad: str) -> Path:
    return kok() / ad


def kullanici_klasoru() -> Path:
    """Kullanıcıya özel uygulama veri klasörü.

    Arayüz varken Qt'nin `QStandardPaths.AppDataLocation` yolu, yoksa işletim sistemine uygun eşdeğeri.
    `OPTIK_SINAV_VERI` ortam değişkeni (testler için) her şeyin önüne geçer.
    """
    ortam = os.environ.get("OPTIK_SINAV_VERI")
    if ortam:
        p = Path(ortam)
    else:
        p = None
        try:
            from PySide6.QtCore import QCoreApplication, QStandardPaths

            if QCoreApplication.instance() is not None:
                p = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        except Exception:
            p = None
        if p is None or str(p) in ("", "."):
            if sys.platform == "darwin":
                p = Path.home() / "Library" / "Application Support" / "OptikSinav"
            elif sys.platform.startswith("win"):
                p = Path(os.environ.get("APPDATA", Path.home())) / "OptikSinav"
            else:
                p = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "OptikSinav"
    p.mkdir(parents=True, exist_ok=True)
    return p


def profil_klasorleri() -> list[Path]:
    return [paket_klasoru("profiles"), kullanici_klasoru() / "profiles"]


def okuyucu_klasorleri() -> list[Path]:
    return [paket_klasoru("readers"), kullanici_klasoru() / "readers"]
