from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"
GERCEK = Path(__file__).resolve().parents[1] / "ornek_veri"


@pytest.fixture(autouse=True)
def _kullanici_klasoru(tmp_path, monkeypatch):
    monkeypatch.setenv("OPTIK_SINAV_VERI", str(tmp_path / "kullanici"))


@pytest.fixture
def fix():
    return FIX
