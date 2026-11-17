"""Klasik sınavda kâğıt sırasıyla puan girişi: öğrenciyi numara ya da adla bul, soru puanlarını ve isteğe bağlı
kâğıttaki toplamı yaz, Enter ile kaydedip bir sonraki kâğıda geç."""
from __future__ import annotations

import unicodedata

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ...core.puanlama import sayi_yaz, soru_puanlari


def _sade(m: str) -> str:
    s = str(m or "").replace("İ", "i").replace("I", "ı").lower().replace("ı", "i")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


SUTUN = 8
YOL = ("Kâğıtlar elinizdeki sırayla gelsin: öğrenciyi numarası ya da adının birkaç harfiyle bulun, puanları yazın "
       "(Enter bir sonraki kutuya geçer); son kutuda Enter kaydeder ve yeni kâğıda hazırlar. Her giriş kendiliğinden kaydedilir.")


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
        self.ara.setMinimumWidth(220)
        self.ara.setToolTip(YOL)
        self.ara.textEdited.connect(self._oneri)
        self.ara.returnPressed.connect(self._ilkini_sec)
        s.addWidget(self.ara)
        self.kim = QLabel()
        self.kim.setStyleSheet("font-weight: bold")
        s.addWidget(self.kim, 1)
        self.kalan = QLabel()
        self.kalan.setTextFormat(Qt.TextFormat.RichText)
        s.addWidget(self.kalan)
        self.kalanlar_dugmesi = QPushButton("Kalanlar…")
        self.kalanlar_dugmesi.setToolTip("Puanı girilmemiş ve bazı soruları boş öğrencileri gösterir; kalanları topluca "
                                         "\"Sınava girmedi\" işaretleyebilirsiniz.")
        self.kalanlar_dugmesi.clicked.connect(self.kalanlari_goster)
        s.addWidget(self.kalanlar_dugmesi)
        v.addLayout(s)
        self.oneriler = QLabel()
        self.oneriler.setStyleSheet("color: gray")
        v.addWidget(self.oneriler)
        # Soru kutuları ızgarada: etiket üstte, kutu altta; satır başına en çok SUTUN soru (dar pencerede de sığsın)
        self.kutu_satiri = QGridLayout()
        self.kutu_satiri.setHorizontalSpacing(8)
        v.addLayout(self.kutu_satiri)
        self.alt_satir = QHBoxLayout()
        self.alt_satir.addWidget(QLabel("Kâğıttaki toplam"))
        self.toplam = QLineEdit()
        self.toplam.setFixedWidth(70)
        self.toplam.setToolTip("İsteğe bağlı: kâğıdın üstüne yazdığınız toplam; tutmazsa uyarılır.")
        self.toplam.returnPressed.connect(self.kaydet)
        self.alt_satir.addWidget(self.toplam)
        self.kaydet_dugmesi = QPushButton("Kaydet, sonraki kâğıt")
        self.kaydet_dugmesi.clicked.connect(self.kaydet)
        self.alt_satir.addWidget(self.kaydet_dugmesi)
        self.girmedi_dugmesi = QPushButton("Sınava girmedi")
        self.girmedi_dugmesi.setToolTip("Seçili öğrenciyi sınava girmedi diye işaretler ve sonraki kâğıda geçer.")
        self.girmedi_dugmesi.clicked.connect(self.girmedi)
        self.alt_satir.addWidget(self.girmedi_dugmesi)
        self.alt_satir.addStretch(1)
        v.addLayout(self.alt_satir)
        self.durum_etiketi = QLabel()
        self.durum_etiketi.setWordWrap(True)
        v.addWidget(self.durum_etiketi)
        self.setToolTip(YOL)

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
            satir, sutun = divmod(k, SUTUN)
            self.kutu_satiri.addWidget(QLabel(etiket), 2 * satir, sutun)
            e = QLineEdit()
            e.setFixedWidth(64)
            e.returnPressed.connect(lambda k=k: self._sonraki_kutu(k))
            self.kutu_satiri.addWidget(e, 2 * satir + 1, sutun)
            self.kutular.append(e)
        self.kutu_satiri.setColumnStretch(SUTUN, 1)
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
            self.oneriler.setText("   ".join(f"{o.no} {o.ad}" for o in r[:3]) + (f"   (+{len(r) - 3} öğrenci daha; biraz daha yazın)" if len(r) > 3 else ""))

    def _ilkini_sec(self):
        r = self.bul(self.ara.text())
        if r:
            self.sec(r[0])

    def sec(self, o):
        self.secili = o
        d = self.durum.proje.klasik_puanlar.get(o.no) or []
        once = any(x not in (None, "") for x in d)
        isaretli = o.no in self.durum.proje.klasik_girmedi
        self.kim.setText(f"{o.no} {o.ad}" + (" (sınava girmedi işaretli; puan kaydederseniz işaret kalkar)" if isaretli else
                                             " (daha önce girilmiş; üzerine yazılır)" if once else ""))
        self.oneriler.setText("")
        for k, e in enumerate(self.kutular):
            e.setEnabled(True)
            e.setText(d[k] if k < len(d) and d[k] is not None else "")
        self.toplam.setEnabled(True)
        self.toplam.setText(self.durum.proje.klasik_toplamlar.get(o.no) or "")
        self.kaydet_dugmesi.setEnabled(True)
        self.girmedi_dugmesi.setEnabled(True)
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
        if any(e.text().strip() for e in self.kutular):
            self.durum.girmedi_isaretle(o.no, False)
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

    def girmedi(self):
        o = self.secili
        if o is None:
            return
        self.durum.girmedi_isaretle(o.no, True)
        self.durum.degerlendir()
        self.kontrol.klasik_model.yenile()
        self.durum_etiketi.setText(f"<b>{o.ad}:</b> sınava girmedi olarak işaretlendi.")
        self._temizle()

    def kalanlari_goster(self):
        """Puanı girilmeyen ve bazı soruları boş öğrenciler; çift tıklayınca kâğıdı açılır; kalanlar topluca "girmedi"."""
        from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QMessageBox

        from ...core.klasik import giris_durumu

        p = self.durum.proje
        kalanlar, eksikler = giris_durumu(self._liste(), p.klasik_puanlar, p.klasik_girmedi, p.anahtar.soru_sayisi)
        pen = QDialog(self)
        pen.setWindowTitle("Puanı girilmeyenler")
        pen.resize(560, 520)
        v = QVBoxLayout(pen)
        if not kalanlar and not eksikler:
            v.addWidget(QLabel("✓ Bütün öğrencilerin puanı girildi ya da \"sınava girmedi\" işaretlendi. Not girişi eksiksiz."))
        secim = {}

        def ac(it):
            secim["o"] = it.data(Qt.ItemDataRole.UserRole)
            pen.accept()

        if kalanlar:
            v.addWidget(QLabel(f"<b>Hiç puanı girilmeyen: {len(kalanlar)}</b> (kâğıdı atlanmış ya da sınava girmemiş olabilir; "
                               "çift tıklayınca kâğıdı açılır)"))
            l1 = QListWidget()
            for o in kalanlar:
                it = QListWidgetItem(f"{o.no}  {o.ad}")
                it.setData(Qt.ItemDataRole.UserRole, o)
                l1.addItem(it)
            l1.itemActivated.connect(ac)
            l1.itemDoubleClicked.connect(ac)
            v.addWidget(l1, 2)
        if eksikler:
            v.addWidget(QLabel(f"<b>Bazı soruları boş: {len(eksikler)}</b> (boş soru sıfır sayılır; çift tıklayınca kâğıdı açılır)"))
            l2 = QListWidget()
            for o, bos in eksikler:
                it = QListWidgetItem(f"{o.no}  {o.ad}: boş soru {', '.join(map(str, bos))}")
                it.setData(Qt.ItemDataRole.UserRole, o)
                l2.addItem(it)
            l2.itemActivated.connect(ac)
            l2.itemDoubleClicked.connect(ac)
            v.addWidget(l2, 1)
        s = QHBoxLayout()
        if kalanlar:
            b = QPushButton(f"Kalan {len(kalanlar)} öğrenciyi \"Sınava girmedi\" işaretle…")

            def toplu():
                ad = "\n".join(f"{o.no} {o.ad}" for o in kalanlar[:25]) + (f"\n… ve {len(kalanlar) - 25} öğrenci daha" if len(kalanlar) > 25 else "")
                if QMessageBox.question(pen, "Sınava girmedi", f"Şu {len(kalanlar)} öğrenci sınava girmedi olarak işaretlensin mi?\n\n{ad}\n\n"
                                        "Sisteme \"G\" (Girmedi) olarak gider. Sonradan puan girerseniz işaret kendiliğinden kalkar.") \
                        != QMessageBox.StandardButton.Yes:
                    return
                for o in kalanlar:
                    self.durum.girmedi_isaretle(o.no, True)
                self.durum.degerlendir()
                self.kontrol.klasik_model.yenile()
                self.durum_etiketi.setText(f"{len(kalanlar)} öğrenci sınava girmedi olarak işaretlendi.")
                pen.accept()

            b.clicked.connect(toplu)
            s.addWidget(b)
        s.addStretch(1)
        k = QPushButton("Kapat")
        k.clicked.connect(pen.reject)
        s.addWidget(k)
        v.addLayout(s)
        pen.exec()
        self._temizle()
        if "o" in secim:
            self.sec(secim["o"])

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
            self.girmedi_dugmesi.setEnabled(False)
        p = self.durum.proje
        girmedi = sum(1 for o in self._liste() if o.no in p.klasik_girmedi)
        girilen = sum(1 for o in self._liste() if o.no not in p.klasik_girmedi
                      and any(x not in (None, "") for x in (p.klasik_puanlar.get(o.no) or [])))
        kalan = len(self._liste()) - girilen - girmedi
        from ...core.klasik import giris_durumu

        _, eksikler = giris_durumu(self._liste(), p.klasik_puanlar, p.klasik_girmedi, p.anahtar.soru_sayisi)
        self.kalan.setText(f"Girilen: {girilen} · Girmedi: {girmedi} · Kalan: {kalan}"
                           + (f" · <span style='color:#C0504D'>Eksik sorulu: {len(eksikler)}</span>" if eksikler else "")
                           + (" ✓ tamam" if not kalan and not eksikler and self._liste() else ""))
        self.ara.setFocus(Qt.FocusReason.OtherFocusReason)
