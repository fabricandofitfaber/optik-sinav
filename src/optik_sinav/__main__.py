"""Giriş noktası: komut verilirse komut satırı, verilmezse arayüz açılır."""
from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("puanla", "onizle", "-h", "--help"):
        from .cli import main as cli_main

        return cli_main(sys.argv[1:])
    from .ui.ana_pencere import calistir

    return calistir(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
