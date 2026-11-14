"""4. adım: renkli sonuç tablosu, uyarılar, düzeltme, sınava girmeyenler ve listede olmayanlar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QMessageBox, QPushButton, QTableView,
    QTableWidget, QTableWidgetItem, QTabWidget, QWidget, QVBoxLayout,
)

from ... import metinler as M
from ...core.modeller import SIKLAR
from ...core.puanlama import sayi_yaz
from ..tablolar import KlasikGirisModeli, SonucModeli, UyariSuzgeci
from ..tema import renk
from .temel import Adim


def _salt_okunur_tablo(basliklar: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(basliklar))
    t.setHorizontalHeaderLabels(basliklar)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)
    return t


class YapistirilabilirTablo(QTableView):
    """Excel'den kopyalanan blok (sekmeyle ayrılmış) seçili hücreden başlayarak yapıştırılır."""

    def keyPressEvent(self, e):
        if e.matches(QKeySequence.StandardKey.Paste):
            self._yapistir()
            return
        if e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.state() != QTableView.State.EditingState:
            for ix in self.selectedIndexes():
                self.model().setData(ix, None)
            return
        super().keyPressEvent(e)

    def _yapistir(self):
        ix = self.currentIndex()
        if not ix.isValid():
            return
        metin = QGuiApplication.clipboard().text().rstrip("\r\n")
        m = self.model()
        for i, satir in enumerate(metin.splitlines()):
            for j, hucre in enumerate(satir.split("\t")):
                hedef = m.index(ix.row() + i, ix.column() + j)
                if hedef.isValid() and m.flags(hedef) & Qt.ItemFlag.ItemIsEditable:
                    m.setData(hedef, hucre.strip() or None)


def _doldur(t: QTableWidget, satirlar: list[list[object]]):
    t.setRowCount(len(satirlar))
    for i, s in enumerate(satirlar):
        for j, v in enumerate(s):
            t.setItem(i, j, QTableWidgetItem("" if v is None else str(v)))


class KontrolAdimi(Adim):
    def __init__(self, durum, parent=None):
        super().__init__(durum, M.ADIMLAR[3], parent)
        ust = QHBoxLayout()
        self.ozet = QLabel()
        self.ozet.setWordWrap(True)
        ust.addWidget(self.ozet, 1)
        self.yalniz_uyarili = QCheckBox("Yalnızca uyarılıları göster")
        self.yalniz_uyarili.toggled.connect(lambda v: self.suzgec.ayarla(v))
        ust.addWidget(self.yalniz_uyarili)
        self.duzen.addLayout(ust)
        aciklama = QLabel(" ".join(
            f'<span style="background:{renk(k).name()}">&nbsp;{v}&nbsp;</span>' for k, v in
            (("D", "doğru"), ("Y", "yanlış"), ("B", "boş"), ("I", "iptal"), ("uyari", "uyarılı satır")))
            + "  Numara, ad ya da tek bir cevabı düzeltmek için hücreye çift tıklayın. Özgün okuma silinmez.")
        aciklama.setWordWrap(True)
        self.duzen.addWidget(aciklama)

        self.sekmeler = QTabWidget()
        # --- klasik sınav puan girişi
        self.klasik_sayfa = QWidget()
        v = QVBoxLayout(self.klasik_sayfa)
        s = QHBoxLayout()
        for metin, islev, ipucu in (
            ("Excel'den puan al…", self._excelden_al, "Öğrenci numarası ve S1, S2… sütunları olan bir Excel dosyasından puanları okur."),
            ("Boş puan şablonu oluştur…", self._sablon_yaz, "Öğrenci listesi ve soru sütunları olan boş bir Excel üretir; doldurup geri alabilirsiniz."),
        ):
            b = QPushButton(metin)
            b.setToolTip(ipucu)
            b.clicked.connect(islev)
            s.addWidget(b)
        s.addStretch(1)
        v.addLayout(s)
        v.addWidget(QLabel("Hücreye tıklayıp puanı yazın (Enter ile alttaki öğrenciye geçer). Excel'den bir bloğu kopyalayıp "
                           "seçili hücreye Ctrl+V (Mac'te Cmd+V) ile yapıştırabilirsiniz. Boş bırakılan öğrenci sınava girmemiş sayılır."))
        self.klasik_model = KlasikGirisModeli(self.durum, self)
        self.klasik_model.dataChanged.connect(lambda *_: self.durum.degerlendir())
        self.klasik_tablo = YapistirilabilirTablo()
        self.klasik_tablo.setModel(self.klasik_model)
        self.klasik_tablo.verticalHeader().setVisible(False)
        self.klasik_tablo.setEditTriggers(QTableView.EditTrigger.AnyKeyPressed | QTableView.EditTrigger.DoubleClicked
                                          | QTableView.EditTrigger.EditKeyPressed | QTableView.EditTrigger.SelectedClicked)
        v.addWidget(self.klasik_tablo, 1)
        self.sekmeler.addTab(self.klasik_sayfa, "Puan girişi")
        self.model = SonucModeli(self)
        self.suzgec = UyariSuzgeci(self)
        self.suzgec.setSourceModel(self.model)
        self.tablo = QTableView()
        self.tablo.setModel(self.suzgec)
        self.tablo.setSortingEnabled(True)
        self.tablo.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.doubleClicked.connect(self._cift_tik)
        self.tablo.activated.connect(self._cift_tik)  # Enter ile de düzeltme
        self.sekmeler.addTab(self.tablo, "Sonuçlar")

        self.girmeyen_tablo = _salt_okunur_tablo([M.SUTUN["no"], M.SUTUN["ad"], "Listedeki satır"])
        self.sekmeler.addTab(self.girmeyen_tablo, "Sınava girmeyenler")
        self.olmayan_tablo = _salt_okunur_tablo(["Dosya satırı", "Okunan numara", "Okunan ad", "Olası numaralar", M.SUTUN["puan"]])
        self.olmayan_tablo.doubleClicked.connect(self._olmayan_duzelt)
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Birebir eşleşmeyen numaralar otomatik eşleştirilmez. Numarayı düzeltmek için satıra çift tıklayın."))
        v.addWidget(self.olmayan_tablo)
        self.sekmeler.addTab(w, "Listede olmayanlar")
        self.duzeltme_tablo = _salt_okunur_tablo(["Dosya satırı", "Alan", "Eski değer", "Yeni değer", "Kim", "Ne zaman"])
        self.sekmeler.addTab(self.duzeltme_tablo, "Düzeltme kaydı")
        self.duzen.addWidget(self.sekmeler, 1)
        durum.sonuc_degisti.connect(self._yenile)

    def girildi(self):
        klasik = self.durum.proje.klasik
        i = self.sekmeler.indexOf(self.klasik_sayfa)
        self.sekmeler.setTabVisible(i, klasik)
        if klasik:
            self.klasik_model.yenile()
            h = self.klasik_tablo.horizontalHeader()
            h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            if self.sekmeler.currentIndex() != i and not self.durum.proje.klasik_puanlar:
                self.sekmeler.setCurrentIndex(i)
        elif self.sekmeler.currentIndex() == i:
            self.sekmeler.setCurrentIndex(1)
        self.durum.degerlendir()

    def _yenile(self):
        self._tabloyu_yenile()
        self.tamamlik_degisti.emit()

    def _tabloyu_yenile(self):
        s = self.durum.sonuc
        self.model.yukle(s)
        self.tablo.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.tablo.verticalHeader().setDefaultSectionSize(22)
        if not s:
            self.ozet.setText("Değerlendirilecek okuma yok.")
            return
        n = s.anahtar.soru_sayisi
        h = self.tablo.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for j in range(3, 3 + n):
            h.setSectionResizeMode(j, QHeaderView.ResizeMode.Fixed)
            self.tablo.setColumnWidth(j, 28)
        h.setStretchLastSection(True)
        if s.klasik:
            for j in range(3, 3 + n):
                self.tablo.setColumnWidth(j, 44)
        uyarili = sum(1 for o in s.ogrenciler if o.uyarili)
        puanlar = [o.puan for o in s.ogrenciler]
        ort = sayi_yaz(sum(puanlar) / len(puanlar), 2) if puanlar else "-"
        metin = (f"<b>{len(s.ogrenciler)}</b> öğrenci {'puanlandı' if s.klasik else 'okundu'}, ortalama {ort}. "
                 f"Uyarılı satır: <b>{uyarili}</b>.")
        kitapciklar = sorted({o.kitapcik for o in s.ogrenciler if o.kitapcik})
        if len(kitapciklar) > 1 or s.anahtar.kitapcik_anahtarlari:
            metin += " Kitapçık: " + ", ".join(f"{k} {sum(1 for o in s.ogrenciler if o.kitapcik == k)}" for k in kitapciklar) + "."
        if s.liste_var:
            metin += f" Sınava girmeyen: <b>{len(s.girmeyenler)}</b>. Listede olmayan numara: <b>{len(s.listede_olmayanlar)}</b>."
        self.ozet.setText(metin)
        self.sekmeler.setTabText(2, f"Sınava girmeyenler ({len(s.girmeyenler)})")
        self.sekmeler.setTabText(3, f"Listede olmayanlar ({len(s.listede_olmayanlar)})")
        self.sekmeler.setTabText(4, f"Düzeltme kaydı ({len(self.durum.proje.duzeltmeler)})")
        _doldur(self.girmeyen_tablo, [[g.no, g.ad, g.kaynak_satir] for g in s.girmeyenler])
        _doldur(self.olmayan_tablo, [[o.kayit.satir_no, o.no, o.okunan_ad, ", ".join(o.oneriler), sayi_yaz(o.puan, s.ayarlar.ondalik)]
                                     for o in s.listede_olmayanlar])
        _doldur(self.duzeltme_tablo, [[d.satir_no, d.alan, d.eski, d.yeni, d.kim, d.zaman] for d in self.durum.proje.duzeltmeler])

    # ---------------------------------------------------------------- düzeltme
    def _cift_tik(self, ix):
        ix = self.suzgec.mapToSource(ix)
        s = self.durum.sonuc
        if not s or not ix.isValid():
            return
        o = s.ogrenciler[ix.row()]
        tur, k = self.model.sutun_turu(ix.column())
        if s.klasik:
            if tur == "soru":
                self.sekmeler.setCurrentWidget(self.klasik_sayfa)
                satir = next((i for i, x in enumerate(self.klasik_model.ogrenciler) if x.no == o.no), 0)
                self.klasik_tablo.setCurrentIndex(self.klasik_model.index(satir, 3 + k))
            return
        if tur == "kitapcik":
            secenekler = s.anahtar.kitapciklar()
            secim, tamam = QInputDialog.getItem(self, "Kitapçık", f"{o.no} {o.ad}\nOkunan kitapçık: {o.kayit.kitapcik or 'yok'}",
                                                secenekler, max(0, secenekler.index(o.kitapcik) if o.kitapcik in secenekler else 0), False)
            if tamam:
                self.durum.duzelt(o.kayit.satir_no, "kitapcik", secim)
            return
        if tur == "no":
            self._numara_duzelt(o)
        elif tur == "ad":
            yeni, tamam = QInputDialog.getText(self, "Ad düzelt", f"Okunan: {o.okunan_ad}\nYeni ad soyad:", text=o.okunan_ad)
            if tamam:
                self.durum.duzelt(o.kayit.satir_no, "ad", yeni)
        elif tur == "soru":
            secenekler = list(SIKLAR) + ["Boş", "Çift işaret (*)"]
            mevcut = o.cevaplar[k] if k < len(o.cevaplar) else " "
            kendi = o.kaynak_soru[k] if o.kaynak_soru else k + 1
            i = secenekler.index(mevcut) if mevcut in SIKLAR else (6 if mevcut == "*" else 5)
            secim, tamam = QInputDialog.getItem(self, "Cevap düzelt", f"{o.no} {o.ad}\n{k + 1}. soru, okunan: {mevcut.strip() or 'boş'!s}",
                                                secenekler, i, False)
            if tamam:
                yeni = secim if secim in SIKLAR else (" " if secim == "Boş" else "*")
                self.durum.duzelt(o.kayit.satir_no, f"cevap:{kendi}", yeni)

    def _numara_duzelt(self, o):
        oneriler = o.oneriler
        ipucu = f"\nOlası numaralar: {', '.join(oneriler)}" if oneriler else ""
        yeni, tamam = QInputDialog.getText(self, "Numara düzelt", f"Dosya satırı {o.kayit.satir_no}, okunan: {o.kayit.ogrenci_no}{ipucu}\nYeni numara:",
                                           text=oneriler[0] if oneriler else o.no)
        if tamam and yeni.strip():
            if not yeni.strip().isdigit():
                QMessageBox.warning(self, "Numara", "Numara yalnızca rakamlardan oluşmalı.")
                return
            self.durum.duzelt(o.kayit.satir_no, "no", yeni.strip())

    def _olmayan_duzelt(self, ix):
        s = self.durum.sonuc
        if s and 0 <= ix.row() < len(s.listede_olmayanlar):
            self._numara_duzelt(s.listede_olmayanlar[ix.row()])

    # ---------------------------------------------------------------- klasik sınav
    def _excelden_al(self):
        from ...core.klasik import tablodan_klasik_puanlar
        from ...io.liste_okuyucu import sayfa_sec, sayfalari_oku

        yol, _ = QFileDialog.getOpenFileName(self, "Puan dosyası", "", "Tablolar (*.xlsx *.xls *.csv *.txt)")
        if not yol:
            return
        try:
            sayfalar = sayfalari_oku(yol)
            puanlar, notlar = tablodan_klasik_puanlar(sayfalar[sayfa_sec(sayfalar)], self.durum.proje.anahtar.soru_sayisi)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Okunamadı", str(e))
            return
        listede = {o.no for o in self.klasik_model.ogrenciler}
        yabanci = [no for no in puanlar if no not in listede]
        for no, v in puanlar.items():
            if no in listede and any(x is not None for x in v):
                self.durum.proje.klasik_puanlar[no] = v
        self.klasik_model.yenile()
        self.durum.degerlendir()
        mesaj = f"{sum(1 for no in puanlar if no in listede)} öğrencinin puanı alındı."
        if yabanci:
            mesaj += f"\nListede olmayan numaralar alınmadı: {', '.join(yabanci[:10])}" + (" …" if len(yabanci) > 10 else "")
        if notlar:
            mesaj += "\n" + "\n".join(notlar)
        QMessageBox.information(self, "Excel'den puan", mesaj)

    def _sablon_yaz(self):
        from openpyxl import Workbook

        from ...core.ciktilar import cikti_adi
        from ...export.xlsx_yazici import baslik_satiri

        yol, _ = QFileDialog.getSaveFileName(self, "Boş puan şablonu", cikti_adi(self.durum.proje.sinav, "puan_girisi"), "Excel (*.xlsx)")
        if not yol:
            return
        n = self.durum.proje.anahtar.soru_sayisi
        wb = Workbook()
        ws = wb.active
        ws.title = "Puanlar"
        baslik_satiri(ws, 1, [M.SUTUN["no"], M.SUTUN["ad"]] + [f"S{k}" for k in range(1, n + 1)])
        for r, o in enumerate(self.klasik_model.ogrenciler, start=2):
            ws.cell(row=r, column=1, value=o.no).number_format = "@"
            ws.cell(row=r, column=2, value=o.ad)
            for k, v in enumerate(self.durum.proje.klasik_puanlar.get(o.no) or [], start=3):
                ws.cell(row=r, column=k, value=v)
        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 28
        ws.freeze_panes = "C2"
        wb.save(yol)
        QMessageBox.information(self, "Şablon", f"Yazıldı:\n{yol}\n\nDoldurduktan sonra \"Excel'den puan al\" ile geri yükleyin.")

    def eksikler(self):
        if self.durum.proje.klasik and self.durum.sonuc is not None and not self.durum.sonuc.ogrenciler:
            return ["Henüz hiçbir öğrenciye puan girilmedi."]
        return [] if self.durum.sonuc else ["Önce değerlendirme yapılmalı."]


