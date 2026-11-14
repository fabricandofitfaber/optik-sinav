# PyInstaller yapılandırması. Çalıştırma: pyinstaller --noconfirm optik_sinav.spec
# macOS'ta "Optik Sinav.app", Windows'ta tek klasörlü "OptikSinav/OptikSinav.exe" üretir.
import sys
from pathlib import Path

KOK = Path(SPECPATH)
sys.path.insert(0, str(KOK / "src"))
from optik_sinav import __version__  # noqa: E402

AD = "OptikSinav"
datas = [(str(KOK / "profiles"), "profiles"), (str(KOK / "readers"), "readers"), (str(KOK / "assets"), "assets"), (str(KOK / "dersler"), "dersler")]
# Kullanılmayan büyük modüller dışarıda bırakılır
haric = ["tkinter", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtOpenGL", "PySide6.QtDBus",
         "PySide6.QtWebEngineCore", "PySide6.QtMultimedia", "numpy.tests", "matplotlib.tests", "IPython", "pytest"]

a = Analysis([str(KOK / "paketleme" / "baslat.py")], pathex=[str(KOK / "src")], datas=datas,
             hiddenimports=["openpyxl", "xlrd", "pypdf", "matplotlib.backends.backend_pdf", "matplotlib.backends.backend_agg"],
             excludes=haric, noarchive=False)
pyz = PYZ(a.pure)
simge = str(KOK / "assets" / ("simge.icns" if sys.platform == "darwin" else "simge.ico"))
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=AD, console=False, icon=simge,
          version=str(KOK / "paketleme" / "windows_surum.txt") if sys.platform.startswith("win") else None)
coll = COLLECT(exe, a.binaries, a.datas, name=AD)
if sys.platform == "darwin":
    app = BUNDLE(coll, name="Optik Sinav.app", icon=simge, bundle_identifier="io.github.optiksinav",
                 info_plist={
                     "CFBundleName": "Optik Sınav",
                     "CFBundleDisplayName": "Optik Sınav",
                     "CFBundleShortVersionString": __version__,
                     "CFBundleVersion": __version__,
                     "NSHighResolutionCapable": True,
                     "LSApplicationCategoryType": "public.app-category.education",
                     "CFBundleDocumentTypes": [{"CFBundleTypeName": "Optik Sınav projesi", "CFBundleTypeExtensions": ["osd"],
                                                "CFBundleTypeRole": "Editor"}],
                 })
