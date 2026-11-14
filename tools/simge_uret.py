"""assets/simge.svg dosyasından simge.png, simge.ico ve simge.icns üretir (yalnızca Qt kullanır).

Çalıştırma: QT_QPA_PLATFORM=offscreen python tools/simge_uret.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

KOK = Path(__file__).resolve().parents[1]
A = KOK / "assets"


def ciz(boyut: int) -> QImage:
    img = QImage(boyut, boyut, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(str(A / "simge.svg")).render(p)
    p.end()
    return img


def png_bayt(img: QImage) -> bytes:
    ba = QByteArray()
    b = QBuffer(ba)
    b.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(b, "PNG")
    return bytes(ba.data())


def ico_yaz(yol: Path, boyutlar=(16, 24, 32, 48, 64, 128, 256)) -> None:
    pngler = [png_bayt(ciz(n)) for n in boyutlar]
    baslik = struct.pack("<HHH", 0, 1, len(boyutlar))
    ofset = 6 + 16 * len(boyutlar)
    girdiler, veri = b"", b""
    for n, png in zip(boyutlar, pngler):
        girdiler += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(png), ofset + len(veri))
        veri += png
    yol.write_bytes(baslik + girdiler + veri)


def icns_yaz(yol: Path) -> None:
    turler = [("icp4", 16), ("icp5", 32), ("icp6", 64), ("ic07", 128), ("ic08", 256), ("ic09", 512), ("ic10", 1024)]
    govde = b""
    for tur, n in turler:
        png = png_bayt(ciz(n))
        govde += tur.encode() + struct.pack(">I", len(png) + 8) + png
    yol.write_bytes(b"icns" + struct.pack(">I", len(govde) + 8) + govde)


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841
    ciz(512).save(str(A / "simge.png"))
    ico_yaz(A / "simge.ico")
    icns_yaz(A / "simge.icns")
    print("Üretildi:", *(p.name for p in sorted(A.iterdir())))


if __name__ == "__main__":
    main()
