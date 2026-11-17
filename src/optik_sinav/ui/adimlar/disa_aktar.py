"""4. adım: Akademik Bilgi Sistemi'ne sırasıyla aktarım (sorular, öğrenci puanları, not girişi), raporlar; gelişmiş bölümde biçim seçimi, önizleme ve tek tek dosyalar."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ... import metinler as M
from ...core.ciktilar import cikti_adi
from ...core.ek_istatistik import ara_agirligi
from ...core.modeller import UyariTuru
from ...export.pano import pano_metni
from ...export.profil import Profil, Sutun, hucre_metni, profil_bul, profilleri_listele, tablo_uret
from ...export.raporlar import tum_raporlari_yaz
from ...export.sablon_doldurucu import numara_sirasi, sablondan_profil_oner, sablonu_doldur
from ...export.xlsx_yazici import aktarim_yaz, uzanti
from ...kaynaklar import kullanici_klasoru
from .temel import Adim, menu_dugmesi


class ProfilOnayi(QDialog):
    """Şablondan önerilen profili gösterir; kullanıcı ad, "girmedi" gösterimi ve ondalık basamağı onaylar."""

    def __init__(self, profil: Profil, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Şablondan profil önerisi")
        self.profil = profil
        v = QVBoxLayout(self)
        sb = profil.sablon
        sorular = ", ".join(f"S{k}→{j}. sütun" for k, j in sorted(sb.soru_sutunlari.items())) or "bulunamadı"
        v.addWidget(QLabel(
            f"<b>Sayfa:</b> {sb.sayfa}<br><b>Başlık satırı:</b> {sb.baslik_satiri}<br><b>Numara sütunu:</b> {sb.no_sutun}<br>"
            f"<b>Ad sütunu:</b> {sb.ad_sutun or '-'}<br><b>Soru sütunları:</b> {sorular}<br><b>Toplam puan sütunu:</b> {sb.puan_sutunu or '-'}"))
        f = QFormLayout()
        self.ad = QLineEdit(profil.ad)
        self.girmedi = QLineEdit(profil.girmedi_gosterimi)
        self.ondalik = QLineEdit(str(profil.ondalik_basamak))
        f.addRow("Profil adı", self.ad)
        f.addRow("Sınava girmeyen gösterimi", self.girmedi)
        f.addRow("Ondalık basamak", self.ondalik)
        v.addLayout(f)
        v.addWidget(QLabel("Bu bir öneridir. Sütunlar yanlışsa kaydedilen JSON dosyasını düzenleyebilirsiniz."))
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def sonuc(self) -> Profil:
        try:
            ondalik = int(self.ondalik.text())
        except ValueError:
            ondalik = self.profil.ondalik_basamak
        return replace(self.profil, ad="".join(c for c in self.ad.text() if c.isalnum() or c in "_-") or self.profil.ad,
                       girmedi_gosterimi=self.girmedi.text(), ondalik_basamak=ondalik)


class DisaAktarAdimi(Adim):
    def __init__(self, durum, parent=None):
        super().__init__(durum, M.ADIMLAR[3], parent)
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QToolButton, QWidget

        from .dosyalar import VURGULU_DUGME

        # Önemli uyarılar en üstte
        self.bilgi = QLabel()
        self.bilgi.setWordWrap(True)
        self.bilgi.setStyleSheet("background: #fff4e5; color: #7a4100; border: 1px solid #f0c27a; border-radius: 6px; padding: 8px;")
        self.bilgi.setVisible(False)
        self.duzen.addWidget(self.bilgi)

        # --- Akademik Bilgi Sistemi'ne aktarım: sırasıyla iki yapıştırma
        g = QGroupBox("Akademik Bilgi Sistemi'ne aktarım (sırasıyla)")
        v = QVBoxLayout(g)
        for metin, islev, aciklama in (
            ("1. Soruları kopyala", self._sorulari_kopyala,
             "Sınav Akreditasyon İşlemleri'nde sınavı açın → \"Toplu Sınav Soru Tanım\" → \"Toplu Aktarım Yap\". "
             "Kolon Ayracı \"Excel'den Kopyalandı\" olsun; Aktarım Kutusu'na yapıştırıp \"Aktar\"a basın. "
             "Soru puanları ve öğrenme çıktısı oranları gider; bonus soru gitmez."),
            ("2. Öğrenci puanlarını kopyala", self._ogrenci_puanlarini_kopyala,
             "Sorular tanımlandıktan sonra açılan öğrenci puanı ekranına yapıştırın: öğrenci listesi sırasıyla numara ve soru "
             "puanları. Bu ekranın biçimi henüz doğrulanmadı; ilk kullanımda bir öğrencinin satırını ekranla karşılaştırın."),
            ("3. Not girişi için puanları kopyala", self._notlari_kopyala,
             "Not Giriş ekranı için: öğrenci numarası ve sınav puanı (öğrenci listesi sırasıyla)."),
        ):
            s = QHBoxLayout()
            b = QPushButton(metin)
            b.setMinimumWidth(260)
            b.setMinimumHeight(34)
            b.setStyleSheet("font-weight: bold; text-align: left; padding-left: 10px;")
            b.clicked.connect(islev)
            s.addWidget(b, 0, Qt.AlignmentFlag.AlignTop)
            l = QLabel(aciklama)
            l.setWordWrap(True)
            l.setStyleSheet("color: gray")
            s.addWidget(l, 1)
            v.addLayout(s)
        self.duzen.addWidget(g)

        # --- Raporlar
        g = QGroupBox("Raporlar")
        s = QHBoxLayout(g)
        b = QPushButton("Bütün raporları klasöre kaydet…")
        b.setToolTip("Sonuç, aktarım, istatistik (grafikli), öğrenme çıktısı, karneler ve özet dosyaları.")
        b.setStyleSheet(VURGULU_DUGME)
        b.setMinimumHeight(38)
        b.clicked.connect(self._hepsi)
        s.addWidget(b)
        b = QPushButton("Öğrenci karneleri…")
        b.setToolTip("Her öğrenciye bir sayfa: puan, sıra, öğrenme çıktıları ve soru soru sonuç. Tarayıcıda açılır, yazdırılır.")
        b.clicked.connect(self._karneler)
        s.addWidget(b)
        s.addStretch(1)
        self.duzen.addWidget(g)

        # --- Gelişmiş: aktarım biçimi (profil), tek tek dosyalar ve önizleme
        self.gelismis_dugme = QToolButton()
        self.gelismis_dugme.setText("Gelişmiş: aktarım biçimi, tek tek dosyalar ve önizleme")
        self.gelismis_dugme.setCheckable(True)
        self.gelismis_dugme.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.gelismis_dugme.setArrowType(Qt.ArrowType.RightArrow)
        self.gelismis_dugme.setStyleSheet("QToolButton { border: none; color: gray; }")
        self.duzen.addWidget(self.gelismis_dugme)
        self.gelismis = QWidget()
        gv = QVBoxLayout(self.gelismis)
        gv.setContentsMargins(0, 0, 0, 0)
        g = QGroupBox("Aktarım biçimi (Akademik Bilgi Sistemi biçimi henüz doğrulanmadı; biçimler geçicidir)")
        f = QFormLayout(g)
        self.akr = QComboBox()
        self.ng = QComboBox()
        f.addRow("Sınav Akreditasyon (soru bazlı)", self.akr)
        f.addRow("Not Giriş", self.ng)
        s = QHBoxLayout()
        b = QPushButton("Şablondan biçim oluştur…")
        b.setToolTip("Sistemden indirdiğiniz boş şablonu gösterin; başlıklar ve öğrenci satırları tanınıp biçim önerilir.")
        b.clicked.connect(self._sablondan_profil)
        s.addWidget(b)
        self.sablon_etiket = QLabel()
        s.addWidget(self.sablon_etiket, 1)
        f.addRow(s)
        gv.addWidget(g)
        self.akr.currentIndexChanged.connect(self._profil_degisti)
        self.ng.currentIndexChanged.connect(self._profil_degisti)
        s = QHBoxLayout()
        s.addWidget(menu_dugmesi("Tek tek kaydet", [
            ("Akreditasyon dosyasını kaydet…", lambda: self._tek_dosya("akr"), "Seçili akreditasyon biçimine göre dosya yazar."),
            ("Not giriş dosyasını kaydet…", lambda: self._tek_dosya("ng"), "Seçili not giriş biçimine göre dosya yazar."),
            ("Sistem şablonunu doldur…", self._sablonu_doldur, "Sistemden indirilen şablonun içine, öğrenci sırasını koruyarak puanları yazar."),
        ], self))
        b = QPushButton("Sütun seçerek panoya kopyala…")
        b.setToolTip("Seçili sütunları sistemdeki öğrenci sırasıyla sekmeyle ayrılmış olarak kopyalar.")
        b.clicked.connect(self._panoya)
        s.addWidget(b)
        self.onizleme_secim = QComboBox()
        self.onizleme_secim.addItems(["Akreditasyon önizlemesi", "Not giriş önizlemesi"])
        self.onizleme_secim.currentIndexChanged.connect(self._onizle)
        s.addWidget(self.onizleme_secim)
        s.addStretch(1)
        gv.addLayout(s)
        self.onizleme = QTableWidget()
        self.onizleme.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.onizleme.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.onizleme.setMinimumHeight(260)
        gv.addWidget(self.onizleme, 1)
        self.gelismis.setVisible(False)
        self.duzen.addWidget(self.gelismis, 1)
        self.gelismis_dugme.toggled.connect(self._gelismis_ac)
        self.duzen.addStretch(0)
        self.durum_satiri = QLabel()
        self.durum_satiri.setWordWrap(True)
        self.durum_satiri.setStyleSheet("color: #1e7b34")
        self.duzen.addWidget(self.durum_satiri)

    def _gelismis_ac(self, acik: bool):
        self.gelismis.setVisible(acik)
        self.gelismis_dugme.setArrowType(Qt.ArrowType.DownArrow if acik else Qt.ArrowType.RightArrow)

    # ---------------------------------------------------------------- sisteme aktarım
    def _sorulari_kopyala(self):
        from .anahtar import soru_tanimini_kopyala

        if soru_tanimini_kopyala(self, self.durum):
            self.durum_satiri.setText(f"✓ {self.durum.sinav_kisa_adi()} için {len(self.durum.proje.anahtar.aktarim_sorulari())} sorunun tanımı "
                                      "panoya kopyalandı. Sistemde aynı dersin ekranında olduğunuzdan emin olun.")

    def _ogrenci_puanlarini_kopyala(self):
        self._kopyala([Sutun("ogrenci_no", "Öğrenci No"), Sutun("soru_puanlari", "S{n}")], "öğrencinin soru puanları")

    def _notlari_kopyala(self):
        self._kopyala([Sutun("ogrenci_no", "Öğrenci No"), Sutun("puan", "Puan")], "öğrencinin numarası ve puanı", profil="ng")

    # ---------------------------------------------------------------- profiller
    def _profilleri_doldur(self):
        profiller = profilleri_listele()
        for cb, secili in ((self.akr, self.durum.proje.profil_akreditasyon), (self.ng, self.durum.proje.profil_not_giris)):
            cb.blockSignals(True)
            cb.clear()
            for ad, yol in profiller.items():
                try:
                    p = Profil.yukle(yol)
                    cb.addItem(f"{p.baslik or ad}" + ("  [taslak]" if p.taslak else ""), ad)
                except Exception:  # noqa: BLE001
                    continue
            i = cb.findData(secili)
            cb.setCurrentIndex(max(i, 0))
            cb.blockSignals(False)
        self.sablon_etiket.setText(f"Sistem şablonu: {self.durum.proje.sistem_sablonu_yolu}" if self.durum.proje.sistem_sablonu_yolu else "")

    def _profil(self, hangi: str) -> Profil:
        cb = self.akr if hangi == "akr" else self.ng
        return profil_bul(cb.currentData())

    def _profil_degisti(self, *_):
        self.durum.proje.profil_akreditasyon = self.akr.currentData() or self.durum.proje.profil_akreditasyon
        self.durum.proje.profil_not_giris = self.ng.currentData() or self.durum.proje.profil_not_giris
        self._onizle()

    def girildi(self):
        if self.durum.sonuc is None:
            self.durum.degerlendir()
        self._profilleri_doldur()
        self._onizle()
        s = self.durum.sonuc
        notlar = []
        if s and any(u.tur == UyariTuru.TEKRAR_NUMARA for o in s.ogrenciler for u in o.uyarilar):
            notlar.append("Aynı numara birden çok satırda var; aktarımda yalnızca sonuncusu kullanılır. 3. adımda düzeltin.")
        if s and s.listede_olmayanlar:
            notlar.append(f"Listede olmayan {len(s.listede_olmayanlar)} numara sisteme aktarılmaz (önce 3. adımda numarasını düzeltin).")
        self.bilgi.setText(" ".join(notlar))
        self.bilgi.setVisible(bool(notlar))

    def _onizle(self, *_):
        s = self.durum.sonuc
        if not s or self.akr.count() == 0:
            return
        try:
            p = self._profil("akr" if self.onizleme_secim.currentIndex() == 0 else "ng")
        except KeyError:
            return
        if p.dosya_turu == "sablon":
            p = replace(p, sutunlar=p.sutunlar or [Sutun("ogrenci_no", "Öğrenci No")])
        _, basliklar, veri = tablo_uret(p, s, self.durum.proje.sinav)
        self.onizleme.setColumnCount(len(basliklar))
        self.onizleme.setHorizontalHeaderLabels(basliklar)
        self.onizleme.setRowCount(len(veri))
        for i, satir in enumerate(veri):
            for j, h in enumerate(satir):
                self.onizleme.setItem(i, j, QTableWidgetItem(hucre_metni(h, p)))

    # ---------------------------------------------------------------- işlemler
    def _sablondan_profil(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Sistemden indirilen şablon", "", "Excel (*.xlsx *.xls)")
        if not yol:
            return
        try:
            p = sablondan_profil_oner(yol)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Şablon", str(e))
            return
        d = ProfilOnayi(p, self)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        p = d.sonuc()
        hedef = kullanici_klasoru() / "profiles" / f"{p.ad}.json"
        p.kaydet(hedef)
        self.durum.proje.profil_akreditasyon = p.ad
        self.durum.proje.sistem_sablonu_yolu = yol
        self._profilleri_doldur()
        self._onizle()
        QMessageBox.information(self, "Profil", f"Profil kaydedildi:\n{hedef}")

    def _tek_dosya(self, hangi):
        s = self.durum.sonuc
        try:
            p = self._profil(hangi)
        except KeyError as e:
            QMessageBox.warning(self, "Profil", str(e))
            return
        if p.dosya_turu == "sablon":
            self._sablonu_doldur()
            return
        oneri = cikti_adi(self.durum.proje.sinav, "akreditasyon" if hangi == "akr" else "not_giris", uzanti(p))
        yol, _ = QFileDialog.getSaveFileName(self, "Kaydet", str(self._klasor() / oneri))
        if yol:
            try:
                aktarim_yaz(p, s, yol, self.durum.proje.sinav)
                self.bilgi.setText(f"Yazıldı: {yol}")
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self, "Yazılamadı", str(e))

    def _sablonu_doldur(self):
        sablon = self.durum.proje.sistem_sablonu_yolu
        if not sablon or not Path(sablon).exists():
            sablon, _ = QFileDialog.getOpenFileName(self, "Sistemden indirilen şablon", "", "Excel (*.xlsx *.xls)")
            if not sablon:
                return
            self.durum.proje.sistem_sablonu_yolu = sablon
        try:
            p = self._profil("akr")
            if p.sablon is None:
                p = sablondan_profil_oner(sablon)
            oneri = cikti_adi(self.durum.proje.sinav, "akreditasyon_sablon")
            yol, _ = QFileDialog.getSaveFileName(self, "Doldurulmuş şablonu kaydet", str(self._klasor() / oneri), "Excel (*.xlsx)")
            if not yol:
                return
            r = sablonu_doldur(sablon, p, self.durum.sonuc, yol)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Şablon doldurulamadı", str(e))
            return
        mesaj = f"Yazıldı: {r.cikti}\nPuan yazılan öğrenci: {r.yazilan}. Şablonda olup sınava girmeyen: {len(r.girmedi)}."
        if r.sablonda_olmayan:
            mesaj += f"\nSonuçta olup şablonda olmayan numaralar: {', '.join(r.sablonda_olmayan)}"
        QMessageBox.information(self, "Şablon dolduruldu", mesaj)

    def _panoya(self):
        s = self.durum.sonuc
        secenekler = ["Soru puanları (S1..Sn)", "Puan", "Öğrenci No ve puan", "Öğrenci No ve soru puanları"]
        from PySide6.QtWidgets import QInputDialog

        secim, tamam = QInputDialog.getItem(self, "Panoya kopyala", "Kopyalanacak sütunlar:", secenekler, 0, False)
        if not tamam:
            return
        sutunlar = {
            0: [Sutun("soru_puanlari", "S{n}")],
            1: [Sutun("puan", "Puan")],
            2: [Sutun("ogrenci_no", "Öğrenci No"), Sutun("puan", "Puan")],
            3: [Sutun("ogrenci_no", "Öğrenci No"), Sutun("soru_puanlari", "S{n}")],
        }[secenekler.index(secim)]
        self._kopyala(sutunlar, "satır")

    def _kopyala(self, sutunlar, ne: str, profil: str = "akr"):
        """Seçili biçimin yuvarlama ve ondalık ayarlarıyla, sistemdeki öğrenci sırasıyla panoya kopyalar (başlık satırı yok)."""
        s = self.durum.sonuc
        if s is None:
            QMessageBox.warning(self, "Sonuç yok", "Önce 1-3. adımları tamamlayın.")
            return
        temel = self._profil(profil)
        p = replace(temel, sutunlar=sutunlar)
        sira = None
        kaynak = "öğrenci listesi sırası" if s.liste_var else "optik dosya sırası"
        sablon = self.durum.proje.sistem_sablonu_yolu
        if sablon and Path(sablon).exists():
            try:
                sira = numara_sirasi(sablon, temel if temel.sablon else None)
                kaynak = "sistem şablonundaki sıra"
            except Exception:  # noqa: BLE001
                sira = None
        QGuiApplication.clipboard().setText(pano_metni(p, s, sira))
        satir = len(sira) if sira is not None else len(tablo_uret(p, s)[2])
        self.durum_satiri.setText(f"✓ {self.durum.sinav_kisa_adi()} için panoya {satir} {ne} kopyalandı ({kaynak}). "
                                  "Sistemde aynı dersin ekranında olduğunuzdan emin olun; tablonun ilk hücresine yapıştırın.")

    def _karneler(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from ...export.karne import karne_yaz

        oneri = cikti_adi(self.durum.proje.sinav, "karneler", ".html")
        yol, _ = QFileDialog.getSaveFileName(self, "Öğrenci karneleri", str(self._klasor() / oneri), "Web sayfası (*.html)")
        if not yol:
            return
        karne_yaz(self.durum.sonuc, self.durum.proje.sinav, yol, self.durum.cikti_aciklamalari())
        QDesktopServices.openUrl(QUrl.fromLocalFile(yol))
        self.bilgi.setText(f"Karneler yazıldı ve tarayıcıda açıldı: {yol}. Yazdırmak için tarayıcıda Cmd+P (Windows'ta Ctrl+P).")

    def _klasor(self) -> Path:
        pr = self.durum.proje
        p = self.durum.proje_yolu or (Path(pr.dat_yolu) if pr.dat_yolu else (Path(pr.liste_yolu) if pr.liste_yolu else None))
        return p.parent if p else Path.home()

    def _hepsi(self):
        klasor = QFileDialog.getExistingDirectory(self, "Raporların yazılacağı klasör", str(self._klasor()))
        if not klasor:
            return
        p = self.durum.proje
        try:
            t = tum_raporlari_yaz(self.durum.sonuc, p.sinav, klasor, p.duzeltmeler, self._profil("akr"), self._profil("ng"),
                                  p.sistem_sablonu_yolu or None, giris_sirasi=p.klasik_giris_sirasi,
                                  kaynaklar={"Sınav biçimi": "Klasik" if p.klasik else "Optik",
                                             "Optik dosya": Path(p.dat_yolu).name if p.dat_yolu else "",
                                             "Öğrenci listesi": Path(p.liste_yolu).name if p.liste_yolu else ""},
                                  cikti_aciklamalari=self.durum.cikti_aciklamalari(),
                                  ara_agirlik=ara_agirligi(p.sinav, self.durum.ders),
                                  arsiv_klasoru=kullanici_klasoru() / "arsiv",
                                  donem=self.window().adimlar[4].donem.donem() if hasattr(self.window(), "adimlar") else None)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Raporlar yazılamadı", str(e))
            return
        QMessageBox.information(self, "Raporlar yazıldı", "\n".join([str(d.name) for d in t.dosyalar] + [""] + t.notlar) + f"\n\nKlasör: {klasor}")
        self.bilgi.setText(f"{len(t.dosyalar)} dosya yazıldı: {klasor}")


