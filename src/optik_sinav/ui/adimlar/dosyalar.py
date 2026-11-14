"""1. adım: sınav bilgileri, optik dosya, öğrenci listesi, okuyucu şablonu önizlemesi."""
from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDateEdit, QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QRadioButton, QSpinBox, QTextEdit, QTimeEdit, QWidget,
)

from ... import metinler as M
from ...core.modeller import SINAV_TURLERI, ListeEslemesi
from ...io.liste_okuyucu import tablodan_liste
from ..tema import renk_hex
from .temel import Adim



VURGULU_DUGME = ("QPushButton { background-color: #2e7d32; color: white; font-weight: bold; font-size: 14px;"
                 " border: 2px solid #1b5e20; border-radius: 7px; padding: 6px 18px; }"
                 " QPushButton:hover { background-color: #388e3c; }"
                 " QPushButton:pressed { background-color: #1b5e20; }")

class DosyalarAdimi(Adim):
    def __init__(self, durum, parent=None):
        super().__init__(durum, M.ADIMLAR[0], parent)
        self.setAcceptDrops(True)
        self._yukleniyor = False

        # --- Sınav bilgileri
        g = QGroupBox("Sınav bilgileri (isteğe bağlı; raporlarda ve dosya adlarında görünür)")
        f = QFormLayout(g)
        s = QHBoxLayout()
        self.bicim_optik = QRadioButton("Optik (test, optik okuyucu dosyası)")
        self.bicim_klasik = QRadioButton("Klasik (yazılı; puanları siz girersiniz)")
        bg = QButtonGroup(self)
        bg.addButton(self.bicim_optik)
        bg.addButton(self.bicim_klasik)
        s.addWidget(self.bicim_optik)
        s.addWidget(self.bicim_klasik)
        self.klasik_sayi_etiket = QLabel("Soru sayısı")
        self.klasik_sayi = QSpinBox(minimum=1, maximum=100)
        s.addWidget(self.klasik_sayi_etiket)
        s.addWidget(self.klasik_sayi)
        s.addStretch(1)
        f.addRow("Sınav biçimi", s)
        self.bicim_optik.toggled.connect(self._bicim_degisti)
        self.klasik_sayi.valueChanged.connect(self._klasik_sayi_degisti)
        self.ders_kodu = QLineEdit(placeholderText="örnek: UTL4513")
        self.ders_adi = QLineEdit(placeholderText="Yatırım Analizi")
        self.sinav_turu = QComboBox()
        self.sinav_turu.addItems(SINAV_TURLERI)
        self.sinav_turu.setEditable(True)
        self.tarih = QDateEdit(QDate.currentDate(), calendarPopup=True, displayFormat="dd.MM.yyyy")
        self.saat = QTimeEdit(QTime(10, 0), displayFormat="HH:mm")
        self.etki = QLineEdit(placeholderText="40")
        self.donem = QLineEdit(placeholderText="2026-2027 Güz")
        satir1 = QHBoxLayout()
        satir1.addWidget(self.ders_kodu)
        satir1.addWidget(self.ders_adi, 2)
        f.addRow("Ders kodu ve adı", satir1)
        satir2 = QHBoxLayout()
        for w in (self.sinav_turu, QLabel("Tarih"), self.tarih, QLabel("Saat"), self.saat, QLabel("Etki oranı %"), self.etki):
            satir2.addWidget(w)
        f.addRow("Sınav türü", satir2)
        f.addRow("Dönem", self.donem)
        s = QHBoxLayout()
        b = QPushButton("Ders bilgi paketini yükle (PDF)…")
        b.setToolTip("Akademik Bilgi Sistemi'nden indirilen ders bilgi paketinden öğrenme ve program çıktılarını okur.")
        b.clicked.connect(self._ders_pdf_sec)
        s.addWidget(b)
        self.ders_etiket = QLabel()
        self.ders_etiket.setWordWrap(True)
        s.addWidget(self.ders_etiket, 1)
        f.addRow("Öğrenme çıktıları", s)
        self.duzen.addWidget(g)
        for w in (self.ders_kodu, self.ders_adi, self.etki, self.donem):
            w.textChanged.connect(self._bilgi_degisti)
        self.sinav_turu.currentTextChanged.connect(self._bilgi_degisti)
        self.tarih.dateChanged.connect(self._bilgi_degisti)
        self.saat.timeChanged.connect(self._bilgi_degisti)

        # --- Dosyalar
        g = QGroupBox("Dosyalar (sürükleyip bırakabilirsiniz)")
        f = QFormLayout(g)
        self.dosya_formu = f
        self.dat_etiket = QLabel("Seçilmedi")
        self.dat_etiket.setWordWrap(True)
        self.dat_etiket.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        b = QPushButton("Optik dosyayı seç…")
        b.clicked.connect(self._dat_sec)
        self.dat_dugmesi = b
        s = QHBoxLayout()
        s.addWidget(b)
        s.addWidget(self.dat_etiket, 1)
        f.addRow("Optik okuyucu dosyası", s)
        self.dat_satiri = s
        self.liste_etiket = QLabel("Seçilmedi (isteğe bağlı)")
        b2 = QPushButton("Öğrenci listesini seç…")
        b2.clicked.connect(self._liste_sec)
        self.liste_dugmesi = b2
        b3 = QPushButton("Kaldır")
        b3.clicked.connect(lambda: self.durum.liste_yukle(None))
        s = QHBoxLayout()
        s.addWidget(b2)
        s.addWidget(b3)
        s.addWidget(self.liste_etiket, 1)
        f.addRow("Öğrenci listesi", s)
        # liste eşlemesi
        self.liste_sayfa = QComboBox()
        self.liste_baslik = QSpinBox(minimum=0, maximum=100)
        self.liste_no = QComboBox()
        self.liste_ad = QComboBox()
        self.liste_soyad = QComboBox()
        s = QGridLayout()
        for sira, (etiket, w) in enumerate((("Sayfa", self.liste_sayfa), ("Başlık satırı", self.liste_baslik),
                                            ("Numara", self.liste_no), ("Ad (soyad)", self.liste_ad), ("Soyad", self.liste_soyad))):
            s.addWidget(QLabel(etiket), sira // 3, 2 * (sira % 3))
            s.addWidget(w, sira // 3, 2 * (sira % 3) + 1)
        for k in (1, 3, 5):
            s.setColumnStretch(k, 1)
        self.esleme_kutusu = QWidget()
        self.esleme_kutusu.setLayout(s)
        s.setContentsMargins(0, 0, 0, 0)
        f.addRow("Sütun eşlemesi", self.esleme_kutusu)
        for w in (self.liste_sayfa, self.liste_no, self.liste_ad, self.liste_soyad):
            w.currentIndexChanged.connect(self._esleme_degisti)
        self.liste_baslik.valueChanged.connect(self._esleme_degisti)
        self.duzen.addWidget(g)

        # --- Okuyucu şablonu
        g = QGroupBox("Okuyucu şablonu (konumlar 1'den sayılır)")
        self.okuyucu_kutusu = g
        izgara = QGridLayout(g)
        self.alanlar = {}
        tanim = [("ad_baslangic", "Ad başlangıcı"), ("ad_uzunluk", "Ad uzunluğu"), ("no_baslangic", "Numara başlangıcı"),
                 ("no_uzunluk", "Numara uzunluğu"), ("cevap_baslangic", "Cevap başlangıcı"), ("soru_sayisi", "Soru sayısı"),
                 ("kitapcik_baslangic", "Kitapçık başlangıcı (0 = yok)")]
        for i, (ad, etiket) in enumerate(tanim):
            sp = QSpinBox(minimum=0 if ad in ("kitapcik_baslangic", "soru_sayisi") else 1, maximum=400)
            sp.valueChanged.connect(self._sablon_degisti)
            self.alanlar[ad] = sp
            izgara.addWidget(QLabel(etiket), i // 4, (i % 4) * 2)
            izgara.addWidget(sp, i // 4, (i % 4) * 2 + 1)
        self.okuma_ozeti = QLabel("")
        self.okuma_ozeti.setWordWrap(True)
        s = QHBoxLayout()
        s.addWidget(self.okuma_ozeti, 1)
        self.gelismis = QPushButton("Gelişmiş ayarlar (okuyucu şablonu)")
        self.gelismis.setCheckable(True)
        self.gelismis.setToolTip("Optik dosyada adın, numaranın ve cevapların hangi karakterlerde olduğunu gösterir. "
                                 "Program bunu kendisi bulur; yalnızca farklı düzende bir optik formda gerekir.")
        self.gelismis.toggled.connect(lambda _v: self._gelismis_goster())
        s.addWidget(self.gelismis)
        self.duzen.addLayout(s)
        self.duzen.addWidget(g)
        self.onizleme = QTextEdit(readOnly=True)
        self.onizleme.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.onizleme.setMinimumHeight(160)
        self.duzen.addWidget(self.onizleme, 1)
        self.duzen.addStretch(0)  # önizleme gizliyken boşluk altta kalsın, başlık yukarıda dursun

        durum.degisti.connect(self.durumdan_yukle)
        self.durumdan_yukle()

    # ---------------------------------------------------------------- sürükle-bırak
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            yol = url.toLocalFile()
            uz = Path(yol).suffix.lower()
            if uz in (".xlsx", ".xls", ".csv"):
                self._liste_ac(yol)
            elif uz == ".pdf":
                self._ders_pdf_ac(yol)
            elif uz == ".osd":
                self.window().proje_ac(yol)
            else:
                self._dat_ac(yol)

    # ---------------------------------------------------------------- olaylar
    def _bilgi_degisti(self, *_):
        if self._yukleniyor:
            return
        s = self.durum.proje.sinav
        s.ders_kodu = self.ders_kodu.text().strip()
        s.ders_adi = self.ders_adi.text().strip()
        s.sinav_turu = self.sinav_turu.currentText().strip()
        s.tarih = self.tarih.date().toString("yyyy-MM-dd")
        s.saat = self.saat.time().toString("HH:mm")
        s.etki_orani = self.etki.text().strip()
        s.donem = self.donem.text().strip()
        if self.sender() is self.ders_kodu:
            onceki = self.durum.ders
            d = self.durum.dersi_yukle()
            if d and not self.ders_adi.text():
                self._yukleniyor = True
                self.ders_adi.setText(d.ad)
                self._yukleniyor = False
            if (d is None) != (onceki is None) or (d and onceki and d.kod != onceki.kod):
                self._ders_etiketi()
                self.durum.degisti.emit()
        self.tamamlik_degisti.emit()

    def _bicim_degisti(self, *_):
        if self._yukleniyor:
            return
        self.durum.bicim_degistir("optik" if self.bicim_optik.isChecked() else "klasik")

    def _klasik_sayi_degisti(self, v):
        if self._yukleniyor or not self.durum.proje.klasik:
            return
        self.durum.klasik_soru_sayisi_ayarla(v)

    def _ders_pdf_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Ders bilgi paketi", "", "PDF (*.pdf)")
        if yol:
            self._ders_pdf_ac(yol)

    def _ders_pdf_ac(self, yol):
        try:
            d = self.durum.ders_pdf_yukle(yol)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Ders bilgi paketi okunamadı", str(e))
            return
        QMessageBox.information(self, "Ders bilgi paketi", f"{d.kod} {d.ad}: {len(d.ogrenme_ciktilari)} öğrenme çıktısı, "
                                f"{len(d.program_ciktilari)} program çıktısı okundu ve saklandı. Bu ders kodu bir dahaki sefere kendiliğinden tanınır.")

    def _ders_etiketi(self):
        d = self.durum.ders
        if d:
            self.ders_etiket.setText(f"<b>{d.kod} {d.ad}</b> ({d.program}): {len(d.ogrenme_ciktilari)} öğrenme çıktısı ("
                                     + ", ".join(d.ogrenme_kodlari()) + f"), {len(d.program_ciktilari)} program çıktısı."
                                     + (" Değerlendirme: " + ", ".join(f"{k} %{v}" for k, v in d.degerlendirme.items()) if d.degerlendirme else ""))
        else:
            self.ders_etiket.setText("Bu ders kodu için kayıtlı ders bilgi paketi yok. PDF'i yükleyin ya da çıktı kodlarını 2. adımda elle yazın.")

    def _dat_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Optik okuyucu dosyası", "", "Optik dosyalar (*.dat *.txt);;Bütün dosyalar (*)")
        if yol:
            self._dat_ac(yol)

    def _dat_ac(self, yol):
        try:
            self.durum.dat_yukle(yol)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Dosya okunamadı", str(e))

    def _liste_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Öğrenci listesi", "", "Listeler (*.xlsx *.xls *.csv *.txt);;Bütün dosyalar (*)")
        if yol:
            self._liste_ac(yol)

    def _liste_ac(self, yol):
        try:
            self.durum.liste_yukle(yol)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Liste okunamadı", str(e))

    def _sablon_degisti(self, *_):
        if self._yukleniyor:
            return
        s = self.durum.proje.okuyucu
        for ad, sp in self.alanlar.items():
            v = sp.value()
            setattr(s, ad, (v or None) if ad == "kitapcik_baslangic" else v)
        self.durum.dat_yeniden_oku()

    def _esleme_degisti(self, *_):
        if self._yukleniyor or not self.durum.liste_sayfalari:
            return
        sayfa = self.liste_sayfa.currentText()
        e = ListeEslemesi(
            sayfa=sayfa,
            baslik_satiri=self.liste_baslik.value() or None,
            no_sutun=self.liste_no.currentData(),
            ad_sutun=self.liste_ad.currentData(),
            soyad_sutun=self.liste_soyad.currentData(),
        )
        if not e.no_sutun:
            return
        try:
            self.durum.liste = tablodan_liste(self.durum.liste_sayfalari[sayfa], e)
            self.durum.proje.liste_esleme = e
        except Exception as hata:  # noqa: BLE001
            QMessageBox.warning(self, "Eşleme", str(hata))
        self.durum.degisti.emit()

    # ---------------------------------------------------------------- görünüm
    def durumdan_yukle(self):
        self._yukleniyor = True
        try:
            p = self.durum.proje
            s = p.sinav
            self.ders_kodu.setText(s.ders_kodu)
            self.ders_adi.setText(s.ders_adi)
            self.sinav_turu.setCurrentText(s.sinav_turu or "Ara Sınav")
            if s.tarih:
                self.tarih.setDate(QDate.fromString(s.tarih, "yyyy-MM-dd"))
            if s.saat:
                self.saat.setTime(QTime.fromString(s.saat, "HH:mm"))
            self.etki.setText(s.etki_orani)
            self.donem.setText(s.donem)
            klasik = p.klasik
            (self.bicim_klasik if klasik else self.bicim_optik).setChecked(True)
            self.klasik_sayi.setValue(p.klasik_soru_sayisi)
            for w in (self.klasik_sayi, self.klasik_sayi_etiket):
                w.setVisible(klasik)
            self.dosya_formu.setRowVisible(self.dat_satiri, not klasik)
            self.okuma_ozeti.setVisible(not klasik)
            self.gelismis.setVisible(not klasik)
            self._gelismis_goster()
            self.liste_etiket.setText(p.liste_yolu or ("Seçilmedi (klasik sınavda gerekli)" if klasik else "Seçilmedi (isteğe bağlı)"))
            self._ders_etiketi()
            for ad, sp in self.alanlar.items():
                sp.setValue(getattr(p.okuyucu, ad) or 0)
            self.dat_etiket.setText(p.dat_yolu or "Seçilmedi")
            self._esleme_doldur()
            self._onizleme_yaz()
        finally:
            self._yukleniyor = False
        self._vurgula()
        self.tamamlik_degisti.emit()

    def _vurgula(self):
        """Zorunlu dosya seçilmemişse düğmesini belirgin (yeşil, dolgulu) gösterir; seçilince sade düğmeye döner."""
        p = self.durum.proje
        dat_eksik = not p.klasik and (not p.dat_yolu or self.durum.okuma is None)
        liste_eksik = p.klasik and self.durum.liste is None
        for dugme, eksik in ((self.dat_dugmesi, dat_eksik), (self.liste_dugmesi, liste_eksik)):
            dugme.setStyleSheet(VURGULU_DUGME if eksik else "")
            dugme.setMinimumHeight(38 if eksik else 0)
        if dat_eksik:
            self.dat_etiket.setText("Gerekli. Dosyayı bu pencereye sürükleyip de bırakabilirsiniz.")
        elif not p.klasik:
            self.dat_etiket.setText("✓ " + p.dat_yolu)
        self.dat_etiket.setStyleSheet("color: #b45309" if dat_eksik else "color: #1e7b34")

    def _esleme_doldur(self):
        d = self.durum
        self.esleme_kutusu.setEnabled(bool(d.liste_sayfalari))
        for w in (self.liste_sayfa, self.liste_no, self.liste_ad, self.liste_soyad):
            w.clear()
        if not d.liste_sayfalari or not d.liste:
            return
        e = d.liste.esleme
        self.liste_sayfa.addItems(list(d.liste_sayfalari))
        self.liste_sayfa.setCurrentText(e.sayfa or next(iter(d.liste_sayfalari)))
        tablo = d.liste_sayfalari.get(self.liste_sayfa.currentText(), [])
        basliklar = tablo[e.baslik_satiri - 1] if e.baslik_satiri and tablo else []
        genislik = max((len(r) for r in tablo), default=0)
        for w in (self.liste_ad, self.liste_soyad):
            w.addItem("(yok)", None)
        for j in range(1, genislik + 1):
            b = basliklar[j - 1] if j - 1 < len(basliklar) and basliklar[j - 1] else ""
            ad = f"{j}. sütun" + (f": {b}" if b else "")
            for w in (self.liste_no, self.liste_ad, self.liste_soyad):
                w.addItem(ad, j)
        self.liste_baslik.setValue(e.baslik_satiri or 0)
        for w, v in ((self.liste_no, e.no_sutun), (self.liste_ad, e.ad_sutun), (self.liste_soyad, e.soyad_sutun)):
            i = w.findData(v)
            w.setCurrentIndex(max(i, 0))
        ilk = d.liste.ogrenciler[0] if d.liste.ogrenciler else None
        self.liste_etiket.setText(f"{d.proje.liste_yolu}  ({len(d.liste.ogrenciler)} öğrenci"
                                  + (f"; ilk: {ilk.no} {ilk.ad}" if ilk else "") + ")")

    def _gelismis_goster(self):
        acik = self.gelismis.isChecked() and not self.durum.proje.klasik
        self.okuyucu_kutusu.setVisible(acik)
        self.onizleme.setVisible(acik)

    def _onizleme_yaz(self):
        d = self.durum
        if not d.ham_satirlar:
            self.onizleme.setHtml("<i>Optik dosya seçildiğinde ilk satırlar alan sınırları renkli olarak burada görünür.</i>")
            self.okuma_ozeti.setText("")
            return
        s = d.proje.okuyucu
        konum_rengi = {}
        for ad, bas, uz in s.alanlar():
            for i in range(bas, bas + uz):
                konum_rengi[i] = renk_hex(ad)
        uzunluk = max(len(x) for x in d.ham_satirlar[:8])
        cetvel = "".join(str(i // 10 % 10) if i % 10 == 0 else " " for i in range(1, uzunluk + 1))
        cetvel2 = "".join(str(i % 10) for i in range(1, uzunluk + 1))
        satirlar = [html.escape(cetvel), html.escape(cetvel2)]
        for x in d.ham_satirlar[:8]:
            parca = []
            for i, c in enumerate(x, start=1):
                arka = konum_rengi.get(i) or (renk_hex("disari") if not c.isspace() else None)
                c = html.escape(c if c != " " else " ")
                parca.append(f'<span style="background:{arka}">{c}</span>' if arka else c)
            satirlar.append("".join(parca))
        aciklama = " ".join(f'<span style="background:{renk_hex(a)}">&nbsp;{e}&nbsp;</span>' for a, e in
                            (("ad", "ad"), ("no", "numara"), ("cevap", "cevaplar"), ("kitapcik", "kitapçık"), ("disari", "alan dışı işaret")))
        self.onizleme.setHtml(f'<div>{aciklama}</div><pre style="font-family: Menlo, Consolas, monospace">' + "<br>".join(satirlar) + "</pre>")
        o = d.okuma
        if o:
            uyarili = sum(1 for k in o.kayitlar if k.uyarilar)
            if o.kayitlar and uyarili > len(o.kayitlar) * 0.3 and not self.gelismis.isChecked():
                self.gelismis.setChecked(True)  # satırların çoğu sorunluysa düzen yanlış olabilir
            self.okuma_ozeti.setText(f"{len(o.kayitlar)} öğrenci, {s.soru_sayisi} soru okundu. Kodlama: {o.kodlama}, satır sonu: {o.satir_sonu}. "
                                     f"Okuma uyarısı olan satır: {uyarili}.")

    def eksikler(self):
        e = []
        if self.durum.proje.klasik:
            if self.durum.liste is None:
                e.append("Klasik sınavda öğrenci listesi gerekli.")
        elif not self.durum.proje.dat_yolu or self.durum.okuma is None:
            e.append(M.EKSIK["dat"])
        if self.durum.soru_sayisi <= 0:
            e.append(M.EKSIK["soru_sayisi"])
        return e
