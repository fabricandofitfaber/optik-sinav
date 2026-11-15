"""5. adım: profil seçimi ve önizleme, sistem şablonunu doldurma, panoya kopyalama, tüm raporları yazma."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

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
from .temel import Adim


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
        super().__init__(durum, M.ADIMLAR[5], parent)
        g = QGroupBox("Aktarım profilleri (Akademik Bilgi Sistemi biçimi henüz doğrulanmadı; profiller geçicidir)")
        f = QFormLayout(g)
        self.akr = QComboBox()
        self.ng = QComboBox()
        f.addRow("Sınav Akreditasyon (soru bazlı)", self.akr)
        f.addRow("Not Giriş", self.ng)
        s = QHBoxLayout()
        b = QPushButton("Şablondan profil oluştur…")
        b.setToolTip("Sistemden indirdiğiniz boş şablonu gösterin; başlıklar ve öğrenci satırları tanınıp profil önerilir.")
        b.clicked.connect(self._sablondan_profil)
        s.addWidget(b)
        self.sablon_etiket = QLabel()
        s.addWidget(self.sablon_etiket, 1)
        f.addRow(s)
        self.duzen.addWidget(g)
        self.akr.currentIndexChanged.connect(self._profil_degisti)
        self.ng.currentIndexChanged.connect(self._profil_degisti)

        self.onizleme = QTableWidget()
        self.onizleme.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.onizleme.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.onizleme_secim = QComboBox()
        self.onizleme_secim.addItems(["Akreditasyon önizlemesi", "Not giriş önizlemesi"])
        self.onizleme_secim.currentIndexChanged.connect(self._onizle)
        self.duzen.addWidget(self.onizleme_secim)
        self.duzen.addWidget(self.onizleme, 1)

        s = QGridLayout()
        for sira, (metin, islev, ipucu) in enumerate((
            ("Akreditasyon dosyasını kaydet…", lambda: self._tek_dosya("akr"), "Seçili akreditasyon profiline göre dosya yazar."),
            ("Not giriş dosyasını kaydet…", lambda: self._tek_dosya("ng"), "Seçili not giriş profiline göre dosya yazar."),
            ("Sistem şablonunu doldur…", self._sablonu_doldur, "Sistemden indirilen şablonun içine, öğrenci sırasını koruyarak puanları yazar."),
            ("Panoya kopyala…", self._panoya, "Seçili sütunları sistemdeki öğrenci sırasıyla sekmeyle ayrılmış olarak kopyalar."),
            ("Öğrenci karneleri…", self._karneler, "Her öğrenciye bir sayfa: puan, sıra, öğrenme çıktıları ve soru soru sonuç. Tarayıcıda açılır, yazdırılır."),
            ("Tüm raporları klasöre yaz…", self._hepsi, "Sonuç, aktarım, istatistik (grafikli), öğrenme çıktısı, karneler ve özet dosyaları."),
        )):
            b = QPushButton(metin)
            b.setToolTip(ipucu)
            b.clicked.connect(islev)
            s.addWidget(b, sira // 3, sira % 3)
        self.duzen.addLayout(s)
        self.bilgi = QLabel()
        self.bilgi.setWordWrap(True)
        self.duzen.addWidget(self.bilgi)

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
            notlar.append("Aynı numara birden çok satırda var; aktarımda yalnızca sonuncusu kullanılır. 4. adımda düzeltin.")
        if s and s.listede_olmayanlar:
            notlar.append(f"Listede olmayan {len(s.listede_olmayanlar)} numara aktarım dosyalarına yazılmaz (profil ayarı).")
        self.bilgi.setText(" ".join(notlar))

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
        temel = self._profil("akr")
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
        self.bilgi.setText(f"Panoya {satir} satır kopyalandı ({kaynak}). Sistemdeki tablonun ilk hücresine yapıştırın.")

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


