"""Tarayıcı sürümünün motoru Python motoruyla aynı sonucu veriyor mu? (Node.js yoksa atlanır.)

Beklenen değerler `python tools/web_parite.py` ile tests/web/ altına yazılır.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js kurulu değil")
def test_tarayici_motoru_python_ile_ayni():
    r = subprocess.run(["node", str(KOK / "web" / "test" / "parite.mjs")], capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "bütün değerler aynı" in r.stdout
