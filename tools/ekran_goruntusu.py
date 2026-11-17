"""README ekran görüntülerini uydurma verilerle üretir.

Çalıştırma: QT_QPA_PLATFORM=offscreen python tools/ekran_goruntusu.py
"""
import os
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "src"))
os.environ.setdefault("OPTIK_SINAV_VERI", tempfile.mkdtemp())

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from optik_sinav.ui.ana_pencere import AnaPencere  # noqa: E402

F = KOK / "tests" / "fixtures"
H = KOK / "docs" / "ekran"
p = AnaPencere()
p.resize(1200, 760)
p.show()
a = p.adimlar[0]
a.ders_kodu.setText("UYD1001")
a.ders_adi.setText("Uydurma Ders")
a._dat_ac(str(F / "uydurma_1254_crlf.dat"))
a._liste_ac(str(F / "uydurma_liste.xlsx"))
app.processEvents()
p.grab().save(str(H / "1_dosyalar.png"))
p.sonraki.click()
an = p.adimlar[1]
an.hizli.setText("ABCDE ABCDE")
an._hizli_uygula()
for i, t in enumerate(["1", "1", "2", "2", "2 %60, 3", "3", "3", "4", "4", "1, 4"]):
    an.satirlar[i].oc.setText(t)
    an._oc_degisti(i)
app.processEvents()
p.grab().save(str(H / "2_anahtar.png"))
p.adim_listesi.setCurrentRow(2)
app.processEvents()
p.grab().save(str(H / "3_kontrol.png"))
p.adim_listesi.setCurrentRow(3)
app.processEvents()
p.grab().save(str(H / "4_sisteme_aktar.png"))
p.adim_listesi.setCurrentRow(4)
app.processEvents()
p.grab().save(str(H / "5_istatistik.png"))
print("Kaydedildi:", *sorted(x.name for x in H.iterdir()))
