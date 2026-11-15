from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from ..durum import Durum


class Adim(QWidget):
    """Bir adım sayfası. `eksikler` boşsa "Sonraki" etkinleşir."""

    tamamlik_degisti = Signal()

    def __init__(self, durum: Durum, baslik: str, parent=None):
        super().__init__(parent)
        self.durum = durum
        self.duzen = QVBoxLayout(self)
        b = QLabel(f"<h2>{baslik}</h2>")
        self.baslik_etiketi = b
        self.duzen.addWidget(b)

    def eksikler(self) -> list[str]:
        return []

    def girildi(self) -> None:
        """Adım gösterildiğinde çağrılır."""

    def durumdan_yukle(self) -> None:
        """Proje açıldığında alanları durumdan doldurur."""


def ayirici() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFrameShadow(QFrame.Shadow.Sunken)
    return f
