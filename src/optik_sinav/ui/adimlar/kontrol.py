"""3. adım: düzeltilmesi gerekenler listesi, renkli sonuç tablosu, uyarılar, düzeltme, sınava girmeyenler ve listede olmayanlar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QListWidgetItem,
    QListWidget,
    QGroupBox,
    QCheckBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QMessageBox, QPushButton, QTableView,
    QTableWidget, QTableWidgetItem, QTabWidget, QWidget, QVBoxLayout,
)

from ... import metinler as M
from ...core.modeller import SIKLAR, UyariTuru
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



def _sarili(metin):
    l = QLabel(metin)
    l.setWordWrap(True)
    return l

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
        super().__init__(durum, M.ADIMLAR[2], parent)
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
            (("D", "doğru"), ("Y", "yanlış"), ("B", "boş"), ("I", "iptal"), ("K", "bonusla doğru"), ("uyari", "uyarılı satır")))
            + "  Numara, ad ya da tek bir cevabı düzeltmek için hücreye çift tıklayın. Özgün okuma silinmez.")
        aciklama.setWordWrap(True)
        self.aciklama = aciklama  # optik sınava özgü; klasikte gizlenir

        # Düzeltilmesi gerekenler: uyarılı satırlar okunur bir listede, tıklayınca tabloda o satıra gidilir (optik)
        self.duzeltilecek_kutusu = QGroupBox("Düzeltilmesi gerekenler")
        v = QVBoxLayout(self.duzeltilecek_kutusu)
        self.duzeltilecekler = QListWidget()
        self.duzeltilecekler.setMaximumHeight(150)
        self.duzeltilecekler.setWordWrap(True)
        self.duzeltilecekler.itemClicked.connect(self._duzeltilecege_git)
        self.duzeltilecekler.itemActivated.connect(self._duzeltilecege_git)
        v.addWidget(self.duzeltilecekler)
        self.geri_al = QPushButton("Otomatik numara düzeltmesini geri al")
        self.geri_al.setToolTip("Seçili satırdaki, adla eşleştirilerek yapılan numara düzeltmesini kaldırır.")
        self.geri_al.clicked.connect(self._otomatigi_geri_al)
        self.geri_al.setVisible(False)
        v.addWidget(self.geri_al)
        ip = QLabel("Satıra tıklayınca tabloda o öğrenci seçilir; hücreye çift tıklayarak düzeltin. Okunan dosyada sorun yoksa bu bölümü geçebilirsiniz.")
        ip.setWordWrap(True)
        ip.setStyleSheet("color: gray")
        v.addWidget(ip)
        self.duzen.addWidget(self.duzeltilecek_kutusu)
        self.temiz_etiketi = QLabel("<span style='color:#1e7b34'><b>✓ Düzeltilmesi gereken satır yok.</b></span>")
        self.temiz_etiketi.setVisible(False)
        self.duzen.addWidget(self.temiz_etiketi)
        self.duzen.addWidget(aciklama)

        self.sekmeler = QTabWidget()
        # --- klasik sınav puan girişi
        self.klasik_sayfa = QWidget()
        v = QVBoxLayout(self.klasik_sayfa)
        from .kagit import KagitPaneli

        self.kagit = KagitPaneli(self.durum, self)
        v.addWidget(self.kagit)
        s = QHBoxLayout()
        for metin, islev, ipucu in (
            ("Excel'den puan al…", self._excelden_al, "Öğrenci numarası ve S1, S2… sütunları olan bir Excel dosyasından puanları okur."),
            ("Puan tablosunu Excel'e kaydet…", self._sablon_yaz, "Aşağıdaki tabloyu (girilen puanlar, toplam ve Girmedi işaretiyle) Excel'e yazar. "
             "Excel'de doldurup \"Excel'den puan al\" ile geri de yükleyebilirsiniz."),
        ):
            b = QPushButton(metin)
            b.setToolTip(ipucu)
            b.clicked.connect(islev)
            s.addWidget(b)
        s.addStretch(1)
        v.addLayout(s)
        v.addWidget(_sarili("Ya da tabloda hücreye tıklayıp yazın. Excel'den bir bloğu kopyalayıp seçili hücreye Ctrl+V (Mac'te Cmd+V) "
                           "ile yapıştırabilirsiniz. Sınava girmeyenleri en sağdaki \"Girmedi\" kutusuyla işaretleyin (hiç puanı girilmeyen öğrenci de girmemiş sayılır). \"Kâğıttaki toplam\" sütunu isteğe bağlıdır; "
                           "tutmazsa kırmızı görünür."))
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
        v.addWidget(_sarili("Birebir eşleşmeyen numaralar otomatik eşleştirilmez. Numarayı düzeltmek için satıra çift tıklayın."))
        v.addWidget(self.olmayan_tablo)
        self.olmayan_sayfa = w
        self.sekmeler.addTab(w, "Listede olmayanlar")
        self.duzeltme_tablo = _salt_okunur_tablo(["Dosya satırı", "Alan", "Eski değer", "Yeni değer", "Kim", "Ne zaman"])
        self.sekmeler.addTab(self.duzeltme_tablo, "Düzeltme kaydı")
        self.duzen.addWidget(self.sekmeler, 1)
        durum.sonuc_degisti.connect(self._yenile)

    def girildi(self):
        klasik = self.durum.proje.klasik
        self.baslik_etiketi.setText(f"<h2>{M.ADIM_KLASIK_3 if klasik else M.ADIMLAR[2]}</h2>")
        i = self.sekmeler.indexOf(self.klasik_sayfa)
        self.sekmeler.setTabVisible(i, klasik)
        # optik sınava özgü olanlar klasikte gizlenir (renk açıklaması, uyarı süzgeci, listede olmayanlar, düzeltme kaydı)
        for w in (self.aciklama, self.yalniz_uyarili):
            w.setVisible(not klasik)
        for w in (self.olmayan_sayfa, self.duzeltme_tablo):
            self.sekmeler.setTabVisible(self.sekmeler.indexOf(w), not klasik)
        if klasik:
            self.klasik_model.yenile()
            self.kagit.kur()
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
            self._duzeltilecekleri_doldur(None)
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
        self._duzeltilecekleri_doldur(s)
        self.sekmeler.setTabText(2, f"Sınava girmeyenler ({len(s.girmeyenler)})")
        self.sekmeler.setTabText(3, f"Listede olmayanlar ({len(s.listede_olmayanlar)})")
        self.sekmeler.setTabText(4, f"Düzeltme kaydı ({len(self.durum.proje.duzeltmeler)})")
        _doldur(self.girmeyen_tablo, [[g.no, g.ad, g.kaynak_satir] for g in s.girmeyenler])
        _doldur(self.olmayan_tablo, [[o.kayit.satir_no, o.no, o.okunan_ad, ", ".join(o.oneriler), sayi_yaz(o.puan, s.ayarlar.ondalik)]
                                     for o in s.listede_olmayanlar])
        _doldur(self.duzeltme_tablo, [[d.satir_no, d.alan, d.eski, d.yeni, d.kim, d.zaman] for d in self.durum.proje.duzeltmeler])

    def _duzeltilecekleri_doldur(self, s):
        self.duzeltilecekler.clear()
        self.geri_al.setVisible(False)
        if s is None or s.klasik:
            self.duzeltilecek_kutusu.setVisible(False)
            self.temiz_etiketi.setVisible(False)
            return
        for i, o in enumerate(s.ogrenciler):
            if not o.uyarilar:
                continue
            it = QListWidgetItem(f"Satır {o.kayit.satir_no} · {o.no} {o.ad}: " + "; ".join(u.mesaj for u in o.uyarilar))
            it.setData(Qt.ItemDataRole.UserRole, i)
            self.duzeltilecekler.addItem(it)
        n = self.duzeltilecekler.count()
        self.duzeltilecek_kutusu.setTitle(f"Düzeltilmesi gerekenler ({n})")
        self.duzeltilecek_kutusu.setVisible(n > 0)
        self.temiz_etiketi.setVisible(n == 0)

    def _otomatigi_geri_al(self):
        it = self.duzeltilecekler.currentItem()
        s = self.durum.sonuc
        if it is None or s is None:
            return
        o = s.ogrenciler[it.data(Qt.ItemDataRole.UserRole)]
        if not any(u.tur == UyariTuru.OTOMATIK_NUMARA for u in o.uyarilar):
            return
        self.durum.proje.otomatik_kapali.append(o.kayit.satir_no)
        self.durum.degerlendir()
        self.durumdan_yukle()

    def _duzeltilecege_git(self, it):
        i = it.data(Qt.ItemDataRole.UserRole)
        s = self.durum.sonuc
        self.geri_al.setVisible(bool(s and i is not None and i < len(s.ogrenciler)
                                     and any(u.tur == UyariTuru.OTOMATIK_NUMARA for u in s.ogrenciler[i].uyarilar)))
        if i is None:
            return
        self.sekmeler.setCurrentWidget(self.tablo)
        ix = self.suzgec.mapFromSource(self.model.index(i, 0))
        if ix.isValid():
            self.tablo.selectRow(ix.row())
            self.tablo.scrollTo(ix)
            self.tablo.setFocus()

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
        from ...core.klasik import tablodan_girmedi, tablodan_klasik_puanlar
        from ...io.liste_okuyucu import sayfa_sec, sayfalari_oku

        yol, _ = QFileDialog.getOpenFileName(self, "Puan dosyası", "", "Tablolar (*.xlsx *.xls *.csv *.txt)")
        if not yol:
            return
        try:
            sayfalar = sayfalari_oku(yol)
            tablo = sayfalar[sayfa_sec(sayfalar)]
            puanlar, notlar = tablodan_klasik_puanlar(tablo, self.durum.proje.anahtar.soru_sayisi)
            girmeyenler = tablodan_girmedi(tablo)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Okunamadı", str(e))
            return
        listede = {o.no for o in self.klasik_model.ogrenciler}
        yabanci = [no for no in puanlar if no not in listede]
        for no, v in puanlar.items():
            if no in listede and any(x is not None for x in v):
                self.durum.proje.klasik_puanlar[no] = v
                if no not in self.durum.proje.klasik_giris_sirasi:
                    self.durum.proje.klasik_giris_sirasi.append(no)  # Excel'deki satır sırası okuma sırası sayılır
        for no in girmeyenler:
            if no in listede:
                self.durum.girmedi_isaretle(no, True)
        self.klasik_model.yenile()
        self.durum.degerlendir()
        mesaj = f"{sum(1 for no in puanlar if no in listede and no not in girmeyenler)} öğrencinin puanı alındı."
        if girmeyenler:
            mesaj += f" {sum(1 for no in girmeyenler if no in listede)} öğrenci sınava girmedi olarak işaretlendi."
        if yabanci:
            mesaj += f"\nListede olmayan numaralar alınmadı: {', '.join(yabanci[:10])}" + (" …" if len(yabanci) > 10 else "")
        if notlar:
            mesaj += "\n" + "\n".join(notlar)
        QMessageBox.information(self, "Excel'den puan", mesaj)

    def _sablon_yaz(self):
        from openpyxl import Workbook

        from ...core.ciktilar import cikti_adi
        from ...export.xlsx_yazici import baslik_satiri

        from ...core.klasik import puan_coz
        from ...core.puanlama import sayi_yaz, soru_puanlari

        yol, _ = QFileDialog.getSaveFileName(self, "Puan tablosunu Excel'e kaydet", cikti_adi(self.durum.proje.sinav, "puan_tablosu"), "Excel (*.xlsx)")
        if not yol:
            return
        p = self.durum.proje
        n = p.anahtar.soru_sayisi
        try:
            tam = soru_puanlari(p.anahtar, p.ayarlar)
        except Exception:  # noqa: BLE001
            tam = [None] * n
        wb = Workbook()
        ws = wb.active
        ws.title = "Puanlar"
        baslik_satiri(ws, 1, [M.SUTUN["no"], M.SUTUN["ad"]]
                      + [f"S{k} ({sayi_yaz(tam[k - 1], 2).rstrip('0').rstrip(',')})" if tam[k - 1] is not None else f"S{k}" for k in range(1, n + 1)]
                      + ["Toplam", "Girmedi"])
        for r, o in enumerate(self.klasik_model.ogrenciler, start=2):
            ws.cell(row=r, column=1, value=o.no).number_format = "@"
            ws.cell(row=r, column=2, value=o.ad)
            toplam, girildi = 0, False
            for k, v in enumerate((p.klasik_puanlar.get(o.no) or [])[:n], start=3):
                try:
                    x = puan_coz(v)
                except (ValueError, ArithmeticError):
                    x = None
                ws.cell(row=r, column=k, value=float(x) if x is not None else v)
                if x is not None:
                    toplam, girildi = toplam + x, True
            if o.no in p.klasik_girmedi:
                ws.cell(row=r, column=n + 4, value="girmedi")
            elif girildi:
                ws.cell(row=r, column=n + 3, value=float(toplam))
        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 28
        ws.freeze_panes = "C2"
        wb.save(yol)
        QMessageBox.information(self, "Puan tablosu", f"Yazıldı:\n{yol}\n\nExcel'de değiştirirseniz \"Excel'den puan al\" ile geri yükleyebilirsiniz.")

    def eksikler(self):
        if self.durum.proje.klasik and self.durum.sonuc is not None and not self.durum.sonuc.ogrenciler:
            return ["Henüz hiçbir öğrenciye puan girilmedi."]
        return [] if self.durum.sonuc else ["Önce değerlendirme yapılmalı."]


