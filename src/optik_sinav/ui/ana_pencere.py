"""Ana pencere: solda adımlar, sağda içerik, altta Geri ve Sonraki."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTime, QTimer
from PySide6.QtGui import QColor, QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QScrollArea, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
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
from .durum import Durum, kurtarma_ozeti, kurtarmayi_yedekle, osd_okunur_adi, son_acilanlar


class KaydirmaAlani(QScrollArea):
    """Adım sayfası için kaydırma alanı. Satıra kayan yazıların o anki genişlikte gerçekten istediği yüksekliği
    sayfaya en az yükseklik olarak verir: yazı sığmazsa kesilmez, sayfa aşağı kayar."""

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)

    def setWidget(self, w):
        super().setWidget(w)
        w.installEventFilter(self)

    def eventFilter(self, nesne, olay):
        if nesne is self.widget() and olay.type() == QEvent.Type.LayoutRequest:
            self._yukseklik()
        return super().eventFilter(nesne, olay)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._yukseklik()

    def _yukseklik(self):
        w = self.widget()
        duzen = w.layout() if w else None
        if duzen is None or not duzen.hasHeightForWidth():
            return
        gerekli = max(duzen.totalHeightForWidth(self.viewport().width()), duzen.totalMinimumSize().height())
        if w.minimumHeight() != gerekli:
            w.setMinimumHeight(gerekli)


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
        self.adim_listesi.setFixedWidth(230)
        self.adim_listesi.setStyleSheet("QListWidget { font-size: 14px; } QListWidget::item { padding: 8px 6px; }")
        self.adim_listesi.currentRowChanged.connect(self._adima_git)
        yatay.addWidget(self.adim_listesi)

        sag = QVBoxLayout()
        # Sınav kimliği: her adımın üstünde hangi sınavla çalışıldığı; tıklayınca 1. adıma gider
        self.kimlik = QLabel()
        self.kimlik.setWordWrap(True)
        self.kimlik.setTextFormat(Qt.TextFormat.RichText)
        self.kimlik.setStyleSheet("QLabel { background: rgba(47, 85, 151, 0.10); border: 1px solid rgba(47, 85, 151, 0.35); "
                                  "border-radius: 6px; padding: 6px 10px; font-size: 14px; }")
        self.kimlik.setToolTip("Açık sınav. Bilgileri değiştirmek için \"düzenle\"ye tıklayın.")
        self.kimlik.linkActivated.connect(lambda _x: self.adim_listesi.setCurrentRow(0))
        sag.addWidget(self.kimlik)
        self.serit = QLabel()
        self.serit.setWordWrap(True)
        self.serit.setStyleSheet("background: #fff4e5; color: #7a4100; border: 1px solid #f0c27a; border-radius: 6px; padding: 8px;")
        self.serit.linkActivated.connect(lambda j: self.adim_listesi.setCurrentRow(int(j)))
        self.serit.setVisible(False)
        sag.addWidget(self.serit)
        self.yigin = QStackedWidget()
        self.adimlar = [DosyalarAdimi(self.durum), AnahtarAdimi(self.durum), KontrolAdimi(self.durum),
                        DisaAktarAdimi(self.durum), IstatistikAdimi(self.durum)]
        for a in self.adimlar:
            kaydirma = KaydirmaAlani()
            kaydirma.setWidget(a)
            self.yigin.addWidget(kaydirma)
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
        self.durum.sonuc_degisti.connect(self._dugmeleri_guncelle)
        self._dugmeleri_guncelle()
        # Otomatik kayıt: iki saniyede bir, yalnızca değişiklik varsa yazar (puan girişi dahil her şey)
        self.kayit_etiketi = QLabel()
        self.statusBar().addPermanentWidget(self.kayit_etiketi)
        self.durum.kaydedildi.connect(self._kayit_etiketini_yaz)
        self._kayit_etiketini_yaz()
        self.kayit_zamanlayici = QTimer(self)
        self.kayit_zamanlayici.setInterval(2000)
        self.kayit_zamanlayici.timeout.connect(self.otomatik_kaydet)
        self.kayit_zamanlayici.start()

    def _kayit_etiketini_yaz(self):
        metin, kalici = self.durum.kayit_ozeti()
        self.kayit_etiketi.setText(metin.split(" (")[0].split(". Kalıcı")[0])
        self.kayit_etiketi.setStyleSheet("color: #1e7b34" if kalici else "color: #9a5b00")
        self.kayit_etiketi.setToolTip(metin)

    def otomatik_kaydet(self):
        try:
            if self.durum.otomatik_kaydet():
                self.statusBar().showMessage(f"Otomatik kaydedildi ({QTime.currentTime().toString('HH:mm:ss')})", 3000)
        except OSError as e:
            self.statusBar().showMessage(f"Otomatik kayıt yapılamadı: {e}", 8000)

    def closeEvent(self, e):
        self.otomatik_kaydet()
        super().closeEvent(e)

    def kurtarmayi_sor(self) -> bool:
        """Yarım kalan çalışma varsa devam edilip edilmeyeceğini sorar. Açtıysa True."""
        o = kurtarma_ozeti()
        if not o:
            return False
        ayrinti = f"{o['ad']}" + (f", {o['puanli']} öğrencinin puanı girilmiş" if o["klasik"] else "")
        if o["zaman"]:
            ayrinti += f" (son kayıt {o['zaman']})"
        k = QMessageBox.question(self, "Kaldığınız yerden devam",
                                 f"Son çalışmanız otomatik kaydedilmiş:\n{ayrinti}\n\nKaldığınız yerden devam edilsin mi?\n"
                                 "Hayır derseniz o çalışma silinmez, yedek klasörüne alınır.")
        if k != QMessageBox.StandardButton.Yes:
            kurtarmayi_yedekle()
            return False
        try:
            eksik = self.durum.kurtarmadan_ac()
        except Exception as hata:  # noqa: BLE001
            QMessageBox.warning(self, "Açılamadı", str(hata))
            return False
        for a in self.adimlar:
            a.durumdan_yukle()
        if eksik:
            QMessageBox.warning(self, "Eksik dosya", "Şu kaynak dosyalar bulunamadı; 1. adımda yeniden seçin:\n" + "\n".join(eksik))
        self.durum._son_ozet = None
        self.adim_listesi.setCurrentRow(2 if self.durum.proje.klasik and self.durum.liste is not None else 0)
        self._dugmeleri_guncelle()
        return True

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
            e = self.son_menu.addAction(osd_okunur_adi(y), lambda y=y: self.proje_ac(y))
            e.setToolTip(y)
        self.son_menu.setToolTipsVisible(True)

    # ---------------------------------------------------------------- gezinme
    def _adima_git(self, i: int):
        # Adımlar arasında serbestçe dolaşılır; eksikler engellemez, sayfanın üstünde gösterilir.
        if i < 0:
            return
        self.yigin.setCurrentIndex(i)
        self.adimlar[i].girildi()
        self._dugmeleri_guncelle()

    def adim_adi(self, j: int) -> str:
        klasik = self.durum.proje.klasik
        if klasik and j == 1:
            return M.ADIM_KLASIK_2
        if klasik and j == 2:
            return M.ADIM_KLASIK_3
        return M.ADIMLAR[j]

    def _dugmeleri_guncelle(self):
        i = self.yigin.currentIndex()
        eksik = self.adimlar[i].eksikler() if i >= 0 else []
        self.geri.setEnabled(i > 0)
        self.sonraki.setEnabled(i < len(self.adimlar) - 1)
        self.eksik.setText(("Eksik: " + " ".join(eksik)) if eksik else "")
        # Hazırlık adımlarının (1-2) durumu: listede işaret, sonuç adımlarında (3-5) üstte şerit
        on = [(j, self.adimlar[j].eksikler()) for j in range(2)]
        tamam = True  # bir adım, kendisi ve öncekiler eksiksizse işaretlenir
        for j, e in on:
            tamam = tamam and not e
            self.adim_listesi.item(j).setText(self.adim_adi(j) + ("  ✓" if tamam else "  •" if e else ""))
        sonuc = self.durum.sonuc
        p = self.durum.proje
        if p.klasik and self.durum.liste is not None:
            # klasik: puanı girilen ya da "girmedi" işaretli öğrenci sayısı; hepsi bitince ✓
            L = self.durum.liste.ogrenciler
            bitti = sum(1 for o in L if o.no in p.klasik_girmedi or any(x not in (None, "") for x in (p.klasik_puanlar.get(o.no) or [])))
            k3 = "  ✓" if L and bitti == len(L) else f"  ({bitti}/{len(L)})" if bitti else ""
        else:
            k3 = "" if sonuc is None else "  ✓"
            if sonuc is not None and any(o.uyarilar for o in sonuc.ogrenciler):
                k3 = f"  ({sum(1 for o in sonuc.ogrenciler if o.uyarilar)} uyarı)"
        self.adim_listesi.item(2).setText(self.adim_adi(2) + k3)
        for j in (3, 4):
            self.adim_listesi.item(j).setText(self.adim_adi(j))
        self.adim_listesi.item(4).setForeground(QColor("gray"))  # isteğe bağlı
        if i >= 2:
            satirlar = [f"<a href='{j}'>{j + 1}. adım</a>: {' '.join(e)}" for j, e in on if e]
            if self.durum.sonuc is None and not satirlar:
                satirlar = [" ".join(self.durum.hesap_eksikleri())]
            self.serit.setText("<b>Sonuç için önce bunlar tamamlanmalı.</b><br>" + "<br>".join(satirlar))
            self.serit.setVisible(bool(satirlar) and self.durum.sonuc is None)
        else:
            self.serit.setVisible(False)
        self.kimlik.setText(self.durum.sinav_kimligi() + "  <a href='duzenle' style='font-size:12px'>düzenle</a>")
        # pencere başlığı: Dock'ta ve görev çubuğunda hangi sınavın açık olduğu görünsün
        baslik = f"{self.durum.sinav_kisa_adi()} — {M.UYGULAMA_ADI}"
        if self.durum.proje_yolu:
            baslik += f" ({self.durum.proje_yolu.name})"
        self.setWindowTitle(baslik)

    # ---------------------------------------------------------------- proje dosyası
    def yeni(self):
        metin = ("Açık sınav kapatılıp yeni sınav başlatılsın mı? Şimdiki çalışma "
                 + (f"{self.durum.proje_yolu.name} dosyasında ve " if self.durum.proje_yolu else "") + "yedek klasöründe saklanır.")
        if QMessageBox.question(self, "Yeni sınav", metin) != QMessageBox.StandardButton.Yes:
            return
        self.otomatik_kaydet()
        kurtarmayi_yedekle()
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
    acilacak = [a for a in argv if a.lower().endswith(".osd") and Path(a).exists()]
    for a in acilacak:
        p.proje_ac(a)
    if not acilacak:
        p.kurtarmayi_sor()
    return app.exec()


