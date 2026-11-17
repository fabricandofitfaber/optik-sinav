"""Öğrenci listesini Excel (xlsx, xls), metin (csv, txt) ya da PDF (sınav yoklama listesi) dosyasından okur.

Sütun eşlemesi (hangi sütun numara, hangisi ad) tahmin edilir; kullanıcı değiştirebilir.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from pathlib import Path

from ..core.modeller import ListeEslemesi, Ogrenci, OgrenciListesi
from .kodlama import baytlari_coz

Tablo = list[list[object]]


def _sade(metin: object) -> str:
    """Başlık karşılaştırması için: küçük harf, Türkçe harfler sadeleşmiş, noktalama yok."""
    s = str(metin or "").strip().replace("İ", "i").replace("I", "ı").lower()
    s = s.translate(str.maketrans("ığüşöç", "igusoc"))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


def numara_normalle(deger: object) -> str:
    """Numarayı metne çevirir: boşluklar atılır, 990000001.0 gibi ondalık yazımlar düzeltilir."""
    if deger is None:
        return ""
    if isinstance(deger, bool):
        return ""
    if isinstance(deger, float):
        if deger.is_integer():
            return str(int(deger))
        return str(deger)
    if isinstance(deger, int):
        return str(deger)
    s = re.sub(r"\s+", "", str(deger))
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".")[0]
    return s


# ---------------------------------------------------------------- tablo okuma
def sayfalari_oku(yol: str | Path) -> dict[str, Tablo]:
    """Dosyadaki bütün sayfaları {sayfa adı: satırlar} olarak döndürür."""
    yol = Path(yol)
    uzanti = yol.suffix.lower()
    if uzanti in (".xlsx", ".xlsm"):
        import openpyxl

        wb = openpyxl.load_workbook(yol, read_only=True, data_only=True)
        try:
            return {ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets}
        finally:
            wb.close()
    if uzanti == ".xls":
        import xlrd

        wb = xlrd.open_workbook(str(yol))
        sonuc = {}
        for sh in wb.sheets():
            satirlar = []
            for r in range(sh.nrows):
                satir = []
                for c in range(sh.ncols):
                    hucre = sh.cell(r, c)
                    satir.append(None if hucre.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK) else hucre.value)
                satirlar.append(satir)
            sonuc[sh.name] = satirlar
        return sonuc
    if uzanti == ".pdf":
        tablo = pdf_hucrelerinden_tablo(pdf_satirlari(yol))
        if len(tablo) < 2:
            raise ValueError("Bu PDF'te öğrenci numarası bulunamadı. Taranmış (resim) PDF ise okunamaz; "
                             "sistemden listeyi Excel olarak indirmeyi deneyin.")
        return {"PDF listesi": tablo}
    # csv / txt
    metin, _ = baytlari_coz(yol.read_bytes())
    ornek = metin[:4096]
    try:
        ayrac = csv.Sniffer().sniff(ornek, delimiters=";,\t|").delimiter
    except csv.Error:
        ayrac = "\t" if "\t" in ornek else (";" if ";" in ornek else ",")
    return {yol.stem: [list(r) for r in csv.reader(io.StringIO(metin), delimiter=ayrac)]}


# ---------------------------------------------------------------- eşleme tahmini
_NO_BASLIK = {"ogrno", "ogrencino", "ogrencinumarasi", "numara", "no", "ogrnumarasi", "okulno", "studentno", "studentid"}
_AD_SOYAD_BASLIK = {"adisoyadi", "adsoyad", "adisoyad", "adsoyadi", "ogrenciadisoyadi", "isim", "adivesoyadi", "name"}
_AD_BASLIK = {"adi", "ad", "ogrenciadi"}
_SOYAD_BASLIK = {"soyadi", "soyad"}


def _numara_gibi(deger: object) -> bool:
    s = numara_normalle(deger)
    return s.isdigit() and 6 <= len(s) <= 12


def esleme_tahmin_et(tablo: Tablo, sayfa: str | None = None) -> ListeEslemesi:
    esleme = ListeEslemesi(sayfa=sayfa)
    # 1) Başlık satırı: ilk 15 satırda numara başlığı içeren satır
    for r, satir in enumerate(tablo[:15]):
        sadeler = [_sade(h) for h in satir]
        no_idx = next((i for i, h in enumerate(sadeler) if h in _NO_BASLIK), None)
        if no_idx is None:
            continue
        esleme.baslik_satiri = r + 1
        esleme.no_sutun = no_idx + 1
        ad_soyad = next((i for i, h in enumerate(sadeler) if h in _AD_SOYAD_BASLIK), None)
        if ad_soyad is not None:
            esleme.ad_sutun = ad_soyad + 1
        else:
            ad = next((i for i, h in enumerate(sadeler) if h in _AD_BASLIK), None)
            soyad = next((i for i, h in enumerate(sadeler) if h in _SOYAD_BASLIK), None)
            if ad is not None:
                esleme.ad_sutun = ad + 1
            if soyad is not None:
                esleme.soyad_sutun = soyad + 1
        return esleme
    # 2) Başlık yoksa: numaraya benzeyen değerlerin en çok olduğu sütun
    if not tablo:
        return esleme
    genislik = max(len(s) for s in tablo)
    puanlar = [sum(1 for s in tablo if i < len(s) and _numara_gibi(s[i])) for i in range(genislik)]
    if max(puanlar, default=0) == 0:
        return esleme
    no_i = puanlar.index(max(puanlar))
    esleme.no_sutun = no_i + 1
    ilk_veri = next(r for r, s in enumerate(tablo) if no_i < len(s) and _numara_gibi(s[no_i]))
    esleme.baslik_satiri = ilk_veri if ilk_veri > 0 else None
    # Ad: numaranın sağındaki ilk metin sütunu
    for i in range(no_i + 1, genislik):
        metinler = [s[i] for s in tablo[ilk_veri:] if i < len(s) and isinstance(s[i], str) and s[i].strip()]
        if len(metinler) >= max(1, (len(tablo) - ilk_veri) // 2) and any(c.isalpha() for c in "".join(metinler)):
            esleme.ad_sutun = i + 1
            break
    return esleme


def sayfa_sec(sayfalar: dict[str, Tablo]) -> str:
    """Numara sütunu bulunan ve en çok numara içeren sayfayı seçer."""
    en_iyi, en_cok = next(iter(sayfalar)), -1
    for ad, tablo in sayfalar.items():
        e = esleme_tahmin_et(tablo, ad)
        if e.no_sutun is None:
            continue
        n = sum(1 for s in tablo if e.no_sutun - 1 < len(s) and _numara_gibi(s[e.no_sutun - 1]))
        if n > en_cok:
            en_iyi, en_cok = ad, n
    return en_iyi


def tablodan_liste(tablo: Tablo, esleme: ListeEslemesi) -> OgrenciListesi:
    if esleme.no_sutun is None:
        raise ValueError("Öğrenci numarası sütunu belirlenemedi.")
    basla = esleme.baslik_satiri or 0  # başlık satırı 1'den; veri onun altından başlar
    basliklar = [str(h or "") for h in tablo[esleme.baslik_satiri - 1]] if esleme.baslik_satiri else []

    def hucre(satir, sutun):
        if sutun is None or sutun - 1 >= len(satir):
            return ""
        v = satir[sutun - 1]
        return "" if v is None else str(v)

    ogrenciler = []
    for r in range(basla, len(tablo)):
        satir = tablo[r]
        no = numara_normalle(satir[esleme.no_sutun - 1] if esleme.no_sutun - 1 < len(satir) else None)
        if not no or not any(ch.isdigit() for ch in no):
            continue
        ad = " ".join(x for x in (hucre(satir, esleme.ad_sutun).strip(), hucre(satir, esleme.soyad_sutun).strip()) if x)
        ad = re.sub(r"\s+", " ", ad)
        ogrenciler.append(Ogrenci(no=no, ad=ad, kaynak_satir=r + 1))
    return OgrenciListesi(ogrenciler=ogrenciler, esleme=esleme, basliklar=basliklar)


# ---------------------------------------------------------------- PDF listesi
_NUMARA = re.compile(r"\d{6,12}")


def _harfli(h: str) -> bool:
    return bool(h) and any(c.isalpha() for c in h) and not any(c.isdigit() for c in h)


def pdf_satirlari(yol: str | Path) -> list[list[str]]:
    """PDF'in her satırını hücrelere böler: sayfa düzeni korunarak çıkarılan metinde iki ve daha çok boşluk sütun ayıracıdır."""
    from pypdf import PdfReader

    satirlar = []
    for sayfa in PdfReader(str(yol)).pages:
        try:
            metin = sayfa.extract_text(extraction_mode="layout") or ""
        except TypeError:  # çok eski pypdf
            metin = sayfa.extract_text() or ""
        for s in metin.splitlines():
            if s.strip():
                satirlar.append(re.split(r"\s{2,}", s.strip()))
    return satirlar


def pdf_hucrelerinden_tablo(satirlar: list[list[str]]) -> Tablo:
    """PDF satırlarından (hücre listeleri) ["Öğrenci No", "Adı Soyadı"] tablosu kurar.

    Numara: 6-12 haneli ilk hücre. Ad: başlık satırı bulunduysa ad (ve soyad) sütununun numara sütununa göre
    konumundan; bulunmadıysa numaranın sağındaki (yoksa solundaki) harfli hücre. Hücrelere bölünemeyen satırda
    kelimelere bakılır. Aynı numara bir kez alınır. Tarayıcı sürümündeki `pdfHucrelerindenTablo` ile aynıdır.
    """
    ad_kaydir = soyad_kaydir = None
    tablo: Tablo = [["Öğrenci No", "Adı Soyadı"]]
    gorulen: set[str] = set()
    for ham in satirlar:
        hucreler = [re.sub(r"\s+", " ", str(h)).strip() for h in ham if h is not None and str(h).strip()]
        if not hucreler:
            continue
        numarali = [i for i, h in enumerate(hucreler) if _NUMARA.fullmatch(h)]
        if not numarali:
            sadeler = [_sade(h) for h in hucreler]
            no_i = next((i for i, h in enumerate(sadeler) if h in _NO_BASLIK and h != "no"), None)
            if no_i is None:
                no_i = next((i for i, h in enumerate(sadeler) if h == "no"), None)
            if no_i is not None:  # başlık satırı
                ad_soyad = next((i for i, h in enumerate(sadeler) if h in _AD_SOYAD_BASLIK), None)
                ad = next((i for i, h in enumerate(sadeler) if h in _AD_BASLIK), None)
                soyad = next((i for i, h in enumerate(sadeler) if h in _SOYAD_BASLIK), None)
                if ad_soyad is not None:
                    ad_kaydir, soyad_kaydir = ad_soyad - no_i, None
                elif ad is not None:
                    ad_kaydir, soyad_kaydir = ad - no_i, (soyad - no_i if soyad is not None else None)
                continue
            kelimeler = " ".join(hucreler).split()
            j = next((j for j, k in enumerate(kelimeler) if _NUMARA.fullmatch(k)), None)
            if j is None:
                continue
            no = kelimeler[j]
            parca: list[str] = []
            for k in kelimeler[j + 1:]:
                if not _harfli(k):
                    break
                parca.append(k)
            if not parca:
                for k in reversed(kelimeler[:j]):
                    if not _harfli(k):
                        break
                    parca.insert(0, k)
            ad_metni = " ".join(parca)
        else:
            i = numarali[0]
            no = hucreler[i]

            def al(kaydir):
                k = None if kaydir is None else i + kaydir
                return hucreler[k] if k is not None and 0 <= k < len(hucreler) and _harfli(hucreler[k]) else ""

            if ad_kaydir is not None:
                ad_metni = " ".join(x for x in (al(ad_kaydir), al(soyad_kaydir)) if x)
            else:
                ad_metni = al(1) or al(-1)
        if no in gorulen:
            continue
        gorulen.add(no)
        tablo.append([no, ad_metni])
    return tablo


_SISTEM_SATIRI = re.compile(r"^\s*(?:\d{1,4}\s*[\t;]\s*)?(\d{6,12})\s*[\t;]\s*([^\t;]*?)\s*[\t;]\s*([^\t;]*?)\s*(?:[\t;]|$)")


def sistem_tablosu_coz(metin: str) -> list[list[str]]:
    """Akademik Bilgi Sistemi'nin öğrenci tablosundan (ekrandan kopyalanan: "# Öğrenci No Adı Soyadı Snf …") liste tablosu:
    [["Öğrenci No", "Adı Soyadı"], [no, "AD SOYAD"], …]. Sıra numarası, sınıf ve puan hücreleri yok sayılır; satır başına
    gelen puan ve durum satırları (sekmesiz) atlanır. Aynı numara bir kez alınır."""
    tablo = [["Öğrenci No", "Adı Soyadı"]]
    gorulen = set()
    for satir in metin.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        m = _SISTEM_SATIRI.match(satir)
        if not m:
            continue
        no = m.group(1)
        ad = " ".join(x for x in (m.group(2).strip(), m.group(3).strip()) if x)
        if no in gorulen or not ad or not _harfli(ad):
            continue
        gorulen.add(no)
        tablo.append([no, ad])
    return tablo


def liste_oku(yol: str | Path, esleme: ListeEslemesi | None = None) -> OgrenciListesi:
    sayfalar = sayfalari_oku(yol)
    if esleme and esleme.no_sutun:
        sayfa = esleme.sayfa if esleme.sayfa in sayfalar else next(iter(sayfalar))
        return tablodan_liste(sayfalar[sayfa], esleme)
    sayfa = sayfa_sec(sayfalar)
    return tablodan_liste(sayfalar[sayfa], esleme_tahmin_et(sayfalar[sayfa], sayfa))
