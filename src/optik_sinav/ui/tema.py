"""Renkler. Açık ve koyu tema işletim sistemine uyar; durum renkleri iki temada da okunur kalır."""
from __future__ import annotations

from PySide6.QtGui import QColor, QGuiApplication, QPalette


def koyu_mu() -> bool:
    app = QGuiApplication.instance()
    if app is None:
        return False
    return app.palette().color(QPalette.ColorRole.Window).lightness() < 128


_ACIK = {
    "D": "#C6EFCE", "K": "#DDEBF7", "Y": "#FFC7CE", "B": "#FFEB9C", "I": "#D9D9D9", "-": "#EDEDED", "uyari": "#FCD5B4",
    "ad": "#DDEBF7", "no": "#E2EFDA", "cevap": "#FFF2CC", "kitapcik": "#EAD1F5", "disari": "#F8CBAD",
}
_KOYU = {
    "D": "#1E5631", "K": "#203F5E", "Y": "#7A1F28", "B": "#6B5A12", "I": "#4A4A4A", "-": "#3A3A3A", "uyari": "#7A4A12",
    "ad": "#203F5E", "no": "#2E4A24", "cevap": "#5A4A10", "kitapcik": "#4A2E5E", "disari": "#7A3A1E",
}


def renk(ad: str) -> QColor:
    return QColor((_KOYU if koyu_mu() else _ACIK)[ad])


def renk_hex(ad: str) -> str:
    return (_KOYU if koyu_mu() else _ACIK)[ad]
