"""Tarayıcı sürümünü tek bir HTML dosyasında birleştirir: web/dist/OptikSinav.html

İçine gömülenler: stil, üç kitaplık (SheetJS, ExcelJS, PDF.js ve işçisi), paketle gelen ders bilgi paketleri
(dersler/*.json) ve web/src altındaki program dosyaları. Sayfanın güvenlik kuralı (Content-Security-Policy)
ağ bağlantısını tarayıcı düzeyinde yasaklar; dosya internete hiçbir şey gönderemez.

Kullanım: python tools/web_derle.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
WEB = KOK / "web"
SURUM = "1.0"

KITAPLIKLAR = [
    "xlsx_0.18.5_dist_xlsx.full.min.js",
    "exceljs_4.4.0_dist_exceljs.min.js",
    "pdfjs-dist_3.11.174_legacy_build_pdf.min.js",
]
ISCI = "pdfjs-dist_3.11.174_legacy_build_pdf.worker.min.js"
PROGRAM = ["cekirdek.js", "istatistik.js", "ciktilar.js", "dosya.js", "donem.js", "arayuz.js", "excel.js", "arayuz2.js"]

CSP = ("default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' blob:; worker-src blob:; style-src 'unsafe-inline'; "
       "img-src data: blob:; font-src data:; connect-src blob: data:; form-action 'none'; base-uri 'none'")


def kitaplik_dogrula() -> None:
    beklenen = {}
    for satir in (WEB / "vendor" / "SHA256SUMS").read_text().splitlines():
        h, ad = satir.split()
        beklenen[ad] = h
    for ad in KITAPLIKLAR + [ISCI]:
        h = hashlib.sha256((WEB / "vendor" / ad).read_bytes()).hexdigest()
        if beklenen.get(ad) != h:
            raise SystemExit(f"Kitaplık değişmiş ya da eksik: {ad}")


def betik(metin: str) -> str:
    return metin.replace("</script", "<\\/script")


def main() -> Path:
    kitaplik_dogrula()
    dersler = {}
    for p in sorted((KOK / "dersler").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        dersler[d["kod"]] = d
    parcalar = [
        "<!doctype html>",
        '<html lang="tr"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<meta http-equiv="Content-Security-Policy" content="{CSP}">',
        "<title>Optik Sınav Değerlendirme</title>",
        f"<style>{(WEB / 'src' / 'stil.css').read_text(encoding='utf-8')}</style>",
        # PDF işçisi başlıkta durur; arayüz gövdeyi yeniden yazınca silinmesin.
        f'<script type="text/plain" id="pdf-isci">{betik((WEB / "vendor" / ISCI).read_text(encoding="utf-8"))}</script>',
        "</head><body><p style=\"padding:20px\">Yükleniyor…</p>",
    ]
    for ad in KITAPLIKLAR:
        parcalar.append(f"<script>{betik((WEB / 'vendor' / ad).read_text(encoding='utf-8'))}</script>")
    parcalar.append(f"<script>window.DERSLER = {json.dumps(dersler, ensure_ascii=False)}; window.OS_SURUM = {json.dumps(SURUM + ' (' + date.today().isoformat() + ')')};</script>")
    for ad in PROGRAM:
        parcalar.append(f"<script>{betik((WEB / 'src' / ad).read_text(encoding='utf-8'))}</script>")
    parcalar.append("</body></html>")
    cikis = WEB / "dist" / "OptikSinav.html"
    cikis.parent.mkdir(parents=True, exist_ok=True)
    cikis.write_text("\n".join(parcalar), encoding="utf-8")
    print(f"Yazıldı: {cikis} ({cikis.stat().st_size / 1e6:.1f} MB)")
    return cikis


if __name__ == "__main__":
    main()
