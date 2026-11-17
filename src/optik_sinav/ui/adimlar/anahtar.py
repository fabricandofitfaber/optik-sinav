"""2. adım: cevap anahtarı (optik formdaki gibi yuvarlak şıklar), soru puanları, kitapçıklar ve öğrenme çıktıları.

Klavye: soru tablosuna tıkladıktan sonra A-E harfine basmak o sorunun şıkkını seçip sonraki soruya geçer;
Boşluk ya da Sil şıkkı temizler, yukarı ve aşağı oklar soru değiştirir.
"""
from __future__ import annotations

import re
from fractions import Fraction

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSpinBox, QTabBar, QToolButton, QVBoxLayout, QWidget,
)

from ... import metinler as M
from ...core.madde_analizi import cikti_atamasi_esit_mi, cikti_dagilimi, cikti_denetimi, ciktilari_esit_dagit
from ...core.modeller import SIKLAR, CevapAnahtari, PuanYontemi, SoruDurumu, esit_yuzdeler
from ...core.klasik import puan_listesi_coz
from ...core.puanlama import anahtar_eksikleri, esit_soru_puanlari, sayi_yaz, soru_puanlari
from ..tema import koyu_mu
from .temel import Adim, menu_dugmesi

BONUS_NOTU = ("Bonus soru {no}: doğru cevaplayan öğrencinin bir yanlışını (yoksa bir boşunu) doğru sayar; bütün soruları doğru olan öğrencide sayılmaz, puan toplamı geçmez. Akademik Bilgi Sistemi'ne gönderilen soru tanımında ve aktarım dosyasında bonus görünmez; öteki sorular 1'den yeniden numaralanır.")


# ---------------------------------------------------------------- çıktı metni
def kod_normalle(ham: str, bilinen: list[str], onek: str) -> str:
    """"1", "ö1", "Ö01" gibi yazımları derste tanımlı koda çevirir ("Ö01")."""
    t = ham.strip().upper().replace("O", "Ö") if onek == "Ö" else ham.strip().upper()
    sayi = re.sub(r"\D", "", t)
    if sayi:
        for k in bilinen:
            if re.sub(r"\D", "", k) and int(re.sub(r"\D", "", k)) == int(sayi):
                return k
        return f"{onek}{int(sayi):02d}"
    return t


def ciktilari_coz(metin: str, bilinen: list[str], onek: str = "Ö") -> tuple[list[str], dict[str, int]]:
    """"Ö01 %60, Ö02 %40", "1, 3" ya da "1 70; 2 30" yazımlarını çözer. Yüzde yazılmayanlara kalan eşit dağıtılır."""
    kodlar, yuzde = [], {}
    for parca in re.split(r"[,;]+", metin):
        parca = parca.strip()
        if not parca:
            continue
        m = re.match(r"^([^\s%]+)\s*(?:%?\s*(\d{1,3})\s*%?)?$", parca)
        if not m:
            raise ValueError(f"Anlaşılamadı: {parca!r}. Örnek yazım: Ö01 %60, Ö02 %40")
        kod = kod_normalle(m.group(1), bilinen, onek)
        if kod in kodlar:
            continue
        kodlar.append(kod)
        if m.group(2) is not None:
            yuzde[kod] = int(m.group(2))
    if yuzde and len(yuzde) < len(kodlar):
        bos = [k for k in kodlar if k not in yuzde]
        kalan = 100 - sum(yuzde.values())
        if kalan < 0:
            raise ValueError("Yazılan yüzdeler 100'ü aşıyor.")
        for k, v in zip(bos, esit_yuzdeler(len(bos), kalan)):
            yuzde[k] = v
    return kodlar, (yuzde if yuzde else {})


def ciktilari_yaz(kodlar: list[str], dagilim: dict[str, int]) -> str:
    if len(kodlar) <= 1:
        return ", ".join(kodlar)
    return ", ".join(f"{k} %{dagilim.get(k, 0)}" for k in kodlar)


class CiktiPenceresi(QDialog):
    """Bir sorunun öğrenme çıktılarını ve yüzdelerini seçme penceresi. Toplam 100 olmadan onaylanmaz."""

    def __init__(self, soru_no: int, kodlar: list[str], dagilim: dict[str, int], ders_kodlari: list[str],
                 aciklamalar: dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{soru_no}. sorunun öğrenme çıktıları")
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Sorunun ölçtüğü çıktıları işaretleyin. Yüzdelerin toplamı 100 olmalı."))
        izgara = QGridLayout()
        self.satirlar: list[tuple[str, QCheckBox, QSpinBox]] = []
        tum = list(dict.fromkeys(ders_kodlari + kodlar))
        for i, k in enumerate(tum):
            cb = QCheckBox(f"{k}  {aciklamalar.get(k, '')}")
            cb.setChecked(k in kodlar)
            sp = QSpinBox(minimum=0, maximum=100, suffix=" %")
            sp.setValue(dagilim.get(k, 0) if k in kodlar else 0)
            sp.setEnabled(k in kodlar)
            cb.toggled.connect(lambda acik, sp=sp: self._isaret(sp, acik))
            sp.valueChanged.connect(self._toplam)
            izgara.addWidget(cb, i, 0)
            izgara.addWidget(sp, i, 1)
            self.satirlar.append((k, cb, sp))
        v.addLayout(izgara)
        s = QHBoxLayout()
        b = QPushButton("Eşit dağıt")
        b.clicked.connect(self._esit)
        s.addWidget(b)
        self.toplam = QLabel()
        s.addWidget(self.toplam, 1)
        v.addLayout(s)
        self.dugmeler = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.dugmeler.accepted.connect(self.accept)
        self.dugmeler.rejected.connect(self.reject)
        v.addWidget(self.dugmeler)
        if not tum:
            v.insertWidget(1, QLabel("Ders bilgi paketi yüklenmedi. 1. adımda PDF'i yükleyin ya da kodları soru satırına elle yazın."))
        self._toplam()

    def _isaret(self, sp: QSpinBox, acik: bool):
        sp.setEnabled(acik)
        if not acik:
            sp.setValue(0)
        self._esit()

    def _esit(self):
        secili = [sp for _, cb, sp in self.satirlar if cb.isChecked()]
        for sp, y in zip(secili, esit_yuzdeler(len(secili))):
            sp.blockSignals(True)
            sp.setValue(y)
            sp.blockSignals(False)
        self._toplam()

    def _toplam(self, *_):
        secili = [(k, sp.value()) for k, cb, sp in self.satirlar if cb.isChecked()]
        t = sum(y for _, y in secili)
        tamam = not secili or t == 100
        self.toplam.setText(f"Toplam: %{t}" + ("" if tamam else "  (100 olmalı)"))
        self.toplam.setStyleSheet("" if tamam else "color: #C0504D; font-weight: bold")
        self.dugmeler.button(QDialogButtonBox.StandardButton.Ok).setEnabled(tamam)

    def sonuc(self) -> tuple[list[str], dict[str, int]]:
        secili = [(k, sp.value()) for k, cb, sp in self.satirlar if cb.isChecked()]
        return [k for k, _ in secili], {k: y for k, y in secili}


# ---------------------------------------------------------------- satır ögeleri
class Kabarcik(QToolButton):
    """Optik formdaki gibi yuvarlak şık düğmesi."""

    def __init__(self, harf: str, parent=None):
        super().__init__(parent)
        self.setText(harf)
        self.setCheckable(True)
        self.setFixedSize(28, 28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        cerceve = "#888" if not koyu_mu() else "#aaa"
        self.setStyleSheet(
            f"QToolButton {{ border: 1.5px solid {cerceve}; border-radius: 14px; font-weight: bold; background: transparent; }}"
            "QToolButton:checked { background: #2F5597; color: white; border-color: #2F5597; }"
            "QToolButton:hover:!checked { background: rgba(47, 85, 151, 0.15); }")


class Izgara(QWidget):
    """Soru satırlarının kabı; klavye girişini yakalar."""

    tus = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, e):
        metin = e.text().upper()
        if metin and metin in SIKLAR:
            self.tus.emit(metin)
        elif e.key() in (Qt.Key.Key_Space, Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Minus):
            self.tus.emit("SIL")
        elif e.key() == Qt.Key.Key_Down:
            self.tus.emit("ASAGI")
        elif e.key() == Qt.Key.Key_Up:
            self.tus.emit("YUKARI")
        else:
            super().keyPressEvent(e)


class DurumDugmesi(QPushButton):
    """Soru durumu: açılır liste yerine tıkladıkça sıradakine geçen düğme (Normal → İptal → Birden fazla doğru → Bonus).
    macOS'un yeni sürümlerinde açılır kutuların listesi ekrana çizilmediği için (kullanıcı bildirimi, 17 Kasım 2026)."""

    degisti = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sira = [d.value for d in SoruDurumu]
        self._deger = SoruDurumu.NORMAL.value
        self.setToolTip("Tıkladıkça değişir: " + " → ".join(M.SORU_DURUMU_ADI[d] for d in self._sira) + ".")
        self.clicked.connect(self._sonraki)
        self._yaz()

    def _yaz(self):
        self.setText(M.SORU_DURUMU_ADI[self._deger])
        self.setStyleSheet("" if self._deger == SoruDurumu.NORMAL.value else "font-weight: bold; color: #2F5597")

    def _sonraki(self):
        self._deger = self._sira[(self._sira.index(self._deger) + 1) % len(self._sira)]
        self._yaz()
        self.degisti.emit()

    def deger(self) -> str:
        return self._deger

    def deger_yaz(self, deger: str):
        self._deger = deger
        self._yaz()


class SoruSatiri:
    def __init__(self):
        self.no: QLabel | None = None
        self.kabarciklar: dict[str, Kabarcik] = {}
        self.durum: DurumDugmesi | None = None
        self.puan: QDoubleSpinBox | None = None
        self.oc: QLineEdit | None = None
        self.oc_dugme: QToolButton | None = None
        self.pc: QLineEdit | None = None
        self.esleme: QSpinBox | None = None


# ---------------------------------------------------------------- adım
class AnahtarAdimi(Adim):
    def __init__(self, durum, parent=None):
        super().__init__(durum, M.ADIMLAR[1], parent)
        self._yukleniyor = False
        self.satirlar: list[SoruSatiri] = []
        self.etkin = 0  # klavyeyle işaretlenecek satır
        self._kurulu = None  # (soru sayısı, kip, kitapçık) — değişince ızgara yeniden kurulur

        # --- üst: kitapçık sekmeleri ve hızlı giriş
        self.ust = QWidget()
        u = QVBoxLayout(self.ust)
        u.setContentsMargins(0, 0, 0, 0)
        s = QHBoxLayout()
        self.sekmeler = QTabBar()
        self.sekmeler.currentChanged.connect(self._kitapcik_secildi)
        s.addWidget(self.sekmeler)
        self.kitapcik_ekle = QPushButton("Kitapçık ekle (B, C…)")
        self.kitapcik_ekle.setToolTip("Farklı soru sırası ya da farklı şık sırası olan kitapçık türü ekler.")
        self.kitapcik_ekle.clicked.connect(self._kitapcik_ekle)
        s.addWidget(self.kitapcik_ekle)
        self.kitapcik_sil = QPushButton("Bu kitapçığı sil")
        self.kitapcik_sil.clicked.connect(self._kitapcik_sil)
        s.addWidget(self.kitapcik_sil)
        s.addStretch(1)
        u.addLayout(s)
        s = QHBoxLayout()
        self.hizli_etiket = QLabel("Hızlı giriş:")
        s.addWidget(self.hizli_etiket)
        self.hizli = QLineEdit()
        self.hizli.returnPressed.connect(self._hizli_uygula)
        self.hizli.editingFinished.connect(self._klasik_odaktan_cikinca)
        s.addWidget(self.hizli, 1)
        b = QPushButton("Uygula")
        b.clicked.connect(self._hizli_uygula)
        s.addWidget(b)
        u.addLayout(s)
        # Bonus soru: açılır kutuya gerek kalmadan numarayla seçilir
        self.bonus_satiri = QWidget()
        s = QHBoxLayout(self.bonus_satiri)
        s.setContentsMargins(0, 0, 0, 0)
        s.addWidget(QLabel("Bonus soru:"))
        self.bonus = QLineEdit()
        self.bonus.setPlaceholderText("örnek: 17")
        self.bonus.setFixedWidth(120)
        self.bonus.editingFinished.connect(self._bonus_degisti)
        s.addWidget(self.bonus)
        l = QLabel("Numarasını yazıp Enter'a basın (birden çoksa virgülle). Bonus soru toplama girmez; doğru yapan öğrencinin bir "
                   "yanlışını (yoksa bir boşunu) doğru sayar. Kaldırmak için kutuyu boşaltın.")
        l.setWordWrap(True)
        l.setStyleSheet("color: gray")
        s.addWidget(l, 1)
        u.addWidget(self.bonus_satiri)
        self.kitapcik_bilgi = QLabel()
        self.kitapcik_bilgi.setWordWrap(True)
        u.addWidget(self.kitapcik_bilgi)
        self.duzen.addWidget(self.ust)

        # --- soru ızgarası
        self.izgara = Izgara()
        self.izgara.tus.connect(self._tus)
        self.izgara_duzen = QGridLayout(self.izgara)
        self.izgara_duzen.setHorizontalSpacing(6)
        self.izgara_duzen.setVerticalSpacing(3)
        self.cikti_serit = QWidget()
        s = QHBoxLayout(self.cikti_serit)
        s.setContentsMargins(0, 2, 0, 2)
        self.cikti_bilgi = QLabel()
        self.cikti_bilgi.setWordWrap(True)
        s.addWidget(self.cikti_bilgi, 1)
        self.cikti_sayisi_etiketi = QLabel("Dersin öğrenme çıktısı sayısı:")
        s.addWidget(self.cikti_sayisi_etiketi)
        self.cikti_sayisi_kutusu = QSpinBox()
        self.cikti_sayisi_kutusu.setRange(0, 30)
        self.cikti_sayisi_kutusu.setSpecialValueText("—")
        self.cikti_sayisi_kutusu.setToolTip("Ders bilgi paketi yüklenmemişse dersin kaç öğrenme çıktısı olduğunu yazın "
                                            "(Ö01, Ö02 …); sorulara eşit dağıtılır.")
        self.cikti_sayisi_kutusu.valueChanged.connect(self._cikti_sayisi_degisti)
        s.addWidget(self.cikti_sayisi_kutusu)
        self.esit_dagit_dugmesi = QPushButton("Öğrenme çıktılarını eşit dağıt")
        self.esit_dagit_dugmesi.setToolTip("Soruları dersin öğrenme çıktılarına sırayla, eşit sayıda paylaştırır; her soru bir çıktıya bağlanır.")
        self.esit_dagit_dugmesi.clicked.connect(self._sirayla_dagit)
        s.addWidget(self.esit_dagit_dugmesi)
        self.duzen.addWidget(self.cikti_serit)
        self.kaydirma = QScrollArea()
        self.kaydirma.setWidgetResizable(True)
        self.kaydirma.setWidget(self.izgara)
        self.duzen.addWidget(self.kaydirma, 1)
        # klasik sınav: soru ekle / son soruyu çıkar
        self.soru_dugmeleri = QWidget()
        s = QHBoxLayout(self.soru_dugmeleri)
        s.setContentsMargins(0, 0, 0, 0)
        b = QPushButton("+ Soru ekle")
        b.clicked.connect(self._soru_ekle)
        s.addWidget(b)
        b = QPushButton("− Son soruyu çıkar")
        b.clicked.connect(self._soru_cikar)
        s.addWidget(b)
        s.addStretch(1)
        self.duzen.addWidget(self.soru_dugmeleri)
        self.ipucu = QLabel()
        self.ipucu.setWordWrap(True)
        self.ipucu.setStyleSheet("color: gray")
        self.duzen.addWidget(self.ipucu)
        self.pc_goster = QCheckBox("Program çıktıları sütununu göster (genellikle gerekmez: sistem bunları ders öğrenme çıktılarından hesaplar)")
        self.pc_goster.setStyleSheet("color: gray")
        self.pc_goster.toggled.connect(lambda _x: self._sutunlari_goster())
        self.duzen.addWidget(self.pc_goster)

        # --- alt: puan ve çıktı özeti
        alt = QFrame()
        alt.setFrameShape(QFrame.Shape.StyledPanel)
        a = QVBoxLayout(alt)
        s = QHBoxLayout()
        self.puan_ozeti = QLabel()
        s.addWidget(self.puan_ozeti, 1)
        b = QPushButton("Puanları eşit dağıt")
        b.setToolTip("Toplam puanı sorulara eşit böler (kesir olarak tutulur; 15 soruda 15 doğru tam 100).")
        b.clicked.connect(self._esit_puan)
        s.addWidget(b)
        a.addLayout(s)
        self.cikti_ozeti = QLabel()
        self.cikti_ozeti.setWordWrap(True)
        self.cikti_ozeti.setTextFormat(Qt.TextFormat.RichText)
        a.addWidget(self.cikti_ozeti)
        s = QHBoxLayout()
        b1 = QPushButton("Bütün sorulara çıktıyı sırayla dağıt")
        b1.setToolTip("Soruları dersin öğrenme çıktılarına sırayla, eşit sayıda paylaştırır. Sonra tek tek düzeltebilirsiniz.")
        b1.clicked.connect(self._sirayla_dagit)
        b2 = QPushButton("Ders eşlemesini kaydet")
        b2.setToolTip("Soru ile çıktı eşlemesini bu ders kodu için saklar; sonraki sınavlarda yüklenebilir.")
        b2.clicked.connect(self._eslemeyi_kaydet)
        b3 = QPushButton("Kayıtlı ders eşlemesini yükle")
        b3.clicked.connect(self._eslemeyi_yukle)
        self.sistem_dugmesi = QPushButton("Soru tanımını sistem için kopyala")
        self.sistem_dugmesi.setToolTip("Akademik Bilgi Sistemi > Sınav Akreditasyon İşlemleri > Toplu Aktarım Yap > Aktarım Kutusu'na "
                                       "yapıştırılacak soru numarası, puan ve öğrenme çıktısı yüzdelerini panoya kopyalar.")
        self.sistem_dugmesi.setStyleSheet("font-weight: bold")
        self.sistem_dugmesi.clicked.connect(self._sisteme_kopyala)
        s = QHBoxLayout()
        s.addWidget(self.sistem_dugmesi)
        s.addWidget(menu_dugmesi("Diğer işlemler", [
            ("Ders eşlemesini kaydet", self._eslemeyi_kaydet, b2.toolTip()),
            ("Kayıtlı ders eşlemesini yükle", self._eslemeyi_yukle, ""),
        ], self))
        s.addStretch(1)
        a.addLayout(s)
        self.duzen.addWidget(alt)

        # Puanlama ayarları: varsayılanlar çoğu sınavda doğrudur; katlanır bölümde, özetiyle
        from PySide6.QtCore import Qt as _Qt
        from PySide6.QtWidgets import QToolButton

        from .puanlama import PuanlamaAdimi

        s = QHBoxLayout()
        self.ayar_dugmesi = QToolButton()
        self.ayar_dugmesi.setText(M.PUANLAMA_AYARLARI)
        self.ayar_dugmesi.setCheckable(True)
        self.ayar_dugmesi.setToolButtonStyle(_Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.ayar_dugmesi.setArrowType(_Qt.ArrowType.RightArrow)
        self.ayar_dugmesi.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self.ayar_dugmesi.toggled.connect(self._ayarlari_ac)
        s.addWidget(self.ayar_dugmesi)
        self.ayar_ozeti = QLabel()
        self.ayar_ozeti.setStyleSheet("color: gray")
        s.addWidget(self.ayar_ozeti, 1)
        self.duzen.addLayout(s)
        self.ayarlar_paneli = PuanlamaAdimi(durum, self)
        self.ayarlar_paneli.setVisible(False)
        self.ayarlar_paneli.tamamlik_degisti.connect(self._ayar_degisti)
        self.duzen.addWidget(self.ayarlar_paneli)
        durum.degisti.connect(self.durumdan_yukle)

    # ---------------------------------------------------------------- yardımcılar
    @property
    def anahtar(self) -> CevapAnahtari:
        return self.durum.proje.anahtar

    @property
    def klasik(self) -> bool:
        return self.durum.proje.klasik

    @property
    def kitapcik(self) -> str:
        i = self.sekmeler.currentIndex()
        return self.sekmeler.tabData(i) if i >= 0 else self.anahtar.ana_kitapcik

    @property
    def ana_mi(self) -> bool:
        return self.klasik or self.kitapcik == self.anahtar.ana_kitapcik

    def _kitapcik_harfleri(self) -> list[str]:
        """Diğer kitapçığın anahtarı, kendi soru sırasıyla, soru sayısı uzunluğunda liste."""
        n = self.anahtar.soru_sayisi
        h = [c for c in self.anahtar.kitapcik_anahtarlari.get(self.kitapcik, "").upper() if not c.isspace()]
        return (h + ["-"] * n)[:n]

    def _kitapcik_harf_yaz(self, i: int, harf: str):
        h = self._kitapcik_harfleri()
        h[i] = harf or "-"
        self.anahtar.kitapcik_anahtarlari[self.kitapcik] = "".join(h)

    def girildi(self):
        self.durumdan_yukle()
        self.ayarlar_paneli.girildi()
        self.izgara.setFocus()

    def _sutunlari_goster(self):
        """Gerekmeyen sütunları gizler: eşit puanda Puan (hepsi aynı), kimse kullanmıyorsa Program çıktıları
        (sistem program çıktılarını ders öğrenme çıktılarından kendisi hesaplar)."""
        if not hasattr(self, "pc_goster"):
            return
        esit = self.durum.proje.ayarlar.yontem == PuanYontemi.ESIT and not self.klasik
        if any(s.program_ciktilari for s in self.anahtar.sorular) and not self.pc_goster.isChecked():
            self.pc_goster.blockSignals(True)
            self.pc_goster.setChecked(True)
            self.pc_goster.blockSignals(False)
        pc = self.pc_goster.isChecked()
        for ad, gorunur in (("Puan", not esit), ("Program çıktıları", pc)):
            if ad in getattr(self, "baslik_w", {}):
                self.baslik_w[ad].setVisible(gorunur)
        for r in getattr(self, "satirlar", []):
            if r.puan is not None:
                r.puan.setVisible(not esit)
            if r.pc is not None:
                r.pc.setVisible(pc)

    def _ayarlari_ac(self, acik: bool):
        self.ayarlar_paneli.setVisible(acik)
        self.ayar_dugmesi.setArrowType(Qt.ArrowType.DownArrow if acik else Qt.ArrowType.RightArrow)

    def _ayar_degisti(self):
        """Puanlama ayarı değişti: puan sütunu, toplam ve özet yenilenir."""
        if getattr(self, "satirlar", None) is not None and len(self.satirlar) == self.anahtar.soru_sayisi and self.ana_mi:
            self._sutunlari_goster()
            self._degerleri_yaz_guvenli()
        self.ayar_ozeti.setText(self.ayarlar_paneli.ozet_metni())
        self._ozet()
        self.tamamlik_degisti.emit()

    def _degerleri_yaz_guvenli(self):
        onceki = self._yukleniyor
        self._yukleniyor = True
        try:
            self._degerleri_yaz()
        finally:
            self._yukleniyor = onceki

    # ---------------------------------------------------------------- kurulum
    def durumdan_yukle(self):
        if self.klasik and self.anahtar.sorular and all(s.puan in (None, "") for s in self.anahtar.sorular):
            for s, p in zip(self.anahtar.sorular, esit_soru_puanlari(self.durum.proje.ayarlar.toplam_puan, self.anahtar.soru_sayisi)):
                s.puan = p
        self._ciktilari_varsayilan_dagit()
        self._yukleniyor = True
        try:
            self._sekmeleri_kur()
            anahtar = (self.anahtar.soru_sayisi, self.klasik, self.kitapcik, tuple(self.durum.ogrenme_kodlari()))
            if anahtar != self._kurulu:
                self._izgarayi_kur()
                self._kurulu = anahtar
            self._degerleri_yaz()
        finally:
            self._yukleniyor = False
        self._ozet()

    def _sekmeleri_kur(self):
        self.ust.setVisible(True)
        for w in (self.kitapcik_ekle, self.kitapcik_sil, self.sekmeler):
            w.setVisible(not self.klasik)
        self.soru_dugmeleri.setVisible(self.klasik)
        self.baslik_etiketi.setText(f"<h2>{M.ADIM_KLASIK_2 if self.klasik else M.ADIMLAR[1]}</h2>")
        if self.klasik:
            self.hizli_etiket.setText("Soru puanları:")
            self.hizli.setPlaceholderText("Sırayla yazın, örneğin 10 10 10 10 20 40. Soru sayısı da buna göre ayarlanır. Enter ile uygulayın.")
            self._hizli_doldur()
        else:
            self.hizli_etiket.setText("Hızlı giriş:")
            self.hizli.setPlaceholderText("Harfleri sırayla yazın, örneğin BEDAC DEDBC BEAAC ('-' soruyu atlar). Enter ile uygulayın.")
        istenen = self.anahtar.kitapciklar() if not self.klasik else []
        mevcut = [self.sekmeler.tabData(i) for i in range(self.sekmeler.count())]
        if istenen != mevcut:
            secili = self.kitapcik if self.sekmeler.count() else None
            self.sekmeler.blockSignals(True)
            while self.sekmeler.count():
                self.sekmeler.removeTab(0)
            for k in istenen:
                i = self.sekmeler.addTab(f"{k} kitapçığı" + (" (ana)" if k == self.anahtar.ana_kitapcik and len(istenen) > 1 else ""))
                self.sekmeler.setTabData(i, k)
            j = istenen.index(secili) if secili in istenen else 0
            self.sekmeler.setCurrentIndex(j)
            self.sekmeler.blockSignals(False)
        self.kitapcik_sil.setVisible(not self.klasik and not self.ana_mi)
        if self.klasik:
            self.kitapcik_bilgi.setText("Klasik sınav: her sorunun puanını ve ölçtüğü öğrenme çıktılarını girin. "
                                        "Öğrencilerin puanları 3. adımda girilir.")
        elif self.ana_mi:
            self.kitapcik_bilgi.setText("Ana kitapçık: soru numaraları bütün çıktılarda bu kitapçığa göredir. "
                                        "Optik formda kitapçık alanı varsa 1. adımda konumunu girin; yoksa 3. adımda öğrencinin kitapçığını seçebilirsiniz."
                                        if len(self.anahtar.kitapciklar()) > 1 else "")
        else:
            self.kitapcik_bilgi.setText(f"{self.kitapcik} kitapçığı: şıkları bu kitapçığın kendi soru sırasıyla işaretleyin. "
                                        "\"Ana kitapçıktaki karşılığı\" sütununa bu sorunun ana kitapçıkta kaçıncı soru olduğunu yazın "
                                        "(sıra aynıysa dokunmayın). Puan ve öğrenme çıktısı ana kitapçıktan gelir.")

    def _izgarayi_kur(self):
        while self.izgara_duzen.count():
            w = self.izgara_duzen.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self.satirlar = []
        n = self.anahtar.soru_sayisi
        kalin = QFont()
        kalin.setBold(True)
        basliklar = ["Soru"]
        if not self.klasik:
            basliklar += ["Doğru şık"]
        if self.ana_mi:
            if not self.klasik:
                basliklar += ["Durum"]
            basliklar += ["Puan", "Öğrenme çıktıları (yüzdeleriyle)", "", "Program çıktıları"]
        else:
            basliklar += ["Ana kitapçıktaki karşılığı"]
        self.baslik_w = {}
        for j, b in enumerate(basliklar):
            l = QLabel(b)
            l.setFont(kalin)
            self.izgara_duzen.addWidget(l, 0, j)
            self.baslik_w[b] = l
        bilinen = self.durum.ogrenme_kodlari()
        for i in range(n):
            r = SoruSatiri()
            j = 0
            r.no = QLabel(str(i + 1))
            r.no.setAlignment(Qt.AlignmentFlag.AlignCenter)
            r.no.setMinimumWidth(30)
            self.izgara_duzen.addWidget(r.no, i + 1, j)
            j += 1
            if not self.klasik:
                kutu = QWidget()
                h = QHBoxLayout(kutu)
                h.setContentsMargins(0, 0, 0, 0)
                h.setSpacing(4)
                for harf in SIKLAR:
                    k = Kabarcik(harf)
                    k.clicked.connect(lambda _x, i=i, harf=harf: self._sik_tiklandi(i, harf))
                    h.addWidget(k)
                    r.kabarciklar[harf] = k
                self.izgara_duzen.addWidget(kutu, i + 1, j)
                j += 1
            if self.ana_mi:
                if not self.klasik:
                    r.durum = DurumDugmesi()
                    r.durum.degisti.connect(lambda i=i: self._durum_degisti(i))
                    self.izgara_duzen.addWidget(r.durum, i + 1, j)
                    j += 1
                r.puan = QDoubleSpinBox(decimals=2, minimum=0, maximum=1000, singleStep=1)
                r.puan.setKeyboardTracking(False)
                r.puan.valueChanged.connect(lambda v, i=i: self._puan_degisti(i, v))
                self.izgara_duzen.addWidget(r.puan, i + 1, j)
                j += 1
                r.oc = QLineEdit(placeholderText="örnek: 1, 3  ya da  Ö01 %60, Ö02 %40")
                r.oc.editingFinished.connect(lambda i=i: self._oc_degisti(i))
                self.izgara_duzen.addWidget(r.oc, i + 1, j)
                j += 1
                r.oc_dugme = QToolButton(text="Seç…")
                r.oc_dugme.setToolTip("Ders bilgi paketindeki çıktılardan seçin ve yüzdelerini girin.")
                r.oc_dugme.clicked.connect(lambda _x, i=i: self._oc_pencere(i))
                self.izgara_duzen.addWidget(r.oc_dugme, i + 1, j)
                j += 1
                r.pc = QLineEdit(placeholderText="örnek: P02, P07")
                r.pc.editingFinished.connect(lambda i=i: self._pc_degisti(i))
                self.izgara_duzen.addWidget(r.pc, i + 1, j)
            else:
                r.esleme = QSpinBox(minimum=1, maximum=max(1, n))
                r.esleme.valueChanged.connect(lambda v, i=i: self._esleme_degisti(i, v))
                self.izgara_duzen.addWidget(r.esleme, i + 1, j)
            self.satirlar.append(r)
        if self.ana_mi:
            self.izgara_duzen.setColumnStretch(len(basliklar) - 3, 3)
            self.izgara_duzen.setColumnStretch(len(basliklar) - 1, 2)
        self._sutunlari_goster()
        self.izgara_duzen.setRowStretch(n + 1, 1)
        # alttaki bölümler açılınca tablo ezilmesin: soru sayısına göre en az yükseklik (en çok 12 satırlık)
        self.kaydirma.setMinimumHeight(min(12, max(n, 1)) * 30 + 40)
        if self.klasik:
            self.ipucu.setText("Puanı değiştirmek için kutuya tıklayıp yazın ya da yukarıdaki satıra bütün puanları sırayla yazın. "
                               + (f"Dersin öğrenme çıktıları: {', '.join(bilinen)}; çıktı sütununa yalnızca numara da yazabilirsiniz (\"1, 3\" → Ö01 ve Ö03 eşit)."
                                  if bilinen else "Ders bilgi paketini 1. adımda yüklerseniz çıktılar açıklamalarıyla seçilebilir."))
        elif bilinen:
            self.ipucu.setText(f"Dersin öğrenme çıktıları: {', '.join(bilinen)}. Çıktı sütununa yalnızca numara da yazabilirsiniz "
                               "(\"1, 3\" → Ö01 ve Ö03 eşit). Klavye: tabloya tıklayıp A-E harflerine basın, otomatik olarak sonraki soruya geçer.")
        else:
            self.ipucu.setText("Klavye: tabloya tıklayıp A-E harflerine basın, otomatik olarak sonraki soruya geçer. "
                               "Ders bilgi paketini 1. adımda yüklerseniz çıktılar açıklamalarıyla seçilebilir.")

    def _bonus_degisti(self):
        if self._yukleniyor or self.klasik:
            return
        n = self.anahtar.soru_sayisi
        metin = self.bonus.text().replace(";", ",").replace(" ", ",")
        try:
            nolar = sorted({int(x) for x in metin.split(",") if x.strip()})
        except ValueError:
            QMessageBox.warning(self, "Bonus soru", "Bonus soru numarasını rakamla yazın, örneğin 17.")
            return
        disarida = [x for x in nolar if not 1 <= x <= n]
        if disarida:
            QMessageBox.warning(self, "Bonus soru", f"{', '.join(map(str, disarida))}. soru yok: sınavda {n} soru var.")
            return
        if nolar and len(nolar) >= n:
            QMessageBox.warning(self, "Bonus soru", "Bütün sorular bonus olamaz.")
            return
        degisti = False
        for s in self.anahtar.sorular:
            if s.no in nolar and s.durum != SoruDurumu.BONUS:
                s.durum = SoruDurumu.BONUS
                if len(s.dogru) > 1:
                    s.dogru = s.dogru[:1]
                degisti = True
            elif s.no not in nolar and s.durum == SoruDurumu.BONUS:
                s.durum = SoruDurumu.NORMAL
                degisti = True
        if degisti:
            self.durumdan_yukle()
            self.tamamlik_degisti.emit()

    def _degerleri_yaz(self):
        a = self.anahtar
        self.bonus_satiri.setVisible(not self.klasik and self.ana_mi)
        if not self.bonus.hasFocus():
            self.bonus.setText(", ".join(str(s.no) for s in a.sorular if s.durum == SoruDurumu.BONUS))
        esit = self.durum.proje.ayarlar.yontem == PuanYontemi.ESIT and not self.klasik
        puanlar = soru_puanlari(a, self.durum.proje.ayarlar) if a.soru_sayisi else []
        harfler = self._kitapcik_harfleri() if not self.ana_mi else None
        esleme = a.esleme(self.kitapcik) if not self.ana_mi else {}
        for i, r in enumerate(self.satirlar):
            s = a.sorular[i]
            dogrular = s.dogru_kume() if self.ana_mi else {harfler[i]} & set(SIKLAR)
            for harf, k in r.kabarciklar.items():
                k.setChecked(harf in dogrular)
                k.setEnabled(s.durum != SoruDurumu.IPTAL or not self.ana_mi)
            if r.durum is not None:
                r.durum.deger_yaz(s.durum.value)
            if r.puan is not None:
                r.puan.blockSignals(True)
                r.puan.setValue(float(puanlar[i]) if puanlar else 0.0)
                r.puan.setToolTip("Eşit puan: kesir olarak tutulur, gösterim yuvarlanmıştır. Değiştirirseniz soru bazlı puana geçilir."
                                  if esit else "")
                r.puan.blockSignals(False)
            if r.oc is not None:
                r.oc.setText(ciktilari_yaz(s.ogrenme_ciktilari, s.cikti_dagilimi()))
            if r.pc is not None:
                r.pc.setText(", ".join(s.program_ciktilari))
            if r.esleme is not None:
                r.esleme.blockSignals(True)
                r.esleme.setValue(esleme.get(i + 1, i + 1))
                r.esleme.blockSignals(False)
        if not self.klasik:
            if self.ana_mi:
                self.hizli.setText(a.metne() if any(s.dogru for s in a.sorular) else "")
            else:
                self.hizli.setText("".join(harfler) if any(h in SIKLAR for h in harfler) else "")
        self._etkin_goster()

    def _etkin_goster(self):
        for i, r in enumerate(self.satirlar):
            secili = i == self.etkin and not self.klasik
            r.no.setText(f"▶ {i + 1}" if secili else str(i + 1))
            r.no.setStyleSheet("color: #2F5597; font-weight: bold" if secili else "")

    # ---------------------------------------------------------------- olaylar
    def _sik_tiklandi(self, i: int, harf: str):
        if self._yukleniyor:
            return
        self.etkin = i
        self._sik_sec(i, harf, tiklama=True)
        self.izgara.setFocus()

    def _sik_sec(self, i: int, harf: str | None, tiklama: bool = False):
        if self.ana_mi:
            s = self.anahtar.sorular[i]
            if harf is None:
                s.dogru = ""
            elif s.durum == SoruDurumu.COKLU:
                kume = s.dogru_kume()
                kume = kume - {harf} if harf in kume else kume | {harf}
                s.dogru = "".join(c for c in SIKLAR if c in kume)
            else:
                s.dogru = "" if (tiklama and s.dogru == harf) else harf
        else:
            mevcut = self._kitapcik_harfleri()[i]
            self._kitapcik_harf_yaz(i, "" if harf is None or (tiklama and mevcut == harf) else harf)
        self._yukleniyor = True
        try:
            self._degerleri_yaz()
        finally:
            self._yukleniyor = False
        self._ozet()

    def _tus(self, t: str):
        n = len(self.satirlar)
        if not n or self.klasik:
            return
        if t == "ASAGI":
            self.etkin = min(n - 1, self.etkin + 1)
        elif t == "YUKARI":
            self.etkin = max(0, self.etkin - 1)
        elif t == "SIL":
            self._sik_sec(self.etkin, None)
            self.etkin = min(n - 1, self.etkin + 1)
        else:
            s = self.anahtar.sorular[self.etkin]
            self._sik_sec(self.etkin, t)
            if not (self.ana_mi and s.durum == SoruDurumu.COKLU):
                self.etkin = min(n - 1, self.etkin + 1)
        self._etkin_goster()
        self.kaydirma.ensureWidgetVisible(self.satirlar[self.etkin].no)

    def _hizli_uygula(self):
        if self.klasik:
            return self._klasik_puanlari_uygula()
        n = self.anahtar.soru_sayisi
        metin = self.hizli.text()
        harf_sayisi = len([c for c in metin if not c.isspace()])
        try:
            yeni = CevapAnahtari.metinden(metin, n)
        except ValueError as e:
            QMessageBox.warning(self, "Cevap anahtarı", str(e))
            return
        if self.ana_mi:
            for eski, s in zip(self.anahtar.sorular, yeni.sorular):
                eski.dogru = s.dogru
                if eski.durum == SoruDurumu.COKLU:
                    eski.durum = SoruDurumu.NORMAL
        else:
            self.anahtar.kitapcik_anahtarlari[self.kitapcik] = yeni.metne()
        self.durumdan_yukle()
        if harf_sayisi != n:
            QMessageBox.information(self, "Cevap anahtarı", f"{harf_sayisi} harf girildi, soru sayısı {n}. Eksik sorular anahtarsız bırakıldı, fazlası atıldı.")

    # ---------------------------------------------------------------- klasik: puan dizisi, soru ekle/çıkar
    def _hizli_doldur(self):
        """Klasik sınavda üstteki satır, o anki soru puanlarını gösterir (doğrudan düzenlenebilir)."""
        if self.klasik and not self.hizli.hasFocus():
            self.hizli.setText(" ".join((s.puan or "?").replace(".", ",") for s in self.anahtar.sorular))

    def _klasik_odaktan_cikinca(self):
        """Klasikte puanlar yazılıp Enter'a basılmadan başka yere geçilirse de uygulanır (değiştiyse)."""
        if not self.klasik or self._yukleniyor:
            return
        simdiki = " ".join((s.puan or "?").replace(".", ",") for s in self.anahtar.sorular)
        if self.hizli.text().strip() and self.hizli.text().split() != simdiki.split():
            self._klasik_puanlari_uygula()

    def _klasik_puanlari_uygula(self):
        try:
            puanlar = puan_listesi_coz(self.hizli.text())
        except ValueError as e:
            QMessageBox.warning(self, "Soru puanları", f"{e}\n\nPuanları boşlukla ayırarak yazın, örneğin: 10 10 10 10 20 40")
            return
        if not puanlar:
            return
        if not self._cikarmayi_onayla(len(puanlar)):
            return
        self.durum.klasik_puanlarini_yaz(puanlar)
        self.hizli.clearFocus()
        self.durumdan_yukle()

    def _cikarmayi_onayla(self, yeni_n: int) -> bool:
        """Soru sayısı azalıyorsa ve çıkan sorulara öğrenci puanı girilmişse onay ister (puanlar silinmez)."""
        etkilenen = [(k + 1, self.durum.puanli_ogrenci_sayisi(k)) for k in range(yeni_n, self.anahtar.soru_sayisi)]
        etkilenen = [(k, n) for k, n in etkilenen if n]
        if not etkilenen:
            return True
        ayrinti = ", ".join(f"{k}. soruda {n} öğrenci" for k, n in etkilenen)
        return QMessageBox.question(
            self, "Soru çıkarılsın mı?",
            f"Çıkarılacak sorulara puan girilmiş: {ayrinti}.\nBu puanlar hesaba katılmaz ama silinmez; soruyu geri eklerseniz geri gelir. Devam edilsin mi?",
        ) == QMessageBox.StandardButton.Yes

    def _soru_ekle(self):
        self.durum.klasik_soru_sayisi_ayarla(self.anahtar.soru_sayisi + 1)
        self.durumdan_yukle()
        if self.satirlar and self.satirlar[-1].puan is not None:
            self.satirlar[-1].puan.setFocus()
            self.satirlar[-1].puan.selectAll()

    def _soru_cikar(self):
        n = self.anahtar.soru_sayisi
        if n <= 1 or not self._cikarmayi_onayla(n - 1):
            return
        self.durum.klasik_soru_sayisi_ayarla(n - 1)
        self.durumdan_yukle()

    def _durum_degisti(self, i):
        if self._yukleniyor:
            return
        r = self.satirlar[i]
        s = self.anahtar.sorular[i]
        s.durum = SoruDurumu(r.durum.deger())
        if s.durum != SoruDurumu.COKLU and len(s.dogru) > 1:
            s.dogru = s.dogru[:1]
        self.durumdan_yukle()

    def _puan_degisti(self, i: int, deger: float):
        if self._yukleniyor:
            return
        a = self.durum.proje.ayarlar
        if a.yontem == PuanYontemi.ESIT:
            # Eşit puandan soru bazlıya geçiş: öteki sorular kuruş farkıyla toplamı tutan eşit değerleri alır.
            for s, p in zip(self.anahtar.sorular, esit_soru_puanlari(a.toplam_puan, self.anahtar.soru_sayisi)):
                s.puan = p
            a.yontem = PuanYontemi.SORU_BAZLI
        self.anahtar.sorular[i].puan = f"{deger:.2f}".rstrip("0").rstrip(".")
        self._hizli_doldur()
        self._ozet()

    def _esit_puan(self):
        a = self.durum.proje.ayarlar
        if self.klasik:
            for s, p in zip(self.anahtar.sorular, esit_soru_puanlari(a.toplam_puan, self.anahtar.soru_sayisi)):
                s.puan = p
        else:
            a.yontem = PuanYontemi.ESIT
            for s in self.anahtar.sorular:
                s.puan = None
        self.durumdan_yukle()

    def _oc_degisti(self, i: int):
        if self._yukleniyor:
            return
        r = self.satirlar[i]
        s = self.anahtar.sorular[i]
        try:
            kodlar, yuzde = ciktilari_coz(r.oc.text(), self.durum.ogrenme_kodlari(), "Ö")
        except ValueError as e:
            QMessageBox.warning(self, "Öğrenme çıktısı", str(e))
            return
        if (kodlar, yuzde) != (s.ogrenme_ciktilari, s.cikti_yuzdeleri):
            self.durum.proje.cikti_elle = True  # hoca değiştirdi: artık kendiliğinden dağıtılmaz
        s.ogrenme_ciktilari = kodlar
        s.cikti_yuzdeleri = yuzde
        r.oc.setText(ciktilari_yaz(s.ogrenme_ciktilari, s.cikti_dagilimi()))
        self._ozet()

    def _oc_pencere(self, i: int):
        s = self.anahtar.sorular[i]
        p = CiktiPenceresi(i + 1, s.ogrenme_ciktilari, s.cikti_dagilimi(), self.durum.ogrenme_kodlari(),
                           self.durum.cikti_aciklamalari(), self)
        if p.exec() == QDialog.DialogCode.Accepted:
            s.ogrenme_ciktilari, s.cikti_yuzdeleri = p.sonuc()
            self.durum.proje.cikti_elle = True
            self.satirlar[i].oc.setText(ciktilari_yaz(s.ogrenme_ciktilari, s.cikti_dagilimi()))
            self._ozet()

    def _pc_degisti(self, i: int):
        if self._yukleniyor:
            return
        r = self.satirlar[i]
        try:
            kodlar, _ = ciktilari_coz(r.pc.text().replace("%", ""), self.durum.program_kodlari(), "P")
        except ValueError as e:
            QMessageBox.warning(self, "Program çıktısı", str(e))
            return
        self.anahtar.sorular[i].program_ciktilari = kodlar
        r.pc.setText(", ".join(kodlar))
        self._ozet()

    def _esleme_degisti(self, i: int, deger: int):
        if self._yukleniyor:
            return
        e = self.anahtar.kitapcik_eslemesi.setdefault(self.kitapcik, {})
        if deger == i + 1:
            e.pop(i + 1, None)
        else:
            e[i + 1] = deger
        self._ozet()

    def _kitapcik_secildi(self, _i):
        if self._yukleniyor:
            return
        self.etkin = 0
        self.durumdan_yukle()

    def _kitapcik_ekle(self):
        mevcut = self.anahtar.kitapciklar()
        oneri = next((c for c in "BCDEFGH" if c not in mevcut), "")
        harf, tamam = QInputDialog.getText(self, "Kitapçık ekle", "Kitapçık harfi (optik formda işaretlenen):", text=oneri)
        harf = (harf or "").strip().upper()[:1]
        if not tamam or not harf.isalpha():
            return
        if harf in mevcut:
            QMessageBox.information(self, "Kitapçık", f"{harf} kitapçığı zaten var.")
            return
        self.anahtar.kitapcik_anahtarlari[harf] = "-" * self.anahtar.soru_sayisi
        self._kurulu = None
        self.durumdan_yukle()
        self.sekmeler.setCurrentIndex(self.anahtar.kitapciklar().index(harf))

    def _kitapcik_sil(self):
        k = self.kitapcik
        if self.ana_mi or QMessageBox.question(self, "Kitapçık sil", f"{k} kitapçığının anahtarı ve eşlemesi silinsin mi?") != QMessageBox.StandardButton.Yes:
            return
        self.anahtar.kitapcik_anahtarlari.pop(k, None)
        self.anahtar.kitapcik_eslemesi.pop(k, None)
        self.sekmeler.setCurrentIndex(0)
        self.durumdan_yukle()

    def _ciktilari_varsayilan_dagit(self):
        """Varsayılan: dersin öğrenme çıktıları biliniyorsa sorulara eşit dağıtılır ve hoca bir soruyu değiştirene kadar
        (soru sayısı ya da ders değişse de) eşit tutulur. Hoca değiştirince (`cikti_elle`) bir daha dokunulmaz."""
        kodlar = self.durum.ogrenme_kodlari()
        if (kodlar and self.anahtar.sorular and not self.durum.proje.cikti_elle
                and not cikti_atamasi_esit_mi(self.anahtar, kodlar)):
            ciktilari_esit_dagit(self.anahtar, kodlar)  # soru sayısı ya da ders değişse de eşit kalır

    def _cikti_sayisi_degisti(self, n: int):
        p = self.durum.proje
        if n == p.cikti_sayisi:
            return
        p.cikti_sayisi = n
        if n == 0 and not p.cikti_elle:
            for s in self.anahtar.sorular:
                s.ogrenme_ciktilari, s.cikti_yuzdeleri = [], {}
        self._kurulu = None
        self.durumdan_yukle()
        self.tamamlik_degisti.emit()

    def _cikti_seridi(self):
        """Tablonun üstündeki satır: çıktılar eşit mi dağıtıldı, elle mi düzenlendi, yoksa ders çıktıları bilinmiyor mu."""
        kodlar = self.durum.ogrenme_kodlari()
        self.cikti_serit.setVisible(self.ana_mi)
        paketsiz = self.durum.ders is None
        self.cikti_sayisi_etiketi.setVisible(paketsiz)
        self.cikti_sayisi_kutusu.setVisible(paketsiz)
        self.cikti_sayisi_kutusu.blockSignals(True)
        self.cikti_sayisi_kutusu.setValue(self.durum.proje.cikti_sayisi)
        self.cikti_sayisi_kutusu.blockSignals(False)
        if not kodlar:
            self.cikti_bilgi.setText("<b>Dersin öğrenme çıktıları bilinmiyor.</b> <span style='color:gray'>Sistem her soru için öğrenme "
                                     "çıktısı istiyor: sağa dersin öğrenme çıktısı sayısını yazın ya da 1. adımda ders bilgi paketini "
                                     "yükleyin; çıktılar sorulara kendiliğinden eşit dağıtılır.</span>")
            self.esit_dagit_dugmesi.setVisible(False)
        elif cikti_atamasi_esit_mi(self.anahtar, kodlar):
            self.cikti_bilgi.setText(f"<b>Öğrenme çıktıları sorulara eşit dağıtıldı</b> (her soru bir çıktıya; {', '.join(kodlar)}). "
                                     "<span style='color:gray'>Değiştirmek için sorunun çıktı kutusuna yazın ya da Seç…'e basın.</span>")
            self.esit_dagit_dugmesi.setVisible(False)
        else:
            self.cikti_bilgi.setText("<b>Öğrenme çıktıları elle düzenlendi.</b> <span style='color:gray'>İsterseniz yeniden eşit dağıtabilirsiniz.</span>")
            self.esit_dagit_dugmesi.setText("Yeniden eşit dağıt")
            self.esit_dagit_dugmesi.setVisible(True)

    def _sirayla_dagit(self):
        kodlar = self.durum.ogrenme_kodlari()
        if not kodlar:
            QMessageBox.information(self, "Öğrenme çıktıları", "Önce dersin öğrenme çıktısı sayısını yazın ya da 1. adımda ders bilgi paketini yükleyin.")
            return
        if any(s.ogrenme_ciktilari for s in self.anahtar.sorular) and not cikti_atamasi_esit_mi(self.anahtar, kodlar):
            if QMessageBox.question(self, "Yeniden eşit dağıt", "Sorulara elle seçtiğiniz öğrenme çıktıları silinip eşit dağıtılsın mı?") \
                    != QMessageBox.StandardButton.Yes:
                return
        ciktilari_esit_dagit(self.anahtar, kodlar)
        self.durum.proje.cikti_elle = False
        self._kurulu = None
        self.durumdan_yukle()

    def _sisteme_kopyala(self):
        soru_tanimini_kopyala(self, self.durum)

    def _eslemeyi_kaydet(self):
        yol = self.durum.ders_eslemesi_kaydet()
        QMessageBox.information(self, "Ders eşlemesi", f"Kaydedildi:\n{yol}")

    def _eslemeyi_yukle(self):
        if self.durum.ders_eslemesi_yukle():
            self.durum.proje.cikti_elle = True
            self.durumdan_yukle()
        else:
            QMessageBox.information(self, "Ders eşlemesi", f"Bu ders kodu için kayıtlı eşleme yok:\n{self.durum.ders_eslemesi_yolu()}")

    # ---------------------------------------------------------------- özet ve denetim
    def _ozet(self):
        self._cikti_seridi()
        p = self.durum.proje
        a = self.anahtar
        try:
            puanlar = soru_puanlari(a, p.ayarlar)
            toplam = sum(puanlar, Fraction(0))
        except Exception:  # noqa: BLE001
            puanlar, toplam = [], Fraction(0)
        hedef = p.ayarlar.toplam_puan
        yontem = "eşit puan" if (p.ayarlar.yontem == PuanYontemi.ESIT and not self.klasik) else "soru bazlı puan"
        try:
            dogru = toplam == Fraction(hedef.replace(",", "."))
        except (ValueError, ZeroDivisionError):
            dogru = False
        try:
            fark = Fraction(hedef.replace(",", ".")) - toplam
            neden = f"{sayi_yaz(abs(fark), 2)} puan {'eksik' if fark > 0 else 'fazla'}" if fark else ""
        except (ValueError, ZeroDivisionError):
            neden = ""
        bos = [str(s.no) for s in a.sorular if s.puan in (None, "")] if (self.klasik or p.ayarlar.yontem != PuanYontemi.ESIT) else []
        if bos:
            neden = f"puanı girilmemiş soru: {', '.join(bos)}"
        bonuslar = [str(s.no) for s in a.sorular if s.durum == SoruDurumu.BONUS]
        bonus_notu = ("<br><span style='color:#2F5597'>" + BONUS_NOTU.format(no=", ".join(bonuslar)) + "</span>") if bonuslar and not self.klasik else ""
        self.puan_ozeti.setWordWrap(True)
        self.puan_ozeti.setText(f"<b>Soru puanlarının toplamı:</b> {sayi_yaz(toplam, 2)} / {hedef} ({yontem})"
                                + (" ✓" if dogru and not bos else f"  <span style='color:#C0504D'><b>toplam tutmuyor{': ' + neden if neden else ''}</b></span>")
                                + bonus_notu)
        hatalar, bilgiler = cikti_denetimi(a, self.durum.ogrenme_kodlari() or None)
        if any(s.ogrenme_ciktilari for s in a.sorular) and puanlar:
            dag = cikti_dagilimi(a, puanlar)
            parca = " · ".join(f"{k} %{sayi_yaz(v, 1)}" for k, v in dag.items())
            t = sum(dag.values(), Fraction(0))
            metin = f"<b>Sınavın öğrenme çıktısı dağılımı:</b> {parca} = %{sayi_yaz(t, 1)}"
            if not hatalar:
                metin += " ✓ (her sorunun yüzdeleri 100)"
        else:
            metin = "<b>Öğrenme çıktıları:</b> henüz girilmedi (isteğe bağlı; Akademik Bilgi Sistemi akreditasyon girişi için gerekir)."
        for h in hatalar:
            metin += f"<br><span style='color:#C0504D'>{h}</span>"
        for b in bilgiler:
            metin += f"<br><span style='color:gray'>{b}</span>"
        self.cikti_ozeti.setText(metin)
        self.tamamlik_degisti.emit()

    def eksikler(self):
        a = self.anahtar
        # Soru puanları ve puanlama ayarları da bu adımdadır (ayarlar katlanır bölümde)
        e = list(anahtar_eksikleri(a, self.durum.proje.ayarlar, self.klasik))
        e += [x for x in self.ayarlar_paneli.eksikler() if x not in e]
        if not self.klasik:
            for k in a.kitapciklar()[1:]:
                harfler = [c for c in a.kitapcik_anahtarlari.get(k, "") if not c.isspace()]
                eksik = [str(i + 1) for i in range(a.soru_sayisi)
                         if (i >= len(harfler) or harfler[i] not in SIKLAR) and a.sorular[a.esleme(k)[i + 1] - 1].durum != SoruDurumu.IPTAL]
                if eksik:
                    e.append(f"{k} kitapçığında anahtarı girilmemiş sorular: {', '.join(eksik)}")
                e.extend(a.esleme_sorunlari(k))
        hatalar, _ = cikti_denetimi(a, self.durum.ogrenme_kodlari() or None)
        return e + hatalar


def ciktilari_hazirla(ebeveyn, durum) -> None:
    """Soru tanımından önce: çıktılar bilinmiyorsa dersin öğrenme çıktısı sayısını sorar; hoca elle değiştirmediyse
    çıktıları sorulara eşit dağıtır (2. adım hiç açılmamış olsa da)."""
    a = durum.proje.anahtar
    if not a.sorular:
        return
    kodlar = durum.ogrenme_kodlari()
    if not kodlar and not any(s.ogrenme_ciktilari for s in a.sorular):
        n, tamam = QInputDialog.getInt(ebeveyn, "Öğrenme çıktısı sayısı",
                                       "Sistem soru tanımında her soru için bir öğrenme çıktısı istiyor.\n"
                                       "Bu dersin kaç öğrenme çıktısı var? (ders bilgi paketindeki sayı)\n\n"
                                       "Çıktılar (Ö01, Ö02 …) sorulara sırayla, eşit sayıda dağıtılır; 2. adımda değiştirebilirsiniz.",
                                       1, 1, 30)
        if not tamam:
            return
        durum.proje.cikti_sayisi = n
        durum.proje.cikti_elle = False
        kodlar = durum.ogrenme_kodlari()
    if kodlar and not durum.proje.cikti_elle and not cikti_atamasi_esit_mi(a, kodlar):
        ciktilari_esit_dagit(a, kodlar)


def soru_tanimini_kopyala(ebeveyn, durum) -> bool:
    """Soru tanımını (bonus hariç) Akademik Bilgi Sistemi'nin Toplu Aktarım biçiminde panoya kopyalar. Kopyaladıysa True."""
    from PySide6.QtGui import QGuiApplication

    from ...export.soru_tanimi import soru_tanimi_metni

    ciktilari_hazirla(ebeveyn, durum)
    a = durum.proje.anahtar
    sorunlar = [x for x in anahtar_eksikleri(a, durum.proje.ayarlar, True) if "puan" in x.lower()]
    hatalar, _ = cikti_denetimi(a, durum.ogrenme_kodlari() or None)
    if not any(s.ogrenme_ciktilari for s in a.sorular):
        hatalar = ["Hiçbir soruya öğrenme çıktısı seçilmedi (2. adım). Sistem her soru için öğrenme çıktısı istiyor."]
    if sorunlar or hatalar:
        QMessageBox.warning(ebeveyn, "Önce düzeltin", "\n".join(sorunlar + hatalar))
        return False
    try:
        metin = soru_tanimi_metni(a, durum.proje.ayarlar, durum.ogrenme_kodlari() or None)
    except Exception as e:  # noqa: BLE001
        QMessageBox.warning(ebeveyn, "Kopyalanamadı", str(e))
        return False
    QGuiApplication.clipboard().setText(metin)
    QMessageBox.information(ebeveyn, "Panoya kopyalandı",
                            f"{durum.sinav_kisa_adi()} için {len(a.aktarim_sorulari())} sorunun tanımı kopyalandı. "
                            "Sistemde aynı dersin ve sınavın ekranını açtığınızdan emin olun.\n\n"
                            "Akademik Bilgi Sistemi'nde:\n"
                            "1. Sınav Akreditasyon İşlemleri'nde dersi ve sınavı açın.\n"
                            "2. \"Toplu Sınav Soru Tanım\" kutusunda \"Toplu Aktarım Yap\" seçin.\n"
                            "3. \"Kolon Ayracı\" \"Excel'den Kopyalandı\" olsun.\n"
                            "4. Sağdaki Aktarım Kutusu'na tıklayıp yapıştırın (Cmd+V).\n"
                            "5. \"Aktar\" düğmesine basın.")
    return True
