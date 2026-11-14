"""Klasik sınavda kâğıt sırasıyla puan girişi: öğrenciyi numara ya da adla bul, soru puanlarını ve isteğe bağlı
kâğıttaki toplamı yaz, Enter ile kaydedip bir sonraki kâğıda geç."""
from __future__ import annotations

import unicodedata

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ...core.puanlama import sayi_yaz, soru_puanlari


def _sade(m: str) -> str:
    s = str(m or "").replace("İ", "i").replace("I", "ı").lower().replace("ı", "i")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


class KagitPaneli(QGroupBox):
    def __init__(self, durum, kontrol, parent=None):
        super().__init__("Kâğıt sırasıyla giriş", parent)
        self.durum = durum
        self.kontrol = kontrol
        self.secili = None
        self.kutular: list[QLineEdit] = []
        v = QVBoxLayout(self)
        s = QHBoxLayout()
        s.addWidget(QLabel("Öğrenci"))
        self.ara = QLineEdit(placeholderText="Numaranın ya da adın birkaç harfi, sonra Enter")
        self.ara.setMinimumWidth(300)
        self.ara.textEdited.connect(self._oneri)
        self.ara.returnPressed.connect(self._ilkini_sec)
        s.addWidget(self.ara)
        self.kim = QLabel()
        self.kim.setStyleSheet("font-weight: bold")
        s.addWidget(self.kim, 1)
        self.kalan = QLabel()
        s.addWidget(self.kalan)
        v.addLayout(s)
        self.oneriler = QLabel()
        self.oneriler.setStyleSheet("color: gray")
        v.addWidget(self.oneriler)
        self.kutu_satiri = QHBoxLayout()
        v.addLayout(self.kutu_satiri)
        self.durum_etiketi = QLabel()
        self.durum_etiketi.setWordWrap(True)
        v.addWidget(self.durum_etiketi)
        v.addWidget(QLabel("Kâğıtlar elinizdeki sırayla gelsin: öğrenciyi bulun, puanları yazın (Enter bir sonraki kutuya geçer), "
                           "son kutuda Enter kaydeder ve yeni kâğıda hazırlar."))

    def kur(self):
        """Soru sayısı ve puanlar değişmiş olabilir: kutuları yeniden kurar."""
        while self.kutu_satiri.count():
            w = self.kutu_satiri.takeAt(0).widget()
            if w:
                w.setParent(None)
        self.kutular = []
        try:
            tam = soru_puanlari(self.durum.proje.anahtar, self.durum.proje.ayarlar)
        except Exception:  # noqa: BLE001
            tam = []
        for k in range(self.durum.proje.anahtar.soru_sayisi):
            etiket = f"S{k + 1}" + (f" ({sayi_yaz(tam[k], 2).rstrip('0').rstrip(',')})" if k < len(tam) else "")
            self.kutu_satiri.addWidget(QLabel(etiket))
            e = QLineEdit()
            e.setFixedWidth(60)
            e.returnPressed.connect(lambda k=k: self._sonraki_kutu(k))
            self.kutu_satiri.addWidget(e)
            self.kutular.append(e)
        self.kutu_satiri.addWidget(QLabel("Kâğıttaki toplam"))
        self.toplam = QLineEdit()
        self.toplam.setFixedWidth(70)
        self.toplam.setToolTip("İsteğe bağlı: kâğıdın üstüne yazdığınız toplam; tutmazsa uyarılır.")
        self.toplam.returnPressed.connect(self.kaydet)
        self.kutu_satiri.addWidget(self.toplam)
        self.kaydet_dugmesi = QPushButton("Kaydet, sonraki kâğıt")
        self.kaydet_dugmesi.clicked.connect(self.kaydet)
        self.kutu_satiri.addWidget(self.kaydet_dugmesi)
        self.kutu_satiri.addStretch(1)
        self._temizle()

    # ------------------------------------------------------------ arama
    def _liste(self):
        return self.durum.liste.ogrenciler if self.durum.liste else []

    def bul(self, metin: str):
        t = metin.strip()
        if not t:
            return []
        ts = _sade(t)
        return [o for o in self._liste() if t in o.no or ts in _sade(o.ad)]

    def _oneri(self, metin):
        r = self.bul(metin)
        if metin.strip() and not r:
            self.oneriler.setText("<span style='color:#C0504D'>Listede bulunamadı</span>")
        else:
            self.oneriler.setText("   ".join(f"{o.no} {o.ad}" for o in r[:6]) + (f"   (+{len(r) - 6} öğrenci daha; biraz daha yazın)" if len(r) > 6 else ""))

    def _ilkini_sec(self):
        r = self.bul(self.ara.text())
        if r:
            self.sec(r[0])

    def sec(self, o):
        self.secili = o
        d = self.durum.proje.klasik_puanlar.get(o.no) or []
        once = any(x not in (None, "") for x in d)
        self.kim.setText(f"{o.no} {o.ad}" + (" (daha önce girilmiş; üzerine yazılır)" if once else ""))
        self.oneriler.setText("")
        for k, e in enumerate(self.kutular):
            e.setEnabled(True)
            e.setText(d[k] if k < len(d) and d[k] is not None else "")
        self.toplam.setEnabled(True)
        self.toplam.setText(self.durum.proje.klasik_toplamlar.get(o.no) or "")
        self.kaydet_dugmesi.setEnabled(True)
        if self.kutular:
            self.kutular[0].setFocus()
            self.kutular[0].selectAll()

    def _sonraki_kutu(self, k):
        hedef = self.kutular[k + 1] if k + 1 < len(self.kutular) else self.toplam
        hedef.setFocus()
        hedef.selectAll()

    # ------------------------------------------------------------ kayıt
    def kaydet(self):
        o = self.secili
        if o is None:
            return
        for k, e in enumerate(self.kutular):
            self.durum.klasik_puan_yaz(o.no, k, e.text())
        x = self.toplam.text().strip()
        if x:
            self.durum.proje.klasik_toplamlar[o.no] = x
        else:
            self.durum.proje.klasik_toplamlar.pop(o.no, None)
        self.durum.degerlendir()
        self.kontrol.klasik_model.yenile()
        s = self.durum.sonuc
        sonuc = next((x for x in s.ogrenciler if x.no == o.no), None) if s else None
        uyari = [u.mesaj for u in (sonuc.uyarilar if sonuc else []) if any(k in u.mesaj for k in ("toplam", "büyük", "eksi", "sayı"))]
        if uyari:
            self.durum_etiketi.setText(f"<span style='color:#C0504D'><b>{o.ad}:</b> kaydedildi, ama dikkat: {'; '.join(uyari)}</span>")
        else:
            self.durum_etiketi.setText(f"<b>{o.ad}:</b> kaydedildi ({sayi_yaz(sonuc.puan, 2) if sonuc else '-'} puan).")
        self._temizle()

    def _temizle(self):
        self.secili = None
        self.ara.clear()
        self.kim.setText("")
        for e in self.kutular:
            e.clear()
            e.setEnabled(False)
        if hasattr(self, "toplam"):
            self.toplam.clear()
            self.toplam.setEnabled(False)
            self.kaydet_dugmesi.setEnabled(False)
        girilen = sum(1 for o in self._liste() if any(x not in (None, "") for x in (self.durum.proje.klasik_puanlar.get(o.no) or [])))
        self.kalan.setText(f"Girilen kâğıt: {girilen} / {len(self._liste())}")
        self.ara.setFocus(Qt.FocusReason.OtherFocusReason)
