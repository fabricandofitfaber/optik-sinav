"""Kontrol ve düzeltme adımındaki tablo modelleri."""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt

from .. import metinler as M
from ..core.modeller import SinavSonucu
from ..core.puanlama import sayi_yaz
from .tema import renk

SABIT_ONCE = ["sira", "no", "ad"]
SABIT_SONRA = ["dogru", "yanlis", "bos", "puan", "uyari"]
SABIT_SONRA_KITAPCIKLI = ["dogru", "yanlis", "bos", "puan", "kitapcik", "uyari"]


class SonucModeli(QAbstractTableModel):
    """Sütunlar: Sıra, Öğrenci No, Ad Soyad, soru sütunları, Doğru, Yanlış, Boş, Puan, Uyarı."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sonuc: SinavSonucu | None = None
        self.sonra = SABIT_SONRA

    def yukle(self, sonuc: SinavSonucu | None) -> None:
        self.beginResetModel()
        self.sonuc = sonuc
        coklu = bool(sonuc and (sonuc.anahtar.kitapcik_anahtarlari or len({o.kitapcik for o in sonuc.ogrenciler}) > 1))
        self.sonra = SABIT_SONRA_KITAPCIKLI if coklu else SABIT_SONRA
        self.endResetModel()

    @property
    def n(self) -> int:
        return self.sonuc.anahtar.soru_sayisi if self.sonuc else 0

    def sutun_turu(self, sutun: int) -> tuple[str, int | None]:
        if sutun < 3:
            return SABIT_ONCE[sutun], None
        if sutun < 3 + self.n:
            return "soru", sutun - 3
        return self.sonra[sutun - 3 - self.n], None

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or not self.sonuc else len(self.sonuc.ogrenciler)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or not self.sonuc else 3 + self.n + len(self.sonra)

    def headerData(self, bolum, yon, rol=Qt.ItemDataRole.DisplayRole):
        if rol != Qt.ItemDataRole.DisplayRole:
            return None
        if yon == Qt.Orientation.Vertical:
            return None
        tur, k = self.sutun_turu(bolum)
        if tur == "soru":
            return str(k + 1)
        if tur == "kitapcik":
            return "Kitapçık"
        return M.SUTUN[tur]

    def data(self, ix: QModelIndex, rol=Qt.ItemDataRole.DisplayRole):
        if not ix.isValid() or not self.sonuc:
            return None
        o = self.sonuc.ogrenciler[ix.row()]
        tur, k = self.sutun_turu(ix.column())
        if rol in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if tur == "sira":
                return ix.row() + 1
            if tur == "no":
                return o.no
            if tur == "ad":
                return o.ad
            if tur == "soru":
                return o.sorular[k].isaret.strip()
            if tur in ("dogru", "yanlis", "bos"):
                return getattr(o, tur)
            if tur == "puan":
                return sayi_yaz(o.puan, self.sonuc.ayarlar.ondalik)
            if tur == "uyari":
                return "; ".join(u.mesaj for u in o.uyarilar)
            if tur == "kitapcik":
                return o.kitapcik
        if rol == Qt.ItemDataRole.UserRole:  # sıralama için
            if tur == "puan":
                return float(o.puan)
            if tur in ("sira",):
                return ix.row()
            return self.data(ix)
        if rol == Qt.ItemDataRole.BackgroundRole:
            if tur == "soru":
                return renk("K") if getattr(o.sorular[k], "bonus_ile", False) else renk(o.sorular[k].durum.value)
            if o.uyarili and tur in ("sira", "no", "ad", "uyari"):
                return renk("uyari")
        if rol == Qt.ItemDataRole.TextAlignmentRole and tur not in ("ad", "uyari"):
            return int(Qt.AlignmentFlag.AlignCenter)
        if rol == Qt.ItemDataRole.ToolTipRole:
            if tur == "soru":
                s = o.sorular[k]
                kendi = o.kaynak_soru[k] if o.kaynak_soru else k + 1
                yer = f" ({o.kitapcik} kitapçığında {kendi}. soru)" if kendi != k + 1 else ""
                if getattr(s, "bonus_ile", False):
                    return f"{k + 1}. soru{yer}: bonus soru sayesinde doğru sayıldı (öğrencinin işareti: {s.isaret.strip() or 'boş'})"
                return f"{k + 1}. soru{yer}: {M.DURUM_ADI[s.durum.value]}, işaret {s.isaret!r}, puan {sayi_yaz(s.puan, 2)}"
            if tur == "ad" and o.okunan_ad != o.ad:
                return f"Optik dosyada okunan: {o.okunan_ad}"
            if tur == "uyari" and o.uyarilar:
                return "\n".join(u.mesaj for u in o.uyarilar)
            if tur == "no":
                return f"Dosya satırı {o.kayit.satir_no}. Düzeltmek için çift tıklayın."
        return None


class UyariSuzgeci(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.yalniz_uyarili = False
        self.setSortRole(Qt.ItemDataRole.UserRole)

    def ayarla(self, yalniz_uyarili: bool) -> None:
        if hasattr(self, "beginFilterChange"):  # Qt 6.10 ve sonrası
            self.beginFilterChange()
            self.yalniz_uyarili = yalniz_uyarili
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
        else:
            self.yalniz_uyarili = yalniz_uyarili
            self.invalidateFilter()

    def filterAcceptsRow(self, satir, ust):
        if not self.yalniz_uyarili:
            return True
        m: SonucModeli = self.sourceModel()
        return bool(m.sonuc and m.sonuc.ogrenciler[satir].uyarili)


class KlasikGirisModeli(QAbstractTableModel):
    """Klasik sınav puan girişi: satırlar öğrenci listesi, sütunlar soru puanları (düzenlenebilir), toplam,
    kâğıttaki toplam ve "Girmedi" işaret kutusu."""

    def __init__(self, durum, parent=None):
        super().__init__(parent)
        self.durum = durum

    def yenile(self):
        self.beginResetModel()
        self.endResetModel()

    @property
    def ogrenciler(self):
        return self.durum.liste.ogrenciler if self.durum.liste else []

    @property
    def n(self) -> int:
        return self.durum.proje.anahtar.soru_sayisi

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.ogrenciler)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 3 + self.n + 3

    @property
    def girmedi_sutunu(self) -> int:
        return 3 + self.n + 2

    def _girmedi(self, satir) -> bool:
        return self.ogrenciler[satir].no in self.durum.proje.klasik_girmedi

    def _kagit(self, satir):
        return (self.durum.proje.klasik_toplamlar or {}).get(self.ogrenciler[satir].no)

    def _toplam(self, satir):
        from ..core.klasik import puan_coz

        t, girildi = 0, False
        for k in range(self.n):
            p = puan_coz(self._deger(satir, k))
            if p is not None:
                t += p
                girildi = True
        return t, girildi

    def _tam(self):
        from ..core.puanlama import soru_puanlari

        try:
            return soru_puanlari(self.durum.proje.anahtar, self.durum.proje.ayarlar)
        except Exception:  # noqa: BLE001
            return [None] * self.n

    def headerData(self, bolum, yon, rol=Qt.ItemDataRole.DisplayRole):
        if rol != Qt.ItemDataRole.DisplayRole or yon != Qt.Orientation.Horizontal:
            return None
        if bolum < 3:
            return [M.SUTUN["sira"], M.SUTUN["no"], M.SUTUN["ad"]][bolum]
        if bolum < 3 + self.n:
            tam = self._tam()[bolum - 3]
            return f"S{bolum - 2}" + (f" ({sayi_yaz(tam, 2).rstrip('0').rstrip(',')})" if tam is not None else "")
        return {3 + self.n: "Toplam", 3 + self.n + 1: "Kâğıttaki toplam"}.get(bolum, "Girmedi")

    def _deger(self, satir, k):
        v = self.durum.proje.klasik_puanlar.get(self.ogrenciler[satir].no) or []
        return v[k] if k < len(v) else None

    def flags(self, ix):
        f = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if ix.column() == self.girmedi_sutunu:
            return f | Qt.ItemFlag.ItemIsUserCheckable
        if 3 <= ix.column() < 3 + self.n or ix.column() == 3 + self.n + 1:
            f |= Qt.ItemFlag.ItemIsEditable
        return f

    def data(self, ix, rol=Qt.ItemDataRole.DisplayRole):
        if not ix.isValid():
            return None
        from ..core.klasik import puan_coz

        o = self.ogrenciler[ix.row()]
        j = ix.column()
        girmedi = self._girmedi(ix.row())
        if j == self.girmedi_sutunu:
            if rol == Qt.ItemDataRole.CheckStateRole:
                return Qt.CheckState.Checked if girmedi else Qt.CheckState.Unchecked
            if rol == Qt.ItemDataRole.ToolTipRole:
                return "İşaretlerseniz öğrenci sınava girmemiş sayılır; girilmiş puanları silinmez, hesaba katılmaz."
            return None
        if girmedi and rol == Qt.ItemDataRole.ForegroundRole and j >= 3:
            return QColor("gray")
        if girmedi and rol == Qt.ItemDataRole.BackgroundRole:
            return renk("I")  # gri: sınava girmedi
        if rol in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if j == 3 + self.n and girmedi and rol == Qt.ItemDataRole.DisplayRole:
                return "sınava girmedi"
            if j == 0:
                return ix.row() + 1
            if j == 1:
                return o.no
            if j == 2:
                return o.ad
            if j < 3 + self.n:
                return self._deger(ix.row(), j - 3) or ""
            if j == 3 + self.n + 1:
                return self._kagit(ix.row()) or ""
            toplam = 0
            girildi = False
            for k in range(self.n):
                try:
                    p = puan_coz(self._deger(ix.row(), k))
                except (ValueError, ArithmeticError):
                    return "hata"
                if p is not None:
                    toplam += p
                    girildi = True
            return sayi_yaz(toplam, 2) if girildi else "—"  # henüz girilmedi
        if rol == Qt.ItemDataRole.BackgroundRole and j == 3 + self.n + 1:
            kt = self._kagit(ix.row())
            if not kt:
                return None
            try:
                t, _ = self._toplam(ix.row())
                return renk("D") if puan_coz(kt) == t else renk("Y")
            except (ValueError, ArithmeticError):
                return renk("Y")
        if rol == Qt.ItemDataRole.BackgroundRole and 3 <= j < 3 + self.n:
            try:
                p = puan_coz(self._deger(ix.row(), j - 3))
            except (ValueError, ArithmeticError):
                return renk("Y")
            tam = self._tam()[j - 3]
            if p is None:
                return None
            if p < 0 or (tam is not None and p > tam):
                return renk("uyari")
            if tam is not None and p >= tam:
                return renk("D")
            return renk("K") if p > 0 else renk("Y")
        if rol == Qt.ItemDataRole.TextAlignmentRole and j != 2:
            return int(Qt.AlignmentFlag.AlignCenter)
        return None

    def setData(self, ix, deger, rol=Qt.ItemDataRole.EditRole):
        if ix.column() == self.girmedi_sutunu and rol == Qt.ItemDataRole.CheckStateRole:
            isaret = deger in (Qt.CheckState.Checked, Qt.CheckState.Checked.value, 2, True)
            self.durum.girmedi_isaretle(self.ogrenciler[ix.row()].no, isaret)
            self.durum.degerlendir()
            self.dataChanged.emit(self.index(ix.row(), 0), self.index(ix.row(), self.columnCount() - 1))
            return True
        if rol != Qt.ItemDataRole.EditRole:
            return False
        if ix.column() == 3 + self.n + 1:
            no = self.ogrenciler[ix.row()].no
            x = str(deger or "").strip()
            if x:
                self.durum.proje.klasik_toplamlar[no] = x
            else:
                self.durum.proje.klasik_toplamlar.pop(no, None)
            self.dataChanged.emit(self.index(ix.row(), 3 + self.n + 1), self.index(ix.row(), 3 + self.n + 1))
            return True
        if not (3 <= ix.column() < 3 + self.n):
            return False
        self.durum.klasik_puan_yaz(self.ogrenciler[ix.row()].no, ix.column() - 3, str(deger) if deger is not None else None)
        self.dataChanged.emit(self.index(ix.row(), 3), self.index(ix.row(), 3 + self.n + 1))
        return True
