"""3. adım: eşit ya da soru bazlı puan, yanlış cezası, çift işaret kuralı, yuvarlama."""
from __future__ import annotations

from fractions import Fraction

from PySide6.QtWidgets import QButtonGroup, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QRadioButton, QSpinBox

from ... import metinler as M
from ...core.modeller import CiftIsaretKurali, PuanYontemi, Yuvarlama
from ...core.puanlama import anahtar_eksikleri, sayi_yaz, soru_puanlari
from .temel import Adim


class PuanlamaAdimi(Adim):
    def __init__(self, durum, parent=None):
        super().__init__(durum, M.ADIMLAR[2], parent)
        self._yukleniyor = False
        g = QGroupBox("Puan yöntemi")
        self.yontem_kutusu = g
        f = QFormLayout(g)
        self.esit = QRadioButton(M.YONTEM_ADI["esit"] + " (toplam / soru sayısı; iptal sorular dahil)")
        self.soru_bazli = QRadioButton(M.YONTEM_ADI["soru_bazli"] + " (her sorunun puanı 2. adımda, soru satırında girilir)")
        grup = QButtonGroup(self)
        grup.addButton(self.esit)
        grup.addButton(self.soru_bazli)
        f.addRow(self.esit)
        f.addRow(self.soru_bazli)
        self.toplam = QLineEdit()
        f.addRow("Toplam puan", self.toplam)
        self.soru_puani = QLabel()
        f.addRow("Soru puanı", self.soru_puani)
        self.duzen.addWidget(g)

        g = QGroupBox("Kurallar")
        self.kural_kutusu = g
        f = QFormLayout(g)
        self.kural_formu = f
        s = QHBoxLayout()
        self.ceza = QCheckBox("Yanlışlar doğruyu götürsün:")
        self.ceza_orani = QSpinBox(minimum=1, maximum=10)
        s.addWidget(self.ceza)
        s.addWidget(self.ceza_orani)
        self.ceza_etiket = QLabel("yanlış bir doğruyu götürür (puan sıfırın altına düşmez; ceza soru puanlarına dağıtılmaz)")
        self.ceza_etiket.setWordWrap(True)
        s.addWidget(self.ceza_etiket, 1)
        f.addRow(s)
        self.cift = QComboBox()
        for k in CiftIsaretKurali:
            self.cift.addItem(M.CIFT_ISARET_ADI[k.value], k.value)
        f.addRow("Çift işaret (*)", self.cift)
        self.cift_etiket = f.labelForField(self.cift)
        self.yuvarlama = QComboBox()
        for k in Yuvarlama:
            self.yuvarlama.addItem(M.YUVARLAMA_ADI[k.value], k.value)
        self.ondalik = QSpinBox(minimum=0, maximum=4)
        s = QHBoxLayout()
        s.addWidget(self.yuvarlama)
        s.addWidget(QLabel("Ondalık basamak"))
        s.addWidget(self.ondalik)
        s.addStretch(1)
        f.addRow("Yuvarlama (yalnızca en sonda)", s)
        self.esik = QSpinBox(minimum=0, maximum=100)
        s = QHBoxLayout()
        s.addWidget(self.esik)
        e = QLabel("İstatistiklerde bu puan ve üstü başarılı sayılır; öğrenme çıktısında bu yüzde ve üstü \"ulaştı\" sayılır.")
        e.setWordWrap(True)
        s.addWidget(e, 1)
        f.addRow("Başarı eşiği", s)
        self.gecme = QSpinBox(minimum=0, maximum=100)
        self.final_alt = QSpinBox(minimum=0, maximum=100)
        s = QHBoxLayout()
        s.addWidget(QLabel("Geçme ortalaması"))
        s.addWidget(self.gecme)
        s.addWidget(QLabel("Final alt sınırı"))
        s.addWidget(self.final_alt)
        s.addStretch(1)
        f.addRow("Dersi geçme kuralı", s)
        e = QLabel("Yalnızca \"finalde gereken puan\" hesabı için; ara sınav ağırlığı 1. adımdaki etki oranından alınır.")
        e.setWordWrap(True)
        e.setStyleSheet("color: gray")
        f.addRow("", e)
        self.duzen.addWidget(g)
        self.durum_etiketi = QLabel()
        self.durum_etiketi.setWordWrap(True)
        self.duzen.addWidget(self.durum_etiketi)
        self.duzen.addStretch(1)

        for w in (self.esit, self.soru_bazli, self.ceza):
            w.toggled.connect(self._degisti)
        self.toplam.textChanged.connect(self._degisti)
        for w in (self.ceza_orani, self.ondalik, self.esik, self.gecme, self.final_alt):
            w.valueChanged.connect(self._degisti)
        for w in (self.cift, self.yuvarlama):
            w.currentIndexChanged.connect(self._degisti)
        durum.degisti.connect(self.durumdan_yukle)
        self.durumdan_yukle()

    def durumdan_yukle(self):
        self._yukleniyor = True
        try:
            a = self.durum.proje.ayarlar
            (self.esit if a.yontem == PuanYontemi.ESIT else self.soru_bazli).setChecked(True)
            self.toplam.setText(a.toplam_puan)
            self.ceza.setChecked(a.yanlis_cezasi)
            self.ceza_orani.setValue(a.ceza_orani)
            self.cift.setCurrentIndex(self.cift.findData(a.cift_isaret.value))
            self.yuvarlama.setCurrentIndex(self.yuvarlama.findData(a.yuvarlama.value))
            self.ondalik.setValue(a.ondalik)
            self.esik.setValue(a.basari_esigi)
            self.gecme.setValue(a.gecme_ortalamasi)
            self.final_alt.setValue(a.final_alt_siniri)
            klasik = self.durum.proje.klasik
            for w in (self.esit, self.ceza, self.ceza_orani, self.ceza_etiket, self.cift, self.cift_etiket):
                w.setVisible(not klasik)
        finally:
            self._yukleniyor = False
        self._ozet()

    def girildi(self):
        self._ozet()

    def _degisti(self, *_):
        if self._yukleniyor:
            return
        a = self.durum.proje.ayarlar
        a.yontem = PuanYontemi.ESIT if self.esit.isChecked() else PuanYontemi.SORU_BAZLI
        a.toplam_puan = self.toplam.text().strip().replace(",", ".") or "100"
        a.yanlis_cezasi = self.ceza.isChecked()
        a.ceza_orani = self.ceza_orani.value()
        a.cift_isaret = CiftIsaretKurali(self.cift.currentData())
        a.yuvarlama = Yuvarlama(self.yuvarlama.currentData())
        a.ondalik = self.ondalik.value()
        a.basari_esigi = self.esik.value()
        a.gecme_ortalamasi = self.gecme.value()
        a.final_alt_siniri = self.final_alt.value()
        self._ozet()

    def _ozet(self):
        p = self.durum.proje
        self.ceza_orani.setEnabled(self.ceza.isChecked())
        try:
            puanlar = soru_puanlari(p.anahtar, p.ayarlar)
        except Exception:  # noqa: BLE001
            puanlar = []
        if p.ayarlar.yontem == PuanYontemi.ESIT and puanlar:
            self.soru_puani.setText(f"{sayi_yaz(puanlar[0], 4)} (kesir olarak tutulur; örneğin 15 doğru tam {sayi_yaz(sum(puanlar, Fraction(0)), 2)})")
        elif puanlar:
            self.soru_puani.setText(f"Girilen soru puanlarının toplamı: {sayi_yaz(sum(puanlar, Fraction(0)), 2)}")
        else:
            self.soru_puani.setText("")
        e = self.eksikler()
        self.durum_etiketi.setText("" if not e else "<b>Eksik:</b> " + " ".join(e))
        self.tamamlik_degisti.emit()

    def eksikler(self):
        try:
            float(self.durum.proje.ayarlar.toplam_puan)
        except ValueError:
            return ["Toplam puan sayı olmalı."]
        if self.durum.proje.klasik:
            return []  # klasik sınavda soru puanları 2. adımda
        return [x for x in anahtar_eksikleri(self.durum.proje.anahtar, self.durum.proje.ayarlar, self.durum.proje.klasik) if "puan" in x.lower()]
