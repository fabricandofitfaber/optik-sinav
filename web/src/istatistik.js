/* Optik Sınav — tarayıcı sürümü: madde analizi, öğrenme çıktısı raporu ve ek istatistikler.
 * Python karşılıkları: src/optik_sinav/core/madde_analizi.py ve ek_istatistik.py (yöntem açıklamaları orada).
 */
(function (kok) {
  "use strict";
  const OS = kok.OS;
  const { SIKLAR, CIFT, fmean, pstdev, pvariance, stdev, variance, median, ceyrekler, v, Kesir, topla } = OS;

  function varsayilanEsikler(o = {}) {
    return Object.assign({ ayirt_edicilik_alt: 0.2, guclik_alt: 0.2, guclik_ust: 0.9, grup_orani: 0.27, celdirici_alt: 0.05,
      uyum_ust: 0.5, celdirici_fark: 0.1, basari_esigi: 50, cikti_esigi: 50 }, o);
  }
  const grupBoyu = (n, oran) => (n ? Math.max(1, Math.floor(n * oran + 0.5)) : 0);
  function pearson(x, y) {
    const n = x.length;
    if (n < 3) return null;
    const mx = fmean(x), my = fmean(y);
    let sxx = 0, syy = 0, sxy = 0;
    for (let i = 0; i < n; i++) { sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; }
    if (sxx <= 0 || syy <= 0) return null;
    for (let i = 0; i < n; i++) sxy += (x[i] - mx) * (y[i] - my);
    return sxy / Math.sqrt(sxx * syy);
  }
  function alfa(sutunlar) {
    const k = sutunlar.length;
    if (k < 2 || !sutunlar[0].length) return null;
    const toplam = sutunlar[0].map((_, j) => sutunlar.reduce((s, c) => s + c[j], 0));
    const vt = pvariance(toplam);
    if (vt <= 0) return null;
    return (k / (k - 1)) * (1 - sutunlar.reduce((s, c) => s + pvariance(c), 0) / vt);
  }
  function carpiklik(x) {
    const n = x.length;
    if (n < 3) return null;
    const m = fmean(x);
    const m2 = x.reduce((s, a) => s + (a - m) ** 2, 0) / n;
    if (m2 <= 0) return null;
    const m3 = x.reduce((s, a) => s + (a - m) ** 3, 0) / n;
    return (m3 / m2 ** 1.5) * Math.sqrt(n * (n - 1)) / (n - 2);
  }
  function basiklik(x) {
    const n = x.length;
    if (n < 4) return null;
    const m = fmean(x);
    const m2 = x.reduce((s, a) => s + (a - m) ** 2, 0) / n;
    if (m2 <= 0) return null;
    const m4 = x.reduce((s, a) => s + (a - m) ** 4, 0) / n;
    const g2 = m4 / m2 ** 2 - 3;
    return (((n + 1) * g2 + 6) * (n - 1)) / ((n - 2) * (n - 3));
  }

  function maddeAnalizi(sonuc, esikler) {
    const e = varsayilanEsikler(esikler);
    const ogr = sonuc.ogrenciler;
    const n = ogr.length;
    const anahtar = sonuc.anahtar;
    const K = anahtar.sorular.length;
    const klasik = sonuc.klasik;
    const tam = sonuc.soru_puanlari.map((p) => p.sayi());
    const analizde = [];
    anahtar.sorular.forEach((s, i) => { if (s.durum !== "iptal" && (klasik || OS.dogruKume(s).size) && tam[i] > 0) analizde.push(i); });
    const analizSet = new Set(analizde);
    let x = ogr.map((o) => Array.from({ length: K }, (_, i) => (tam[i] ? o.sorular[i].puan.sayi() / tam[i] : 0)));
    if (!klasik) x = ogr.map((o) => Array.from({ length: K }, (_, i) => (o.sorular[i].durum === "D" ? 1 : 0)));
    const puanM = ogr.map((o) => Array.from({ length: K }, (_, i) => o.sorular[i].puan.sayi()));
    const toplamDogru = x.map((s) => analizde.reduce((t, i) => t + s[i], 0));
    const toplamPuan = puanM.map((s) => analizde.reduce((t, i) => t + s[i], 0));

    const sirali = Array.from({ length: n }, (_, j) => j).sort((a, b) => {
      const c = ogr[b].puan.kars(ogr[a].puan);
      return c !== 0 ? c : toplamDogru[b] - toplamDogru[a];
    });
    const g = grupBoyu(n, e.grup_orani);
    const ust = g ? sirali.slice(0, g) : [];
    const alt = g ? sirali.slice(-g) : [];
    const artan = [...sirali].reverse();
    const besler = n >= 5 ? Array.from({ length: 5 }, (_, q) => artan.slice(Math.floor((n * q) / 5), Math.floor((n * (q + 1)) / 5))) : [];
    const sdT = n ? pstdev(toplamDogru) : 0;
    const sutunTumu = new Map(analizde.map((i) => [i, puanM.map((s) => s[i])]));
    const genelAlfa = n > 1 ? alfa(analizde.map((i) => sutunTumu.get(i))) : null;

    const kitGruplari = new Map();
    ogr.forEach((o, j) => { const b = o.kitapcik || anahtar.ana_kitapcik; if (!kitGruplari.has(b)) kitGruplari.set(b, []); kitGruplari.get(b).push(j); });
    const ana = kitGruplari.has(anahtar.ana_kitapcik) ? anahtar.ana_kitapcik : (kitGruplari.size ? [...kitGruplari.keys()][0] : anahtar.ana_kitapcik);
    const dogruSik = new Map([...kitGruplari.keys()].map((b) => [b, OS.kitapcikIcin(anahtar, b)[0].sorular.map(OS.dogruKume)]));

    function oranlar(isaretler) {
      const m = isaretler.length;
      const o = {};
      for (const s of SIKLAR) o[s] = m ? isaretler.filter((c) => c === s).length / m : 0;
      o["Çift"] = m ? isaretler.filter((c) => c === CIFT).length / m : 0;
      o["Boş"] = m ? isaretler.filter((c) => !SIKLAR.includes(c) && c !== CIFT).length / m : 0;
      return o;
    }
    const maddeler = [];
    let pqToplam = 0;
    anahtar.sorular.forEach((soru, i) => {
      const isaretler = ogr.map((o) => (i < o.cevaplar.length ? o.cevaplar[i] : " "));
      const kitOran = new Map();
      if (!klasik) for (const [b, js] of kitGruplari) kitOran.set(b, oranlar(js.map((j) => isaretler[j])));
      const oran = klasik ? {} : (kitOran.get(ana) || oranlar(isaretler));
      const kitOranCikti = kitOran.size > 1 ? Object.fromEntries(kitOran) : {};
      if (!analizSet.has(i) || n === 0) {
        maddeler.push({ soru_no: soru.no, dogru_sik: soru.dogru, analiz_disi: true, guclik: null, ayirt_edicilik: null, nokta_cift_serili: null,
          sik_oranlari: oran, sorunlar: [], tam_puan: tam[i], ortalama_puan: null, duzeltilmis_r: null, alfa_cikarilirsa: null, ust_grup: null, alt_grup: null,
          celdiriciler: [], bes_grup: [], kitapcik_sik_oranlari: kitOranCikti });
        return;
      }
      const sutun = x.map((s) => s[i]);
      const p = fmean(sutun);
      pqToplam += p * (1 - p);
      const ustO = ust.length ? fmean(ust.map((j) => sutun[j])) : null;
      const altO = alt.length ? fmean(alt.map((j) => sutun[j])) : null;
      const d = ustO !== null && altO !== null ? ustO - altO : null;
      let r = null;
      if (!klasik) {
        if (sdT > 0 && p > 0 && p < 1) {
          const m1 = fmean(toplamDogru.filter((_, j) => sutun[j]));
          const m0 = fmean(toplamDogru.filter((_, j) => !sutun[j]));
          r = ((m1 - m0) / sdT) * Math.sqrt(p * (1 - p));
        }
      } else r = pearson(sutun, toplamPuan);
      const kalan = toplamPuan.map((t, j) => t - puanM[j][i]);
      const rDuz = pearson(sutun, kalan);
      const alfaC = n > 1 ? alfa(analizde.filter((t) => t !== i).map((t) => sutunTumu.get(t))) : null;
      const bes = besler.map((grup) => (grup.length ? fmean(grup.map((j) => sutun[j])) : null));
      const sorunlar = [];
      if (d !== null && d < e.ayirt_edicilik_alt) sorunlar.push(`Ayırt edicilik düşük (${v(d, 2)})`);
      if (p < e.guclik_alt) sorunlar.push(`Çok zor (güçlük ${v(p, 2)})`);
      else if (p > e.guclik_ust) sorunlar.push(`Çok kolay (güçlük ${v(p, 2)})`);
      if (genelAlfa !== null && alfaC !== null && alfaC > genelAlfa + 0.01) sorunlar.push(`Soru çıkarılırsa güvenirlik artıyor (${v(genelAlfa, 2)} → ${v(alfaC, 2)})`);
      const celdiriciler = [];
      if (!klasik) {
        const dogrular = dogruSik.get(ana)[i];
        const enCokDogru = Math.max(0, ...[...dogrular].map((s) => oran[s]));
        const yanlisCok = [...SIKLAR].filter((s) => !dogrular.has(s) && oran[s] > enCokDogru);
        if (yanlisCok.length) sorunlar.push("Yanlış şık doğrudan çok seçilmiş: " + yanlisCok.join(", "));
        const anaJs = new Set(kitGruplari.get(ana) || []);
        const ustA = ust.filter((j) => anaJs.has(j)), altA = alt.filter((j) => anaJs.has(j));
        for (const s of SIKLAR) {
          if (dogrular.has(s)) continue;
          const uo = ustA.length ? ustA.filter((j) => isaretler[j] === s).length / ustA.length : 0;
          const ao = altA.length ? altA.filter((j) => isaretler[j] === s).length / altA.length : 0;
          const c = { sik: s, oran: oran[s], ust: uo, alt: ao, sorunlar: [] };
          if (oran[s] < e.celdirici_alt) c.sorunlar.push("işlemiyor (çok az seçilmiş)");
          if (uo - ao >= e.celdirici_fark && oran[s] >= e.celdirici_alt) c.sorunlar.push("üst grup alt gruptan çok seçmiş");
          celdiriciler.push(c);
        }
        const ustDogru = ustA.length ? ustA.filter((j) => dogrular.has(isaretler[j])).length / ustA.length : 0;
        for (const c of celdiriciler) {
          if (c.ust >= 0.4 && c.ust > ustDogru) {
            c.sorunlar.push("olası anahtar hatası");
            sorunlar.unshift(`Olası anahtar hatası: en başarılı öğrencilerin %${pyRound0(c.ust * 100)}'i ${c.sik} şıkkını seçmiş, anahtardaki ${[...dogrular].sort().join("")} şıkkını %${pyRound0(ustDogru * 100)}`);
          }
        }
        const ters = celdiriciler.filter((c) => c.sorunlar.includes("üst grup alt gruptan çok seçmiş")).map((c) => c.sik);
        if (ters.length) sorunlar.push("Üst grubu yanıltan çeldirici: " + ters.join(", "));
      }
      maddeler.push({ soru_no: soru.no, dogru_sik: soru.dogru, analiz_disi: false, guclik: p, ayirt_edicilik: d, nokta_cift_serili: r, sik_oranlari: oran,
        sorunlar, tam_puan: tam[i], ortalama_puan: fmean(sutunTumu.get(i)), duzeltilmis_r: rDuz, alfa_cikarilirsa: alfaC, ust_grup: ustO, alt_grup: altO,
        celdiriciler, bes_grup: bes, kitapcik_sik_oranlari: kitOranCikti });
    });

    const puanlar = ogr.map((o) => o.puan.sayi());
    const k = analizde.length;
    const varT = sdT ** 2;
    const kr20 = !klasik && k > 1 && varT > 0 ? (k / (k - 1)) * (1 - pqToplam / varT) : null;
    const sd = n > 1 ? stdev(puanlar) : null;
    const cey = n > 1 ? ceyrekler(puanlar) : null;
    const analizli = maddeler.filter((m) => !m.analiz_disi);
    const ayirtlar = analizli.filter((m) => m.ayirt_edicilik !== null);
    const kitSay = {}, kitOrt = {};
    for (const b of [...kitGruplari.keys()].sort()) { const js = kitGruplari.get(b); kitSay[b] = js.length; if (js.length) kitOrt[b] = fmean(js.map((j) => puanlar[j])); }
    const genel = {
      ogrenci_sayisi: n, ortalama: n ? fmean(puanlar) : null, standart_sapma: sd, en_dusuk: n ? Math.min(...puanlar) : null, en_yuksek: n ? Math.max(...puanlar) : null,
      medyan: n ? median(puanlar) : null, kr20, analizdeki_soru_sayisi: k, birinci_ceyrek: cey ? cey[0] : null, ucuncu_ceyrek: cey ? cey[2] : null,
      carpiklik: carpiklik(puanlar), basiklik: basiklik(puanlar), alfa: genelAlfa,
      olcme_hatasi: sd !== null && genelAlfa !== null ? sd * Math.sqrt(Math.max(0, 1 - genelAlfa)) : null,
      basari_orani: n ? puanlar.filter((p) => p >= e.basari_esigi).length / n : null, basari_esigi: e.basari_esigi,
      ortalama_guclik: analizli.length ? fmean(analizli.map((m) => m.guclik)) : null,
      ortalama_ayirt_edicilik: ayirtlar.length ? fmean(ayirtlar.map((m) => m.ayirt_edicilik)) : null,
      kitapcik_sayilari: kitSay, kitapcik_ortalamalari: kitOrt, bos_orani_sirayla: [], hiz_uyarisi: "", kisi_uyumu: [], benzer_ciftler: [], yorumlar: [],
    };
    [genel.bos_orani_sirayla, genel.hiz_uyarisi] = hizAnalizi(sonuc);
    if (!klasik && k >= 4) {
      const pSoru = new Map(analizde.map((i) => [i, fmean(x.map((s) => s[i]))]));
      genel.kisi_uyumu = kisiUyumu(sonuc, x, analizde, pSoru, e.uyum_ust);
      genel.benzer_ciftler = benzerCiftler(sonuc, analizde, dogruSik);
    }
    genel.yorumlar = yorumlar(genel, maddeler, sonuc, e);
    return [maddeler, genel];
  }
  const pyRound0 = (x) => OS.pyOndalik(x, 0);

  function hizAnalizi(sonuc) {
    const n = sonuc.anahtar.sorular.length;
    if (!sonuc.ogrenciler.length || n < 4) return [[], ""];
    const bos = Array(n).fill(0);
    for (const o of sonuc.ogrenciler) {
      const kaynak = o.kaynak_soru && o.kaynak_soru.length ? o.kaynak_soru : Array.from({ length: n }, (_, i) => i + 1);
      o.sorular.forEach((s, i) => { if (s.durum === "B" && s.isaret !== CIFT) bos[kaynak[i] - 1]++; });
    }
    const oran = bos.map((b) => b / sonuc.ogrenciler.length);
    const ceyrek = Math.max(1, Math.floor(n / 4));
    const son = fmean(oran.slice(-ceyrek));
    const once = n > ceyrek ? fmean(oran.slice(0, -ceyrek)) : 0;
    let uyari = "";
    if (son >= 0.1 && son >= 2 * Math.max(once, 0.01)) uyari = `Son ${ceyrek} soruda boş bırakma oranı %${pyRound0(son * 100)}, öncekilerde %${pyRound0(once * 100)}. Süre yetmemiş olabilir.`;
    return [oran, uyari];
  }
  function kisiUyumu(sonuc, x, analizde, pSoru, esik) {
    const sira = [...analizde].sort((a, b) => pSoru.get(b) - pSoru.get(a));
    const ps = sira.map((i) => pSoru.get(i));
    const r = [];
    sonuc.ogrenciler.forEach((o, j) => {
      const u = sira.map((i) => x[j][i]);
      const top = u.reduce((s, a) => s + a, 0);
      if (top === 0 || top === sira.length) return;
      const payda = ps.slice(0, top).reduce((s, a) => s + a, 0) - ps.slice(-top).reduce((s, a) => s + a, 0);
      if (payda <= 0) return;
      let pay = 0;
      for (let t = 0; t < top; t++) pay += (1 - u[t]) * ps[t];
      let ek = 0;
      for (let t = top; t < sira.length; t++) ek += u[t] * ps[t];
      const indeks = (pay - ek) / payda;
      if (indeks > esik) {
        const b = new Set();
        for (let t = 0; t < top; t++) if (!u[t]) b.add(sira[t] + 1);
        for (let t = top; t < sira.length; t++) if (u[t]) b.add(sira[t] + 1);
        r.push({ no: o.no, ad: o.ad, puan: o.puan.sayi(), indeks, beklenmedik: [...b].sort((a, c) => a - c) });
      }
    });
    return r.sort((a, b) => b.indeks - a.indeks);
  }
  function benzerCiftler(sonuc, analizde, dogruSik, enFazla = 15) {
    const ogr = sonuc.ogrenciler;
    const ana = sonuc.anahtar.ana_kitapcik;
    const kayit = [];
    for (let a = 0; a < ogr.length; a++) for (let b = a + 1; b < ogr.length; b++) {
      const oa = ogr[a], ob = ogr[b];
      if ((oa.kitapcik || ana) !== (ob.kitapcik || ana)) continue;
      const dogru = dogruSik.get(oa.kitapcik || ana) || [...dogruSik.values()][0];
      let ay = 0, iy = 0, ac = 0;
      const sorular = [];
      for (const i of analizde) {
        const ca = oa.cevaplar[i], cb = ob.cevaplar[i];
        const ya = SIKLAR.includes(ca) && ca !== "" && !dogru[i].has(ca);
        const yb = SIKLAR.includes(cb) && cb !== "" && !dogru[i].has(cb);
        if (ca === cb) ac++;
        if (ya && yb) { iy++; if (ca === cb) { ay++; sorular.push(i + 1); } }
      }
      kayit.push([a, b, ay, iy, ac, sorular]);
    }
    if (kayit.length < 10) return [];
    const deg = kayit.map((k) => k[2]);
    const ort = fmean(deg), sd = pstdev(deg);
    if (sd <= 0) return [];
    const altSinir = Math.max(4, Math.ceil(0.3 * analizde.length));
    const sec = [];
    for (const [a, b, ay, iy, ac, sorular] of kayit) {
      const z = (ay - ort) / sd;
      if (ay >= altSinir && z >= 4) sec.push({ no1: ogr[a].no, ad1: ogr[a].ad, no2: ogr[b].no, ad2: ogr[b].ad, ayni_yanlis: ay, ikisi_yanlis: iy, ayni_cevap: ac, z, sorular });
    }
    return sec.sort((p, q) => q.ayni_yanlis - p.ayni_yanlis || q.z - p.z).slice(0, enFazla);
  }
  function yorumlar(g, maddeler, sonuc, e) {
    const y = [];
    if (!g.ogrenci_sayisi) return y;
    y.push(`Sınıf ortalaması ${v(g.ortalama)}, ortanca ${v(g.medyan)}. ${fmtG(e.basari_esigi)} ve üstü alan öğrenci oranı %${pyRound0(g.basari_orani * 100)}.`);
    if (g.carpiklik !== null) {
      if (g.carpiklik > 0.5) y.push("Puanlar düşük tarafta yığılmış (sağa çarpık): sınav sınıf için zor gelmiş.");
      else if (g.carpiklik < -0.5) y.push("Puanlar yüksek tarafta yığılmış (sola çarpık): sınav sınıf için kolay gelmiş.");
      else y.push("Puan dağılımı ortaya göre dengeli.");
    }
    const r = g.alfa !== null ? g.alfa : g.kr20;
    if (r !== null) {
      const d = r >= 0.8 ? "yüksek" : r >= 0.7 ? "kabul edilebilir" : r >= 0.6 ? "sınırda" : "düşük";
      y.push(`Güvenirlik katsayısı ${v(r, 2)} (${d}). Ölçmenin standart hatası yaklaşık ±${v(g.olcme_hatasi || 0)} puan; bir öğrencinin puanı ölçme hatası yüzünden bu kadar oynayabilir.`);
    }
    const sorunlu = maddeler.filter((m) => m.sorunlar.length).map((m) => m.soru_no);
    if (sorunlu.length) y.push(`Gözden geçirilmesi önerilen sorular: ${sorunlu.join(", ")} (ayrıntı Madde Analizi sayfasında).`);
    if (g.hiz_uyarisi) y.push(g.hiz_uyarisi);
    const ko = Object.entries(g.kitapcik_ortalamalari);
    if (ko.length > 1) y.push("Kitapçık ortalamaları: " + ko.map(([b, x]) => `${b} ${v(x)} (${g.kitapcik_sayilari[b]} kişi)`).join(", ") + ".");
    if (g.kisi_uyumu.length) y.push(`${g.kisi_uyumu.length} öğrencide beklenmedik cevap örüntüsü var (kolay soruları kaçırıp zorları bilmiş). Okuma hatası, dikkatsizlik ya da şans olabilir; Kişi Uyumu sayfasına bakın.`);
    if (g.benzer_ciftler.length) y.push(`${g.benzer_ciftler.length} öğrenci çiftinde sınıf geneline göre olağandışı sayıda aynı yanlış şık var. Bu tek başına kopya kanıtı değildir; oturma düzeniyle birlikte değerlendirin.`);
    return y;
  }
  /** Python "{x:g}" (yalnızca eşik gibi basit sayılar için). */
  function fmtG(x) { return Number.isInteger(x) ? String(x) : String(x); }

  // ------------------------------------------------------------------ öğrenme çıktısı
  function ciktiDagilimiSinav(anahtar, puanlar) {
    const toplam = topla(puanlar);
    const pay = new Map();
    if (toplam.sifirMi()) return pay;
    anahtar.sorular.forEach((s, i) => {
      for (const [kod, y] of OS.ciktiDagilimi(s)) pay.set(kod, (pay.get(kod) || Kesir.SIFIR).ekle(puanlar[i].carp(new Kesir(BigInt(y), 100n))));
    });
    const kodlar = [...pay.keys()].sort(OS.dogalKarsilastir);
    return new Map(kodlar.map((k) => [k, pay.get(k).bol(toplam).carp(100)]));
  }
  function tamSayiDagilim(d) {
    if (!d.size) return new Map();
    const toplam = topla([...d.values()]);
    const hedef = OS.kesirYuvarlaCift(toplam);
    const taban = new Map([...d].map(([k, x]) => [k, x.taban()]));
    let kalan = hedef - [...taban.values()].reduce((s, a) => s + a, 0n);
    const sira = [...d.keys()].sort((a, b) => d.get(b).cikar(new Kesir(taban.get(b))).kars(d.get(a).cikar(new Kesir(taban.get(a)))));
    for (const k of sira.slice(0, Math.max(0, Number(kalan)))) taban.set(k, taban.get(k) + 1n);
    return new Map([...taban].map(([k, x]) => [k, Number(x)]));
  }
  function ciktiDenetimi(anahtar, dersCiktilari = null) {
    const hatalar = [], bilgiler = [];
    if (!anahtar.sorular.some((s) => (s.ogrenme_ciktilari || []).length)) return [hatalar, bilgiler];
    const ciktisiz = anahtar.sorular.filter((s) => !(s.ogrenme_ciktilari || []).length && s.durum !== "iptal").map((s) => s.no);
    if (ciktisiz.length) hatalar.push("Öğrenme çıktısı seçilmemiş sorular: " + ciktisiz.join(", "));
    const yuzEtmeyen = [];
    for (const s of anahtar.sorular) {
      const d = OS.ciktiDagilimi(s);
      const t = [...d.values()].reduce((a, b) => a + b, 0);
      if (d.size && t !== 100) yuzEtmeyen.push(`${s.no} (%${t})`);
      if ([...d.values()].some((x) => x < 0)) yuzEtmeyen.push(`${s.no} (eksi yüzde)`);
    }
    if (yuzEtmeyen.length) hatalar.push("Çıktı yüzdeleri 100 etmeyen sorular: " + yuzEtmeyen.join(", "));
    if (dersCiktilari && dersCiktilari.length) {
      const bilinen = new Set(dersCiktilari);
      const yabanci = [...new Set(anahtar.sorular.flatMap((s) => s.ogrenme_ciktilari || []).filter((k) => !bilinen.has(k)))].sort(OS.dogalKarsilastir);
      if (yabanci.length) hatalar.push("Ders bilgi paketinde olmayan çıktı kodları: " + yabanci.join(", "));
      const kullanilan = new Set(anahtar.sorular.flatMap((s) => s.ogrenme_ciktilari || []));
      const olculmeyen = dersCiktilari.filter((k) => !kullanilan.has(k));
      if (olculmeyen.length) bilgiler.push("Bu sınavda ölçülmeyen ders çıktıları: " + olculmeyen.join(", "));
    }
    return [hatalar, bilgiler];
  }
  function ogrenmeCiktisiRaporu(sonuc, esik = 50, aciklamalar = {}) {
    const rapor = [];
    const toplamPuan = topla(sonuc.soru_puanlari);
    for (const [tur, alan] of [["Öğrenme çıktısı", "ogrenme_ciktilari"], ["Program çıktısı", "program_ciktilari"]]) {
      const ag = new Map();
      sonuc.anahtar.sorular.forEach((s, i) => {
        if (alan === "ogrenme_ciktilari") {
          for (const [kod, y] of OS.ciktiDagilimi(s)) { if (!ag.has(kod)) ag.set(kod, new Map()); ag.get(kod).set(i, new Kesir(BigInt(y), 100n)); }
        } else for (let kod of s.program_ciktilari || []) { kod = kod.trim(); if (kod) { if (!ag.has(kod)) ag.set(kod, new Map()); ag.get(kod).set(i, new Kesir(1n)); } }
      });
      for (const kod of [...ag.keys()].sort(OS.dogalKarsilastir)) {
        const w = ag.get(kod);
        const olasi = topla([...w].map(([i, a]) => sonuc.soru_puanlari[i].carp(a)));
        const ogrenci = new Map();
        for (const o of sonuc.ogrenciler) {
          const alinan = topla([...w].map(([i, a]) => o.sorular[i].puan.carp(a)));
          ogrenci.set(o.no, olasi.sifirMi() ? 0 : alinan.bol(olasi).carp(100).sayi());
        }
        const vals = [...ogrenci.values()];
        rapor.push({ kod, tur, sorular: [...w.keys()].sort((a, b) => a - b).map((i) => i + 1), sinif_yuzdesi: vals.length ? fmean(vals) : null,
          ogrenci_yuzdeleri: ogrenci, sinav_agirligi: !toplamPuan.sifirMi() && alan === "ogrenme_ciktilari" ? olasi.bol(toplamPuan).carp(100).sayi() : 0,
          ulasan_orani: vals.length ? vals.filter((x) => x >= esik).length / vals.length : null, aciklama: aciklamalar[kod] || "" });
      }
    }
    return rapor;
  }

  // ------------------------------------------------------------------ ek istatistikler
  function sinirdakiOgrenciler(sonuc, esik, olcmeHatasi) {
    const pay = olcmeHatasi && olcmeHatasi > 0 ? olcmeHatasi : 5;
    return sonuc.ogrenciler.map((o) => ({ no: o.no, ad: o.ad, puan: o.puan.sayi(), fark: o.puan.sayi() - esik }))
      .filter((x) => Math.abs(x.fark) <= pay).sort((a, b) => a.fark - b.fark);
  }
  function finalGereken(sonuc, araAgirlik, gecme = 50, finalAlt = 50) {
    if (!(araAgirlik > 0 && araAgirlik < 100)) return [];
    const fw = (100 - araAgirlik) / 100;
    const r = sonuc.ogrenciler.map((o) => {
      const p = o.puan.sayi();
      let g = Math.max(finalAlt, (gecme - (p * araAgirlik) / 100) / fw, 0);
      g = Math.ceil(g * 100 - 1e-9) / 100;
      return { no: o.no, ad: o.ad, puan: p, gereken: g > 100 ? null : g };
    });
    return r.sort((a, b) => {
      const ka = [a.gereken === null ? 1 : 0, -(a.gereken || 0)], kb = [b.gereken === null ? 1 : 0, -(b.gereken || 0)];
      return ka[0] - kb[0] || ka[1] - kb[1];
    });
  }
  function sansPuani(sonuc, sikSayisi = 5) {
    if (sonuc.klasik) return null;
    const a = sonuc.ayarlar;
    let b = 0;
    sonuc.anahtar.sorular.forEach((s, i) => {
      const p = sonuc.soru_puanlari[i].sayi();
      if (s.durum === "iptal") { b += p; return; }
      const ol = OS.dogruKume(s).size / sikSayisi;
      b += p * ol;
      if (a.yanlis_cezasi && a.ceza_orani > 0) b -= (p / a.ceza_orani) * (1 - ol);
    });
    return Math.max(0, b);
  }
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
  function betaDuzenli(a, b, x) {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    const ln = lgamma(a + b) - lgamma(a) - lgamma(b) + a * Math.log(x) + b * Math.log(1 - x);
    if (x > (a + 1) / (a + b + 2)) return 1 - betaDuzenli(b, a, 1 - x);
    const k0 = 1e-300;
    let c = 1, d = 1 - ((a + b) * x) / (a + 1);
    d = 1 / (Math.abs(d) > k0 ? d : k0);
    let f = d;
    for (let m = 1; m < 300; m++) {
      for (const cift of [true, false]) {
        const k = cift ? (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m)) : (-(a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1));
        d = 1 + k * d; d = 1 / (Math.abs(d) > k0 ? d : k0);
        c = 1 + k / c; c = Math.abs(c) > k0 ? c : k0;
        f *= c * d;
      }
      if (Math.abs(c * d - 1) < 1e-12) break;
    }
    return (Math.exp(ln) * f) / a;
  }
  const tIkiYonluP = (t, sd) => betaDuzenli(sd / 2, 0.5, sd / (sd + t * t));
  function kitapcikKarsilastirma(sonuc) {
    const gr = new Map();
    for (const o of sonuc.ogrenciler) { const b = o.kitapcik || sonuc.anahtar.ana_kitapcik; if (!gr.has(b)) gr.set(b, []); gr.get(b).push(o.puan.sayi()); }
    const adlar = [...gr.keys()].filter((k) => gr.get(k).length >= 2).sort();
    if (adlar.length < 2) return null;
    const a = gr.get(adlar[0]), b = gr.get(adlar[1]);
    const m1 = fmean(a), m2 = fmean(b), v1 = variance(a), v2 = variance(b);
    const se = Math.sqrt(v1 / a.length + v2 / b.length);
    if (se === 0) return null;
    const t = (m1 - m2) / se;
    const sd = (v1 / a.length + v2 / b.length) ** 2 / ((v1 / a.length) ** 2 / (a.length - 1) + (v2 / b.length) ** 2 / (b.length - 1));
    const bir = Math.sqrt(((a.length - 1) * v1 + (b.length - 1) * v2) / (a.length + b.length - 2));
    return { kitapcik1: adlar[0], kitapcik2: adlar[1], n1: a.length, n2: b.length, ortalama1: m1, ortalama2: m2, fark: m1 - m2, t, serbestlik: sd, p: tIkiYonluP(t, sd), etki: bir ? (m1 - m2) / bir : 0 };
  }
  function siraNumaralari(x) {
    const s = x.map((_, i) => i).sort((a, b) => x[a] - x[b]);
    const r = Array(x.length).fill(0);
    let i = 0;
    while (i < s.length) {
      let j = i;
      while (j + 1 < s.length && x[s[j + 1]] === x[s[i]]) j++;
      for (let t = i; t <= j; t++) r[s[t]] = (i + j) / 2 + 1;
      i = j + 1;
    }
    return r;
  }
  function spearman(x, y) {
    if (x.length < 3) return null;
    const rx = siraNumaralari(x), ry = siraNumaralari(y);
    const mx = fmean(rx), my = fmean(ry);
    let sxx = 0, syy = 0, sxy = 0;
    for (let i = 0; i < rx.length; i++) { sxx += (rx[i] - mx) ** 2; syy += (ry[i] - my) ** 2; }
    if (!sxx || !syy) return null;
    for (let i = 0; i < rx.length; i++) sxy += (rx[i] - mx) * (ry[i] - my);
    return sxy / Math.sqrt(sxx * syy);
  }
  function tasarimDenetimi(sonuc, guclukler) {
    if (sonuc.klasik) return null;
    const h = sonuc.anahtar.sorular.map((s) => (s.durum !== "iptal" ? (s.dogru || "").slice(0, 1) : ""));
    const say = {};
    for (const c of SIKLAR) say[c] = h.filter((x) => x === c).length;
    let enUzun = 0, harf = "", bas = 0, i = 0;
    while (i < h.length) {
      let j = i;
      while (j + 1 < h.length && h[j + 1] === h[i] && h[i]) j++;
      if (h[i] && j - i + 1 > enUzun) { enUzun = j - i + 1; harf = h[i]; bas = i + 1; }
      i = j + 1;
    }
    const cift = guclukler.map((g, k) => [k + 1, g]).filter(([, g]) => g !== null && g !== undefined);
    const r = cift.length >= 3 ? spearman(cift.map((c) => c[0]), cift.map((c) => c[1])) : null;
    const notlar = [];
    const n = h.filter((x) => x).length;
    if (n >= 10) {
      const bek = n / 5;
      const az = [...SIKLAR].filter((c) => say[c] < bek / 2), cok = [...SIKLAR].filter((c) => say[c] > bek * 1.8);
      if (az.length || cok.length) notlar.push("Doğru şıklar dengesiz dağılmış: " + [...SIKLAR].map((c) => `${c} ${say[c]} kez`).join(", ") + ". Öğrenciler en çok ya da en az kullanılan harfe göre tahmin yürütebilir.");
    }
    if (enUzun >= 3) notlar.push(`${bas}. sorudan başlayarak ${enUzun} soru art arda ${harf} şıkkı doğru.`);
    if (r !== null) {
      if (r < -0.4) notlar.push("Sorular sona doğru zorlaşıyor (kolaydan zora sıralanmış).");
      else if (r > 0.4) notlar.push("Sorular sona doğru kolaylaşıyor; zor sorular başta öğrencinin moralini bozabilir.");
      else notlar.push("Soru sırası ile güçlük arasında belirgin bir ilişki yok (karışık sıralanmış).");
    }
    return { sik_sayilari: say, en_uzun_seri: enUzun, seri_harfi: harf, seri_baslangic: bas, sira_guclik_korelasyonu: r, notlar };
  }
  function rasch(sonuc, enFazla = 200) {
    if (sonuc.klasik) return null;
    let sorular = [];
    sonuc.anahtar.sorular.forEach((s, i) => { if (s.durum !== "iptal" && OS.dogruKume(s).size) sorular.push(i); });
    let x = new Map();
    for (const o of sonuc.ogrenciler) x.set(o.no, sorular.map((i) => (o.sorular[i].durum === "D" ? 1 : 0)));
    const disaridaSoru = [];
    let kisiler, sutun;
    for (;;) {
      const k = sorular.length;
      kisiler = new Map([...x].filter(([, v2]) => { const t = v2.reduce((a, b) => a + b, 0); return t > 0 && t < k; }));
      if (kisiler.size < 3 || k < 3) return null;
      sutun = Array.from({ length: k }, (_, j) => [...kisiler.values()].reduce((a, v2) => a + v2[j], 0));
      const uc = [];
      for (let j = 0; j < k; j++) if (sutun[j] === 0 || sutun[j] === kisiler.size) uc.push(j);
      if (!uc.length) break;
      const ucS = new Set(uc);
      disaridaSoru.push(...uc.map((j) => sorular[j] + 1));
      sorular = sorular.filter((_, j) => !ucS.has(j));
      x = new Map([...x].map(([no, v2]) => [no, v2.filter((_, j) => !ucS.has(j))]));
    }
    const k = sorular.length;
    const nolar = [...kisiler.keys()];
    const toplam = new Map(nolar.map((no) => [no, kisiler.get(no).reduce((a, b) => a + b, 0)]));
    let b = sutun.map((s) => Math.log((kisiler.size - s) / s));
    let ort = fmean(b);
    b = b.map((q) => q - ort);
    const th = new Map(nolar.map((no) => [no, Math.log(toplam.get(no) / (k - toplam.get(no)))]));
    let yakinsadi = false;
    for (let d = 0; d < enFazla; d++) {
      let enBuyuk = 0;
      for (const no of nolar) {
        const p = b.map((bj) => 1 / (1 + Math.exp(bj - th.get(no))));
        const bek = p.reduce((a, c) => a + c, 0);
        const va = p.reduce((a, q) => a + q * (1 - q), 0);
        const adim = Math.max(-1, Math.min(1, (toplam.get(no) - bek) / va));
        th.set(no, th.get(no) + adim);
        enBuyuk = Math.max(enBuyuk, Math.abs(adim));
      }
      for (let j = 0; j < k; j++) {
        const p = nolar.map((no) => 1 / (1 + Math.exp(b[j] - th.get(no))));
        const bek = p.reduce((a, c) => a + c, 0);
        const va = p.reduce((a, q) => a + q * (1 - q), 0);
        const adim = Math.max(-1, Math.min(1, (bek - sutun[j]) / va));
        b[j] += adim;
        enBuyuk = Math.max(enBuyuk, Math.abs(adim));
      }
      ort = fmean(b);
      b = b.map((q) => q - ort);
      if (enBuyuk < 1e-4) { yakinsadi = true; break; }
    }
    const duz = (k - 1) / k;
    b = b.map((q) => q * duz);
    const hatalar = b.map((bj) => {
      const va = nolar.reduce((a, no) => { const q = 1 / (1 + Math.exp(bj - th.get(no) * duz)); return a + q * (1 - q); }, 0);
      return va > 0 ? 1 / Math.sqrt(va) : NaN;
    });
    const egri = [];
    for (let t10 = -40; t10 <= 40; t10++) { const t = t10 / 10; egri.push([t, b.reduce((a, bj) => { const q = 1 / (1 + Math.exp(bj - t)); return a + q * (1 - q); }, 0)]); }
    let enIyi = egri[0];
    for (const e2 of egri) if (e2[1] > enIyi[1]) enIyi = e2;
    const beklenenYuzde = fmean(b.map((bj) => 1 / (1 + Math.exp(bj - enIyi[0])))) * 100;
    return {
      soru_zorluklari: new Map(sorular.map((s, j) => [s + 1, b[j]])), soru_hatalari: new Map(sorular.map((s, j) => [s + 1, hatalar[j]])),
      kisi_yetenekleri: new Map(nolar.map((no) => [no, th.get(no) * duz])), bilgi_egrisi: egri, en_iyi_olctugu: enIyi[0], en_iyi_puan: beklenenYuzde,
      disarida_kalan_ogrenci: sonuc.ogrenciler.length - kisiler.size, disarida_kalan_soru: disaridaSoru.sort((p, q) => p - q), yakinsadi,
    };
  }
  function araAgirligi(sinav, ders) {
    const x = parseFloat(String(sinav.etki_orani || "").replace(",", "."));
    if (x > 0 && x < 100) return x;
    if (ders && ders.degerlendirme && ders.degerlendirme["Ara Sınav"] > 0 && ders.degerlendirme["Ara Sınav"] < 100) return ders.degerlendirme["Ara Sınav"];
    return 40;
  }
  function arsivKaydi(sonuc, sinav, genel, ciktiRaporu) {
    const c = {};
    for (const r of ciktiRaporu) if (r.tur.startsWith("Öğrenme") && r.sinif_yuzdesi !== null) c[r.kod] = r.sinif_yuzdesi;
    return { ders_kodu: sinav.ders_kodu, sinav_turu: sinav.sinav_turu, tarih: sinav.tarih, donem: sinav.donem, ogrenci_sayisi: genel.ogrenci_sayisi,
      ortalama: genel.ortalama || 0, medyan: genel.medyan || 0, standart_sapma: genel.standart_sapma, basari_orani: genel.basari_orani || 0,
      guvenirlik: genel.alfa !== null ? genel.alfa : genel.kr20, cikti_basarilari: c };
  }

  Object.assign(OS, {
    varsayilanEsikler, maddeAnalizi, ogrenmeCiktisiRaporu, ciktiDagilimiSinav, tamSayiDagilim, ciktiDenetimi,
    sinirdakiOgrenciler, finalGereken, sansPuani, tIkiYonluP, kitapcikKarsilastirma, spearman, tasarimDenetimi, rasch, araAgirligi, arsivKaydi,
  });
})(typeof globalThis !== "undefined" ? globalThis : window);
