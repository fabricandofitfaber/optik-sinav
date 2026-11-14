"""Arayüzün ortak durumu: proje, okuma, liste ve sonuç. İş kuralları motorda; burada yalnızca bağlantı var."""
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal

from ..core.dogrulama import duzeltme_olustur, sinavi_degerlendir
from ..core.klasik import klasik_degerlendir
from ..core.puanlama import anahtar_eksikleri
from .. import metinler as M
from ..io.ders_paketi import DersPaketi, ders_bul, ders_kaydet, pdf_oku
from ..core.modeller import DatOkumaSonucu, OgrenciListesi, SinavSonucu, Soru
from ..core.proje import SinavProjesi, ders_eslemesi_kaydet, ders_eslemesi_uygula
from ..io.dat_okuyucu import dat_oku, sablon_oner
from ..io.kodlama import metin_dosyasi_oku
from ..io.liste_okuyucu import liste_oku, sayfalari_oku
from ..kaynaklar import kullanici_klasoru


def ayarlar() -> QSettings:
    return QSettings(str(kullanici_klasoru() / "ayarlar.ini"), QSettings.Format.IniFormat)


class Durum(QObject):
    degisti = Signal()  # proje, okuma ya da liste değişti
    sonuc_degisti = Signal()

    def __init__(self):
        super().__init__()
        self.proje = SinavProjesi()
        self.proje_yolu: Path | None = None
        self.okuma: DatOkumaSonucu | None = None
        self.ham_satirlar: list[str] = []
        self.liste: OgrenciListesi | None = None
        self.liste_sayfalari: dict | None = None
        self.sonuc: SinavSonucu | None = None
        self.hata: str = ""
        self.ders: DersPaketi | None = None

    # ---------------------------------------------------------- ders bilgi paketi
    def dersi_yukle(self) -> DersPaketi | None:
        """Ders koduna göre kayıtlı ders bilgi paketini yükler (öğrenme çıktıları ve açıklamaları)."""
        kod = self.proje.sinav.ders_kodu
        self.ders = ders_bul(kod) if kod else None
        if self.ders and not self.proje.sinav.ders_adi:
            self.proje.sinav.ders_adi = self.ders.ad
        return self.ders

    def ders_pdf_yukle(self, yol: str) -> DersPaketi:
        d = pdf_oku(yol)
        ders_kaydet(d)
        self.ders = d
        self.proje.sinav.ders_kodu = d.kod
        self.proje.sinav.ders_adi = d.ad
        self.degisti.emit()
        return d

    def ogrenme_kodlari(self) -> list[str]:
        return self.ders.ogrenme_kodlari() if self.ders else []

    def program_kodlari(self) -> list[str]:
        return [c.kod for c in self.ders.program_ciktilari] if self.ders else []

    def cikti_aciklamalari(self) -> dict[str, str]:
        return self.ders.aciklamalar() if self.ders else {}

    @property
    def soru_sayisi(self) -> int:
        return self.proje.klasik_soru_sayisi if self.proje.klasik else self.proje.okuyucu.soru_sayisi

    def bicim_degistir(self, bicim: str) -> None:
        self.proje.bicim = bicim
        if bicim == "klasik":
            from ..core.modeller import PuanYontemi

            self.proje.ayarlar.yontem = PuanYontemi.SORU_BAZLI
            self.proje.ayarlar.yanlis_cezasi = False
        self.anahtari_boyutla()
        self.sonuc = None
        self.degisti.emit()

    def klasik_soru_sayisi_ayarla(self, n: int) -> None:
        from ..core.puanlama import esit_soru_puanlari

        sorular = self.proje.anahtar.sorular
        # Puanlar hâlâ eşit dağılımdaysa (kullanıcı dokunmamışsa) yeni soru sayısına göre yeniden eşit dağıtılır.
        if [s.puan for s in sorular] == esit_soru_puanlari(self.proje.ayarlar.toplam_puan, len(sorular)):
            for s in sorular:
                s.puan = None
        self.proje.klasik_soru_sayisi = max(1, n)
        self.anahtari_boyutla()
        self.degisti.emit()

    def klasik_puan_yaz(self, no: str, soru_indeksi: int, deger: str | None) -> None:
        satir = self.proje.klasik_puanlar.setdefault(no, [])
        while len(satir) <= soru_indeksi:
            satir.append(None)
        satir[soru_indeksi] = (deger or "").strip() or None
        if all(v is None for v in satir):
            del self.proje.klasik_puanlar[no]

    # ---------------------------------------------------------- dosyalar
    def dat_yukle(self, yol: str, sablonu_oner: bool = True) -> None:
        self.proje.dat_yolu = str(yol)
        self.ham_satirlar, _, _ = metin_dosyasi_oku(yol)
        if sablonu_oner:
            self.proje.okuyucu = sablon_oner(self.ham_satirlar, self.proje.okuyucu)
        self.anahtari_boyutla()
        self.dat_yeniden_oku()

    def dat_yeniden_oku(self) -> None:
        if not self.proje.dat_yolu:
            self.okuma = None
        else:
            self.okuma = dat_oku(self.proje.dat_yolu, self.proje.okuyucu)
        self.anahtari_boyutla()
        self.degisti.emit()

    def anahtari_boyutla(self) -> None:
        n = self.soru_sayisi
        sorular = self.proje.anahtar.sorular
        if len(sorular) < n:
            sorular.extend(Soru(no=k) for k in range(len(sorular) + 1, n + 1))
        elif len(sorular) > n:
            del sorular[n:]
        # Klasik sınavda hiç soru puanı yoksa toplam eşit dağıtılır (2. adım atlanırsa da puan girişi hemen açılsın)
        if self.proje.klasik and sorular and all(s.puan in (None, "") for s in sorular):
            from ..core.puanlama import esit_soru_puanlari

            for s, p in zip(sorular, esit_soru_puanlari(self.proje.ayarlar.toplam_puan, len(sorular))):
                s.puan = p

    def liste_yukle(self, yol: str | None, esleme=None) -> None:
        if not yol:
            self.proje.liste_yolu = ""
            self.liste = None
            self.liste_sayfalari = None
        else:
            self.proje.liste_yolu = str(yol)
            self.liste_sayfalari = sayfalari_oku(yol)
            self.liste = liste_oku(yol, esleme)
            self.proje.liste_esleme = self.liste.esleme
        self.degisti.emit()

    # ---------------------------------------------------------- değerlendirme
    def hesap_eksikleri(self) -> list[str]:
        """Sonucun hesaplanmasına engel olan eksikler (boşsa hesaplanabilir)."""
        e = []
        if self.proje.klasik:
            if self.liste is None:
                e.append("Klasik sınavda öğrenci listesi gerekli.")
        elif self.okuma is None:
            e.append(M.EKSIK["dat"])
        try:
            float(self.proje.ayarlar.toplam_puan)
        except ValueError:
            e.append("Toplam puan sayı olmalı.")
            return e
        if self.okuma is not None or self.proje.klasik:
            e.extend(anahtar_eksikleri(self.proje.anahtar, self.proje.ayarlar, self.proje.klasik))
        return e

    def degerlendir(self) -> SinavSonucu | None:
        if self.hesap_eksikleri():
            self.sonuc = None
        elif self.proje.klasik:
            self.sonuc = (klasik_degerlendir(self.liste, self.proje.anahtar, self.proje.ayarlar, self.proje.klasik_puanlar, self.proje.klasik_toplamlar)
                          if self.liste is not None else None)
        elif self.okuma is None:
            self.sonuc = None
        else:
            self.sonuc = sinavi_degerlendir(self.okuma.kayitlar, self.proje.anahtar, self.proje.ayarlar, self.liste, self.proje.duzeltmeler)
        self.sonuc_degisti.emit()
        return self.sonuc

    def duzelt(self, satir_no: int, alan: str, yeni: str) -> None:
        kayit = next(k for k in self.okuma.kayitlar if k.satir_no == satir_no)
        d = duzeltme_olustur(kayit, alan, yeni, self.proje.duzeltmeler)
        if d.eski == d.yeni:
            return
        self.proje.duzeltmeler.append(d)
        self.degerlendir()

    # ---------------------------------------------------------- proje dosyası
    def yeni(self) -> None:
        self.__init__()  # type: ignore[misc]

    def ac(self, yol: str, son_acilanlara: bool = True) -> list[str]:
        """Projeyi açar; bulunamayan kaynak dosyaları döndürür.

        Dosyaya gömülü optik dosya ve liste varsa (otomatik kayıt ve tarayıcı sürümü gömer), özgün dosya
        bulunamadığında gömülü kopya kullanıcı klasörüne çıkarılıp ondan okunur.
        """
        veri = json.loads(Path(yol).read_text(encoding="utf-8"))
        self.proje = SinavProjesi.from_dict(veri)
        self.proje_yolu = Path(yol)
        gomulu = veri.get("gomulu_dosyalar") or {}
        for alan, yol_alani in (("dat", "dat_yolu"), ("liste", "liste_yolu")):
            kaynak = getattr(self.proje, yol_alani)
            if kaynak and not Path(kaynak).exists() and gomulu.get(alan):
                hedef = kurtarma_klasoru() / "dosyalar" / Path(kaynak).name
                hedef.parent.mkdir(parents=True, exist_ok=True)
                hedef.write_bytes(base64.b64decode(gomulu[alan]))
                setattr(self.proje, yol_alani, str(hedef))
        eksik = []
        if self.proje.dat_yolu and Path(self.proje.dat_yolu).exists():
            self.ham_satirlar, _, _ = metin_dosyasi_oku(self.proje.dat_yolu)
            self.okuma = dat_oku(self.proje.dat_yolu, self.proje.okuyucu)
        elif self.proje.dat_yolu:
            eksik.append(self.proje.dat_yolu)
            self.okuma = None
        if self.proje.liste_yolu and Path(self.proje.liste_yolu).exists():
            self.liste_sayfalari = sayfalari_oku(self.proje.liste_yolu)
            self.liste = liste_oku(self.proje.liste_yolu, self.proje.liste_esleme if self.proje.liste_esleme.no_sutun else None)
        elif self.proje.liste_yolu:
            eksik.append(self.proje.liste_yolu)
            self.liste = None
        self.anahtari_boyutla()
        self.dersi_yukle()
        if son_acilanlara:
            son_acilanlara_ekle(yol)
        self.degisti.emit()
        return eksik

    def kaydet(self, yol: str | None = None) -> Path:
        hedef = Path(yol) if yol else self.proje_yolu
        if hedef is None:
            raise ValueError("Kayıt yolu yok")
        if hedef.suffix.lower() != ".osd":
            hedef = hedef.with_suffix(".osd")
        yaz_atomik(hedef, self.kayit_verisi())
        self.proje_yolu = hedef
        son_acilanlara_ekle(str(hedef))
        return hedef

    # ---------------------------------------------------------- otomatik kayıt
    def kayit_verisi(self, gomulu: bool = True) -> dict:
        """Proje sözlüğü; istenirse optik dosya ve liste base64 olarak gömülür (tarayıcı sürümüyle aynı alan)."""
        d = self.proje.to_dict()
        if gomulu:
            d["gomulu_dosyalar"] = {"dat": self._gomulu(self.proje.dat_yolu), "liste": self._gomulu(self.proje.liste_yolu)}
        return d

    def _gomulu(self, yol: str) -> str | None:
        if not yol or not Path(yol).exists():
            return None
        p = Path(yol)
        anahtar = (str(p), p.stat().st_mtime_ns, p.stat().st_size)
        onbellek = getattr(self, "_gomulu_onbellek", {})
        if anahtar not in onbellek:
            onbellek = {anahtar: base64.b64encode(p.read_bytes()).decode("ascii")}
            self._gomulu_onbellek = onbellek
        return onbellek[anahtar]

    def bos_mu(self) -> bool:
        """Kaydetmeye değer bir şey yok mu (dosya seçilmemiş, puan girilmemiş)."""
        p = self.proje
        return not (p.dat_yolu or p.liste_yolu or p.klasik_puanlar or p.final_puanlar
                    or any(s.dogru for s in p.anahtar.sorular))

    def otomatik_kaydet(self) -> bool:
        """Değişiklik varsa kurtarma dosyasına ve (açık bir sınav dosyası varsa) ona yazar. Yazdıysa True."""
        if self.bos_mu():
            return False
        ozet = json.dumps([self.kayit_verisi(gomulu=False), str(self.proje_yolu or "")], ensure_ascii=False, sort_keys=True)
        if ozet == getattr(self, "_son_ozet", None):
            return False
        veri = self.kayit_verisi()
        kurtarma = dict(veri, kaynak_proje_yolu=str(self.proje_yolu or ""), kayit_zamani=time.strftime("%Y-%m-%d %H:%M"))
        yaz_atomik(kurtarma_yolu(), kurtarma)
        if self.proje_yolu is not None:
            yaz_atomik(self.proje_yolu, veri)
        self._son_ozet = ozet
        return True

    def kurtarmadan_ac(self) -> list[str]:
        """Son otomatik kaydı açar; sınav bir dosyadan açılmışsa kayıt yeri yine o dosya olur."""
        yol = kurtarma_yolu()
        kaynak = json.loads(yol.read_text(encoding="utf-8")).get("kaynak_proje_yolu") or ""
        eksik = self.ac(str(yol), son_acilanlara=False)
        self.proje_yolu = Path(kaynak) if kaynak else None
        return eksik

    # ---------------------------------------------------------- ders eşlemesi
    def ders_eslemesi_yolu(self) -> Path:
        kod = "".join(c for c in self.proje.sinav.ders_kodu if c.isalnum()) or "ders"
        return kullanici_klasoru() / "ders_eslemeleri" / f"{kod}.json"

    def ders_eslemesi_kaydet(self) -> Path:
        yol = self.ders_eslemesi_yolu()
        ders_eslemesi_kaydet(yol, self.proje.anahtar)
        return yol

    def ders_eslemesi_yukle(self) -> bool:
        return ders_eslemesi_uygula(self.ders_eslemesi_yolu(), self.proje.anahtar)


def son_acilanlar() -> list[str]:
    v = ayarlar().value("son_acilanlar", [])
    if isinstance(v, str):
        v = [v]
    return [x for x in (v or []) if Path(x).exists()]


def kurtarma_klasoru() -> Path:
    return kullanici_klasoru() / "kurtarma"


def kurtarma_yolu() -> Path:
    """Son çalışmanın otomatik kaydı. Program açılınca varsa devam edilip edilmeyeceği sorulur."""
    return kurtarma_klasoru() / "son_calisma.osd"


def kurtarma_ozeti() -> dict | None:
    """Kurtarma dosyası varsa kullanıcıya gösterilecek kısa bilgi; yoksa None."""
    yol = kurtarma_yolu()
    if not yol.exists():
        return None
    try:
        v = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    s = v.get("sinav") or {}
    ad = " ".join(x for x in (s.get("ders_kodu"), s.get("ders_adi"), s.get("sinav_turu")) if x) or "Adsız sınav"
    return {"ad": ad, "zaman": v.get("kayit_zamani", ""), "klasik": v.get("bicim") == "klasik",
            "puanli": len(v.get("klasik_puanlar") or {}), "kaynak": v.get("kaynak_proje_yolu") or ""}


def kurtarmayi_yedekle() -> Path | None:
    """Kurtarma dosyasını silmeden kenara alır (son 20 yedek tutulur)."""
    yol = kurtarma_yolu()
    if not yol.exists():
        return None
    hedef = kurtarma_klasoru() / "yedekler" / f"son_calisma_{time.strftime('%Y%m%d_%H%M%S')}.osd"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    os.replace(yol, hedef)
    for eski in sorted(hedef.parent.glob("son_calisma_*.osd"))[:-20]:
        eski.unlink()
    return hedef


def yaz_atomik(yol: Path, veri: dict) -> None:
    """Önce geçici dosyaya yazar, sonra yerine koyar: yazarken kapanırsa eski dosya bozulmaz."""
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_name(yol.name + ".yaziliyor")
    gecici.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(gecici, yol)


def son_acilanlara_ekle(yol: str) -> None:
    a = ayarlar()
    liste = [str(Path(yol))] + [x for x in son_acilanlar() if x != str(Path(yol))]
    a.setValue("son_acilanlar", liste[:10])


