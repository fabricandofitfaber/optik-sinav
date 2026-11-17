"""Sistemden indirilen boş şablonu tanır, profil önerir ve puanları şablonun içine yazar.

Şablondaki öğrenci sırası ve biçimi korunur; yalnızca puan hücrelerine yazılır. En güvenli
"doğrudan giriş" yolu budur (PROJE_TANIMI.md bölüm 4.4, madde 2).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..core.modeller import SinavSonucu, Yuvarlama
from ..core.puanlama import yuvarla
from ..io.liste_okuyucu import _sade, esleme_tahmin_et, numara_normalle, sayfa_sec, sayfalari_oku
from .profil import Profil, SablonBilgisi, Sutun

_SORU_DESENI = re.compile(r"^(?:s|soru|q|madde)?(\d{1,3})(?:soru|puan|p)?$")
_PUAN_BASLIK = {"puan", "not", "notu", "sinavnotu", "toplam", "toplampuan", "sinavpuani", "basaripuani", "puani"}


def _soru_no(baslik: object) -> int | None:
    s = _sade(baslik)
    if not s:
        return None
    m = _SORU_DESENI.match(s)
    if m:
        return int(m.group(1))
    m = re.match(r"^(\d{1,3})\.?soru", s)
    return int(m.group(1)) if m else None


def sablondan_profil_oner(yol: str | Path, ad: str | None = None) -> Profil:
    """Şablonun başlıklarını ve öğrenci satırlarını tanıyıp profil önerir. Kullanıcı onaylayınca kaydedilir."""
    yol = Path(yol)
    sayfalar = sayfalari_oku(yol)
    sayfa = sayfa_sec(sayfalar)
    tablo = sayfalar[sayfa]
    e = esleme_tahmin_et(tablo, sayfa)
    if e.no_sutun is None:
        raise ValueError("Şablonda öğrenci numarası sütunu bulunamadı.")
    baslik_r = e.baslik_satiri or 1
    basliklar = tablo[baslik_r - 1] if tablo else []
    soru_sutunlari: dict[int, int] = {}
    puan_sutunu = None
    for j, b in enumerate(basliklar, start=1):
        if j in (e.no_sutun, e.ad_sutun, e.soyad_sutun):
            continue
        k = _soru_no(b)
        if k is not None and k not in soru_sutunlari:
            soru_sutunlari[k] = j
        elif _sade(b) in _PUAN_BASLIK and puan_sutunu is None:
            puan_sutunu = j
    sablon = SablonBilgisi(sayfa=sayfa, baslik_satiri=baslik_r, no_sutun=e.no_sutun, ad_sutun=e.ad_sutun,
                           soru_sutunlari=soru_sutunlari, puan_sutunu=puan_sutunu)
    sutunlar = [Sutun("ogrenci_no", str(basliklar[e.no_sutun - 1] or ""))]
    if e.ad_sutun:
        sutunlar.append(Sutun("ad_soyad", str(basliklar[e.ad_sutun - 1] or "")))
    for k, j in sorted(soru_sutunlari.items()):
        sutunlar.append(Sutun(f"soru:{k}", str(basliklar[j - 1] or "")))
    if puan_sutunu:
        sutunlar.append(Sutun("puan", str(basliklar[puan_sutunu - 1] or "")))
    return Profil(
        ad=ad or f"sablon_{yol.stem}",
        baslik=f"Şablondan: {yol.name}",
        aciklama="Sistem şablonundan otomatik önerildi. Sütunları kontrol edip onaylayın.",
        dosya_turu="sablon",
        sayfa_adi=sayfa,
        sutunlar=sutunlar,
        sablon=sablon,
        taslak=True,
    )


@dataclass
class DoldurmaRaporu:
    yazilan: int = 0
    girmedi: list[str] = field(default_factory=list)  # şablonda var, sonuçta yok
    sablonda_olmayan: list[str] = field(default_factory=list)  # sonuçta var, şablonda yok
    cikti: Path | None = None


def sablonu_doldur(sablon_yolu: str | Path, profil: Profil, sonuc: SinavSonucu, cikti_yolu: str | Path) -> DoldurmaRaporu:
    """Puanları şablonun içine yazar. `.xls` şablon okunur, çıktı `.xlsx` olarak kaydedilir."""
    import openpyxl

    if profil.sablon is None:
        profil = sablondan_profil_oner(sablon_yolu)
    sb = profil.sablon
    sablon_yolu = Path(sablon_yolu)
    if sablon_yolu.suffix.lower() == ".xls":
        wb = _xls_den_xlsx(sablon_yolu)
    else:
        wb = openpyxl.load_workbook(sablon_yolu)
    ws = wb[sb.sayfa] if sb.sayfa in wb.sheetnames else wb.worksheets[0]

    okunan = sonuc.no_ile()
    rapor = DoldurmaRaporu()
    sablondaki = set()

    def yaz(satir, sutun, deger):
        c = ws.cell(row=satir, column=sutun)
        if deger is None:
            c.value = None if profil.girmedi_gosterimi == "" else profil.girmedi_gosterimi
            return
        d = yuvarla(deger, profil.ondalik_basamak, profil.yuvarlama)
        c.value = float(d) if profil.ondalik_basamak > 0 else int(d)

    for r in range(sb.baslik_satiri + 1, ws.max_row + 1):
        no = numara_normalle(ws.cell(row=r, column=sb.no_sutun).value)
        if not no or not no.isdigit():
            continue
        sablondaki.add(no)
        o = okunan.get(no)
        if o is None:
            rapor.girmedi.append(no)
        sira = sonuc.anahtar.aktarim_sorulari()  # şablondaki k. soru = bonus dışı k. soru
        for k, j in sb.soru_sutunlari.items():
            yaz(r, j, o.sorular[sira[k - 1]].puan if o and k - 1 < len(sira) else None)
        if sb.puan_sutunu:
            yaz(r, sb.puan_sutunu, o.puan if o else None)
        if o is not None:
            rapor.yazilan += 1
    rapor.sablonda_olmayan = [o.no for o in sonuc.ogrenciler if o.no not in sablondaki]
    cikti = Path(cikti_yolu)
    if cikti.suffix.lower() != ".xlsx":
        cikti = cikti.with_suffix(".xlsx")
    wb.save(cikti)
    rapor.cikti = cikti
    return rapor


def _xls_den_xlsx(yol: Path):
    import openpyxl

    sayfalar = sayfalari_oku(yol)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for ad, tablo in sayfalar.items():
        ws = wb.create_sheet(ad[:31])
        for satir in tablo:
            ws.append(satir)
    return wb


def numara_sirasi(yol: str | Path, profil: Profil | None = None) -> list[str]:
    """Şablondaki (ya da sistem listesindeki) öğrenci numaraları, sırasıyla. Pano modu için."""
    profil = profil or sablondan_profil_oner(yol)
    sayfalar = sayfalari_oku(yol)
    tablo = sayfalar.get(profil.sablon.sayfa) or next(iter(sayfalar.values()))
    sira = []
    for satir in tablo[profil.sablon.baslik_satiri:]:
        j = profil.sablon.no_sutun - 1
        no = numara_normalle(satir[j] if j < len(satir) else None)
        if no.isdigit():
            sira.append(no)
    return sira


__all__ = ["sablondan_profil_oner", "sablonu_doldur", "numara_sirasi", "DoldurmaRaporu", "Yuvarlama"]
