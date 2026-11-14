"""Ana pencere: solda adımlar, sağda içerik, altta Geri ve Sonraki."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from .. import __version__
from .. import metinler as M
from ..kaynaklar import paket_klasoru
from .adimlar.anahtar import AnahtarAdimi
from .adimlar.disa_aktar import DisaAktarAdimi
from .adimlar.dosyalar import DosyalarAdimi
from .adimlar.istatistik import IstatistikAdimi
from .adimlar.kontrol import KontrolAdimi
from .adimlar.puanlama import PuanlamaAdimi
from .durum import Durum, son_acilanlar


class AnaPencere(QMainWindow):
    def __init__(self):
        super().__init__()
        self.durum = Durum()
        self.setWindowTitle(M.UYGULAMA_ADI)
        self.resize(1200, 800)

        merkez = QWidget()
        yatay = QHBoxLayout(merkez)
        self.adim_listesi = QListWidget()
        self.adim_listesi.addItems(M.ADIMLAR)
        self.adim_listesi.setFixedWidth(210)
        self.adim_listesi.currentRowChanged.connect(self._adima_git)
        yatay.addWidget(self.adim_listesi)

        sag = QVBoxLayout()
        self.yigin = QStackedWidget()
        self.adimlar = [DosyalarAdimi(self.durum), AnahtarAdimi(self.durum), PuanlamaAdimi(self.durum),
                        KontrolAdimi(self.durum), IstatistikAdimi(self.durum), DisaAktarAdimi(self.durum)]
        for a in self.adimlar:
            self.yigin.addWidget(a)
            a.tamamlik_degisti.connect(self._dugmeleri_guncelle)
        sag.addWidget(self.yigin, 1)
        alt = QHBoxLayout()
        self.eksik = QLabel()
        self.eksik.setWordWrap(True)
        self.eksik.setStyleSheet("color: #C0504D")
        alt.addWidget(self.eksik, 1)
        self.geri = QPushButton("Geri")
        self.geri.clicked.connect(lambda: self.adim_listesi.setCurrentRow(self.yigin.currentIndex() - 1))
        self.sonraki = QPushButton("Sonraki")
        self.sonraki.setToolTip("Ctrl+Enter")
        self.sonraki.setShortcut(QKeySequence("Ctrl+Return"))
        self.sonraki.clicked.connect(lambda: self.adim_listesi.setCurrentRow(self.yigin.currentIndex() + 1))
        alt.addWidget(self.geri)
        alt.addWidget(self.sonraki)
        sag.addLayout(alt)
        yatay.addLayout(sag, 1)
        self.setCentralWidget(merkez)
        self._menuler()
        self.adim_listesi.setCurrentRow(0)
        self.durum.degisti.connect(self._dugmeleri_guncelle)
        self._dugmeleri_guncelle()

    # ---------------------------------------------------------------- menüler
    def _menuler(self):
        m = self.menuBar().addMenu("Dosya")
        for metin, kisayol, islev in (
            ("Yeni sınav", QKeySequence.StandardKey.New, self.yeni),
            ("Sınav aç…", QKeySequence.StandardKey.Open, self.proje_ac_sec),
            ("Kaydet", QKeySequence.StandardKey.Save, self.kaydet),
            ("Farklı kaydet…", QKeySequence.StandardKey.SaveAs, self.farkli_kaydet),
        ):
            e = QAction(metin, self)
            e.setShortcut(kisayol)
            e.triggered.connect(islev)
            m.addAction(e)
        self.son_menu = m.addMenu("Son açılanlar")
        self.son_menu.aboutToShow.connect(self._son_menuyu_doldur)
        m.addSeparator()
        e = QAction("Çıkış", self)
        e.setShortcut(QKeySequence.StandardKey.Quit)
        e.triggered.connect(self.close)
        m.addAction(e)
        y = self.menuBar().addMenu("Yardım")
        e = QAction("Hakkında", self)
        e.triggered.connect(lambda: QMessageBox.about(self, M.UYGULAMA_ADI, f"{M.UYGULAMA_ADI} {__version__}\n\n"
                                                      "Optik okuyucu dosyalarını soru bazında puanlar. Çevrim dışı çalışır; "
                                                      "öğrenci verisi bilgisayarınızdan dışarı gönderilmez.\n\nMIT lisansı."))
        y.addAction(e)

    def _son_menuyu_doldur(self):
        self.son_menu.clear()
        yollar = son_acilanlar()
        if not yollar:
            self.son_menu.addAction("(boş)").setEnabled(False)
        for y in yollar:
            self.son_menu.addAction(y, lambda y=y: self.proje_ac(y))

    # ---------------------------------------------------------------- gezinme
    def _adima_git(self, i: int):
        if i < 0:
            return
        onceki = self.yigin.currentIndex()
        # İleri atlarken aradaki adımların zorunlu bilgileri tam olmalı
        for j in range(min(onceki, i), i):
            if j < i and self.adimlar[j].eksikler():
                self.adim_listesi.blockSignals(True)
                self.adim_listesi.setCurrentRow(j)
                self.adim_listesi.blockSignals(False)
                self.yigin.setCurrentIndex(j)
                self.adimlar[j].girildi()
                self._dugmeleri_guncelle()
                return
        self.yigin.setCurrentIndex(i)
        self.adimlar[i].girildi()
        self._dugmeleri_guncelle()

    def _dugmeleri_guncelle(self):
        i = self.yigin.currentIndex()
        eksik = self.adimlar[i].eksikler() if i >= 0 else []
        self.geri.setEnabled(i > 0)
        self.sonraki.setEnabled(i < len(self.adimlar) - 1 and not eksik)
        self.eksik.setText(("Eksik: " + " ".join(eksik)) if eksik else "")
        baslik = M.UYGULAMA_ADI
        if self.durum.proje_yolu:
            baslik += f" — {self.durum.proje_yolu.name}"
        self.setWindowTitle(baslik)

    # ---------------------------------------------------------------- proje dosyası
    def yeni(self):
        if QMessageBox.question(self, "Yeni sınav", "Kaydedilmemiş değişiklikler kaybolur. Devam edilsin mi?") != QMessageBox.StandardButton.Yes:
            return
        self.durum.yeni()
        for a in self.adimlar:
            a.durumdan_yukle()
        self.durum.degisti.emit()
        self.adim_listesi.setCurrentRow(0)

    def proje_ac_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Sınav aç", "", "Sınav projesi (*.osd)")
        if yol:
            self.proje_ac(yol)

    def proje_ac(self, yol: str):
        try:
            eksik = self.durum.ac(yol)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Açılamadı", str(e))
            return
        for a in self.adimlar:
            a.durumdan_yukle()
        if eksik:
            QMessageBox.warning(self, "Eksik dosya", "Şu kaynak dosyalar bulunamadı; 1. adımda yeniden seçin:\n" + "\n".join(eksik))
        self.adim_listesi.setCurrentRow(0)
        self._dugmeleri_guncelle()

    def kaydet(self):
        if self.durum.proje_yolu is None:
            return self.farkli_kaydet()
        self.durum.kaydet()
        self.statusBar().showMessage(f"Kaydedildi: {self.durum.proje_yolu}", 4000)

    def farkli_kaydet(self):
        from ..core.ciktilar import cikti_adi

        oneri = cikti_adi(self.durum.proje.sinav, "sinav", ".osd")
        klasor = Path(self.durum.proje.dat_yolu).parent if self.durum.proje.dat_yolu else Path.home()
        yol, _ = QFileDialog.getSaveFileName(self, "Farklı kaydet", str(klasor / oneri), "Sınav projesi (*.osd)")
        if yol:
            hedef = self.durum.kaydet(yol)
            self.statusBar().showMessage(f"Kaydedildi: {hedef}", 4000)
            self._dugmeleri_guncelle()


def simge() -> QIcon:
    for ad in ("simge.png", "simge.svg"):
        p = paket_klasoru("assets") / ad
        if p.exists():
            return QIcon(str(p))
    return QIcon()


def calistir(argv: list[str] | None = None) -> int:
    argv = argv or []
    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName(M.UYGULAMA_ADI)
    app.setOrganizationName(M.KURULUS)
    app.setWindowIcon(simge())
    # Qt'nin kendi düğmeleri (Tamam, İptal, Evet, Hayır) Türkçe görünsün
    from PySide6.QtCore import QLibraryInfo, QTranslator

    ceviri = QTranslator(app)
    if ceviri.load("qtbase_tr", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(ceviri)
    p = AnaPencere()
    p.show()
    for a in argv:
        if a.lower().endswith(".osd") and Path(a).exists():
            p.proje_ac(a)
    return app.exec()


