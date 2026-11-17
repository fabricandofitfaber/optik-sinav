"""5. adım (isteğe bağlı): sınav istatistikleri — yorum, temel sayılar, puan dağılımı, madde analizi, öğrenme çıktıları,
kişi uyumu ve benzer yanlış örüntüsü. Hesaplar `core/madde_analizi.py` içindedir; burada yalnızca gösterim var."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QProgressBar, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget,
)

from ... import metinler as M
from ...core.madde_analizi import MaddeEsikleri, madde_analizi, ogrenme_ciktisi_raporu
from ...core.modeller import fraction_decimal
from ..tema import renk
from .temel import Adim


def _v(x, basamak=2, yuzde=False):
    if x is None:
        return "-"
    if yuzde:
        m = f"{abs(x) * 100:.0f}"
        return ("-" if x < 0 and m != "0" else "") + f"%{m}"  # Türkçe yazım: -%1
    return f"{x:.{basamak}f}".replace(".", ",")


class Histogram(QWidget):
    """Puan dağılımı çubuk grafiği (on aralık)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sayilar: list[int] = []
        self.etiketler: list[str] = []
        self.esik_indeksi: int | None = None
        self.setMinimumHeight(170)

    def ayarla(self, puanlar: list[float], ust: float, esik: float):
        adim = ust / 10 if ust else 10
        self.sayilar = [sum(1 for p in puanlar if (k * adim <= p < (k + 1) * adim) or (k == 9 and p == ust)) for k in range(10)]
        self.etiketler = [f"{k * adim:g}" for k in range(10)]
        self.esik_indeksi = int(esik // adim) if adim else None
        self.update()

    def paintEvent(self, _e):
        if not self.sayilar:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        sol, alt, ust = 28, 22, 22
        en_cok = max(self.sayilar) or 1
        genislik = (w - sol - 8) / len(self.sayilar)
        yazi = self.palette().color(self.foregroundRole())
        p.setPen(QPen(yazi))
        for i, sayi in enumerate(self.sayilar):
            yuk = (h - alt - ust) * sayi / en_cok
            x = sol + i * genislik
            kutu = QRectF(x + 3, h - alt - yuk, genislik - 6, yuk)
            gecti = self.esik_indeksi is not None and i >= self.esik_indeksi
            p.fillRect(kutu, QColor("#2F5597") if gecti else QColor("#C0504D"))
            if sayi:
                p.drawText(QRectF(x, h - alt - yuk - 16, genislik, 14), Qt.AlignmentFlag.AlignCenter, str(sayi))
            p.drawText(QRectF(x, h - alt + 3, genislik, 16), Qt.AlignmentFlag.AlignLeft, self.etiketler[i])
        p.drawLine(sol, h - alt, w - 8, h - alt)
        p.end()


def _kart(baslik: str) -> tuple[QFrame, QLabel]:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.StyledPanel)
    v = QVBoxLayout(f)
    v.setContentsMargins(10, 6, 10, 6)
    deger = QLabel("-")
    deger.setStyleSheet("font-size: 20px; font-weight: bold")
    b = QLabel(baslik)
    b.setStyleSheet("color: gray")
    b.setWordWrap(True)
    v.addWidget(deger)
    v.addWidget(b)
    return f, deger


def _tablo(basliklar: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(basliklar))
    t.setHorizontalHeaderLabels(basliklar)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)
    return t


def _hucre(t: QTableWidget, i: int, j: int, metin, arka: str | None = None, hiza=True):
    it = QTableWidgetItem("" if metin is None else str(metin))
    if arka:
        it.setBackground(renk(arka))
    if hiza:
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    t.setItem(i, j, it)


class IstatistikAdimi(Adim):
    def __init__(self, durum, parent=None):
        super().__init__(durum, M.ADIMLAR[4], parent)
        self.yorum = QLabel()
        self.yorum.setWordWrap(True)
        self.yorum.setTextFormat(Qt.TextFormat.RichText)
        self.duzen.addWidget(self.yorum)

        ust = QHBoxLayout()
        kartlar = QGridLayout()
        self.kartlar = {}
        for i, (ad, baslik) in enumerate([
            ("ortalama", "Ortalama"), ("medyan", "Ortanca"), ("sd", "Standart sapma"), ("basari", "Başarılı oranı"),
            ("guven", "Güvenirlik (alfa)"), ("hata", "Ölçme hatası (±puan)"), ("guclik", "Ortalama güçlük"),
            ("ayirt", "Ortalama ayırt edicilik"),
        ]):
            f, d = _kart(baslik)
            self.kartlar[ad] = (d, f.findChildren(QLabel)[1])
            kartlar.addWidget(f, i // 4, i % 4)
        ust.addLayout(kartlar, 3)
        self.histogram = Histogram()
        ust.addWidget(self.histogram, 2)
        self.duzen.addLayout(ust)

        self.sekmeler = QTabWidget()
        self.madde = _tablo(["Soru", "Doğru", "Güçlük", "Ayırt edicilik", "Düzeltilmiş madde-toplam", "Çıkarılırsa alfa",
                             "En düşük beşte bir → en yüksek beşte bir", "Değerlendirme"])
        self.sekmeler.addTab(self.madde, "Madde analizi")
        self.cikti = _tablo(["Çıktı", "Açıklama", "Sınavdaki payı", "Sınıf başarısı", "Eşiğe ulaşan öğrenci"])
        self.sekmeler.addTab(self.cikti, "Öğrenme çıktıları")
        self.uyum = _tablo([M.SUTUN["no"], M.SUTUN["ad"], M.SUTUN["puan"], "Uyum indeksi", "Beklenmedik sorular"])
        w = QWidget()
        v = QVBoxLayout(w)
        l = QLabel("Kolay soruları kaçırıp zor soruları bilen öğrenciler (Harnisch ve Linn uyarı indeksi 0,50 üstü). "
                   "Okuma hatası (bir satır kaydırarak işaretleme), dikkatsizlik ya da şans olabilir; kâğıda bakılması önerilir.")
        l.setWordWrap(True)
        v.addWidget(l)
        v.addWidget(self.uyum)
        self.uyum_sayfa = w
        self.sekmeler.addTab(w, "Kişi uyumu")
        self.benzer = _tablo(["1. öğrenci", "2. öğrenci", "Aynı yanlış şık", "İkisinin de yanlışı", "Uzaklık (standart sapma)", "Sorular"])
        w = QWidget()
        v = QVBoxLayout(w)
        l = QLabel("Aynı kitapçıktaki öğrenci çiftlerinden, sınıf geneline göre olağandışı sayıda aynı yanlış şıkkı işaretleyenler. "
                   "Bu yalnızca istatistiksel bir işarettir, kopya kanıtı değildir; oturma düzeni ve kâğıtlarla birlikte değerlendirin.")
        l.setWordWrap(True)
        v.addWidget(l)
        v.addWidget(self.benzer)
        self.benzer_sayfa = w
        self.sekmeler.addTab(w, "Benzer cevaplar")
        from PySide6.QtWidgets import QTextBrowser

        self.kavram = QTextBrowser()
        self.sekmeler.addTab(self.kavram, "Kavram yanılgıları")
        self.yapi = QTextBrowser()
        self.sekmeler.addTab(self.yapi, "Sınav yapısı")
        self.belirleyen = QTextBrowser()
        self.sekmeler.addTab(self.belirleyen, "Notu belirleyen sorular")
        self.puanlama = QTextBrowser()
        self.sekmeler.addTab(self.puanlama, "Puanlama (klasik)")
        from .donem import DonemPaneli

        self.donem = DonemPaneli(self.durum)
        self.sekmeler.addTab(self.donem, "Dönem sonu notu")
        self.ek = QTextBrowser()
        self.sekmeler.addTab(self.ek, "Ek analizler")
        # Sık bakılan üç sekme önde; ötekiler "Diğer analizler ▾" menüsünden açılır ve seçilen önde sekme olarak görünür.
        self.sekmeler.tabBar().moveTab(self.sekmeler.indexOf(self.donem), 2)
        self.ikincil = [self.uyum_sayfa, self.benzer_sayfa, self.kavram, self.yapi, self.belirleyen, self.puanlama, self.ek]
        self.uygun = {id(w): True for w in self.ikincil}
        for w in self.ikincil:
            self.sekmeler.setTabVisible(self.sekmeler.indexOf(w), False)
        from PySide6.QtWidgets import QMenu, QToolButton

        self.diger_dugme = QToolButton()
        self.diger_dugme.setText("Diğer analizler")
        self.diger_dugme.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.diger_menu = QMenu(self.diger_dugme)
        self.diger_menu.aboutToShow.connect(self._diger_menuyu_doldur)
        self.diger_dugme.setMenu(self.diger_menu)
        self.sekmeler.setCornerWidget(self.diger_dugme, Qt.Corner.TopRightCorner)
        self.duzen.addWidget(self.sekmeler, 1)
        self.not_ = QLabel("Bütün tablolar ve grafikler 4. adımdaki \"Bütün raporları klasöre kaydet\" ile Excel'e (istatistik ve öğrenme çıktısı dosyaları) yazılır.")
        self.not_.setStyleSheet("color: gray")
        self.not_.setWordWrap(True)
        self.duzen.addWidget(self.not_)

    def _diger_menuyu_doldur(self):
        self.diger_menu.clear()
        for w in self.ikincil:
            if self.uygun[id(w)]:
                e = self.diger_menu.addAction(self.sekmeler.tabText(self.sekmeler.indexOf(w)))
                e.triggered.connect(lambda _x=False, w=w: self.analiz_ac(w))

    def analiz_ac(self, w):
        """Menüden seçilen analizi önde sekme olarak açar (önceki seçilen geri menüye döner)."""
        for x in self.ikincil:
            self.sekmeler.setTabVisible(self.sekmeler.indexOf(x), x is w)
        self.sekmeler.setCurrentWidget(w)

    def _uygunluk(self, w, uygun: bool):
        """Analiz bu sınav biçiminde yoksa menüden kalkar; açıksa kapanır."""
        self.uygun[id(w)] = uygun
        if not uygun:
            self.sekmeler.setTabVisible(self.sekmeler.indexOf(w), False)

    def girildi(self):
        if self.durum.sonuc is None:
            self.durum.degerlendir()
        self.yenile()

    def yenile(self):
        s = self.durum.sonuc
        if not s or not s.ogrenciler:
            self.yorum.setText("Değerlendirilecek sonuç yok.")
            return
        esik = float(s.ayarlar.basari_esigi)
        e = MaddeEsikleri(basari_esigi=esik, cikti_esigi=esik)
        maddeler, g = madde_analizi(s, e)
        self.yorum.setText("<b>Kısaca:</b><ul>" + "".join(f"<li>{y}</li>" for y in g.yorumlar) + "</ul>")
        r = g.alfa if g.alfa is not None else g.kr20
        degerler = {
            "ortalama": _v(g.ortalama, 1), "medyan": _v(g.medyan, 1), "sd": _v(g.standart_sapma, 1),
            "basari": _v(g.basari_orani, yuzde=True), "guven": _v(r), "hata": _v(g.olcme_hatasi, 1),
            "guclik": _v(g.ortalama_guclik), "ayirt": _v(g.ortalama_ayirt_edicilik),
        }
        for ad, (etiket, _) in self.kartlar.items():
            etiket.setText(degerler[ad])
        self.kartlar["basari"][1].setText(f"{esik:g} ve üstü alan")
        try:
            ust = float(fraction_decimal(s.ayarlar.toplam_puan))
        except Exception:  # noqa: BLE001
            ust = 100.0
        self.histogram.ayarla([float(o.puan) for o in s.ogrenciler], ust, esik)

        t = self.madde
        t.setRowCount(len(maddeler))
        for i, m in enumerate(maddeler):
            _hucre(t, i, 0, m.soru_no)
            _hucre(t, i, 1, (f"{m.tam_puan:g}".replace(".", ",") + " p") if s.klasik else (m.dogru_sik or "-"))
            if m.analiz_disi:
                _hucre(t, i, 2, "analiz dışı")
                for j in range(3, 8):
                    _hucre(t, i, j, "")
                continue
            _hucre(t, i, 2, _v(m.guclik), "D" if 0.3 <= m.guclik <= 0.7 else ("B" if 0.2 <= m.guclik <= 0.9 else "Y"))
            d = m.ayirt_edicilik
            _hucre(t, i, 3, _v(d), None if d is None else ("D" if d >= 0.3 else ("B" if d >= 0.2 else "Y")))
            _hucre(t, i, 4, _v(m.duzeltilmis_r), None if m.duzeltilmis_r is None else ("Y" if m.duzeltilmis_r < 0.1 else None))
            _hucre(t, i, 5, _v(m.alfa_cikarilirsa), "uyari" if (m.alfa_cikarilirsa is not None and r is not None and m.alfa_cikarilirsa > r + 0.01) else None)
            _hucre(t, i, 6, " → ".join(_v(x, yuzde=True) for x in m.bes_grup) if m.bes_grup else "-")
            _hucre(t, i, 7, "; ".join(m.sorunlar) or "iyi", "uyari" if m.sorunlar else None, hiza=False)

        rapor = [c for c in ogrenme_ciktisi_raporu(s, esik, self.durum.cikti_aciklamalari()) if c.tur.startswith("Öğrenme")]
        t = self.cikti
        t.setRowCount(len(rapor))
        for i, c in enumerate(rapor):
            _hucre(t, i, 0, c.kod)
            _hucre(t, i, 1, c.aciklama, hiza=False)
            _hucre(t, i, 2, f"%{c.sinav_agirligi:.1f}".replace(".", ","))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(round(c.sinif_yuzdesi or 0))
            bar.setFormat(f"%{(c.sinif_yuzdesi or 0):.1f}".replace(".", ","))
            t.setCellWidget(i, 3, bar)
            _hucre(t, i, 4, _v(c.ulasan_orani, yuzde=True))
        if not rapor:
            t.setRowCount(1)
            _hucre(t, 0, 0, "-")
            _hucre(t, 0, 1, "Sorulara öğrenme çıktısı atanmadı (2. adım).", hiza=False)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        t.horizontalHeader().setStretchLastSection(False)
        t.setColumnWidth(3, 220)

        t = self.uyum
        t.setRowCount(len(g.kisi_uyumu))
        for i, k in enumerate(g.kisi_uyumu):
            for j, v in enumerate([k.no, k.ad, _v(k.puan), _v(k.indeks), ", ".join(map(str, k.beklenmedik))]):
                _hucre(t, i, j, v, hiza=j not in (1, 4))
        self.sekmeler.setTabText(self.sekmeler.indexOf(self.uyum_sayfa), f"Kişi uyumu ({len(g.kisi_uyumu)})")
        self._uygunluk(self.uyum_sayfa, not s.klasik)

        t = self.benzer
        t.setRowCount(len(g.benzer_ciftler))
        for i, c in enumerate(g.benzer_ciftler):
            for j, v in enumerate([f"{c.no1} {c.ad1}", f"{c.no2} {c.ad2}", c.ayni_yanlis, c.ikisi_yanlis, _v(c.z, 1),
                                   ", ".join(map(str, c.sorular))]):
                _hucre(t, i, j, v, hiza=j not in (0, 1, 5))
        self.sekmeler.setTabText(self.sekmeler.indexOf(self.benzer_sayfa), f"Benzer cevaplar ({len(g.benzer_ciftler)})")
        self._uygunluk(self.benzer_sayfa, not s.klasik)
        self.ek.setHtml(self._ek_html(s, maddeler, g, esik))
        self.kavram.setHtml(self._kavram_html(s))
        self.yapi.setHtml(self._yapi_html(s))
        self.belirleyen.setHtml(self._belirleyen_html(s))
        self.puanlama.setHtml(self._puanlama_html(s))
        self._uygunluk(self.puanlama, s.klasik)
        self._uygunluk(self.kavram, not s.klasik)
        self.donem.yenile()

    def _kavram_html(self, s) -> str:
        from ...core import ek_istatistik as E

        k = E.kavram_yanilgilari(s)
        self.sekmeler.setTabText(self.sekmeler.indexOf(self.kavram), f"Kavram yanılgıları ({len(k)})")
        if not k:
            return "<p>Sınıf geneline göre belirgin biçimde birlikte seçilen yanlış şık çifti bulunmadı.</p>"
        h = ["<p style='color:gray'>İki farklı sorunun yanlış şıklarını birlikte seçen öğrenciler. Aynı yanlış düşünce iki soruda birden "
             "yanıltıyor olabilir; o iki sorunun ortak konusunu sınıfla yeniden ele almak yararlı olur. Yalnızca şansla açıklanamayacak "
             "(Fisher kesin testi, p ≤ 0,01) çiftler listelenir.</p><ul>"]
        for x in k:
            h.append(f"<li><b>{x.soru1}. sorunun {x.sik1} şıkkını</b> seçen {x.secen1} öğrencinin <b>%{x.kosullu * 100:.0f}</b>'i "
                     f"<b>{x.soru2}. sorunun {x.sik2} şıkkını</b> da seçmiş (sınıfın tamamında bu oran %{x.taban * 100:.0f}; p = {_v(x.p, 4)}).</li>")
        return "".join(h) + "</ul>"

    def _belirleyen_html(self, s) -> str:
        from ...core import ek_istatistik as E

        nb = E.notu_belirleyen_sorular(s)
        if nb is None:
            return "<p>Bu analiz için en az 5 öğrenci, 2 soru ve öğrenciler arasında puan farkı gerekir.</p>"
        h = [f"<p><b>{nb.yorum}</b></p><p style='color:gray'>Öğrencilerin toplam puanları arasındaki farkların (varyansın) her sorudan gelen payı. "
             "Bir sorunun nota katkısı puan payıyla aynıysa oran 1'dir; 1,5 ve üstü soru notu puanından fazla belirliyor, "
             "0,5 ve altı az belirliyor demektir. Paylar toplamı %100'dür. Bir soru öteki sorularla ters yönde gidiyorsa payı eksi çıkar; o zaman başka bir sorunun payı %100'ü aşabilir.</p>"
             "<table cellpadding=4><tr><th>Soru</th><th>Puan payı</th><th>Nota katkı payı</th><th>Oran</th><th>Değerlendirme</th><th></th></tr>"]
        en = max((k.katki_payi for k in nb.sorular), default=0) or 1
        for k in nb.sorular:
            renk = "#C0504D" if k.durum == "fazla_belirleyici" else "#B45309" if k.durum == "az_etkili" else "#2F5597"
            cubuk = max(0, int(round(160 * k.katki_payi / en)))
            ad = {"fazla_belirleyici": "notu puanından fazla belirliyor", "az_etkili": "notu puanından az belirliyor"}.get(k.durum, "")
            h.append(f"<tr><td align=center>{k.soru_no}</td><td align=center>{_v(k.puan_payi, yuzde=True)}</td>"
                     f"<td align=center><b>{_v(k.katki_payi, yuzde=True)}</b></td><td align=center>{_v(k.oran)}</td><td>{ad}</td>"
                     f"<td><span style='background:{renk}'>{'&nbsp;' * max(1, cubuk // 4)}</span></td></tr>")
        return "".join(h) + "</table>"

    def _puanlama_html(self, s) -> str:
        from ...core import ek_istatistik as E

        if not s.klasik:
            return ""
        h = ["<h3>Okuma sırası etkisi</h3>"]
        ok = E.okuma_sirasi_etkisi(s, self.durum.proje.klasik_giris_sirasi)
        if ok is None:
            h.append("<p style='color:gray'>En az 10 kâğıdın girildiği sıra gerekir. Sıra, 3. adımda bir öğrenciye ilk puan girildiğinde "
                     "kendiliğinden kaydedilir (Excel'den alınan puanlarda dosyadaki satır sırası).</p>")
        else:
            h.append(f"<p><b>{ok.yorum}</b></p>")
        h.append("<h3>Kısmi puan profili</h3><p style='color:gray'>Her soruda tam puan, kısmi puan, sıfır ve boş sayısı. Çoğu öğrencinin kısmi "
                 "puan aldığı soruda puanlama ölçütü belirsiz olabilir.</p><table cellpadding=4><tr><th>Soru</th><th>Tam</th><th>Kısmi</th>"
                 "<th>Sıfır</th><th>Boş</th><th>Ortalama başarı</th><th>Not</th></tr>")
        for k in E.kismi_puan_profili(s) or []:
            h.append(f"<tr><td align=center>{k.soru_no}</td><td align=center>{k.tam}</td><td align=center>{k.kismi}</td>"
                     f"<td align=center>{k.sifir}</td><td align=center>{k.bos}</td><td align=center>{_v(k.ortalama_oran, yuzde=True)}</td>"
                     f"<td style='color:#C0504D'>{'; '.join(k.notlar)}</td></tr>")
        return "".join(h) + "</table>"

    def _yapi_html(self, s) -> str:
        from ...core import ek_istatistik as E

        y = E.sinav_yapisi(s)
        if y is None:
            return "<p>Bu analiz için en az 10 öğrenci ve 3 analiz edilebilir soru gerekir.</p>"
        h = [f"<p><b>{y.yorum}</b></p><p style='color:gray'>Birinci bileşenin açıkladığı pay %{y.ilk_pay * 100:.0f}, birinci / ikinci özdeğer "
             f"{'-' if y.oran_1_2 is None else _v(y.oran_1_2)}, sorular arası ortalama korelasyon {_v(y.ortalama_korelasyon, 3)}. "
             f"Özdeğerler: {', '.join(_v(d) for d in y.ozdegerler)}.</p>"]
        if y.zayif_sorular:
            h.append(f"<p>Sınavın geri kalanından farklı bir şey ölçen sorular (ortak bileşene yükü 0,20'nin altında): <b>{', '.join(map(str, y.zayif_sorular))}</b>. "
                     "Bu sorular ya ayrı bir konuyu ölçüyor ya da öğrencileri ayırmıyor; madde analiziyle birlikte bakın.</p>")
        if y.cikti_uyumu:
            h.append("<h3>Öğrenme çıktısı eşlemesi verilerle uyumlu mu?</h3><table cellpadding=3><tr><th>Çıktı</th><th>Soru</th><th>Kendi soruları arasında</th>"
                     "<th>Öteki sorularla</th><th>Değerlendirme</th></tr>")
            for kod, ic, dis, n in y.cikti_uyumu:
                h.append(f"<tr><td>{kod}</td><td align=center>{n}</td><td align=center>{_v(ic, 3)}</td><td align=center>{_v(dis, 3)}</td>"
                         f"<td>{'uyumlu' if ic > dis + 0.05 else 'ayrışmıyor'}</td></tr>")
            h.append("</table>")
        return "".join(h)

    def _ek_html(self, s, maddeler, g, esik) -> str:
        from ...core import ek_istatistik as E
        from ...kaynaklar import kullanici_klasoru

        a = s.ayarlar
        h = []
        t = E.tasarim_denetimi(s, [m.guclik for m in maddeler])
        sans = E.sans_puani(s)
        anahtar_hatasi = [m for m in maddeler if any(x.startswith("Olası anahtar hatası") for x in m.sorunlar)]
        h.append("<h3>Sınav tasarımı</h3><ul>")
        if anahtar_hatasi:
            for m in anahtar_hatasi:
                h.append(f"<li><b style='color:#C0504D'>{m.soru_no}. soru — {next(x for x in m.sorunlar if x.startswith('Olası'))}</b>. Anahtarı kontrol edin.</li>")
        if t:
            h.append("<li>Anahtarda şıklar: " + ", ".join(f"{k} {v}" for k, v in t.sik_sayilari.items()) + "</li>")
            h += [f"<li>{n}</li>" for n in t.notlar]
        if sans is not None:
            altinda = sum(1 for o in s.ogrenciler if float(o.puan) < sans)
            h.append(f"<li>Rastgele işaretleyen birinin beklenen puanı {_v(sans, 1)}. Bunun altında kalan öğrenci: {altinda}.</li>")
        h.append("</ul>")
        kk = E.kitapcik_karsilastirma(s)
        if kk:
            h.append(f"<h3>Kitapçıklar eşdeğer mi?</h3><p>{kk.kitapcik1}: {_v(kk.ortalama1, 1)} ({kk.n1} kişi), {kk.kitapcik2}: "
                     f"{_v(kk.ortalama2, 1)} ({kk.n2} kişi). Fark {_v(kk.fark, 1)}, p = {_v(kk.p, 3)}. "
                     + ("<b>Fark anlamlı: kitapçıklardan biri daha zor olmuş olabilir.</b>" if kk.p < 0.05 else "Fark anlamlı değil.") + "</p>")
        sinir = E.sinirdaki_ogrenciler(s, esik, g.olcme_hatasi)
        h.append(f"<h3>Sınırdaki öğrenciler</h3><p>Puanı {esik:g} eşiğine ölçme hatası (±{_v(g.olcme_hatasi or 5, 1)}) kadar yakın "
                 f"{len(sinir)} öğrenci var; özellikle eşiğin hemen altındakilerin kâğıdına bir daha bakmak adil olur.</p>")
        alt = [x for x in sinir if x.fark < 0][-10:]
        if alt:
            h.append("<table border=0 cellspacing=0 cellpadding=3>" + "".join(
                f"<tr><td>{x.no}</td><td>{x.ad}</td><td align=right>{_v(x.puan, 2)}</td><td style='color:#C0504D'>{_v(x.fark, 1)}</td></tr>" for x in alt) + "</table>")
        ara = E.ara_agirligi(self.durum.proje.sinav, self.durum.ders)
        f = E.final_gereken(s, ara, a.gecme_ortalamasi, a.final_alt_siniri)
        if f:
            zor = [x for x in f if x.gereken is None or x.gereken > 80]
            h.append(f"<h3>Finalde gereken puan</h3><p>Ara sınav %{ara:g}, final %{100 - ara:g}; geçme ortalaması {a.gecme_ortalamasi}, "
                     f"final alt sınırı {a.final_alt_siniri}. Finalden 80'in üstünde alması gereken ya da 100 alsa da yetişemeyecek öğrenci: "
                     f"<b>{len(zor)}</b>. Bütün liste istatistik Excel dosyasının \"Ek Analizler\" sayfasında.</p>")
        rs = E.rasch(s)
        if rs:
            kolay = sorted(rs.soru_zorluklari.items(), key=lambda kv: kv[1])
            h.append(f"<h3>Rasch modeli</h3><p>Sınav en iyi, yaklaşık %{rs.en_iyi_puan:.0f} başarı düzeyindeki öğrencileri ayırt ediyor. "
                     f"En kolay soru {kolay[0][0]}, en zor soru {kolay[-1][0]}. Soru zorlukları ve bilgi eğrisi Excel raporunda.</p>")
        arsiv = E.arsivi_oku(kullanici_klasoru() / "arsiv", self.durum.proje.sinav.ders_kodu)
        h.append("<h3>Önceki sınavlar</h3>")
        if arsiv:
            h.append("<table border=0 cellspacing=0 cellpadding=3><tr><th>Tarih</th><th>Sınav</th><th>Öğrenci</th><th>Ortalama</th><th>Başarılı</th></tr>"
                     + "".join(f"<tr><td>{x.tarih}</td><td>{x.sinav_turu}</td><td align=right>{x.ogrenci_sayisi}</td><td align=right>{_v(x.ortalama, 1)}</td>"
                               f"<td align=right>%{x.basari_orani * 100:.0f}</td></tr>" for x in arsiv) + "</table>")
        else:
            h.append("<p>Bu ders için arşivde kayıt yok. 4. adımda \"Bütün raporları klasöre kaydet\" her kullanıldığında sınavın özeti "
                     "bilgisayarınızdaki arşive eklenir; sonraki dönemlerde burada karşılaştırma görünür.</p>")
        return "".join(h)
