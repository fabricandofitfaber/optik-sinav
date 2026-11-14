"""Öğrenci karneleri: her öğrenciye bir sayfa, tarayıcıda açılıp yazdırılır (A4)."""
from __future__ import annotations

import html
from pathlib import Path

from ..core.donem_sonu import karneler
from ..core.madde_analizi import ogrenme_ciktisi_raporu
from ..core.modeller import SinavBilgisi, SinavSonucu

DURUM = {"D": ("✓", "#1e7b34"), "Y": ("✗", "#c0392b"), "B": ("–", "#8a6d00"), "I": ("İptal", "#666"), "K": ("kısmi", "#2f5597"), "-": ("", "#666")}


def _v(x: float, n: int = 1) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def karne_html(sonuc: SinavSonucu, sinav: SinavBilgisi, aciklamalar: dict[str, str] | None = None) -> str:
    esik = float(getattr(sonuc.ayarlar, "basari_esigi", 50))
    rapor = ogrenme_ciktisi_raporu(sonuc, esik, aciklamalar)
    e = html.escape
    sayfalar = []
    for k in karneler(sonuc, rapor, aciklamalar):
        sorular = "".join(
            f"<tr><td>{no}</td><td>{e(isaret) or '–'}</td><td>{e(dogru)}</td>"
            f"<td style='color:{DURUM[durum][1]};font-weight:600'>{DURUM[durum][0]}</td><td>{_v(alinan, 2)} / {_v(tam, 2)}</td></tr>"
            for no, isaret, dogru, durum, alinan, tam in k.sorular)
        ciktilar = "".join(
            f"<tr><td><b>{e(kod)}</b> {e(ac)}</td><td class='cubuk'><div><i style='width:{max(0, min(100, ogr)):.0f}%'></i>"
            f"<s style='left:{max(0, min(100, sinif)):.0f}%'></s></div></td><td>%{_v(ogr, 0)}</td><td class='soluk'>%{_v(sinif, 0)}</td></tr>"
            for kod, ac, ogr, sinif in k.ciktilar)
        yorum = []
        if k.guclu:
            yorum.append("Sınıf ortalamasının belirgin üstünde olduğunuz çıktılar: <b>" + ", ".join(map(e, k.guclu)) + "</b>.")
        if k.gelismeli:
            yorum.append("Üzerinde çalışmanız önerilen çıktılar: <b>" + ", ".join(map(e, k.gelismeli)) + "</b>.")
        sayfalar.append(f"""<section class="sayfa">
<header><div><b>{e(sinav.ders_kodu)} {e(sinav.ders_adi)}</b><br>{e(sinav.sinav_turu)} {e(sinav.tarih)}</div><div class="sag"><b>{e(k.ad)}</b><br>{e(k.no)}</div></header>
<div class="kartlar"><div><b>{_v(k.puan, 2)}</b><span>Puanınız</span></div><div><b>{_v(k.sinif_ortalamasi, 1)}</b><span>Sınıf ortalaması</span></div>
<div><b>{k.sira} / {k.ogrenci_sayisi}</b><span>Sıranız</span></div><div><b>%{_v(k.yuzdelik * 100, 0)}</b><span>Sizden düşük alanlar</span></div></div>
{f'<h3>Öğrenme çıktıları</h3><table class="cikti"><tr><th>Çıktı</th><th>Başarınız (çizgi: sınıf ortalaması)</th><th>Siz</th><th>Sınıf</th></tr>{ciktilar}</table><p>{" ".join(yorum)}</p>' if k.ciktilar else ''}
<h3>Sorular</h3><table class="soru"><tr><th>Soru</th><th>Cevabınız</th><th>{'' if sonuc.klasik else 'Doğru cevap'}</th><th>Durum</th><th>Puan</th></tr>{sorular}</table>
</section>""")
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>{e(sinav.ders_kodu)} öğrenci karneleri</title>
<style>
body{{font:13px/1.4 -apple-system,"Segoe UI",Arial,sans-serif;color:#111;margin:0;background:#eee}}
.sayfa{{background:#fff;width:190mm;min-height:270mm;margin:10mm auto;padding:10mm;box-sizing:border-box;page-break-after:always}}
header{{display:flex;justify-content:space-between;border-bottom:2px solid #2f5597;padding-bottom:6px}} .sag{{text-align:right}}
.kartlar{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:12px 0}} .kartlar div{{border:1px solid #ccd;border-radius:8px;padding:6px 8px}}
.kartlar b{{display:block;font-size:20px}} .kartlar span{{color:#666;font-size:11px}}
table{{border-collapse:collapse;width:100%}} th,td{{border-bottom:1px solid #ddd;padding:3px 6px;text-align:left}} th{{color:#555;font-weight:600}}
table.soru td,table.soru th{{text-align:center}} .soluk{{color:#777}} h3{{margin:14px 0 6px;font-size:14px;color:#2f5597}}
.cubuk div{{position:relative;height:10px;background:#eef;border-radius:5px;min-width:160px}} .cubuk i{{display:block;height:100%;background:#2f5597;border-radius:5px}}
.cubuk s{{position:absolute;top:-3px;width:2px;height:16px;background:#c0392b}}
@media print{{body{{background:#fff}} .sayfa{{margin:0;width:auto;min-height:0}} @page{{size:A4;margin:12mm}}}}
</style></head><body>{''.join(sayfalar)}</body></html>"""


def karne_yaz(sonuc: SinavSonucu, sinav: SinavBilgisi, yol: str | Path, aciklamalar: dict[str, str] | None = None) -> Path:
    yol = Path(yol)
    yol.write_text(karne_html(sonuc, sinav, aciklamalar), encoding="utf-8")
    return yol
