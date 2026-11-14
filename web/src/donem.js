/* Optik Sınav — tarayıcı sürümü: kavram yanılgıları, sınav yapısı, dönem sonu notu ve öğrenci karnesi.
 * Python karşılıkları: core/ek_istatistik.py (kavram_yanilgilari, sinav_yapisi), core/donem_sonu.py, export/karne.py.
 */
(function (kok) {
  "use strict";
  const OS = kok.OS;
  const { SIKLAR, fmean, pvariance, stdev, Kesir } = OS;

  // ------------------------------------------------------------------ kavram yanılgıları
  function lgamma(x) {
    const g = 7, c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059,
      12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
    if (x < 0.5) return Math.log(Math.PI / Math.abs(Math.sin(Math.PI * x))) - lgamma(1 - x);
    x -= 1;
    let a = c[0];
    const t = x + g + 0.5;
    for (let i = 1; i < g + 2; i++) a += c[i] / (x + i);
    return 0.5 * Math.log(2 * Math.PI) + (x + 0.5) * Math.log(t) - t + Math.log(a);
  }
  const logKomb = (n, k) => lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1);
  function fisherUst(n11, n1, n2, n) {
    let t = 0;
    for (let x = n11; x <= Math.min(n1, n2); x++) t += Math.exp(logKomb(n1, x) + logKomb(n - n1, n2 - x) - logKomb(n, n2));
    return Math.min(1, t);
  }
  function kavramYanilgilari(sonuc, enFazla = 15) {
    if (sonuc.klasik) return [];
    const ana = sonuc.anahtar.ana_kitapcik;
    const ogr = sonuc.ogrenciler.filter((o) => (o.kitapcik || ana) === ana);
    const n = ogr.length;
    if (n < 10) return [];
    const alt = Math.max(3, Math.ceil(0.05 * n));
    const g = [];
    sonuc.anahtar.sorular.forEach((s, i) => {
      const d = OS.dogruKume(s);
      if (s.durum === "iptal" || !d.size) return;
      for (const sik of SIKLAR) {
        if (d.has(sik)) continue;
        const v = ogr.map((o) => (o.cevaplar[i] === sik ? 1 : 0));
        if (v.reduce((a, b) => a + b, 0) >= alt) g.push([i, sik, v]);
      }
    });
    const r = [];
    for (let a = 0; a < g.length; a++) for (let b = a + 1; b < g.length; b++) {
      const [i1, s1, v1] = g[a], [i2, s2, v2] = g[b];
      if (i1 === i2) continue;
      let n11 = 0;
      for (let j = 0; j < n; j++) if (v1[j] && v2[j]) n11++;
      if (n11 < alt) continue;
      const n1 = v1.reduce((x, y) => x + y, 0), n2 = v2.reduce((x, y) => x + y, 0);
      const payda = Math.sqrt(n1 * (n - n1) * n2 * (n - n2));
      if (payda === 0) continue;
      const phi = (n * n11 - n1 * n2) / payda;
      const kosullu = n11 / n1, taban = n2 / n;
      if (phi >= 0.3 && kosullu >= 1.5 * taban) {
        const p = fisherUst(n11, n1, n2, n);
        if (p <= 0.01) r.push({ soru1: i1 + 1, sik1: s1, soru2: i2 + 1, sik2: s2, birlikte: n11, secen1: n1, secen2: n2, kosullu, taban, phi, p });
      }
    }
    return r.sort((x, y) => y.phi - x.phi || y.birlikte - x.birlikte || x.soru1 - y.soru1 || x.soru2 - y.soru2).slice(0, enFazla);
  }

  // ------------------------------------------------------------------ sınav yapısı
  function jacobi(m, enFazla = 500) {
    const n = m.length;
    const a = m.map((r) => r.slice());
    const v = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));
    for (let d = 0; d < enFazla; d++) {
      let enb = 0, p = 0, q = 1;
      for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (Math.abs(a[i][j]) > enb) { enb = Math.abs(a[i][j]); p = i; q = j; }
      if (enb < 1e-12) break;
      const th = 0.5 * Math.atan2(2 * a[p][q], a[q][q] - a[p][p]);
      const c = Math.cos(th), s = Math.sin(th);
      for (let k = 0; k < n; k++) { const akp = a[k][p], akq = a[k][q]; a[k][p] = c * akp - s * akq; a[k][q] = s * akp + c * akq; }
      for (let k = 0; k < n; k++) { const apk = a[p][k], aqk = a[q][k]; a[p][k] = c * apk - s * aqk; a[q][k] = s * apk + c * aqk; }
      for (let k = 0; k < n; k++) { const vkp = v[k][p], vkq = v[k][q]; v[k][p] = c * vkp - s * vkq; v[k][q] = s * vkp + c * vkq; }
    }
    const deg = a.map((r, i) => r[i]);
    const sira = deg.map((_, i) => i).sort((x, y) => deg[y] - deg[x]);
    return [sira.map((i) => deg[i]), sira.map((i) => { let vec = v.map((r) => r[i]); if (vec.reduce((s, x) => s + x, 0) < 0) vec = vec.map((x) => -x); return vec; })];
  }
  function sinavYapisi(sonuc) {
    const tam = sonuc.soru_puanlari.map((p) => p.sayi());
    let sec = [];
    sonuc.anahtar.sorular.forEach((s, i) => { if (s.durum !== "iptal" && (sonuc.klasik || OS.dogruKume(s).size) && tam[i] > 0) sec.push(i); });
    const ogr = sonuc.ogrenciler;
    if (ogr.length < 10) return null;
    const sutun = new Map(sec.map((i) => [i, ogr.map((o) => o.sorular[i].puan.sayi() / tam[i])]));
    sec = sec.filter((i) => pvariance(sutun.get(i)) > 0);
    const k = sec.length;
    if (k < 3) return null;
    const r = (x, y) => {
      const mx = fmean(x), my = fmean(y);
      let sxx = 0, syy = 0, sxy = 0;
      for (let i = 0; i < x.length; i++) { sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; }
      for (let i = 0; i < x.length; i++) sxy += (x[i] - mx) * (y[i] - my);
      return sxy / Math.sqrt(sxx * syy);
    };
    const m = Array.from({ length: k }, (_, a) => Array.from({ length: k }, (_, b) => (a === b ? 1 : r(sutun.get(sec[a]), sutun.get(sec[b])))));
    const [deg, vek] = jacobi(m);
    const yukler = new Map(sec.map((i, j) => [i + 1, vek[0][j] * Math.sqrt(Math.max(deg[0], 0))]));
    const ciftler = [];
    for (let a = 0; a < k; a++) for (let b = a + 1; b < k; b++) ciftler.push(m[a][b]);
    const ortR = fmean(ciftler);
    const oran = deg[1] > 1e-12 ? deg[0] / deg[1] : null;
    const zayif = [...yukler].filter(([, y]) => y < 0.2).map(([no]) => no).sort((p, q) => p - q);
    const kodlar = new Map();
    sec.forEach((i, j) => { for (const kod of sonuc.anahtar.sorular[i].ogrenme_ciktilari || []) { if (!kodlar.has(kod)) kodlar.set(kod, []); kodlar.get(kod).push(j); } });
    const uyum = [];
    for (const kod of [...kodlar.keys()].sort(OS.dogalKarsilastir)) {
      const ic = kodlar.get(kod);
      const dis = Array.from({ length: k }, (_, j) => j).filter((j) => !ic.includes(j));
      if (ic.length < 2 || !dis.length) continue;
      const icv = [];
      ic.forEach((a, x) => { for (const b of ic.slice(x + 1)) icv.push(m[a][b]); });
      const disv = [];
      for (const a of ic) for (const b of dis) disv.push(m[a][b]);
      uyum.push([kod, fmean(icv), fmean(disv), ic.length]);
    }
    let yorum;
    if (oran !== null && oran >= 3) yorum = "Sınav büyük ölçüde tek bir beceriyi ölçüyor (birinci bileşen ikinciden en az 3 kat güçlü); toplam puan anlamlı bir özet.";
    else if (oran !== null && oran >= 1.5) yorum = "Sınavda baskın bir ortak beceri var ama sorular birkaç ayrı konuya da dağılıyor; öğrenme çıktısı bazında bakmak toplam puandan daha bilgilendirici olabilir.";
    else yorum = "Sorular büyük ölçüde birbirinden bağımsız davranıyor; sınav ortak bir beceriden çok ayrı ayrı konuları ölçüyor. Toplam puan bu durumda kaba bir özettir.";
    return { sorular: sec.map((i) => i + 1), ozdegerler: deg, ilk_pay: deg[0] / k, oran_1_2: oran, ortalama_korelasyon: ortR, yukler, zayif_sorular: zayif, cikti_uyumu: uyum, yorum };
  }

  // ------------------------------------------------------------------ dönem sonu notu
  const ORNEK_MUTLAK = "AA 90, BA 85, BB 75, CB 70, CC 60, DC 55, DD 50, FD 40, FF 0";
  const ORNEK_BAGIL = "AA 63, BA 58, BB 53, CB 48, CC 43, DC 38, DD 33, FD 28, FF 0";
  const GECEN = "AA, BA, BB, CB, CC, DC, DD";
  const harfAyarlari = (d = {}) => Object.assign({ yontem: "mutlak", mutlak: ORNEK_MUTLAK, bagil: ORNEK_BAGIL, bagil_en_az: 30, gecen: GECEN }, d || {});
  function tabloCoz(m) {
    const t = [];
    for (let p of String(m).split(/[,;\n]+/)) {
      p = p.trim();
      if (!p) continue;
      const x = /^([A-Za-zÇĞİÖŞÜçğıöşü]{1,3})\s*[:=]?\s*(-?\d+(?:[.,]\d+)?)$/.exec(p);
      if (!x) throw new Error(`Harf tablosunda anlaşılamayan parça: '${p}'. Örnek yazım: AA 90, BA 85`);
      t.push([x[1].toLocaleUpperCase("tr"), parseFloat(x[2].replace(",", "."))]);
    }
    if (!t.length) throw new Error("Harf tablosu boş.");
    return t.sort((a, b) => b[1] - a[1]);
  }
  function harfBul(d, tablo) {
    for (let i = 0; i < tablo.length; i++) {
      const [h, alt] = tablo[i];
      if (d >= alt - 1e-9) {
        let sinir = "";
        if (i > 0) { const [uh, ust] = tablo[i - 1]; if (ust - d <= 1 + 1e-9) sinir = `${uh} için ${OS.pyOndalik(ust - d, 2).replace(".", ",")} eksik`; }
        return [h, sinir];
      }
    }
    return [tablo[tablo.length - 1][0], ""];
  }
  const g = (x) => (Number.isInteger(x) ? String(x) : String(x));
  function donemSonu(sonuc, finaller, araAgirlik, finalAlt, gecme, ayar) {
    ayar = harfAyarlari(ayar);
    const mutlak = tabloCoz(ayar.mutlak), bagil = tabloCoz(ayar.bagil);
    const gecen = new Set(String(ayar.gecen).split(/[,;\s]+/).map((h) => h.trim().toLocaleUpperCase("tr")).filter((h) => h));
    const w = Kesir.ondaliktan(String(araAgirlik));
    const satir = sonuc.ogrenciler.map((o) => {
      const ham = finaller[o.no];
      let f = null;
      if (ham !== null && ham !== undefined && ham !== "") { try { f = Kesir.ondaliktan(String(ham)); } catch (_) { f = null; } }
      const h = f === null ? null : o.puan.carp(w).bol(100).ekle(f.carp(new Kesir(100n).cikar(w)).bol(100));
      return [o, f, h];
    });
    const grup = satir.filter(([, f]) => f !== null && f.sayi() >= finalAlt).map(([, , h]) => h.sayi());
    let uyg = ayar.yontem;
    const notlar = [];
    if (uyg === "bagil" && grup.length < Math.max(2, ayar.bagil_en_az)) { notlar.push(`Bağıl değerlendirmeye giren öğrenci sayısı (${grup.length}) ${ayar.bagil_en_az}'dan az; mutlak tablo uygulandı.`); uyg = "mutlak"; }
    const ort = grup.length ? fmean(grup) : null;
    const sd = grup.length > 1 ? stdev(grup) : null;
    if (uyg === "bagil" && !sd) { notlar.push("Ham notların standart sapması sıfır; mutlak tablo uygulandı."); uyg = "mutlak"; }
    const tablo = uyg === "bagil" ? bagil : mutlak;
    const enDusuk = tablo[tablo.length - 1][0];
    const sonucNotlar = satir.map(([o, f, h]) => {
      const ara = o.puan.sayi();
      if (f === null) return { no: o.no, ad: o.ad, ara, final: null, ham: null, t: null, harf: "", gecti: null, aciklama: "final girilmedi", sinirda: "" };
      const hs = h.sayi();
      if (f.sayi() < finalAlt) return { no: o.no, ad: o.ad, ara, final: f.sayi(), ham: hs, t: null, harf: enDusuk, gecti: false, aciklama: `final ${g(finalAlt)} altında`, sinirda: "" };
      let t = null, harf, sinir;
      if (uyg === "bagil") { t = 50 + (10 * (hs - ort)) / sd; [harf, sinir] = harfBul(t, bagil); } else [harf, sinir] = harfBul(hs, mutlak);
      const gecti = gecen.has(harf) && hs >= gecme - 1e-9;
      return { no: o.no, ad: o.ad, ara, final: f.sayi(), ham: hs, t, harf, gecti, aciklama: gecti || !gecen.has(harf) ? "" : `ortalama ${g(gecme)} altında`, sinirda: sinir };
    });
    const dagilim = {};
    for (const [h] of tablo) dagilim[h] = sonucNotlar.filter((n) => n.harf === h).length;
    return { notlar: sonucNotlar, uygulanan: uyg, ortalama: ort, standart_sapma: sd, bagil_grup: grup.length, dagilim, notlar_metin: notlar };
  }
  function tablodanFinalPuanlari(tablo) {
    const e = OS.eslemeTahminEt(tablo);
    if (e.no_sutun === null) return [{}, ["Numara sütunu bulunamadı."]];
    const baslik = e.baslik_satiri ? tablo[e.baslik_satiri - 1] : [];
    let sutun = null;
    const ADLAR = new Set(["final", "puan", "not", "finalpuani", "finalnotu", "yariyilsonu", "yariyilsonusinavi", "ysn"]);
    for (let j = 0; j < baslik.length; j++) { const sh = OS.sade(baslik[j]); if (j + 1 !== e.no_sutun && (ADLAR.has(sh) || sh.startsWith("final"))) { sutun = j; break; } }
    const notlar = [];
    const veri = tablo.slice(e.baslik_satiri || 0);
    const sayiMi = (x) => { if (typeof x === "number") return true; try { Kesir.ondaliktan(String(x)); return true; } catch (_) { return false; } };
    if (sutun === null) {
      const bas = Math.max(e.no_sutun, e.ad_sutun || 0, e.soyad_sutun || 0);
      const gen = Math.max(0, ...veri.map((s) => s.length));
      for (let j = bas; j < gen; j++) {
        if (veri.filter((s) => j < s.length && s[j] !== null && sayiMi(s[j])).length >= Math.max(1, Math.floor(veri.length / 2))) { sutun = j; notlar.push(`Final başlığı bulunamadı; ${j + 1}. sütun final puanı sayıldı.`); break; }
      }
    }
    if (sutun === null) return [{}, ["Final puanı sütunu bulunamadı."]];
    const r = {};
    for (const s of veri) {
      const no = OS.numaraNormalle(e.no_sutun - 1 < s.length ? s[e.no_sutun - 1] : null);
      if (!no || !/^\d+$/.test(no)) continue;
      const x = sutun < s.length ? s[sutun] : null;
      r[no] = x === null || x === undefined || x === "" ? null : String(x);
    }
    return [r, notlar];
  }

  // ------------------------------------------------------------------ öğrenci karnesi
  function karneler(sonuc, rapor, aciklamalar = {}) {
    const ogr = sonuc.ogrenciler, n = ogr.length;
    const ort = n ? fmean(ogr.map((o) => o.puan.sayi())) : 0;
    const r = (rapor || []).filter((c) => c.tur.startsWith("Öğrenme"));
    return ogr.map((o) => {
      const sira = 1 + ogr.filter((x) => x.puan.kars(o.puan) > 0).length;
      const yuzdelik = n ? ogr.filter((x) => x.puan.kars(o.puan) < 0).length / n : 0;
      const sorular = o.sorular.map((s, i) => {
        const q = sonuc.anahtar.sorular[i];
        return [i + 1, String(s.isaret).trim(), sonuc.klasik ? "" : q.durum === "iptal" ? "İptal" : q.dogru, s.durum, s.puan.sayi(), sonuc.soru_puanlari[i].sayi()];
      });
      const ciktilar = r.map((c) => [c.kod, aciklamalar[c.kod] || c.aciklama, c.ogrenci_yuzdeleri.get(o.no) || 0, c.sinif_yuzdesi || 0]);
      let guclu = ciktilar.filter((c) => c[2] - c[3] >= 10).map((c) => c[0]);
      let zayif = ciktilar.filter((c) => c[3] - c[2] >= 10).map((c) => c[0]);
      if (ciktilar.length && !guclu.length && !zayif.length) {
        const fark = (c) => c[2] - c[3];
        guclu = [ciktilar.reduce((a, b) => (fark(b) > fark(a) ? b : a))[0]];
        zayif = ciktilar.length > 1 ? [ciktilar.reduce((a, b) => (fark(b) < fark(a) ? b : a))[0]] : [];
      }
      return { no: o.no, ad: o.ad, puan: o.puan.sayi(), sira, ogrenci_sayisi: n, yuzdelik, sinif_ortalamasi: ort, sorular, ciktilar, guclu, gelismeli: zayif };
    });
  }
  const DURUM = { D: ["✓", "#1e7b34"], Y: ["✗", "#c0392b"], B: ["–", "#8a6d00"], I: ["İptal", "#666"], K: ["kısmi", "#2f5597"], "-": ["", "#666"] };
  function karneHtml(sonuc, sinav, aciklamalar = {}) {
    const e = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
    const v = (x, n = 1) => OS.pyOndalik(x, n).replace(".", ",");
    const esik = sonuc.ayarlar.basari_esigi;
    const rapor = OS.ogrenmeCiktisiRaporu(sonuc, esik, aciklamalar);
    const sayfalar = karneler(sonuc, rapor, aciklamalar).map((k) => {
      const sorular = k.sorular.map(([no, isaret, dogru, durum, alinan, tam]) => `<tr><td>${no}</td><td>${e(isaret) || "–"}</td><td>${e(dogru)}</td><td style="color:${DURUM[durum][1]};font-weight:600">${DURUM[durum][0]}</td><td>${v(alinan, 2)} / ${v(tam, 2)}</td></tr>`).join("");
      const ciktilar = k.ciktilar.map(([kod, ac, ogr, sinif]) => `<tr><td><b>${e(kod)}</b> ${e(ac)}</td><td class="cubuk"><div><i style="width:${Math.max(0, Math.min(100, ogr)).toFixed(0)}%"></i><s style="left:${Math.max(0, Math.min(100, sinif)).toFixed(0)}%"></s></div></td><td>%${v(ogr, 0)}</td><td class="soluk">%${v(sinif, 0)}</td></tr>`).join("");
      const yorum = [];
      if (k.guclu.length) yorum.push(`Sınıf ortalamasının belirgin üstünde olduğunuz çıktılar: <b>${k.guclu.map(e).join(", ")}</b>.`);
      if (k.gelismeli.length) yorum.push(`Üzerinde çalışmanız önerilen çıktılar: <b>${k.gelismeli.map(e).join(", ")}</b>.`);
      return `<section class="sayfa"><header><div><b>${e(sinav.ders_kodu)} ${e(sinav.ders_adi)}</b><br>${e(sinav.sinav_turu)} ${e(sinav.tarih)}</div><div class="sag"><b>${e(k.ad)}</b><br>${e(k.no)}</div></header>
<div class="kartlar"><div><b>${v(k.puan, 2)}</b><span>Puanınız</span></div><div><b>${v(k.sinif_ortalamasi, 1)}</b><span>Sınıf ortalaması</span></div><div><b>${k.sira} / ${k.ogrenci_sayisi}</b><span>Sıranız</span></div><div><b>%${v(k.yuzdelik * 100, 0)}</b><span>Sizden düşük alanlar</span></div></div>
${k.ciktilar.length ? `<h3>Öğrenme çıktıları</h3><table class="cikti"><tr><th>Çıktı</th><th>Başarınız (çizgi: sınıf ortalaması)</th><th>Siz</th><th>Sınıf</th></tr>${ciktilar}</table><p>${yorum.join(" ")}</p>` : ""}
<h3>Sorular</h3><table class="soru"><tr><th>Soru</th><th>Cevabınız</th><th>${sonuc.klasik ? "" : "Doğru cevap"}</th><th>Durum</th><th>Puan</th></tr>${sorular}</table></section>`;
    });
    return `<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>${e(sinav.ders_kodu)} öğrenci karneleri</title><style>
body{font:13px/1.4 -apple-system,"Segoe UI",Arial,sans-serif;color:#111;margin:0;background:#eee}
.sayfa{background:#fff;width:190mm;min-height:270mm;margin:10mm auto;padding:10mm;box-sizing:border-box;page-break-after:always}
header{display:flex;justify-content:space-between;border-bottom:2px solid #2f5597;padding-bottom:6px} .sag{text-align:right}
.kartlar{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:12px 0} .kartlar div{border:1px solid #ccd;border-radius:8px;padding:6px 8px}
.kartlar b{display:block;font-size:20px} .kartlar span{color:#666;font-size:11px}
table{border-collapse:collapse;width:100%} th,td{border-bottom:1px solid #ddd;padding:3px 6px;text-align:left} th{color:#555;font-weight:600}
table.soru td,table.soru th{text-align:center} .soluk{color:#777} h3{margin:14px 0 6px;font-size:14px;color:#2f5597}
.cubuk div{position:relative;height:10px;background:#eef;border-radius:5px;min-width:160px} .cubuk i{display:block;height:100%;background:#2f5597;border-radius:5px}
.cubuk s{position:absolute;top:-3px;width:2px;height:16px;background:#c0392b}
@media print{body{background:#fff} .sayfa{margin:0;width:auto;min-height:0} @page{size:A4;margin:12mm}}
</style></head><body>${sayfalar.join("")}</body></html>`;
  }

  Object.assign(OS, { fisherUst, kavramYanilgilari, sinavYapisi, harfAyarlari, tabloCoz, donemSonu, tablodanFinalPuanlari, karneler, karneHtml,
    ORNEK_MUTLAK, ORNEK_BAGIL });
})(typeof globalThis !== "undefined" ? globalThis : window);
