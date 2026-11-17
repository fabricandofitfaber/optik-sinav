"""İstatistik adımındaki "Dönem sonu notu" sekmesi: final puanları, harf tablosu ve sonuçlar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QRadioButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ...core.donem_sonu import HarfAyarlari, donem_sonu, tablodan_final_puanlari
from ...core.ek_istatistik import ara_agirligi
from ..tema import renk


def _v(x, n=2):
    return "" if x is None else f"{x:.{n}f}".replace(".", ",")


class DonemPaneli(QWidget):
    def __init__(self, durum, parent=None):
        super().__init__(parent)
        self.durum = durum
        self._yukleniyor = False
        v = QVBoxLayout(self)
        self.bilgi = QLabel()
        self.bilgi.setWordWrap(True)
        v.addWidget(self.bilgi)
        s = QHBoxLayout()
        self.mutlak_r = QRadioButton("Mutlak")
        self.bagil_r = QRadioButton("Bağıl (T-puanı)")
        g = QButtonGroup(self)
        g.addButton(self.mutlak_r)
        g.addButton(self.bagil_r)
        self.en_az = QSpinBox(minimum=2, maximum=1000)
        for w in (QLabel("Değerlendirme"), self.mutlak_r, self.bagil_r, QLabel("Bağıl için en az öğrenci"), self.en_az):
            s.addWidget(w)
        s.addStretch(1)
        v.addLayout(s)
        self.mutlak = QLineEdit()
        self.bagil = QLineEdit()
        self.gecen = QLineEdit()
        for etiket, w in (("Mutlak tablo (ham not)", self.mutlak), ("Bağıl tablo (T-puanı)", self.bagil), ("Geçer harfler", self.gecen)):
            s = QHBoxLayout()
            s.addWidget(QLabel(etiket))
            s.addWidget(w, 1)
            v.addLayout(s)
        s = QHBoxLayout()
        b = QPushButton("Uygula")
        b.clicked.connect(self._ayar_kaydet)
        s.addWidget(b)
        b = QPushButton("Final puanlarını Excel'den al…")
        b.clicked.connect(self._excelden)
        s.addWidget(b)
        s.addWidget(QLabel("Final hücresine çift tıklayıp elle de yazabilirsiniz."))
        s.addStretch(1)
        v.addLayout(s)
        self.ozet = QLabel()
        self.ozet.setWordWrap(True)
        v.addWidget(self.ozet)
        self.tablo = QTableWidget(0, 0)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.itemChanged.connect(self._final_degisti)
        v.addWidget(self.tablo, 1)
        self.mutlak_r.toggled.connect(lambda _x: self._ayar_kaydet())

    def _ayar(self) -> HarfAyarlari:
        return HarfAyarlari.from_dict(self.durum.proje.harf_ayarlari)

    def _ayar_kaydet(self):
        if self._yukleniyor:
            return
        self.durum.proje.harf_ayarlari = HarfAyarlari(
            yontem="bagil" if self.bagil_r.isChecked() else "mutlak", mutlak=self.mutlak.text(), bagil=self.bagil.text(),
            bagil_en_az=self.en_az.value(), gecen=self.gecen.text()).to_dict()
        self.yenile()

    def _excelden(self):
        from ...io.liste_okuyucu import sayfa_sec, sayfalari_oku

        yol, _ = QFileDialog.getOpenFileName(self, "Final puanları", "", "Tablolar (*.xlsx *.xls *.csv *.txt)")
        if not yol:
            return
        try:
            sayfalar = sayfalari_oku(yol)
            fin, notlar = tablodan_final_puanlari(sayfalar[sayfa_sec(sayfalar)])
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Okunamadı", str(e))
            return
        var = {o.no for o in self.durum.sonuc.ogrenciler} if self.durum.sonuc else set()
        n = 0
        for no, x in fin.items():
            if no in var:
                if x is None:
                    self.durum.proje.final_puanlar.pop(no, None)
                else:
                    self.durum.proje.final_puanlar[no] = x
                    n += 1
        self.yenile()
        QMessageBox.information(self, "Final puanları", f"{n} öğrencinin final puanı alındı." + ("\n" + "\n".join(notlar) if notlar else ""))

    def _final_degisti(self, it: QTableWidgetItem):
        if self._yukleniyor or it.column() != 3:
            return
        no = self.tablo.item(it.row(), 0).text()
        x = it.text().strip()
        if x:
            self.durum.proje.final_puanlar[no] = x
        else:
            self.durum.proje.final_puanlar.pop(no, None)
        self.yenile()

    def yenile(self):
        s = self.durum.sonuc
        p = self.durum.proje
        a = p.ayarlar
        h = self._ayar()
        ara = ara_agirligi(p.sinav, self.durum.ders)
        self._yukleniyor = True
        try:
            (self.bagil_r if h.yontem == "bagil" else self.mutlak_r).setChecked(True)
            self.en_az.setValue(h.bagil_en_az)
            self.mutlak.setText(h.mutlak)
            self.bagil.setText(h.bagil)
            self.gecen.setText(h.gecen)
            self.bilgi.setText(f"Final puanlarını girin ya da Excel'den alın; ara sınav bu sınavdan gelir. Ağırlıklar: ara sınav %{ara:g}, final "
                               f"%{100 - ara:g} (1. adımdaki etki oranı). Final alt sınırı {a.final_alt_siniri}, geçme ortalaması {a.gecme_ortalamasi} "
                               "(2. adımdaki Puanlama ayarları bölümünde değiştirilir). <b>Harf tabloları örnektir; üniversitenizin yönetmeliğiyle karşılaştırın.</b>")
            if not s:
                return
            d = None
            if any(x not in (None, "") for x in p.final_puanlar.values()):
                try:
                    d = donem_sonu(s, p.final_puanlar, ara, a.final_alt_siniri, a.gecme_ortalamasi, h)
                except ValueError as e:
                    self.ozet.setText(f"<span style='color:#C0504D'>{e}</span>")
            bagil = d is not None and d.uygulanan == "bagil"
            bas = ["Öğrenci No", "Ad Soyad", "Ara sınav", "Final", "Ham not"] + (["T puanı"] if bagil else []) + ["Harf", "Durum", "Açıklama", "Sınırda"]
            self.tablo.clear()
            self.tablo.setColumnCount(len(bas))
            self.tablo.setHorizontalHeaderLabels(bas)
            self.tablo.setRowCount(len(s.ogrenciler))
            notlar = {n.no: n for n in d.notlar} if d else {}
            for i, o in enumerate(s.ogrenciler):
                n = notlar.get(o.no)
                degerler = [o.no, o.ad, _v(float(o.puan)), p.final_puanlar.get(o.no) or "", _v(n.ham) if n else ""]
                if bagil:
                    degerler.append(_v(n.t, 1) if n and n.t is not None else "")
                degerler += [n.harf if n else "", ("" if not n or n.gecti is None else ("Geçti" if n.gecti else "Kaldı")), n.aciklama if n else "", n.sinirda if n else ""]
                for j, x in enumerate(degerler):
                    it = QTableWidgetItem(str(x))
                    if j != 3:
                        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if bas[j] == "Durum" and n and n.gecti is not None:
                        it.setBackground(renk("D" if n.gecti else "Y"))
                    if bas[j] == "Sınırda" and n and n.sinirda:
                        it.setBackground(renk("uyari"))
                    self.tablo.setItem(i, j, it)
            self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            if d:
                dag = "  ".join(f"<b>{k}</b> {v}" for k, v in d.dagilim.items())
                self.ozet.setText(
                    f"<b>Uygulanan: {'bağıl (T-puanı)' if bagil else 'mutlak'} değerlendirme.</b> "
                    + (f"Bağıl grup {d.bagil_grup} öğrenci, ortalama {_v(d.ortalama)}, standart sapma {_v(d.standart_sapma)}. " if bagil else "")
                    + " ".join(d.notlar_metin) + f"<br>Harf dağılımı: {dag}<br>Geçen: <b>{sum(1 for n in d.notlar if n.gecti)}</b>, kalan: "
                    f"<b>{sum(1 for n in d.notlar if n.gecti is False)}</b>, finali girilmeyen: <b>{sum(1 for n in d.notlar if n.gecti is None)}</b>, "
                    f"bir üst harfe 1 puandan az kalan: <b>{sum(1 for n in d.notlar if n.sinirda)}</b>.")
            elif not self.ozet.text().startswith("<span"):
                self.ozet.setText("Henüz final puanı girilmedi.")
        finally:
            self._yukleniyor = False

    def donem(self):
        """Dışa aktarma için güncel dönem sonu sonucu (final girilmemişse None)."""
        s, p = self.durum.sonuc, self.durum.proje
        if not s or not any(x not in (None, "") for x in p.final_puanlar.values()):
            return None
        try:
            return donem_sonu(s, p.final_puanlar, ara_agirligi(p.sinav, self.durum.ders), p.ayarlar.final_alt_siniri,
                              p.ayarlar.gecme_ortalamasi, self._ayar())
        except ValueError:
            return None
