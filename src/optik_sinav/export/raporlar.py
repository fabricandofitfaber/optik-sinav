"""Sonuç dosyası, madde analizi, öğrenme çıktısı raporu ve isteğe bağlı özet (PDF biçiminde) yazımı."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from .. import metinler as M
from ..core.ciktilar import cikti_adi
from ..core.madde_analizi import (
    MaddeEsikleri, cikti_dagilimi, madde_analizi, ogrenme_ciktisi_raporu, tam_sayi_dagilim,
)
from ..core.modeller import Duzeltme, SinavBilgisi, SinavSonucu, fraction_decimal
from ..core.puanlama import net, yuvarla
from .xlsx_yazici import KALIN, RENK, baslik_satiri, dolgu, sayi_bicimi, sutun_genislikleri


def _puan(ws, r, c, deger, ondalik=2, yontem=None):
    from ..core.modeller import Yuvarlama

    d = yuvarla(deger, ondalik, yontem or Yuvarlama.YARIM_YUKARI)
    cell = ws.cell(row=r, column=c, value=float(d))
    cell.number_format = sayi_bicimi(ondalik)
    return cell


def _yazdirma(wb) -> None:
    """Yazdırırken her sayfa yatay ve tek sayfa genişliğinde olsun."""
    for ws in wb.worksheets:
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True


def _tablo_bitir(ws, son_sutun: int, genislik: dict[int, float] | None = None):
    ws.freeze_panes = "A2"
    if ws.max_row >= 1 and son_sutun >= 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(son_sutun)}{max(ws.max_row, 1)}"
    sutun_genislikleri(ws, genislik)


def sonuc_dosyasi_yaz(sonuc: SinavSonucu, sinav: SinavBilgisi, yol: str | Path, duzeltmeler: list[Duzeltme] | None = None,
                      kaynaklar: dict[str, str] | None = None) -> Path:
    a = sonuc.ayarlar
    n = sonuc.anahtar.soru_sayisi
    wb = Workbook()

    # --- Sonuç
    ws = wb.active
    ws.title = "Sonuç"
    basliklar = [M.SUTUN["sira"], M.SUTUN["no"], M.SUTUN["ad"]] + [str(k) for k in range(1, n + 1)] + [
        M.SUTUN["dogru"], M.SUTUN["yanlis"], M.SUTUN["bos"]]
    if a.yanlis_cezasi:
        basliklar += ["Net", M.SUTUN["ham_puan"], M.SUTUN["ceza"]]
    basliklar += [M.SUTUN["puan"], M.SUTUN["uyari"]]
    coklu_kitapcik = len({o.kitapcik for o in sonuc.ogrenciler if o.kitapcik}) > 1 or bool(sonuc.anahtar.kitapcik_anahtarlari)
    if coklu_kitapcik:
        basliklar.append("Kitapçık")
    baslik_satiri(ws, 1, basliklar)
    r = 2
    for sira, o in enumerate(sonuc.ogrenciler, start=1):
        ws.cell(row=r, column=1, value=sira)
        ws.cell(row=r, column=2, value=o.no).number_format = "@"
        ws.cell(row=r, column=3, value=o.ad)
        for k, s in enumerate(o.sorular):
            c = _puan(ws, r, 4 + k, s.puan, a.ondalik, a.yuvarlama)
            c.fill = dolgu(RENK[s.durum.value])
        c0 = 4 + n
        ws.cell(row=r, column=c0, value=o.dogru)
        ws.cell(row=r, column=c0 + 1, value=o.yanlis)
        ws.cell(row=r, column=c0 + 2, value=o.bos)
        c0 += 3
        if a.yanlis_cezasi:
            _puan(ws, r, c0, net(o.dogru, o.yanlis, a), 2)
            _puan(ws, r, c0 + 1, o.ham_puan, a.ondalik, a.yuvarlama)
            _puan(ws, r, c0 + 2, o.ceza, a.ondalik, a.yuvarlama)
            c0 += 3
        _puan(ws, r, c0, o.puan, a.ondalik, a.yuvarlama).font = KALIN
        ws.cell(row=r, column=c0 + 1, value="; ".join(u.mesaj for u in o.uyarilar))
        if coklu_kitapcik:
            ws.cell(row=r, column=c0 + 2, value=o.kitapcik)
        if o.uyarili:
            for j in (1, 2, 3, c0 + 1):
                ws.cell(row=r, column=j).fill = dolgu(RENK["uyari"])
        r += 1
    for g in sonuc.girmeyenler:
        ws.cell(row=r, column=1, value=None)
        ws.cell(row=r, column=2, value=g.no).number_format = "@"
        ws.cell(row=r, column=3, value=g.ad)
        ws.cell(row=r, column=len(basliklar) - (1 if coklu_kitapcik else 0), value=M.GIRMEDI)
        r += 1
    _tablo_bitir(ws, len(basliklar), {1: 6, 2: 13, 3: 28, len(basliklar) - (1 if coklu_kitapcik else 0): 45})

    # --- Cevaplar
    ws = wb.create_sheet("Cevaplar")
    baslik_satiri(ws, 1, [M.SUTUN["sira"], M.SUTUN["no"], M.SUTUN["ad"]] + [str(k) for k in range(1, n + 1)])
    ws.cell(row=2, column=3, value="Cevap anahtarı").font = KALIN
    for k, s in enumerate(sonuc.anahtar.sorular):
        ws.cell(row=2, column=4 + k, value=s.dogru if s.durum.value != "iptal" else "İptal").font = KALIN
    for i, o in enumerate(sonuc.ogrenciler, start=1):
        r = i + 2
        ws.cell(row=r, column=1, value=i)
        ws.cell(row=r, column=2, value=o.no).number_format = "@"
        ws.cell(row=r, column=3, value=o.ad)
        for k, s in enumerate(o.sorular):
            c = ws.cell(row=r, column=4 + k, value=s.isaret.strip() or None)
            c.fill = dolgu(RENK[s.durum.value])
            c.alignment = Alignment(horizontal="center")
    _tablo_bitir(ws, 3 + n, {1: 6, 2: 13, 3: 28})
    for k in range(n):
        ws.column_dimensions[get_column_letter(4 + k)].width = 4

    # --- Uyarılar
    ws = wb.create_sheet("Uyarılar")
    baslik_satiri(ws, 1, ["Dosya satırı", M.SUTUN["no"], "Okunan ad", "Uyarı türü", "Açıklama"])
    r = 2
    for o in sonuc.ogrenciler:
        for u in o.uyarilar:
            for j, v in enumerate([o.kayit.satir_no, o.no, o.okunan_ad, u.tur.value, u.mesaj], start=1):
                ws.cell(row=r, column=j, value=v)
            r += 1
    for g in sonuc.girmeyenler:
        for j, v in enumerate([None, g.no, g.ad, "girmedi", M.GIRMEDI], start=1):
            ws.cell(row=r, column=j, value=v)
        r += 1
    _tablo_bitir(ws, 5, {1: 12, 2: 13, 3: 28, 4: 20, 5: 70})

    # --- Düzeltme Kaydı
    ws = wb.create_sheet("Düzeltme Kaydı")
    baslik_satiri(ws, 1, ["Dosya satırı", "Alan", "Eski değer", "Yeni değer", "Kim", "Ne zaman"])
    for r, d in enumerate(duzeltmeler or [], start=2):
        for j, v in enumerate([d.satir_no, d.alan, d.eski, d.yeni, d.kim, d.zaman], start=1):
            ws.cell(row=r, column=j, value=v)
    _tablo_bitir(ws, 6, {1: 12, 2: 12, 3: 20, 4: 20, 5: 14, 6: 20})

    # --- Anahtar ve Ayarlar
    ws = wb.create_sheet("Anahtar ve Ayarlar")
    bilgiler = [
        ("Ders kodu", sinav.ders_kodu), ("Ders adı", sinav.ders_adi), ("Sınav türü", sinav.sinav_turu),
        ("Tarih", sinav.tarih), ("Saat", sinav.saat), ("Etki oranı (%)", sinav.etki_orani), ("Dönem", sinav.donem),
        ("Puanlama", M.YONTEM_ADI[a.yontem.value]), ("Toplam puan", a.toplam_puan),
        ("Yanlış cezası", f"{a.ceza_orani} yanlış 1 doğruyu götürür" if a.yanlis_cezasi else "Yok"),
        ("Çift işaret", M.CIFT_ISARET_ADI[a.cift_isaret.value]),
        ("Yuvarlama", f"{M.YUVARLAMA_ADI[a.yuvarlama.value]}, {a.ondalik} basamak"),
        ("Sınava giren", len(sonuc.ogrenciler)), ("Sınava girmeyen (listede olup dosyada olmayan)", len(sonuc.girmeyenler)),
        ("Listede olmayan numara", len(sonuc.listede_olmayanlar)),
    ]
    for ad, deger in (kaynaklar or {}).items():
        bilgiler.append((ad, deger))
    for r, (ad, deger) in enumerate(bilgiler, start=1):
        ws.cell(row=r, column=1, value=ad).font = KALIN
        ws.cell(row=r, column=2, value=deger)
    r = len(bilgiler) + 2
    baslik_satiri(ws, r, ["Soru", "Doğru şık", "Durum", "Puan", "Öğrenme çıktıları", "Program çıktıları"])
    for k, s in enumerate(sonuc.anahtar.sorular):
        rr = r + 1 + k
        ws.cell(row=rr, column=1, value=s.no)
        ws.cell(row=rr, column=2, value=s.dogru)
        ws.cell(row=rr, column=3, value=M.SORU_DURUMU_ADI[s.durum.value])
        _puan(ws, rr, 4, sonuc.soru_puanlari[k], 4)
        ws.cell(row=rr, column=5, value=", ".join(s.ogrenme_ciktilari))
        ws.cell(row=rr, column=6, value=", ".join(s.program_ciktilari))
    sutun_genislikleri(ws, {1: 34, 2: 30, 3: 24, 4: 10, 5: 20, 6: 20})

    _yazdirma(wb)
    yol = Path(yol)
    wb.save(yol)
    return yol


def _sayi(ws, r, c, v, bicim="0.00"):
    cell = ws.cell(row=r, column=c, value=None if v is None else (round(v, 4) if isinstance(v, float) else v))
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        cell.number_format = bicim
    return cell


def _not(ws, r, metin, sutun_sayisi=8):
    c = ws.cell(row=r, column=1, value=metin)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=sutun_sayisi)
    ws.row_dimensions[r].height = max(15, 15 * (len(metin) // 110 + 1))


def madde_analizi_yaz(sonuc: SinavSonucu, sinav: SinavBilgisi, yol: str | Path, esikler: MaddeEsikleri | None = None,
                      ara_agirlik: float = 40.0, arsiv: list | None = None, donem=None) -> Path:
    """Grafikli istatistik raporu: özet ve yorum, puan dağılımı, madde analizi, çeldiriciler, beş grup, boş bırakma,
    kişi uyumu ve benzer yanlış örüntüsü."""
    from openpyxl.chart import BarChart, LineChart, Reference

    e = esikler or MaddeEsikleri(basari_esigi=float(getattr(sonuc.ayarlar, "basari_esigi", 50)),
                                 cikti_esigi=float(getattr(sonuc.ayarlar, "basari_esigi", 50)))
    maddeler, genel = madde_analizi(sonuc, e)
    klasik = sonuc.klasik
    wb = Workbook()

    # --- Özet
    ws = wb.active
    ws.title = "Özet"
    ws.cell(row=1, column=1, value=f"{sinav.ders_kodu} {sinav.ders_adi} — {sinav.sinav_turu} {sinav.tarih}").font = Font(bold=True, size=13)
    r = 3
    ws.cell(row=r, column=1, value="Yorum").font = KALIN
    r += 1
    for y in genel.yorumlar:
        _not(ws, r, "• " + y)
        r += 1
    r += 1
    satirlar = [
        ("Sınava giren öğrenci", genel.ogrenci_sayisi, "0"), ("Sınava girmeyen", len(sonuc.girmeyenler), "0"),
        ("Ortalama", genel.ortalama, "0.00"), ("Ortanca (medyan)", genel.medyan, "0.00"),
        ("Standart sapma (örneklem)", genel.standart_sapma, "0.00"),
        ("En düşük", genel.en_dusuk, "0.00"), ("En yüksek", genel.en_yuksek, "0.00"),
        ("Birinci çeyrek (öğrencilerin dörtte biri bunun altında)", genel.birinci_ceyrek, "0.00"),
        ("Üçüncü çeyrek (öğrencilerin dörtte biri bunun üstünde)", genel.ucuncu_ceyrek, "0.00"),
        (f"{e.basari_esigi:g} ve üstü alanların oranı", genel.basari_orani, "0%"),
        ("Çarpıklık (artı: puanlar düşükte yığılmış)", genel.carpiklik, "0.00"),
        ("Basıklık (normal dağılımda 0)", genel.basiklik, "0.00"),
        ("Cronbach alfa güvenirlik katsayısı", genel.alfa, "0.00"),
        ("Kuder-Richardson 20 güvenirlik katsayısı", genel.kr20, "0.00"),
        ("Ölçmenin standart hatası (puan)", genel.olcme_hatasi, "0.00"),
        ("Ortalama güçlük (doğru oranı)", genel.ortalama_guclik, "0.00"),
        ("Ortalama ayırt edicilik", genel.ortalama_ayirt_edicilik, "0.00"),
        ("Analizdeki soru sayısı", genel.analizdeki_soru_sayisi, "0"),
    ]
    if len(genel.kitapcik_sayilari) > 1:
        for b, sayi in genel.kitapcik_sayilari.items():
            satirlar.append((f"{b} kitapçığı: öğrenci / ortalama", f"{sayi} / {genel.kitapcik_ortalamalari[b]:.2f}".replace(".", ","), None))
    for ad, v, bicim in satirlar:
        if klasik and ad.startswith("Kuder"):
            continue
        ws.cell(row=r, column=1, value=ad).font = KALIN
        c = ws.cell(row=r, column=2, value=None if v is None else (round(v, 4) if isinstance(v, float) else v))
        if bicim and v is not None:
            c.number_format = bicim
        r += 1
    r += 1
    _not(ws, r, "Okuma rehberi: Güçlük, soruyu doğru yapanların oranıdır (0,30-0,70 arası ideal). Ayırt edicilik, en başarılı "
                "%27 ile en başarısız %27'nin o sorudaki başarı farkıdır (0,40 üstü çok iyi, 0,30-0,39 iyi, 0,20-0,29 "
                "düzeltilebilir, 0,20 altı sorunlu). Güvenirlik katsayısı 0,70 ve üstü sınıf içi sınavlar için yeterli kabul edilir. "
                "Ölçmenin standart hatası, bir öğrencinin puanının ölçme hatası yüzünden ne kadar oynayabileceğini gösterir.")
    sutun_genislikleri(ws, {1: 58, 2: 16})

    # --- Puan Dağılımı (grafik)
    ws = wb.create_sheet("Puan Dağılımı")
    baslik_satiri(ws, 1, ["Puan aralığı", "Öğrenci sayısı"])
    puanlar = [float(o.puan) for o in sonuc.ogrenciler]
    ust_sinir = float(fraction_decimal(sonuc.ayarlar.toplam_puan)) if sonuc.ayarlar.toplam_puan else 100.0
    adim = ust_sinir / 10
    for k in range(10):
        alt_s, ust_s = k * adim, (k + 1) * adim
        sayi = sum(1 for p in puanlar if (alt_s <= p < ust_s) or (k == 9 and p == ust_s))
        ws.cell(row=k + 2, column=1, value=f"{alt_s:g}-{ust_s:g}".replace(".", ","))
        ws.cell(row=k + 2, column=2, value=sayi)
    ch = BarChart()
    ch.title = "Puan dağılımı"
    ch.y_axis.title = "Öğrenci"
    ch.x_axis.title = "Puan"
    ch.add_data(Reference(ws, min_col=2, min_row=1, max_row=11), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=11))
    ch.legend = None
    ch.height, ch.width = 8, 16
    ws.add_chart(ch, "D2")
    sutun_genislikleri(ws, {1: 14, 2: 16})

    # --- Madde Analizi
    ws = wb.create_sheet("Madde Analizi")
    basliklar = ["Soru", "Doğru şık" if not klasik else "Tam puan", "Güçlük", "Ayırt edicilik", "Nokta çift serili",
                 "Düzeltilmiş madde-toplam", "Soru çıkarılırsa alfa", "Üst grup", "Alt grup"]
    if not klasik:
        basliklar += ["A", "B", "C", "D", "E", "Çift", "Boş"]
    basliklar += ["Sorunlu", "Açıklama"]
    baslik_satiri(ws, 1, basliklar)
    for r, m in enumerate(maddeler, start=2):
        s_ = sonuc.anahtar.sorular[m.soru_no - 1]
        ws.cell(row=r, column=1, value=m.soru_no)
        if klasik:
            _sayi(ws, r, 2, m.tam_puan, "0.##")
        else:
            ws.cell(row=r, column=2, value="İptal" if s_.durum.value == "iptal" else m.dogru_sik)
        for j, v in ((3, m.guclik), (4, m.ayirt_edicilik), (5, m.nokta_cift_serili), (6, m.duzeltilmis_r),
                     (7, m.alfa_cikarilirsa), (8, m.ust_grup), (9, m.alt_grup)):
            _sayi(ws, r, j, v)
        j = 10
        if not klasik:
            for sik in ["A", "B", "C", "D", "E", "Çift", "Boş"]:
                c = _sayi(ws, r, j, m.sik_oranlari.get(sik), "0%")
                if sik in s_.dogru_kume():
                    c.fill = dolgu(RENK["D"])
                    c.font = KALIN
                j += 1
        ws.cell(row=r, column=j, value="Evet" if m.sorunlu else "")
        ws.cell(row=r, column=j + 1, value="; ".join(m.sorunlar) if not m.analiz_disi else "Analiz dışı")
        if m.sorunlu:
            for jj in (1, j, j + 1):
                ws.cell(row=r, column=jj).fill = dolgu(RENK["uyari"])
        if m.ayirt_edicilik is not None:
            ws.cell(row=r, column=4).fill = dolgu(RENK["D"] if m.ayirt_edicilik >= 0.30 else (RENK["B"] if m.ayirt_edicilik >= 0.20 else RENK["Y"]))
    _tablo_bitir(ws, len(basliklar), {1: 6, 2: 9, 3: 9, 4: 11, 5: 11, 6: 13, 7: 12, 8: 9, 9: 9, len(basliklar): 70})
    son = len(maddeler) + 1
    ch = BarChart()
    ch.type = "col"
    ch.title = "Güçlük ve ayırt edicilik"
    ch.add_data(Reference(ws, min_col=3, max_col=4, min_row=1, max_row=son), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=son))
    ch.height, ch.width = 8, 22
    ch.x_axis.title = "Soru"
    ws.add_chart(ch, f"A{son + 3}")
    _not(ws, son + 20, "Nokta çift serili: soru ile toplam arasındaki ilişki. Düzeltilmiş madde-toplam: soru ile, o soru çıkarılmış "
                       "toplam arasındaki ilişki (0,20 altı zayıf, eksi ise soru sınavın geri kalanıyla ters yönde çalışıyor). "
                       "Soru çıkarılırsa alfa: o soru olmasaydı güvenirlik katsayısı; sınavın genel değerinden büyükse soru "
                       "güvenirliği düşürüyor. Üst grup ve alt grup: en başarılı ve en başarısız %27'nin o sorudaki başarısı.",
          len(basliklar))

    if not klasik:
        # --- Çeldiriciler
        ws = wb.create_sheet("Çeldiriciler")
        baslik_satiri(ws, 1, ["Soru", "Doğru şık", "Yanlış şık", "Seçilme oranı", "Üst grupta", "Alt grupta", "Değerlendirme"])
        r = 2
        for m in maddeler:
            for c in m.celdiriciler:
                ws.cell(row=r, column=1, value=m.soru_no)
                ws.cell(row=r, column=2, value=m.dogru_sik)
                ws.cell(row=r, column=3, value=c.sik)
                _sayi(ws, r, 4, c.oran, "0%")
                _sayi(ws, r, 5, c.ust, "0%")
                _sayi(ws, r, 6, c.alt, "0%")
                ws.cell(row=r, column=7, value="; ".join(c.sorunlar) or "işliyor")
                if c.sorunlar:
                    ws.cell(row=r, column=7).fill = dolgu(RENK["uyari"])
                r += 1
        _tablo_bitir(ws, 7, {1: 6, 2: 9, 3: 9, 4: 13, 5: 11, 6: 11, 7: 42})
        _not(ws, r + 1, "İyi bir çeldirici (yanlış şık) alt gruptaki öğrencileri üst gruptakilerden daha çok çeker. %5'ten az seçilen "
                        "şık işlemiyor demektir: kimse onu makul bulmamış. Üst grubun daha çok seçtiği yanlış şık, soruda "
                        "belirsizlik ya da anahtar hatası olabileceğini düşündürür.", 7)

    # --- Beş Grup
    ws = wb.create_sheet("Beş Grup")
    baslik_satiri(ws, 1, ["Soru", "1. grup (en düşük)", "2. grup", "3. grup", "4. grup", "5. grup (en yüksek)"])
    r = 2
    for m in maddeler:
        if m.analiz_disi or not m.bes_grup:
            continue
        ws.cell(row=r, column=1, value=f"Soru {m.soru_no}")
        for j, v in enumerate(m.bes_grup, start=2):
            c = _sayi(ws, r, j, v, "0%")
            if v is not None:
                c.fill = dolgu(RENK["D"] if v >= 0.7 else (RENK["B"] if v >= 0.4 else RENK["Y"]))
        r += 1
    _tablo_bitir(ws, 6, {1: 10, 2: 18, 3: 10, 4: 10, 5: 10, 6: 20})
    _not(ws, r + 1, "Öğrenciler toplam puana göre beş eşit gruba ayrıldı. İyi bir soruda başarı soldan sağa düzenli artar. "
                    "Düz kalan ya da azalan satır, sorunun bilenle bilmeyeni ayırmadığını gösterir.", 6)

    # --- Boş Bırakma
    if genel.bos_orani_sirayla:
        ws = wb.create_sheet("Boş Bırakma")
        baslik_satiri(ws, 1, ["Kitapçıktaki sıra", "Boş bırakma oranı"])
        for k, v in enumerate(genel.bos_orani_sirayla, start=1):
            ws.cell(row=k + 1, column=1, value=k)
            _sayi(ws, k + 1, 2, v, "0%")
        ch = LineChart()
        ch.title = "Soru sırasına göre boş bırakma"
        ch.add_data(Reference(ws, min_col=2, min_row=1, max_row=len(genel.bos_orani_sirayla) + 1), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=len(genel.bos_orani_sirayla) + 1))
        ch.legend = None
        ch.height, ch.width = 8, 16
        ws.add_chart(ch, "D2")
        _not(ws, len(genel.bos_orani_sirayla) + 3, genel.hiz_uyarisi or "Son sorularda belirgin bir boş bırakma artışı yok; süre yeterli görünüyor.", 3)
        sutun_genislikleri(ws, {1: 18, 2: 18})

    if not klasik:
        # --- Kişi Uyumu
        ws = wb.create_sheet("Kişi Uyumu")
        baslik_satiri(ws, 1, [M.SUTUN["no"], M.SUTUN["ad"], M.SUTUN["puan"], "Uyum indeksi", "Beklenmedik sorular"])
        for r, k in enumerate(genel.kisi_uyumu, start=2):
            ws.cell(row=r, column=1, value=k.no).number_format = "@"
            ws.cell(row=r, column=2, value=k.ad)
            _sayi(ws, r, 3, k.puan)
            _sayi(ws, r, 4, k.indeks)
            ws.cell(row=r, column=5, value=", ".join(map(str, k.beklenmedik)))
        r = len(genel.kisi_uyumu) + 3
        _tablo_bitir(ws, 5, {1: 13, 2: 28, 3: 9, 4: 13, 5: 30})
        _not(ws, r, f"Harnisch ve Linn düzeltilmiş uyarı indeksi. {e.uyum_ust:.2f} üstü listelenir: öğrenci kolay soruları "
                    "kaçırıp zor soruları bilmiş. Nedeni okuma hatası (yanlış satıra işaretleme), dikkatsizlik, şans ya da "
                    "kopya olabilir; kâğıdın kendisine bakılması önerilir.".replace("0.", "0,"), 5)

        # --- Benzer Cevaplar
        ws = wb.create_sheet("Benzer Cevaplar")
        baslik_satiri(ws, 1, ["1. öğrenci no", "1. öğrenci", "2. öğrenci no", "2. öğrenci", "Aynı yanlış şık",
                              "İkisinin de yanlışı", "Bütün aynı cevaplar", "Sınıf ortalamasından uzaklık (standart sapma)", "Sorular"])
        for r, c in enumerate(genel.benzer_ciftler, start=2):
            for j, v in enumerate([c.no1, c.ad1, c.no2, c.ad2, c.ayni_yanlis, c.ikisi_yanlis, c.ayni_cevap], start=1):
                ws.cell(row=r, column=j, value=v)
            _sayi(ws, r, 8, c.z, "0.0")
            ws.cell(row=r, column=9, value=", ".join(map(str, c.sorular)))
        r = len(genel.benzer_ciftler) + 3
        _tablo_bitir(ws, 9, {1: 13, 2: 24, 3: 13, 4: 24, 5: 10, 6: 10, 7: 10, 8: 16, 9: 30})
        _not(ws, r, "Aynı kitapçıktaki her öğrenci çifti için, ikisinin de aynı yanlış şıkkı işaretlediği soru sayısı sayıldı. "
                    "Sınıf geneline göre 4 standart sapmadan uzak ve soruların en az %30'unda aynı yanlışı yapan çiftler "
                    "listelenir. Bu bir istatistiksel işarettir, kopya kanıtı değildir; oturma düzeni ve kâğıtlarla "
                    "birlikte değerlendirilmelidir." if genel.benzer_ciftler else
              "Sınıf geneline göre olağandışı sayıda aynı yanlış şık işaretleyen öğrenci çifti bulunmadı.", 9)

    _ek_analizler_sayfasi(wb, sonuc, maddeler, genel, e, ara_agirlik, arsiv or [])
    _yapi_sayfalari(wb, sonuc)
    if donem is not None:
        _donem_sayfasi(wb, donem)

    # --- Öğrenci Puanları (standart puanlar)
    ws = wb.create_sheet("Standart Puanlar")
    baslik_satiri(ws, 1, [M.SUTUN["no"], M.SUTUN["ad"], M.SUTUN["puan"], "Sıra", "Yüzdelik sıra", "z puanı", "T puanı"])
    ort, sd = genel.ortalama or 0.0, genel.standart_sapma or 0.0
    sirali = sorted(sonuc.ogrenciler, key=lambda o: -o.puan)
    n = len(sirali)
    for r, o in enumerate(sirali, start=2):
        p = float(o.puan)
        ws.cell(row=r, column=1, value=o.no).number_format = "@"
        ws.cell(row=r, column=2, value=o.ad)
        _sayi(ws, r, 3, p)
        ws.cell(row=r, column=4, value=1 + sum(1 for x in sirali if x.puan > o.puan))
        _sayi(ws, r, 5, sum(1 for x in sirali if x.puan < o.puan) / n if n else None, "0%")
        z = (p - ort) / sd if sd else None
        _sayi(ws, r, 6, z)
        _sayi(ws, r, 7, None if z is None else 50 + 10 * z, "0.0")
    _tablo_bitir(ws, 7, {1: 13, 2: 28, 3: 9, 4: 7, 5: 13, 6: 9, 7: 9})
    _not(ws, n + 3, "z puanı, öğrencinin sınıf ortalamasından kaç standart sapma uzakta olduğudur. T puanı = 50 + 10 × z. "
                    "Yüzdelik sıra, öğrenciden düşük puan alanların oranıdır.", 7)

    _yazdirma(wb)
    yol = Path(yol)
    wb.save(yol)
    return yol


def _ek_analizler_sayfasi(wb, sonuc, maddeler, genel, e, ara_agirlik, arsiv):
    from openpyxl.chart import LineChart, Reference

    from ..core import ek_istatistik as E

    a = sonuc.ayarlar
    ws = wb.create_sheet("Ek Analizler")
    r = 1

    def bolum(baslik):
        nonlocal r
        r += 1
        ws.cell(row=r, column=1, value=baslik).font = Font(bold=True, size=12)
        r += 1

    # Sınav tasarımı
    t = E.tasarim_denetimi(sonuc, [m.guclik for m in maddeler])
    sans = E.sans_puani(sonuc)
    if t or sans is not None:
        bolum("Sınav tasarımı")
        if t:
            ws.cell(row=r, column=1, value="Anahtarda şıkların sayısı")
            ws.cell(row=r, column=2, value=", ".join(f"{h}: {c}" for h, c in t.sik_sayilari.items()))
            r += 1
            ws.cell(row=r, column=1, value="Soru sırası ile güçlük sıra korelasyonu")
            _sayi(ws, r, 2, t.sira_guclik_korelasyonu)
            r += 1
            for n in t.notlar:
                _not(ws, r, "• " + n, 6)
                r += 1
        if sans is not None:
            ws.cell(row=r, column=1, value="Rastgele işaretleyenin beklenen puanı (şans puanı)")
            _sayi(ws, r, 2, sans)
            r += 1
            altinda = sum(1 for o in sonuc.ogrenciler if float(o.puan) < sans)
            ws.cell(row=r, column=1, value="Şans puanının altında kalan öğrenci")
            ws.cell(row=r, column=2, value=altinda)
            r += 1

    # Kitapçık eşdeğerliği
    kk = E.kitapcik_karsilastirma(sonuc)
    if kk:
        bolum("Kitapçıklar eşdeğer mi? (Welch t testi)")
        for ad, v, b in ((f"{kk.kitapcik1} ortalaması ({kk.n1} kişi)", kk.ortalama1, "0.00"), (f"{kk.kitapcik2} ortalaması ({kk.n2} kişi)", kk.ortalama2, "0.00"),
                         ("Fark", kk.fark, "0.00"), ("t", kk.t, "0.00"), ("Serbestlik derecesi", kk.serbestlik, "0.0"),
                         ("p değeri", kk.p, "0.000"), ("Etki büyüklüğü (Cohen d)", kk.etki, "0.00")):
            ws.cell(row=r, column=1, value=ad)
            _sayi(ws, r, 2, v, b)
            r += 1
        _not(ws, r, "p değeri 0,05'ten küçükse kitapçıklardan biri ötekinden anlamlı biçimde zor ya da kolay olmuş olabilir."
             if kk.p < 0.05 else "Kitapçıklar arasında anlamlı bir fark yok (p ≥ 0,05).", 6)
        r += 1

    # Sınırdaki öğrenciler
    sinir = E.sinirdaki_ogrenciler(sonuc, e.basari_esigi, genel.olcme_hatasi)
    bolum(f"Sınırdaki öğrenciler (puanı {e.basari_esigi:g} eşiğine ölçme hatası kadar yakın)")
    baslik_satiri(ws, r, [M.SUTUN["no"], M.SUTUN["ad"], M.SUTUN["puan"], "Eşiğe uzaklık"])
    r += 1
    for x in sinir:
        ws.cell(row=r, column=1, value=x.no).number_format = "@"
        ws.cell(row=r, column=2, value=x.ad)
        _sayi(ws, r, 3, x.puan)
        c = _sayi(ws, r, 4, x.fark)
        c.fill = dolgu(RENK["Y"] if x.fark < 0 else RENK["D"])
        r += 1
    _not(ws, r, "Ölçme hatası içinde kalan farklar şanstan kaynaklanabilir; bu kâğıtlara bir daha bakmak, özellikle eşiğin hemen "
                "altındakilerde, adil bir karar için yararlıdır.", 6)
    r += 1

    # Finalde gereken puan
    f = E.final_gereken(sonuc, ara_agirlik, a.gecme_ortalamasi, a.final_alt_siniri)
    if f:
        bolum(f"Finalde gereken puan (ara sınav %{ara_agirlik:g}, final %{100 - ara_agirlik:g}; geçme ortalaması "
              f"{a.gecme_ortalamasi}, final alt sınırı {a.final_alt_siniri})")
        baslik_satiri(ws, r, [M.SUTUN["no"], M.SUTUN["ad"], "Ara sınav", "Finalde en az"])
        r += 1
        for x in f:
            ws.cell(row=r, column=1, value=x.no).number_format = "@"
            ws.cell(row=r, column=2, value=x.ad)
            _sayi(ws, r, 3, x.puan)
            c = _sayi(ws, r, 4, x.gereken) if x.gereken is not None else ws.cell(row=r, column=4, value="100 de yetmez")
            if x.gereken is None or x.gereken > 80:
                c.fill = dolgu(RENK["Y"])
            r += 1
        _not(ws, r, "Geçme kuralı ders yönetmeliğine göre farklı olabilir; geçme ortalaması ve final alt sınırı 3. adımda değiştirilebilir. "
                    "Bütünleme ve harf notu dönüşümü hesaba katılmamıştır.", 6)
        r += 1

    # Rasch modeli
    rs = E.rasch(sonuc)
    if rs:
        bolum("Rasch modeli: soruların zorluk ölçeği (logit; 0 = ortalama soru, artı = zor)")
        baslik_satiri(ws, r, ["Soru", "Zorluk (logit)", "Standart hata"])
        r += 1
        bas = r
        for no, b in sorted(rs.soru_zorluklari.items(), key=lambda kv: kv[1]):
            ws.cell(row=r, column=1, value=no)
            _sayi(ws, r, 2, b)
            _sayi(ws, r, 3, rs.soru_hatalari[no])
            r += 1
        _not(ws, r, f"Sınav en iyi, yeteneği {rs.en_iyi_olctugu:+.1f} logit olan öğrenciyi ölçüyor; bu, yaklaşık %{rs.en_iyi_puan:.0f} "
                    "başarıya karşılık gelir. Bu düzeyin çok altındaki ve üstündeki öğrencileri ayırmakta sınav daha az bilgi verir. "
                    + (f"Herkesin bildiği ya da kimsenin bilmediği sorular ({', '.join(map(str, rs.disarida_kalan_soru))}) ölçekte yer almaz. " if rs.disarida_kalan_soru else "")
                    + (f"Tam ya da sıfır doğru yapan {rs.disarida_kalan_ogrenci} öğrenci ölçek hesabına katılmadı." if rs.disarida_kalan_ogrenci else ""), 6)
        r += 2
        egri_bas = r
        ws.cell(row=r, column=5, value="Yetenek (logit)").font = KALIN
        ws.cell(row=r, column=6, value="Sınav bilgisi").font = KALIN
        for i, (t_, v) in enumerate(rs.bilgi_egrisi[::4], start=1):
            ws.cell(row=r + i, column=5, value=t_)
            _sayi(ws, r + i, 6, v)
        son = r + len(rs.bilgi_egrisi[::4])
        ch = LineChart()
        ch.title = "Sınav bilgi eğrisi: sınav hangi başarı düzeyini en iyi ölçüyor"
        ch.add_data(Reference(ws, min_col=6, min_row=egri_bas, max_row=son), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=5, min_row=egri_bas + 1, max_row=son))
        ch.legend = None
        ch.height, ch.width = 8, 16
        ws.add_chart(ch, f"H{bas}")
        r = son + 2

    # Arşiv: aynı dersin önceki sınavları
    if arsiv:
        bolum("Aynı dersin önceki sınavlarıyla karşılaştırma")
        kodlar = sorted({k for x in arsiv for k in x.cikti_basarilari}, key=_dogal)
        baslik_satiri(ws, r, ["Tarih", "Sınav", "Öğrenci", "Ortalama", "Başarılı oranı", "Güvenirlik"] + kodlar)
        r += 1
        for x in arsiv:
            for j, v in enumerate([x.tarih, x.sinav_turu, x.ogrenci_sayisi], start=1):
                ws.cell(row=r, column=j, value=v)
            _sayi(ws, r, 4, x.ortalama)
            _sayi(ws, r, 5, x.basari_orani, "0%")
            _sayi(ws, r, 6, x.guvenirlik)
            for j, k in enumerate(kodlar, start=7):
                _sayi(ws, r, j, x.cikti_basarilari.get(k))
            r += 1
        _not(ws, r, "Öğrenme çıktısı sütunları sınıf başarı yüzdesidir. Kayıtlar 'Tüm raporları klasöre yaz' her kullanıldığında "
                    "bilgisayarınızdaki arşive eklenir.", 6)
    sutun_genislikleri(ws, {1: 50, 2: 28, 3: 14, 4: 16, 5: 14, 6: 14})


def _yapi_sayfalari(wb, sonuc):
    from ..core import ek_istatistik as E

    if not sonuc.klasik:
        ws = wb.create_sheet("Kavram Yanılgıları")
        baslik_satiri(ws, 1, ["Soru", "Yanlış şık", "Birlikte seçilen soru", "Yanlış şık", "İkisini birden seçen", "1. şıkkı seçen",
                              "1'i seçenlerde 2'yi seçme oranı", "Sınıfta 2'yi seçme oranı", "Phi", "p değeri"])
        k = E.kavram_yanilgilari(sonuc)
        for r, x in enumerate(k, start=2):
            for j, v in enumerate([x.soru1, x.sik1, x.soru2, x.sik2, x.birlikte, x.secen1], start=1):
                ws.cell(row=r, column=j, value=v)
            _sayi(ws, r, 7, x.kosullu, "0%")
            _sayi(ws, r, 8, x.taban, "0%")
            _sayi(ws, r, 9, x.phi)
            _sayi(ws, r, 10, x.p, "0.000")
        _tablo_bitir(ws, 10, {1: 7, 2: 10, 3: 12, 4: 10, 5: 12, 6: 10, 7: 16, 8: 14, 9: 8, 10: 9})
        _not(ws, len(k) + 3, "İki farklı sorunun yanlış şıklarını birlikte seçen öğrenciler. Aynı yanlış düşünce iki soruda birden "
                             "yanıltıyor olabilir: o iki sorunun ortak konusunu sınıfla yeniden ele almak yararlı olur. Fisher kesin "
                             "testinde p ≤ 0,01 olan çiftler listelenir." if k else
              "Sınıf geneline göre belirgin biçimde birlikte seçilen yanlış şık çifti bulunmadı.", 10)
    y = E.sinav_yapisi(sonuc)
    if y is None:
        return
    ws = wb.create_sheet("Sınav Yapısı")
    ws.cell(row=1, column=1, value="Yorum").font = KALIN
    _not(ws, 2, y.yorum, 6)
    satirlar = [("Birinci bileşenin açıkladığı varyans", y.ilk_pay, "0%"), ("Birinci / ikinci özdeğer", y.oran_1_2, "0.00"),
                ("Sorular arası ortalama korelasyon", y.ortalama_korelasyon, "0.000")]
    for r, (ad, v, b) in enumerate(satirlar, start=4):
        ws.cell(row=r, column=1, value=ad).font = KALIN
        _sayi(ws, r, 2, v, b)
    r = 8
    baslik_satiri(ws, r, ["Soru", "Ortak bileşene yükü", "Değerlendirme"])
    for no in y.sorular:
        r += 1
        ws.cell(row=r, column=1, value=no)
        _sayi(ws, r, 2, y.yukler[no])
        if no in y.zayif_sorular:
            c = ws.cell(row=r, column=3, value="sınavın geri kalanından farklı bir şey ölçüyor")
            c.fill = dolgu(RENK["uyari"])
    if y.cikti_uyumu:
        r += 2
        baslik_satiri(ws, r, ["Öğrenme çıktısı", "Kendi soruları arasında ortalama korelasyon", "Öteki sorularla ortalama korelasyon", "Soru sayısı"])
        for kod, ic, dis, n in y.cikti_uyumu:
            r += 1
            ws.cell(row=r, column=1, value=kod)
            _sayi(ws, r, 2, ic, "0.000")
            _sayi(ws, r, 3, dis, "0.000")
            ws.cell(row=r, column=4, value=n)
        r += 1
        _not(ws, r + 1, "Aynı öğrenme çıktısına bağlı sorular kendi aralarında ötekilerden daha çok ilişkiliyse, soru-çıktı eşlemesi "
                        "verilerle uyumludur.", 6)
    r += 3
    ws.cell(row=r, column=1, value="Özdeğerler").font = KALIN
    for j, v in enumerate(y.ozdegerler, start=2):
        _sayi(ws, r, j, v)
    sutun_genislikleri(ws, {1: 44, 2: 22, 3: 44, 4: 12})


def _donem_sayfasi(wb, d):
    ws = wb.create_sheet("Dönem Sonu Notu")
    bas = ["Öğrenci No", "Ad Soyad", "Ara sınav", "Final", "Ham başarı notu"] + (["T puanı"] if d.uygulanan == "bagil" else []) + ["Harf", "Durum", "Açıklama", "Sınırda"]
    baslik_satiri(ws, 1, bas)
    for r, n in enumerate(d.notlar, start=2):
        j = 1
        ws.cell(row=r, column=j, value=n.no).number_format = "@"
        ws.cell(row=r, column=j + 1, value=n.ad)
        _sayi(ws, r, j + 2, n.ara)
        _sayi(ws, r, j + 3, n.final)
        _sayi(ws, r, j + 4, n.ham)
        j += 5
        if d.uygulanan == "bagil":
            _sayi(ws, r, j, n.t)
            j += 1
        ws.cell(row=r, column=j, value=n.harf).font = KALIN
        c = ws.cell(row=r, column=j + 1, value="" if n.gecti is None else ("Geçti" if n.gecti else "Kaldı"))
        if n.gecti is not None:
            c.fill = dolgu(RENK["D"] if n.gecti else RENK["Y"])
        ws.cell(row=r, column=j + 2, value=n.aciklama)
        if n.sinirda:
            ws.cell(row=r, column=j + 3, value=n.sinirda).fill = dolgu(RENK["uyari"])
    _tablo_bitir(ws, len(bas), {1: 13, 2: 28, len(bas) - 1: 24, len(bas): 18})
    r = len(d.notlar) + 3
    ws.cell(row=r, column=1, value="Harf dağılımı").font = KALIN
    for j, (h, sayi) in enumerate(d.dagilim.items(), start=2):
        ws.cell(row=r, column=j, value=h).font = KALIN
        ws.cell(row=r + 1, column=j, value=sayi)
    aciklama = (f"Uygulanan: {'bağıl (T-puanı)' if d.uygulanan == 'bagil' else 'mutlak'} değerlendirme."
                + (f" Bağıl grup: {d.bagil_grup} öğrenci, ortalama {d.ortalama:.2f}, standart sapma {d.standart_sapma:.2f}.".replace(".", ",") if d.uygulanan == "bagil" else "")
                + " " + " ".join(d.notlar_metin)
                + " Harf tabloları örnektir; üniversitenizin yönetmeliğiyle karşılaştırın.")
    _not(ws, r + 3, aciklama, 8)


def ogrenme_ciktisi_yaz(sonuc: SinavSonucu, sinav: SinavBilgisi, yol: str | Path, aciklamalar: dict[str, str] | None = None) -> Path | None:
    from openpyxl.chart import BarChart, Reference

    esik = float(getattr(sonuc.ayarlar, "basari_esigi", 50))
    rapor = ogrenme_ciktisi_raporu(sonuc, esik, aciklamalar)
    if not rapor:
        return None
    aciklamalar = aciklamalar or {}
    aciklamalar_ogrenme = [k for k in aciklamalar if k.startswith("Ö")]
    wb = Workbook()

    # --- Soru-Çıktı Eşlemesi: sisteme girilecek tablo
    ws = wb.active
    ws.title = "Soru-Çıktı Eşlemesi"
    kodlar = sorted({k for s in sonuc.anahtar.sorular for k in s.ogrenme_ciktilari}, key=_dogal)
    baslik_satiri(ws, 1, ["Soru", "Soru puanı"] + kodlar + ["Toplam %", "Program çıktıları"])
    for r, (s_, p) in enumerate(zip(sonuc.anahtar.sorular, sonuc.soru_puanlari), start=2):
        ws.cell(row=r, column=1, value=s_.no)
        _puan(ws, r, 2, p, 2)
        d = s_.cikti_dagilimi()
        for j, k in enumerate(kodlar, start=3):
            ws.cell(row=r, column=j, value=d.get(k))
        t = ws.cell(row=r, column=3 + len(kodlar), value=sum(d.values()) if d else None)
        if d and sum(d.values()) != 100:
            t.fill = dolgu(RENK["Y"])
        ws.cell(row=r, column=4 + len(kodlar), value=", ".join(s_.program_ciktilari))
    _tablo_bitir(ws, 4 + len(kodlar), {1: 7, 2: 11, 3 + len(kodlar): 10, 4 + len(kodlar): 22})
    _not(ws, len(sonuc.anahtar.sorular) + 3, "Her satır bir sorudur; hücreler o sorunun öğrenme çıktılarına yüzde dağılımıdır ve her "
                                             "satırın toplamı 100 olmalıdır. Akademik Bilgi Sistemi'nde soruları tanımlarken bu tabloyu kullanın.",
          4 + len(kodlar))

    # --- Sisteme Aktarım: Akademik Bilgi Sistemi "Toplu Aktarım Yap" biçimi
    from .soru_tanimi import soru_tanimi_satirlari

    ws = wb.create_sheet("Sisteme Aktarım")
    try:
        satirlar = soru_tanimi_satirlari(sonuc.anahtar, sonuc.ayarlar, list(aciklamalar_ogrenme or []) or None)
    except Exception:  # noqa: BLE001
        satirlar = []
    en_fazla = max((len(x) for x in satirlar), default=3)
    bas = ["Soru No", "Soru Puan", "Soru metni"]
    for _ in range((en_fazla - 3) // 2):
        bas += ["DÇ Sıra", "Etki Oran"]
    baslik_satiri(ws, 1, bas)
    for r, satir in enumerate(satirlar, start=2):
        for j, v in enumerate(satir, start=1):
            ws.cell(row=r, column=j, value=v)
    sutun_genislikleri(ws, {1: 9, 2: 10, 3: 12})
    _not(ws, len(satirlar) + 3, "Başlık satırı dışındaki hücreleri seçip kopyalayın; Sınav Akreditasyon İşlemleri > Toplu Aktarım Yap > "
                                "Aktarım Kutusu'na yapıştırıp Aktar'a basın (Kolon Ayracı: Excel'den Kopyalandı). DÇ Sıra, dersin "
                                "öğrenme çıktısı sırasıdır (Ö05 için 5).", max(6, en_fazla))

    # --- Sınav Dağılımı
    ws = wb.create_sheet("Sınav Dağılımı")
    dag = cikti_dagilimi(sonuc)
    tam = tam_sayi_dagilim(dag)
    baslik_satiri(ws, 1, ["Öğrenme çıktısı", "Açıklama", "Sınavdaki payı (%)", "Tam sayı (%)"])
    r = 2
    for k, v in dag.items():
        ws.cell(row=r, column=1, value=k)
        ws.cell(row=r, column=2, value=aciklamalar.get(k, ""))
        _sayi(ws, r, 3, float(v))
        ws.cell(row=r, column=4, value=tam[k])
        r += 1
    ws.cell(row=r, column=1, value="Toplam").font = KALIN
    _sayi(ws, r, 3, float(sum(dag.values()))).font = KALIN
    ws.cell(row=r, column=4, value=sum(tam.values())).font = KALIN
    sutun_genislikleri(ws, {1: 16, 2: 70, 3: 18, 4: 13})

    # --- Sınıf Başarısı
    ws = wb.create_sheet("Sınıf Başarısı")
    baslik_satiri(ws, 1, ["Tür", "Kod", "Açıklama", "Sorular", "Sınavdaki payı (%)", "Sınıf başarı yüzdesi",
                          f"%{esik:g} ve üstüne ulaşan öğrenci"])
    for r, c in enumerate(rapor, start=2):
        ws.cell(row=r, column=1, value=c.tur)
        ws.cell(row=r, column=2, value=c.kod)
        ws.cell(row=r, column=3, value=c.aciklama)
        ws.cell(row=r, column=4, value=", ".join(map(str, c.sorular)))
        _sayi(ws, r, 5, c.sinav_agirligi if c.tur.startswith("Öğrenme") else None)
        h = _sayi(ws, r, 6, None if c.sinif_yuzdesi is None else round(c.sinif_yuzdesi, 2))
        if c.sinif_yuzdesi is not None:
            h.fill = dolgu(RENK["D"] if c.sinif_yuzdesi >= esik + 10 else (RENK["B"] if c.sinif_yuzdesi >= esik else RENK["Y"]))
        _sayi(ws, r, 7, c.ulasan_orani, "0%")
    _tablo_bitir(ws, 7, {1: 18, 2: 8, 3: 60, 4: 16, 5: 16, 6: 16, 7: 20})
    ogr_say = sum(1 for c in rapor if c.tur.startswith("Öğrenme"))
    if ogr_say:
        ch = BarChart()
        ch.type = "bar"
        ch.title = "Öğrenme çıktılarına göre sınıf başarısı (%)"
        ch.add_data(Reference(ws, min_col=6, min_row=1, max_row=1 + ogr_say), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=2, max_row=1 + ogr_say))
        ch.legend = None
        ch.height, ch.width = 7 + ogr_say * 0.4, 16
        ws.add_chart(ch, f"B{len(rapor) + 4}")

    # --- Öğrenci Bazında
    ws = wb.create_sheet("Öğrenci Bazında")
    etiket = [c.kod for c in rapor]
    baslik_satiri(ws, 1, [M.SUTUN["no"], M.SUTUN["ad"]] + etiket)
    for r, o in enumerate(sonuc.ogrenciler, start=2):
        ws.cell(row=r, column=1, value=o.no).number_format = "@"
        ws.cell(row=r, column=2, value=o.ad)
        for j, c in enumerate(rapor, start=3):
            v = c.ogrenci_yuzdeleri[o.no]
            h = _sayi(ws, r, j, round(v, 2))
            if v < esik:
                h.fill = dolgu(RENK["Y"])
    _tablo_bitir(ws, 2 + len(rapor), {1: 13, 2: 28})
    ws.cell(row=ws.max_row + 2, column=1, value=f"Kırmızı hücreler %{esik:g} eşiğinin altıdır. Ö ile başlayan kodlar öğrenme, "
                                                "P ile başlayanlar program çıktısıdır.")
    _yazdirma(wb)
    yol = Path(yol)
    wb.save(yol)
    return yol


def _dogal(s: str):
    import re

    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", s)]


def pdf_ozet_yaz(sonuc: SinavSonucu, sinav: SinavBilgisi, yol: str | Path, esikler: MaddeEsikleri | None = None) -> Path | None:
    """Arşiv için özet: sınav bilgileri, puan dağılımı ve madde analizi tablosu. matplotlib yoksa None."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except ImportError:
        return None
    maddeler, genel = madde_analizi(sonuc, esikler)
    yol = Path(yol)
    puanlar = [float(o.puan) for o in sonuc.ogrenciler]
    with PdfPages(yol) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.08, 0.95, f"{sinav.ders_kodu} {sinav.ders_adi}", fontsize=14, weight="bold")
        fig.text(0.08, 0.925, f"{sinav.sinav_turu}  {sinav.tarih} {sinav.saat}", fontsize=10)
        ozet = (f"Sınava giren: {genel.ogrenci_sayisi}   Girmeyen: {len(sonuc.girmeyenler)}   "
                f"Ortalama: {genel.ortalama or 0:.2f}   Standart sapma: {genel.standart_sapma or 0:.2f}   "
                f"Medyan: {genel.medyan or 0:.2f}   En düşük / en yüksek: {genel.en_dusuk or 0:.2f} / {genel.en_yuksek or 0:.2f}   "
                f"Kuder-Richardson 20: {'' if genel.kr20 is None else f'{genel.kr20:.2f}'}")
        fig.text(0.08, 0.89, ozet, fontsize=8, wrap=True)
        import textwrap

        yorum = "\n".join(textwrap.fill("• " + y, 120) for y in genel.yorumlar)
        fig.text(0.08, 0.86, yorum, fontsize=7, va="top")
        ax = fig.add_axes([0.1, 0.50, 0.8, 0.22])
        ax.hist(puanlar, bins=[i * 10 for i in range(11)], color="#4472C4", edgecolor="white")
        ax.set_xlabel("Puan")
        ax.set_ylabel("Öğrenci sayısı")
        ax.set_title("Puan dağılımı", fontsize=10)
        ax2 = fig.add_axes([0.05, 0.03, 0.9, 0.40])
        ax2.axis("off")
        tablo = [[m.soru_no, m.dogru_sik or "-",
                  "" if m.guclik is None else f"{m.guclik:.2f}",
                  "" if m.ayirt_edicilik is None else f"{m.ayirt_edicilik:.2f}",
                  "" if m.nokta_cift_serili is None else f"{m.nokta_cift_serili:.2f}",
                  "Evet" if m.sorunlu else ""] for m in maddeler]
        t = ax2.table(cellText=tablo, colLabels=["Soru", "Doğru", "Güçlük", "Ayırt edicilik", "Nokta çift serili", "Sorunlu"],
                      loc="upper center", cellLoc="center")
        t.auto_set_font_size(False)
        t.set_fontsize(7)
        pdf.savefig(fig)
        plt.close(fig)
    return yol


@dataclass
class TopluCikti:
    dosyalar: list[Path] = field(default_factory=list)
    notlar: list[str] = field(default_factory=list)


def tum_raporlari_yaz(sonuc: SinavSonucu, sinav: SinavBilgisi, klasor: str | Path, duzeltmeler=None,
                      akreditasyon_profili=None, not_giris_profili=None, sistem_sablonu: str | Path | None = None,
                      pdf: bool = True, kaynaklar: dict[str, str] | None = None,
                      cikti_aciklamalari: dict[str, str] | None = None, ara_agirlik: float = 40.0,
                      arsiv_klasoru: str | Path | None = None, donem=None, karne: bool = True) -> TopluCikti:
    from .sablon_doldurucu import sablonu_doldur
    from .xlsx_yazici import aktarim_yaz, uzanti

    klasor = Path(klasor)
    klasor.mkdir(parents=True, exist_ok=True)
    t = TopluCikti()
    t.dosyalar.append(sonuc_dosyasi_yaz(sonuc, sinav, klasor / cikti_adi(sinav, "sonuc"), duzeltmeler, kaynaklar))
    if akreditasyon_profili is not None:
        if sistem_sablonu:
            rapor = sablonu_doldur(sistem_sablonu, akreditasyon_profili, sonuc, klasor / cikti_adi(sinav, "akreditasyon_sablon"))
            t.dosyalar.append(rapor.cikti)
            if rapor.girmedi:
                t.notlar.append(f"Şablonda olup sınava girmeyen: {len(rapor.girmedi)}")
            if rapor.sablonda_olmayan:
                t.notlar.append("Sonuçta olup şablonda olmayan numaralar: " + ", ".join(rapor.sablonda_olmayan))
        elif akreditasyon_profili.dosya_turu != "sablon":
            t.dosyalar.append(aktarim_yaz(akreditasyon_profili, sonuc, klasor / cikti_adi(sinav, "akreditasyon", uzanti(akreditasyon_profili)), sinav))
    if not_giris_profili is not None and not_giris_profili.dosya_turu != "sablon":
        t.dosyalar.append(aktarim_yaz(not_giris_profili, sonuc, klasor / cikti_adi(sinav, "not_giris", uzanti(not_giris_profili)), sinav))
    arsiv = []
    if arsiv_klasoru and sinav.ders_kodu and sonuc.ogrenciler:
        from ..core import ek_istatistik as E

        esik = float(sonuc.ayarlar.basari_esigi)
        _, genel = madde_analizi(sonuc, MaddeEsikleri(basari_esigi=esik, cikti_esigi=esik))
        E.arsive_yaz(Path(arsiv_klasoru), E.arsiv_kaydi_olustur(sonuc, sinav, genel, ogrenme_ciktisi_raporu(sonuc, esik)))
        arsiv = E.arsivi_oku(Path(arsiv_klasoru), sinav.ders_kodu)
    t.dosyalar.append(madde_analizi_yaz(sonuc, sinav, klasor / cikti_adi(sinav, "istatistik"), ara_agirlik=ara_agirlik, arsiv=arsiv, donem=donem))
    if karne and sonuc.ogrenciler:
        from .karne import karne_yaz

        t.dosyalar.append(karne_yaz(sonuc, sinav, klasor / cikti_adi(sinav, "karneler", ".html"), cikti_aciklamalari))
    oc = ogrenme_ciktisi_yaz(sonuc, sinav, klasor / cikti_adi(sinav, "ogrenme_ciktisi"), cikti_aciklamalari)
    if oc:
        t.dosyalar.append(oc)
    else:
        t.notlar.append("Soru ile öğrenme çıktısı eşlemesi girilmediği için öğrenme çıktısı raporu yazılmadı.")
    if pdf:
        p = pdf_ozet_yaz(sonuc, sinav, klasor / cikti_adi(sinav, "ozet", ".pdf"))
        if p:
            t.dosyalar.append(p)
        else:
            t.notlar.append("matplotlib kurulu olmadığı için özet yazılmadı.")
    return t


