/* Optik Sınav — tarayıcı sürümü: puanlama motoru.
 * Masaüstü programın Python motorunun (src/optik_sinav/core, io) birebir karşılığıdır; kurallar orada belgelenmiştir.
 * Puanlar BigInt tabanlı kesirlerle tam tutulur, yuvarlama yalnızca en sonda yapılır.
 * Veri yapıları, masaüstü programın .osd proje dosyasıyla aynı biçimdedir (iki program aynı dosyayı açar).
 */
(function (kok) {
  "use strict";
  const OS = kok.OS || (kok.OS = {});

  // ------------------------------------------------------------------ kesir
  function ebob(a, b) {
    a = a < 0n ? -a : a;
    b = b < 0n ? -b : b;
    while (b) [a, b] = [b, a % b];
    return a;
  }
  class Kesir {
    constructor(p, q = 1n) {
      p = BigInt(p);
      q = BigInt(q);
      if (q === 0n) throw new Error("Sıfıra bölme");
      if (q < 0n) { p = -p; q = -q; }
      const g = ebob(p, q) || 1n;
      this.p = p / g;
      this.q = q / g;
    }
    static of(x) {
      if (x instanceof Kesir) return x;
      if (typeof x === "bigint") return new Kesir(x);
      if (typeof x === "number") {
        if (Number.isInteger(x)) return new Kesir(BigInt(x));
        return Kesir.ondaliktan(String(x));
      }
      return Kesir.ondaliktan(String(x));
    }
    /** "6,5", "6.5", "-0.25", "1e2" gibi ondalık metinden tam kesir. */
    static ondaliktan(s) {
      s = String(s).trim().replace(",", ".");
      const m = /^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(s);
      if (!m || (m[2] === "" && (m[3] === undefined || m[3] === ""))) throw new Error(`Sayı değil: ${s}`);
      const tam = m[2] || "0";
      const ond = m[3] || "";
      let p = BigInt(tam + ond);
      let q = 10n ** BigInt(ond.length);
      const us = m[4] ? parseInt(m[4], 10) : 0;
      if (us > 0) p *= 10n ** BigInt(us);
      else if (us < 0) q *= 10n ** BigInt(-us);
      if (m[1] === "-") p = -p;
      return new Kesir(p, q);
    }
    ekle(o) { o = Kesir.of(o); return new Kesir(this.p * o.q + o.p * this.q, this.q * o.q); }
    cikar(o) { o = Kesir.of(o); return new Kesir(this.p * o.q - o.p * this.q, this.q * o.q); }
    carp(o) { o = Kesir.of(o); return new Kesir(this.p * o.p, this.q * o.q); }
    bol(o) { o = Kesir.of(o); return new Kesir(this.p * o.q, this.q * o.p); }
    kars(o) { o = Kesir.of(o); const f = this.p * o.q - o.p * this.q; return f < 0n ? -1 : f > 0n ? 1 : 0; }
    esit(o) { return this.kars(o) === 0; }
    sifirMi() { return this.p === 0n; }
    sayi() {
      // Büyük paylarda da doğru: önce tam kısım, sonra kalan
      const t = this.p / this.q;
      const k = this.p % this.q;
      return Number(t) + Number(k) / Number(this.q);
    }
    taban() { let t = this.p / this.q; if (this.p % this.q !== 0n && this.p < 0n) t -= 1n; return t; }
    tavan() { let t = this.p / this.q; if (this.p % this.q !== 0n && this.p > 0n) t += 1n; return t; }
    toString() { return this.q === 1n ? String(this.p) : `${this.p}/${this.q}`; }
  }
  Kesir.SIFIR = new Kesir(0n);
  const topla = (liste) => liste.reduce((a, b) => a.ekle(b), Kesir.SIFIR);

  /** Python round(Fraction): yarım değerde çift olana. */
  function kesirYuvarlaCift(k) {
    const t = k.taban();
    const kalan = k.cikar(new Kesir(t));
    const c = kalan.kars(new Kesir(1n, 2n));
    if (c < 0) return t;
    if (c > 0) return t + 1n;
    return t % 2n === 0n ? t : t + 1n;
  }

  /** Tam aritmetikle yuvarlar; {n: BigInt, ondalik} döndürür (değer = n / 10^ondalik). */
  function yuvarla(deger, ondalik = 2, yontem = "yarim_yukari") {
    const olcek = 10n ** BigInt(ondalik);
    const o = Kesir.of(deger).carp(new Kesir(olcek));
    let n;
    if (yontem === "asagi") n = o.taban();
    else if (yontem === "yukari") n = o.tavan();
    else if (o.p >= 0n) n = o.ekle(new Kesir(1n, 2n)).taban();
    else n = -(new Kesir(-o.p, o.q).ekle(new Kesir(1n, 2n)).taban());
    return { n, ondalik };
  }
  function ondalikMetni(y, ayirici = ".") {
    const neg = y.n < 0n;
    let s = (neg ? -y.n : y.n).toString();
    if (y.ondalik > 0) {
      s = s.padStart(y.ondalik + 1, "0");
      s = s.slice(0, -y.ondalik) + ayirici + s.slice(-y.ondalik);
    }
    return (neg ? "-" : "") + s;
  }
  const ondalikSayi = (y) => Number(ondalikMetni(y, "."));
  /** Gösterim için: yarım yukarı yuvarlar, virgüllü. */
  function sayiYaz(deger, ondalik = 2, ayirici = ",") {
    return ondalikMetni(yuvarla(deger, ondalik), ayirici);
  }

  /** Python biçimlendirmesiyle ("{x:.nf}") aynı: tam ikili değere göre yuvarlar, tam yarıda çifte. */
  function pyOndalik(x, n) {
    if (!isFinite(x)) return String(x);
    const neg = x < 0 || Object.is(x, -0);
    const t = Math.abs(x).toFixed(Math.min(100, n + 40));
    const [tam, ond] = t.split(".");
    let basamaklar = tam + ond.slice(0, n);
    const kalan = ond.slice(n);
    const ilk = kalan.charCodeAt(0) - 48;
    const sonrasiSifir = /^0*$/.test(kalan.slice(1));
    let yukari = ilk > 5 || (ilk === 5 && !sonrasiSifir);
    if (ilk === 5 && sonrasiSifir) yukari = (basamaklar.charCodeAt(basamaklar.length - 1) - 48) % 2 === 1;
    let b = BigInt(basamaklar) + (yukari ? 1n : 0n);
    let s = b.toString().padStart(n + 1, "0");
    s = n > 0 ? s.slice(0, -n) + "." + s.slice(-n) : s;
    return (neg && /[1-9]/.test(s) ? "-" : neg ? "-" : "") + s;
  }
  const v = (x, n = 1) => pyOndalik(x, n).replace(".", ",");

  // ------------------------------------------------------------------ istatistik yardımcıları (Python statistics)
  const fmean = (a) => { a = Array.from(a); return a.reduce((s, x) => s + x, 0) / a.length; };
  function _ss(a) { const m = fmean(a); return a.reduce((s, x) => s + (x - m) * (x - m), 0); }
  const pvariance = (a) => _ss(a) / a.length;
  const variance = (a) => _ss(a) / (a.length - 1);
  const pstdev = (a) => Math.sqrt(pvariance(a));
  const stdev = (a) => Math.sqrt(variance(a));
  function median(a) { const s = [...a].sort((x, y) => x - y); const n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; }
  function ceyrekler(a) { // statistics.quantiles(n=4, method="inclusive")
    const d = [...a].sort((x, y) => x - y);
    const m = d.length - 1;
    const r = [];
    for (let i = 1; i < 4; i++) {
      const j = Math.floor((i * m) / 4);
      const delta = i * m - j * 4;
      r.push((d[j] * (4 - delta) + d[j + 1 < d.length ? j + 1 : j] * delta) / 4);
    }
    return r;
  }

  // ------------------------------------------------------------------ sabitler ve metinler
  const SIKLAR = "ABCDE";
  const CIFT = "*";
  const BOZUK = "�";
  const UYARI = {
    kisa_satir: "Kısa satır ({uzunluk} karakter): son {eksik} cevap boş sayıldı",
    numara_bos: "Öğrenci numarası boş",
    numara_okunamadi: "Öğrenci numarasında okunamayan karakter: {no}",
    ad_bos: "Ad soyad boş",
    ad_okunamadi: "Ad soyadda okunamayan karakter: {ad}",
    ad_bozuk_karakter: "Ad soyadda bozuk Türkçe karakter var; doğru ad öğrenci listesinden alınmalı",
    cevapta_gecersiz: "Cevap alanında geçersiz işaret (boş sayıldı), soru: {sorular}",
    cift_isaret: "Çift işaret, soru: {sorular}",
    tekrar_numara: "Aynı numara başka satırda da var (satır {satirlar})",
    alan_disi_isaret: "Soru alanı dışında işaret var (konum {konumlar})",
    listede_yok: "Numara öğrenci listesinde yok",
    listede_yok_oneri: "Numara öğrenci listesinde yok. Olası numaralar: {oneriler}",
    kitapcik_okunamadi: "Kitapçık türü okunamadı: {k}",
    kitapcik_bilinmiyor: "Anahtarı girilmemiş kitapçık {k}; {ana} kitapçığı sayıldı",
    klasik_fazla: "{soru}. soruda girilen puan ({puan}) sorunun puanından ({en_fazla}) büyük",
    klasik_eksi: "{soru}. soruda eksi puan girilmiş",
    klasik_eksik: "Puanı girilmemiş soru: {sorular} (sıfır sayıldı)",
    klasik_toplam: "Kâğıttaki toplam ({kagit}) soru puanlarının toplamıyla ({hesap}) tutmuyor",
  };
  const EKSIK = {
    dat: "Optik okuyucu dosyası seçilmedi.",
    ders_kodu: "Ders kodu girilmedi.",
    soru_sayisi: "Soru sayısı sıfır.",
    anahtar: "Anahtarı girilmemiş sorular var: {sorular}",
    soru_puan_toplam: "Soru puanlarının toplamı {toplam}, olması gereken {beklenen}.",
    soru_puan_eksik: "Puanı girilmemiş sorular var: {sorular}",
    coklu_tek: "'Birden fazla doğru' seçilen sorularda en az iki şık işaretlenmeli: {sorular}",
  };
  const DURUM_ADI = { D: "Doğru", Y: "Yanlış", B: "Boş", I: "İptal", "-": "Anahtarsız", K: "Kısmi puan" };
  const SORU_DURUMU_ADI = { normal: "Normal", iptal: "İptal (herkese tam puan)", coklu: "Birden fazla doğru" };
  const bicimle = (s, d) => s.replace(/\{(\w+)\}/g, (_, k) => (k in d ? String(d[k]) : `{${k}}`));
  const pyRepr = (s) => (s.includes("'") && !s.includes('"') ? `"${s}"` : `'${s.replace(/'/g, "\\'")}'`);

  // ------------------------------------------------------------------ varsayılan nesneler
  function yeniOkuyucu() {
    return { ad: "varsayilan_136", aciklama: "", ad_baslangic: 1, ad_uzunluk: 25, no_baslangic: 26, no_uzunluk: 9,
      cevap_baslangic: 37, soru_sayisi: 15, kitapcik_baslangic: null, kitapcik_uzunluk: 1, satir_uzunlugu: 136 };
  }
  function yeniSoru(no) {
    return { no, dogru: "", durum: "normal", puan: null, ogrenme_ciktilari: [], program_ciktilari: [], cikti_yuzdeleri: {} };
  }
  function yeniAyarlar() {
    return { basari_esigi: 50, gecme_ortalamasi: 50, final_alt_siniri: 50, toplam_puan: "100", yontem: "esit",
      yanlis_cezasi: false, ceza_orani: 4, cift_isaret: "bos", yuvarlama: "yarim_yukari", ondalik: 2 };
  }
  function yeniProje() {
    return {
      surum: 1, uygulama: "optik-sinav",
      sinav: { ders_kodu: "", ders_adi: "", sinav_turu: "Ara Sınav", tarih: "", saat: "", etki_orani: "", donem: "" },
      anahtar: { sorular: [], kitapcik_eslemesi: {}, ana_kitapcik: "A", kitapcik_anahtarlari: {} },
      ayarlar: yeniAyarlar(), okuyucu: yeniOkuyucu(), dat_yolu: "", liste_yolu: "",
      liste_esleme: { sayfa: null, baslik_satiri: null, no_sutun: null, ad_sutun: null, soyad_sutun: null },
      duzeltmeler: [], profil_akreditasyon: "akreditasyon_soru_bazli_varsayilan", profil_not_giris: "not_giris_varsayilan",
      sistem_sablonu_yolu: "", bicim: "optik", klasik_soru_sayisi: 5, klasik_puanlar: {}, klasik_toplamlar: {}, klasik_giris_sirasi: [], final_puanlar: {}, harf_ayarlari: {},
    };
  }
  /** Masaüstü programın kaydettiği .osd dosyasını eksik alanları tamamlayarak yükler. */
  function projeyiTamamla(d) {
    const p = yeniProje();
    for (const k of Object.keys(p)) if (d[k] !== undefined) p[k] = d[k];
    p.sinav = Object.assign(yeniProje().sinav, d.sinav || {});
    p.ayarlar = Object.assign(yeniAyarlar(), d.ayarlar || {});
    p.okuyucu = Object.assign(yeniOkuyucu(), d.okuyucu || {});
    p.anahtar = Object.assign({ sorular: [], kitapcik_eslemesi: {}, ana_kitapcik: "A", kitapcik_anahtarlari: {} }, d.anahtar || {});
    p.anahtar.sorular = (p.anahtar.sorular || []).map((s) => Object.assign(yeniSoru(s.no), s));
    p.klasik_puanlar = d.klasik_puanlar || {};
    p.final_puanlar = d.final_puanlar || {};
    p.klasik_toplamlar = d.klasik_toplamlar || {};
    p.klasik_giris_sirasi = (d.klasik_giris_sirasi || []).map(String);
    p.harf_ayarlari = d.harf_ayarlari || {};
    return p;
  }

  // ------------------------------------------------------------------ soru ve anahtar
  function esitYuzdeler(n, toplam = 100) {
    if (n <= 0) return [];
    const taban = Math.floor(toplam / n), kalan = toplam - taban * n;
    return Array.from({ length: n }, (_, i) => taban + (i < kalan ? 1 : 0));
  }
  const dogruKume = (s) => new Set([...String(s.dogru || "").toUpperCase()].filter((c) => SIKLAR.includes(c)));
  function ciktiDagilimi(s) {
    const kodlar = (s.ogrenme_ciktilari || []).filter((k) => k);
    if (!kodlar.length) return new Map();
    const y = s.cikti_yuzdeleri || {};
    const yk = Object.keys(y);
    if (yk.length && yk.length === new Set(kodlar).size && kodlar.every((k) => k in y)) return new Map(kodlar.map((k) => [k, parseInt(y[k], 10)]));
    const e = esitYuzdeler(kodlar.length);
    return new Map(kodlar.map((k, i) => [k, e[i]]));
  }
  const kitapciklar = (a) => [a.ana_kitapcik, ...Object.keys(a.kitapcik_anahtarlari || {}).filter((k) => k !== a.ana_kitapcik).sort()];
  function esleme(a, kitapcik) {
    const n = a.sorular.length;
    const e = new Map();
    for (let k = 1; k <= n; k++) e.set(k, k);
    const t = (a.kitapcik_eslemesi || {})[kitapcik] || {};
    for (const [x, y] of Object.entries(t)) {
      const xi = parseInt(x, 10), yi = parseInt(y, 10);
      if (xi >= 1 && xi <= n && yi >= 1 && yi <= n) e.set(xi, yi);
    }
    return e;
  }
  function eslemeSorunlari(a, kitapcik) {
    const h = [...esleme(a, kitapcik).values()];
    const tekrar = [...new Set(h.filter((x) => h.filter((y) => y === x).length > 1))].sort((p, q) => p - q);
    return tekrar.length ? [`${kitapcik} kitapçığında ana kitapçığın ${tekrar.join(", ")}. sorusuna birden fazla soru eşlenmiş.`] : [];
  }
  /** Kitapçığın anahtarını ana sıraya çevirir: [anahtar kopyası, Map(ana soru no -> kitapçık soru no)]. */
  function kitapcikIcin(a, kitapcik) {
    const n = a.sorular.length;
    if (!kitapcik || kitapcik === a.ana_kitapcik || !(kitapcik in (a.kitapcik_anahtarlari || {}))) {
      return [a, new Map(Array.from({ length: n }, (_, i) => [i + 1, i + 1]))];
    }
    const harfler = [...a.kitapcik_anahtarlari[kitapcik].toUpperCase()].filter((c) => !/\s/.test(c));
    const ters = new Map();
    for (const [x, y] of esleme(a, kitapcik)) ters.set(y, x);
    const sorular = a.sorular.map((s) => {
      const k = ters.has(s.no) ? ters.get(s.no) : s.no;
      const harf = k - 1 < harfler.length ? harfler[k - 1] : "";
      const kopya = JSON.parse(JSON.stringify(s));
      kopya.dogru = s.durum !== "coklu" ? (SIKLAR.includes(harf) && harf ? harf : "") : [...harf].filter((c) => SIKLAR.includes(c)).join("");
      return kopya;
    });
    return [{ sorular, ana_kitapcik: a.ana_kitapcik, kitapcik_eslemesi: {}, kitapcik_anahtarlari: {} },
      new Map(a.sorular.map((s) => [s.no, ters.has(s.no) ? ters.get(s.no) : s.no]))];
  }
  function anahtarMetinden(metin, soruSayisi = null) {
    const harfler = [...String(metin).toUpperCase()].filter((c) => !/\s/.test(c));
    let sorular = harfler.map((c, i) => {
      if (c === "-") return yeniSoru(i + 1);
      if (SIKLAR.includes(c)) return Object.assign(yeniSoru(i + 1), { dogru: c });
      throw new Error(`Cevap anahtarında geçersiz karakter: ${pyRepr(c)} (${i + 1}. soru)`);
    });
    if (soruSayisi !== null) {
      while (sorular.length < soruSayisi) sorular.push(yeniSoru(sorular.length + 1));
      sorular = sorular.slice(0, soruSayisi);
    }
    return sorular;
  }
  const anahtarMetne = (a) => a.sorular.map((s) => (s.dogru ? s.dogru[0] : "-")).join("");

  // ------------------------------------------------------------------ puanlama
  function soruPuanlari(a, ayar) {
    const n = a.sorular.length;
    if (!n) return [];
    if (ayar.yontem === "esit") return Array(n).fill(Kesir.ondaliktan(ayar.toplam_puan).bol(n));
    return a.sorular.map((s) => (s.puan === null || s.puan === undefined || s.puan === "" ? Kesir.SIFIR : Kesir.ondaliktan(s.puan)));
  }
  function esitSoruPuanlari(toplam, n, basamak = 2) {
    if (n <= 0) return [];
    const birim = new Kesir(1n, 10n ** BigInt(basamak));
    const t = Kesir.ondaliktan(toplam);
    const taban = new Kesir(t.bol(n).bol(birim).taban()).carp(birim);
    const kalan = Number(t.cikar(taban.carp(n)).bol(birim).taban());
    return Array.from({ length: n }, (_, i) => {
      const d = i < kalan ? taban.ekle(birim) : taban;
      let s = ondalikMetni(yuvarla(d, basamak), ".");
      if (s.includes(".")) s = s.replace(/0+$/, "").replace(/\.$/, "");
      return s;
    });
  }
  function soruDegerlendir(isaret, soru, ayar) {
    if (soru.durum === "iptal") return "I";
    const d = dogruKume(soru);
    if (!d.size) return "-";
    if (isaret === CIFT) return ayar.cift_isaret === "yanlis" ? "Y" : "B";
    if (!SIKLAR.includes(isaret) || !isaret) return "B";
    return d.has(isaret) ? "D" : "Y";
  }
  function ogrenciPuanla(cevaplar, a, ayar, puanlar) {
    puanlar = puanlar || soruPuanlari(a, ayar);
    const sonuclar = [];
    let dogru = 0, yanlis = 0, bos = 0, ham = Kesir.SIFIR, ceza = Kesir.SIFIR;
    a.sorular.forEach((soru, i) => {
      const isaret = i < cevaplar.length ? cevaplar[i] : " ";
      const durum = soruDegerlendir(isaret, soru, ayar);
      let p = Kesir.SIFIR;
      if (durum === "D" || durum === "I") { dogru++; p = puanlar[i]; }
      else if (durum === "Y") { yanlis++; if (ayar.yanlis_cezasi && ayar.ceza_orani > 0) ceza = ceza.ekle(puanlar[i].bol(ayar.ceza_orani)); }
      else if (durum === "B") bos++;
      ham = ham.ekle(p);
      sonuclar.push({ isaret, durum, puan: p });
    });
    const fark = ham.cikar(ceza);
    return { sonuclar, dogru, yanlis, bos, ham, ceza, puan: fark.kars(0) < 0 ? Kesir.SIFIR : fark };
  }
  function net(dogru, yanlis, ayar) {
    if (!ayar.yanlis_cezasi || ayar.ceza_orani <= 0) return new Kesir(BigInt(dogru));
    const n = new Kesir(BigInt(dogru)).cikar(new Kesir(BigInt(yanlis), BigInt(ayar.ceza_orani)));
    return n.kars(0) < 0 ? Kesir.SIFIR : n;
  }
  function anahtarEksikleri(a, ayar, klasik = false) {
    const e = [];
    if (!a.sorular.length) return [EKSIK.soru_sayisi];
    if (klasik) a = { sorular: a.sorular.map((s) => Object.assign(yeniSoru(s.no), { dogru: "A", puan: s.puan })) };
    const anahtarsiz = a.sorular.filter((s) => s.durum !== "iptal" && !dogruKume(s).size).map((s) => s.no);
    if (anahtarsiz.length) e.push(bicimle(EKSIK.anahtar, { sorular: anahtarsiz.join(", ") }));
    const cokluTek = a.sorular.filter((s) => s.durum === "coklu" && dogruKume(s).size < 2).map((s) => s.no);
    if (cokluTek.length) e.push(bicimle(EKSIK.coklu_tek, { sorular: cokluTek.join(", ") }));
    if (ayar.yontem === "soru_bazli") {
      const puansiz = a.sorular.filter((s) => s.puan === null || s.puan === undefined || s.puan === "").map((s) => s.no);
      if (puansiz.length) e.push(bicimle(EKSIK.soru_puan_eksik, { sorular: puansiz.join(", ") }));
      else {
        const toplam = topla(soruPuanlari(a, ayar));
        const beklenen = Kesir.ondaliktan(ayar.toplam_puan);
        if (!toplam.esit(beklenen)) e.push(bicimle(EKSIK.soru_puan_toplam, { toplam: sayiYaz(toplam), beklenen: sayiYaz(beklenen) }));
      }
    }
    return e;
  }

  // ------------------------------------------------------------------ dosya okuma
  function baytlariCoz(bayt) {
    if (bayt.length >= 3 && bayt[0] === 0xef && bayt[1] === 0xbb && bayt[2] === 0xbf) {
      return [new TextDecoder("utf-8").decode(bayt.subarray(3)), "utf-8-sig"];
    }
    try { return [new TextDecoder("utf-8", { fatal: true }).decode(bayt), "utf-8"]; } catch (_) { /* sonraki */ }
    return [new TextDecoder("windows-1254").decode(bayt), "windows-1254"];
  }
  function satirSonuAlgila(m) {
    const crlf = (m.match(/\r\n/g) || []).length;
    const cr = (m.match(/\r/g) || []).length - crlf;
    const lf = (m.match(/\n/g) || []).length - crlf;
    const t = [["CRLF", crlf], ["LF", lf], ["CR", cr]].filter(([, n]) => n).map(([a]) => a);
    return !t.length ? "LF" : t.length === 1 ? t[0] : "karışık";
  }
  function satirlaraBol(m) {
    const s = m.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
    if (s.length && s[s.length - 1] === "") s.pop();
    return s;
  }
  function metinDosyasiOku(bayt) {
    const [m, kodlama] = baytlariCoz(bayt);
    return { satirlar: satirlaraBol(m), kodlama, satir_sonu: satirSonuAlgila(m) };
  }

  const alan = (s, bas, uz) => s.slice(bas - 1, bas - 1 + uz);
  const harfMi = (c) => /\p{L}/u.test(c);
  const rakamMi = (s) => /^\d+$/.test(s);
  const _liste = (a) => a.join(", ");
  function alanlar(o) {
    const a = [["ad", o.ad_baslangic, o.ad_uzunluk], ["no", o.no_baslangic, o.no_uzunluk], ["cevap", o.cevap_baslangic, o.soru_sayisi]];
    if (o.kitapcik_baslangic) a.push(["kitapcik", o.kitapcik_baslangic, o.kitapcik_uzunluk]);
    return a;
  }
  function satiriCoz(satir, satirNo, o) {
    const uyarilar = [];
    const ad = alan(satir, o.ad_baslangic, o.ad_uzunluk).trim();
    const no = alan(satir, o.no_baslangic, o.no_uzunluk).trim();
    let ch = alan(satir, o.cevap_baslangic, o.soru_sayisi);
    const bitis = o.cevap_baslangic + o.soru_sayisi - 1;
    if (satir.length < bitis) {
      const eksik = bitis - Math.max(satir.length, o.cevap_baslangic - 1);
      uyarilar.push({ tur: "kisa_satir", mesaj: bicimle(UYARI.kisa_satir, { uzunluk: satir.length, eksik }), satir_no: satirNo });
    }
    ch = ch.padEnd(o.soru_sayisi, " ");
    const cevaplar = [...ch].map((c) => c.toUpperCase());
    if (!no) uyarilar.push({ tur: "numara_bos", mesaj: UYARI.numara_bos, satir_no: satirNo });
    else if (!rakamMi(no)) uyarilar.push({ tur: "numara_okunamadi", mesaj: bicimle(UYARI.numara_okunamadi, { no }), satir_no: satirNo });
    if (!ad) uyarilar.push({ tur: "ad_bos", mesaj: UYARI.ad_bos, satir_no: satirNo });
    else {
      if (ad.includes(BOZUK)) uyarilar.push({ tur: "ad_bozuk_karakter", mesaj: UYARI.ad_bozuk_karakter, satir_no: satirNo });
      if ([...ad.split(BOZUK).join("")].some((c) => c === "*" || (!harfMi(c) && !" .'-".includes(c)))) {
        uyarilar.push({ tur: "ad_okunamadi", mesaj: bicimle(UYARI.ad_okunamadi, { ad }), satir_no: satirNo });
      }
    }
    const gecersiz = cevaplar.map((c, i) => [c, i + 1]).filter(([c]) => !SIKLAR.includes(c) && c !== " " && c !== CIFT).map(([, i]) => i);
    if (gecersiz.length) uyarilar.push({ tur: "cevapta_gecersiz", mesaj: bicimle(UYARI.cevapta_gecersiz, { sorular: _liste(gecersiz) }), satir_no: satirNo, ayrinti: gecersiz });
    const cift = cevaplar.map((c, i) => [c, i + 1]).filter(([c]) => c === CIFT).map(([, i]) => i);
    if (cift.length) uyarilar.push({ tur: "cift_isaret", mesaj: bicimle(UYARI.cift_isaret, { sorular: _liste(cift) }), satir_no: satirNo, ayrinti: cift });
    let kitapcik = "";
    if (o.kitapcik_baslangic) {
      kitapcik = alan(satir, o.kitapcik_baslangic, o.kitapcik_uzunluk).trim().toUpperCase();
      if (!kitapcik || ![...kitapcik].every(harfMi)) uyarilar.push({ tur: "kitapcik_okunamadi", mesaj: bicimle(UYARI.kitapcik_okunamadi, { k: pyRepr(kitapcik) }), satir_no: satirNo });
    }
    const tanimli = new Set();
    for (const [, bas, uz] of alanlar(o)) for (let i = bas; i < bas + uz; i++) tanimli.add(i);
    const disarida = [...satir].map((c, i) => [c, i + 1]).filter(([c, i]) => !tanimli.has(i) && !/\s/.test(c)).map(([, i]) => i);
    if (disarida.length) uyarilar.push({ tur: "alan_disi_isaret", mesaj: bicimle(UYARI.alan_disi_isaret, { konumlar: _liste(disarida) }), satir_no: satirNo, ayrinti: disarida });
    return { satir_no: satirNo, ham_satir: satir, ad, ogrenci_no: no, cevaplar, kitapcik, uyarilar };
  }
  function satirlariOku(satirlar, o) {
    const kayitlar = [];
    let bos = 0;
    satirlar.forEach((s, i) => { if (!s.trim()) { bos++; return; } kayitlar.push(satiriCoz(s, i + 1, o)); });
    const gruplar = new Map();
    for (const k of kayitlar) if (k.ogrenci_no) { if (!gruplar.has(k.ogrenci_no)) gruplar.set(k.ogrenci_no, []); gruplar.get(k.ogrenci_no).push(k.satir_no); }
    for (const [no, nolar] of gruplar) {
      if (nolar.length < 2) continue;
      for (const k of kayitlar) if (k.ogrenci_no === no) {
        k.uyarilar.push({ tur: "tekrar_numara", mesaj: bicimle(UYARI.tekrar_numara, { satirlar: _liste(nolar.filter((s) => s !== k.satir_no)) }), satir_no: k.satir_no });
      }
    }
    return { kayitlar, bos };
  }
  function soruSayisiOner(satirlar, cevapBaslangic, enAzOran = 0.1) {
    const dolu = satirlar.filter((s) => s.trim());
    if (!dolu.length) return 0;
    const sayac = new Map();
    for (const s of dolu) for (let i = cevapBaslangic - 1; i < s.length; i++) if (SIKLAR.includes(s[i].toUpperCase()) || s[i] === CIFT) sayac.set(i, (sayac.get(i) || 0) + 1);
    const esik = dolu.length > 2 ? Math.max(2, Math.floor(dolu.length * enAzOran)) : 1;
    const son = [...sayac].filter(([, n]) => n >= esik).map(([i]) => i);
    if (!son.length) return 0;
    return Math.max(...son) - (cevapBaslangic - 1) + 1;
  }
  function sablonOner(satirlar, temel) {
    const s = Object.assign(yeniOkuyucu(), temel || {});
    const n = soruSayisiOner(satirlar, s.cevap_baslangic);
    if (n) s.soru_sayisi = n;
    const say = new Map();
    for (const x of satirlar) if (x.trim()) say.set(x.length, (say.get(x.length) || 0) + 1);
    let enIyi = null;
    for (const [u, n2] of say) if (enIyi === null || n2 > say.get(enIyi)) enIyi = u;
    if (enIyi !== null) s.satir_uzunlugu = enIyi;
    return s;
  }

  // ------------------------------------------------------------------ öğrenci listesi
  function sade(m) {
    let s = String(m ?? "").trim().replace(/İ/g, "i").replace(/I/g, "ı").toLowerCase();
    s = s.replace(/[ığüşöç]/g, (c) => ({ ı: "i", ğ: "g", ü: "u", ş: "s", ö: "o", ç: "c" })[c]);
    s = s.normalize("NFKD").replace(/[̀-ͯ]/g, "");
    return s.replace(/[^a-z0-9]/g, "");
  }
  function numaraNormalle(d) {
    if (d === null || d === undefined || typeof d === "boolean") return "";
    if (typeof d === "number") return Number.isInteger(d) ? String(d) : String(d);
    let s = String(d).replace(/\s+/g, "");
    if (/^\d+\.0+$/.test(s)) s = s.split(".")[0];
    return s;
  }
  const NO_B = new Set(["ogrno", "ogrencino", "ogrencinumarasi", "numara", "no", "ogrnumarasi", "okulno", "studentno", "studentid"]);
  const ADSOYAD_B = new Set(["adisoyadi", "adsoyad", "adisoyad", "adsoyadi", "ogrenciadisoyadi", "isim", "adivesoyadi", "name"]);
  const AD_B = new Set(["adi", "ad", "ogrenciadi"]);
  const SOYAD_B = new Set(["soyadi", "soyad"]);
  const numaraGibi = (d) => { const s = numaraNormalle(d); return rakamMi(s) && s.length >= 6 && s.length <= 12; };
  // PDF listesi: satırların hücrelerinden ["Öğrenci No", "Adı Soyadı"] tablosu (Python: pdf_hucrelerinden_tablo)
  const NUMARA = /^\d{6,12}$/;
  const harfli = (h) => !!h && /\p{L}/u.test(h) && !/\d/.test(h);
  function pdfHucrelerindenTablo(satirlar) {
    let adKaydir = null, soyadKaydir = null;
    const tablo = [["Öğrenci No", "Adı Soyadı"]];
    const gorulen = new Set();
    for (const ham of satirlar) {
      const hucreler = ham.filter((h) => h !== null && h !== undefined && String(h).trim()).map((h) => String(h).replace(/\s+/g, " ").trim());
      if (!hucreler.length) continue;
      const numarali = hucreler.map((h, i) => (NUMARA.test(h) ? i : -1)).filter((i) => i >= 0);
      let no, ad;
      if (!numarali.length) {
        const sadeler = hucreler.map(sade);
        let ni = sadeler.findIndex((h) => NO_B.has(h) && h !== "no");
        if (ni < 0) ni = sadeler.findIndex((h) => h === "no");
        if (ni >= 0) {
          const as = sadeler.findIndex((h) => ADSOYAD_B.has(h));
          const a = sadeler.findIndex((h) => AD_B.has(h));
          const so = sadeler.findIndex((h) => SOYAD_B.has(h));
          if (as >= 0) { adKaydir = as - ni; soyadKaydir = null; }
          else if (a >= 0) { adKaydir = a - ni; soyadKaydir = so >= 0 ? so - ni : null; }
          continue;
        }
        const kelimeler = hucreler.join(" ").split(" ").filter(Boolean);
        const j = kelimeler.findIndex((k) => NUMARA.test(k));
        if (j < 0) continue;
        no = kelimeler[j];
        const parca = [];
        for (const k of kelimeler.slice(j + 1)) { if (!harfli(k)) break; parca.push(k); }
        if (!parca.length) for (const k of kelimeler.slice(0, j).reverse()) { if (!harfli(k)) break; parca.unshift(k); }
        ad = parca.join(" ");
      } else {
        const i = numarali[0];
        no = hucreler[i];
        const al = (kaydir) => {
          if (kaydir === null) return "";
          const k = i + kaydir;
          return k >= 0 && k < hucreler.length && harfli(hucreler[k]) ? hucreler[k] : "";
        };
        ad = adKaydir !== null ? [al(adKaydir), al(soyadKaydir)].filter(Boolean).join(" ") : (al(1) || al(-1));
      }
      if (gorulen.has(no)) continue;
      gorulen.add(no);
      tablo.push([no, ad]);
    }
    return tablo;
  }
  function eslemeTahminEt(tablo, sayfa = null) {
    const e = { sayfa, baslik_satiri: null, no_sutun: null, ad_sutun: null, soyad_sutun: null };
    for (let r = 0; r < Math.min(15, tablo.length); r++) {
      const sadeler = tablo[r].map(sade);
      const ni = sadeler.findIndex((h) => NO_B.has(h));
      if (ni < 0) continue;
      e.baslik_satiri = r + 1;
      e.no_sutun = ni + 1;
      const as = sadeler.findIndex((h) => ADSOYAD_B.has(h));
      if (as >= 0) e.ad_sutun = as + 1;
      else {
        const a = sadeler.findIndex((h) => AD_B.has(h));
        const so = sadeler.findIndex((h) => SOYAD_B.has(h));
        if (a >= 0) e.ad_sutun = a + 1;
        if (so >= 0) e.soyad_sutun = so + 1;
      }
      return e;
    }
    if (!tablo.length) return e;
    const gen = Math.max(...tablo.map((s) => s.length));
    const puanlar = Array.from({ length: gen }, (_, i) => tablo.filter((s) => i < s.length && numaraGibi(s[i])).length);
    const enCok = Math.max(0, ...puanlar);
    if (enCok === 0) return e;
    const noI = puanlar.indexOf(enCok);
    e.no_sutun = noI + 1;
    const ilk = tablo.findIndex((s) => noI < s.length && numaraGibi(s[noI]));
    e.baslik_satiri = ilk > 0 ? ilk : null;
    for (let i = noI + 1; i < gen; i++) {
      const m = tablo.slice(ilk).filter((s) => i < s.length && typeof s[i] === "string" && s[i].trim()).map((s) => s[i]);
      if (m.length >= Math.max(1, Math.floor((tablo.length - ilk) / 2)) && [...m.join("")].some(harfMi)) { e.ad_sutun = i + 1; break; }
    }
    return e;
  }
  function sayfaSec(sayfalar) {
    let enIyi = Object.keys(sayfalar)[0], enCok = -1;
    for (const [ad, t] of Object.entries(sayfalar)) {
      const e = eslemeTahminEt(t, ad);
      if (e.no_sutun === null) continue;
      const n = t.filter((s) => e.no_sutun - 1 < s.length && numaraGibi(s[e.no_sutun - 1])).length;
      if (n > enCok) { enIyi = ad; enCok = n; }
    }
    return enIyi;
  }
  function tablodanListe(tablo, e) {
    if (e.no_sutun === null) throw new Error("Öğrenci numarası sütunu belirlenemedi.");
    const bas = e.baslik_satiri || 0;
    const basliklar = e.baslik_satiri ? tablo[e.baslik_satiri - 1].map((h) => String(h ?? "")) : [];
    const hucre = (s, j) => (j === null || j === undefined || j - 1 >= s.length || s[j - 1] === null || s[j - 1] === undefined ? "" : String(s[j - 1]));
    const ogrenciler = [];
    for (let r = bas; r < tablo.length; r++) {
      const s = tablo[r];
      const no = numaraNormalle(e.no_sutun - 1 < s.length ? s[e.no_sutun - 1] : null);
      if (!no || !/\d/.test(no)) continue;
      const ad = [hucre(s, e.ad_sutun).trim(), hucre(s, e.soyad_sutun).trim()].filter((x) => x).join(" ").replace(/\s+/g, " ");
      ogrenciler.push({ no, ad, kaynak_satir: r + 1 });
    }
    return { ogrenciler, esleme: e, basliklar };
  }

  // ------------------------------------------------------------------ düzeltme ve değerlendirme
  const ALANA_GORE_KALKAN = {
    no: ["numara_bos", "numara_okunamadi"],
    ad: ["ad_bos", "ad_okunamadi", "ad_bozuk_karakter"],
    kitapcik: ["kitapcik_okunamadi"],
  };
  function duzeltilmisDegerler(k, duzeltmeler) {
    let no = k.ogrenci_no, ad = k.ad;
    const c = [...k.cevaplar];
    for (const d of duzeltmeler) {
      if (d.satir_no !== k.satir_no) continue;
      if (d.alan === "no") no = d.yeni;
      else if (d.alan === "ad") ad = d.yeni;
      else if (d.alan.startsWith("cevap:")) {
        const i = parseInt(d.alan.split(":")[1], 10) - 1;
        while (c.length <= i) c.push(" ");
        c[i] = (d.yeni || " ")[0];
      }
    }
    return [no, ad, c];
  }
  function duzeltilmisKitapcik(k, duzeltmeler) {
    let x = k.kitapcik;
    for (const d of duzeltmeler) if (d.satir_no === k.satir_no && d.alan === "kitapcik") x = d.yeni;
    return x;
  }
  function duzeltmeOlustur(k, alanAdi, yeni, onceki = [], kim = "") {
    const [no, ad, c] = duzeltilmisDegerler(k, onceki);
    let eski;
    if (alanAdi === "no") eski = no;
    else if (alanAdi === "ad") eski = ad;
    else if (alanAdi.startsWith("cevap:")) eski = c[parseInt(alanAdi.split(":")[1], 10) - 1];
    else if (alanAdi === "kitapcik") { eski = duzeltilmisKitapcik(k, onceki); yeni = String(yeni || "").trim().toUpperCase().slice(0, 1); }
    else throw new Error(`Bilinmeyen alan: ${alanAdi}`);
    if (alanAdi.startsWith("cevap:")) yeni = String(yeni || " ").toUpperCase().slice(0, 1);
    const z = new Date();
    const pad = (x) => String(x).padStart(2, "0");
    const zaman = `${z.getFullYear()}-${pad(z.getMonth() + 1)}-${pad(z.getDate())}T${pad(z.getHours())}:${pad(z.getMinutes())}:${pad(z.getSeconds())}`;
    return { satir_no: k.satir_no, alan: alanAdi, eski, yeni: String(yeni).trim(), kim, zaman };
  }
  function duzenlemeUzakligi(a, b) {
    let onceki = Array.from({ length: b.length + 1 }, (_, i) => i);
    for (let i = 1; i <= a.length; i++) {
      const simdi = [i];
      for (let j = 1; j <= b.length; j++) simdi.push(Math.min(onceki[j] + 1, simdi[j - 1] + 1, onceki[j - 1] + (a[i - 1] !== b[j - 1] ? 1 : 0)));
      onceki = simdi;
    }
    return onceki[b.length];
  }
  function numaraOnerileri(no, adaylar, enFazla = 3) {
    if (!no) return [];
    const p = [];
    for (const a of adaylar) {
      let son = 0;
      for (let i = 1; i <= Math.min(no.length, a.length); i++) { if (no[no.length - i] !== a[a.length - i]) break; son++; }
      const uz = duzenlemeUzakligi(no, a);
      const icerir = no.includes(a) || a.includes(no);
      if (icerir || uz <= 2 || son >= Math.max(4, Math.min(no.length, a.length) - 3)) p.push([-(icerir ? 1 : 0), uz, -son, a]);
    }
    p.sort((x, y) => x[0] - y[0] || x[1] - y[1] || x[2] - y[2] || (x[3] < y[3] ? -1 : x[3] > y[3] ? 1 : 0));
    return p.slice(0, enFazla).map((x) => x[3]);
  }
  function sinaviDegerlendir(kayitlar, anahtar, ayar, liste = null, duzeltmeler = []) {
    const puanlar = soruPuanlari(anahtar, ayar);
    const ls = new Map();
    if (liste) for (const o of liste.ogrenciler) ls.set(o.no, o);
    const kitList = kitapciklar(anahtar);
    const ogrenciler = [];
    for (const k of kayitlar) {
      let [no, okunanAd, cevaplar] = duzeltilmisDegerler(k, duzeltmeler);
      const duzAlan = new Set(duzeltmeler.filter((d) => d.satir_no === k.satir_no).map((d) => d.alan));
      const kalkan = new Set();
      for (const a of duzAlan) for (const t of ALANA_GORE_KALKAN[a] || []) kalkan.add(t);
      let uyarilar = k.uyarilar.filter((u) => !kalkan.has(u.tur) && u.tur !== "tekrar_numara");
      let kit = duzeltilmisKitapcik(k, duzeltmeler) || anahtar.ana_kitapcik;
      if (!kitList.includes(kit)) {
        if (Object.keys(anahtar.kitapcik_anahtarlari || {}).length) {
          uyarilar.push({ tur: "kitapcik_okunamadi", mesaj: bicimle(UYARI.kitapcik_bilinmiyor, { k: pyRepr(kit), ana: anahtar.ana_kitapcik }), satir_no: k.satir_no });
        }
        kit = anahtar.ana_kitapcik;
      }
      const [kAnahtar, anaKendi] = kitapcikIcin(anahtar, kit);
      const kaynak = anahtar.sorular.map((s) => (anaKendi.has(s.no) ? anaKendi.get(s.no) : s.no));
      const kendi = cevaplar;
      cevaplar = kaynak.map((j) => (j - 1 < kendi.length ? kendi[j - 1] : " "));
      const r = ogrenciPuanla(cevaplar, kAnahtar, ayar, puanlar);
      let listede = true, ad = okunanAd;
      if (liste) {
        if (ls.has(no)) {
          ad = ls.get(no).ad || okunanAd;
          uyarilar = uyarilar.filter((u) => !["ad_bozuk_karakter", "ad_okunamadi", "ad_bos"].includes(u.tur));
        } else listede = false;
      }
      ogrenciler.push({ kayit: k, no, ad, okunan_ad: okunanAd, cevaplar, sorular: r.sonuclar, dogru: r.dogru, yanlis: r.yanlis, bos: r.bos,
        ham_puan: r.ham, ceza: r.ceza, puan: r.puan, listede, uyarilar, oneriler: [], kitapcik: kit, kaynak_soru: kaynak });
    }
    const sayac = new Map();
    for (const o of ogrenciler) if (o.no) { if (!sayac.has(o.no)) sayac.set(o.no, []); sayac.get(o.no).push(o); }
    for (const g of sayac.values()) if (g.length > 1) for (const o of g) {
      o.uyarilar.push({ tur: "tekrar_numara", mesaj: bicimle(UYARI.tekrar_numara, { satirlar: g.filter((x) => x !== o).map((x) => x.kayit.satir_no).join(", ") }), satir_no: o.kayit.satir_no });
    }
    let girmeyenler = [], listedeOlmayanlar = [];
    if (liste) {
      const okunan = new Set(ogrenciler.map((o) => o.no));
      girmeyenler = liste.ogrenciler.filter((o) => !okunan.has(o.no));
      const bosNo = girmeyenler.map((o) => o.no);
      for (const o of ogrenciler) if (!o.listede) {
        o.oneriler = numaraOnerileri(o.no, bosNo);
        o.uyarilar.push({ tur: "listede_yok", mesaj: o.oneriler.length ? bicimle(UYARI.listede_yok_oneri, { oneriler: o.oneriler.join(", ") }) : UYARI.listede_yok, satir_no: o.kayit.satir_no, ayrinti: o.oneriler });
        listedeOlmayanlar.push(o);
      }
    }
    return { ogrenciler, girmeyenler, listede_olmayanlar: listedeOlmayanlar, soru_puanlari: puanlar, anahtar, ayarlar: ayar, liste_var: !!liste, liste, klasik: false };
  }

  // ------------------------------------------------------------------ klasik sınav
  function puanCoz(m) {
    if (m === null || m === undefined) return null;
    if (typeof m === "number") return Kesir.of(m);
    const s = String(m).trim().replace(/ /g, "");
    if (!s) return null;
    return Kesir.ondaliktan(s);
  }
  /** "10 10 10 10 20 40" gibi soru puanı dizisi (Python: puan_listesi_coz). Virgül ondalıktır; sondaki ya da çoklu virgül ayırıcıdır. */
  function puanListesiCoz(metin) {
    const parcalar = [];
    for (let p of String(metin ?? "").trim().split(/[\s;+/|]+/)) {
      p = p.replace(/^,+|,+$/g, "");
      if (!p) continue;
      if ((p.match(/,/g) || []).length > 1) parcalar.push(...p.split(",").filter(Boolean)); else parcalar.push(p);
    }
    return parcalar.map((p) => {
      let v;
      try { v = puanCoz(p); } catch (_) { throw new Error(`Sayı değil: '${p}'`); }
      if (v === null || v.p < 0n) throw new Error(`Puan sıfır ya da daha büyük olmalı: '${p}'`);
      return v.q === 1n ? String(v.p) : p.replace(",", ".");
    });
  }
  function klasikYaz(x) {
    if (x === null) return "";
    if (x.q === 1n) return String(x.p);
    return sayiYaz(x, 2).replace(/0+$/, "").replace(/,$/, "");
  }
  function klasikDegerlendir(liste, anahtar, ayar, puanlar, toplamlar = {}) {
    toplamlar = toplamlar || {};
    const enFazla = soruPuanlari(anahtar, ayar);
    const n = anahtar.sorular.length;
    const ogrenciler = [], girmeyenler = [];
    liste.ogrenciler.forEach((og, idx) => {
      const sira = idx + 1;
      const satir = [...(puanlar[og.no] || [])];
      while (satir.length < n) satir.push(null);
      const degerler = [], uyarilar = [];
      for (let k = 0; k < n; k++) {
        try { degerler.push(puanCoz(satir[k])); } catch (_) {
          degerler.push(null);
          uyarilar.push({ tur: "cevapta_gecersiz", mesaj: `${k + 1}. soruda sayı olmayan değer: ${pyRepr(String(satir[k]))}`, satir_no: sira });
        }
      }
      if (degerler.every((x) => x === null) && !uyarilar.length) { girmeyenler.push(og); return; }
      const sonuclar = [];
      let dogru = 0, yanlis = 0, bos = 0, ham = Kesir.SIFIR;
      const eksik = [];
      degerler.forEach((x, k) => {
        const tam = enFazla[k];
        let durum, p;
        if (x === null) { eksik.push(k + 1); durum = "B"; p = Kesir.SIFIR; bos++; }
        else {
          p = x;
          if (x.kars(0) < 0) { uyarilar.push({ tur: "cevapta_gecersiz", mesaj: bicimle(UYARI.klasik_eksi, { soru: k + 1 }), satir_no: sira }); p = Kesir.SIFIR; }
          else if (x.kars(tam) > 0) uyarilar.push({ tur: "cevapta_gecersiz", mesaj: bicimle(UYARI.klasik_fazla, { soru: k + 1, puan: klasikYaz(x), en_fazla: klasikYaz(tam) }), satir_no: sira });
          if (p.kars(tam) >= 0 && tam.kars(0) > 0) { durum = "D"; dogru++; }
          else if (p.sifirMi()) { durum = "Y"; yanlis++; }
          else durum = "K";
        }
        ham = ham.ekle(p);
        sonuclar.push({ isaret: x !== null ? klasikYaz(x) : "", durum, puan: p });
      });
      if (eksik.length && eksik.length < n) uyarilar.push({ tur: "cevapta_gecersiz", mesaj: bicimle(UYARI.klasik_eksik, { sorular: eksik.join(", ") }), satir_no: sira });
      const kagit = toplamlar[og.no];
      if (kagit !== null && kagit !== undefined && kagit !== "") {
        let kt = null;
        try { kt = puanCoz(kagit); } catch (_) { kt = null; }
        if (kt === null) uyarilar.push({ tur: "cevapta_gecersiz", mesaj: `Kâğıttaki toplam sayı değil: ${pyRepr(String(kagit))}`, satir_no: sira });
        else if (!kt.esit(ham)) uyarilar.push({ tur: "cevapta_gecersiz", mesaj: bicimle(UYARI.klasik_toplam, { kagit: klasikYaz(kt), hesap: klasikYaz(ham) }), satir_no: sira });
      }
      const kayit = { satir_no: sira, ham_satir: "", ad: og.ad, ogrenci_no: og.no, cevaplar: sonuclar.map((s) => s.isaret), kitapcik: "", uyarilar: [] };
      ogrenciler.push({ kayit, no: og.no, ad: og.ad, okunan_ad: og.ad, cevaplar: sonuclar.map((s) => s.isaret), sorular: sonuclar, dogru, yanlis, bos,
        ham_puan: ham, ceza: Kesir.SIFIR, puan: ham.kars(0) < 0 ? Kesir.SIFIR : ham, listede: true, uyarilar, oneriler: [], kitapcik: "",
        kaynak_soru: Array.from({ length: n }, (_, i) => i + 1) });
    });
    return { ogrenciler, girmeyenler, listede_olmayanlar: [], soru_puanlari: enFazla, anahtar, ayarlar: ayar, liste_var: true, liste, klasik: true };
  }
  function tablodanKlasikPuanlar(tablo, soruSayisi) {
    const e = eslemeTahminEt(tablo);
    const notlar = [];
    if (e.no_sutun === null) return [{}, ["Numara sütunu bulunamadı."]];
    const baslik = e.baslik_satiri ? tablo[e.baslik_satiri - 1] : [];
    const soruSutun = new Map();
    baslik.forEach((h, j) => {
      const m = /^(?:s|soru|q)?(\d{1,3})(?:puan|p)?$/.exec(sade(h));
      if (m && j + 1 !== e.no_sutun) { const k = parseInt(m[1], 10); if (k >= 1 && k <= soruSayisi && !soruSutun.has(k)) soruSutun.set(k, j); }
    });
    if (!soruSutun.size) {
      const bas = Math.max(e.no_sutun, e.ad_sutun || 0, e.soyad_sutun || 0);
      for (let k = 1; k <= soruSayisi; k++) soruSutun.set(k, bas + k - 1);
      notlar.push(`Soru başlıkları bulunamadı; ${bas + 1}. sütundan başlayan ${soruSayisi} sütun soru sayıldı.`);
    }
    const puanlar = {};
    for (const s of tablo.slice(e.baslik_satiri || 0)) {
      const no = numaraNormalle(e.no_sutun - 1 < s.length ? s[e.no_sutun - 1] : null);
      if (!no || !rakamMi(no)) continue;
      const d = [];
      for (let k = 1; k <= soruSayisi; k++) {
        const j = soruSutun.get(k);
        let x = j !== undefined && j < s.length ? s[j] : null;
        d.push(x === null || x === undefined || x === "" ? null : String(x));
      }
      puanlar[no] = d;
    }
    const eksik = [];
    for (let k = 1; k <= soruSayisi; k++) if (!soruSutun.has(k)) eksik.push(k);
    if (eksik.length) notlar.push("Sütunu bulunamayan sorular: " + eksik.join(", "));
    return [puanlar, notlar];
  }

  // ------------------------------------------------------------------ ders bilgi paketi (metin)
  const kodSirala = (k) => k.split(/(\d+)/).map((p) => (/^\d+$/.test(p) ? parseInt(p, 10) : p));
  function dogalKarsilastir(a, b) {
    const x = kodSirala(a), y = kodSirala(b);
    for (let i = 0; i < Math.max(x.length, y.length); i++) {
      if (x[i] === undefined) return -1;
      if (y[i] === undefined) return 1;
      if (x[i] < y[i]) return -1;
      if (x[i] > y[i]) return 1;
    }
    return 0;
  }
  function dersPaketiCoz(metin) {
    const satirlar = metin.replace(/\r/g, "").split("\n").map((s) => s.trim());
    let kod = "", ad = "";
    for (const s of satirlar.slice(0, 8)) {
      const m = /^([A-ZÇĞİÖŞÜ]{2,5}\d{3,5})\s+(.+)$/.exec(s);
      if (m) { kod = m[1]; ad = m[2].trim(); break; }
    }
    let program = "";
    for (let i = 0; i < satirlar.length; i++) if (/^Bölümü\s*\/\s*Programı/.test(satirlar[i]) && i + 1 < satirlar.length) { program = satirlar[i + 1]; break; }
    function bolum(baslik, onek) {
      const bas = satirlar.indexOf(baslik);
      if (bas < 0) return [];
      const r = [];
      const desen = new RegExp(`^(${onek}\\d{1,2})\\s+(.*)$`);
      for (const s of satirlar.slice(bas + 1)) {
        const m = desen.exec(s);
        if (m) r.push({ kod: m[1], aciklama: m[2].trim() });
        else if (s.startsWith("Sıra No") || !s) continue;
        else if (r.length && !/^(Dersin|Programın|Değerlendirme|Katkı|Yarıyıl|P\d|Ö\d|Tüm)(\s|$)/.test(s)) r[r.length - 1].aciklama += " " + s;
        else break;
      }
      return r.sort((a, b) => dogalKarsilastir(a.kod, b.kod));
    }
    const katki = {};
    for (let i = 0; i < satirlar.length; i++) {
      if (/^(P\d{1,2}\s*)+$/.test(satirlar[i]) && i + 1 < satirlar.length) {
        const kodlar = satirlar[i].split(/\s+/);
        const m = /^Tüm\s+([\d\s]+)$/.exec(satirlar[i + 1]);
        if (m) m[1].trim().split(/\s+/).map(Number).forEach((d, j) => { if (j < kodlar.length) katki[kodlar[j]] = d; });
      }
    }
    const degerlendirme = {};
    for (const s of satirlar) {
      const m = /^(Ara Sınav|Kısa Sınav|Ödev|Devam|Uygulama|Proje|Yarıyıl Sonu Sınavı)\s+\d+\s+%(\d+)(?:\s|$)/.exec(s);
      if (m && parseInt(m[2], 10) > 0) degerlendirme[m[1]] = parseInt(m[2], 10);
    }
    return { kod, ad, program, ogrenme_ciktilari: bolum("Dersin Öğrenme Çıktıları", "Ö"), program_ciktilari: bolum("Programın Öğrenme Çıktıları", "P"), katki, degerlendirme };
  }

  Object.assign(OS, {
    Kesir, topla, yuvarla, ondalikMetni, ondalikSayi, sayiYaz, pyOndalik, v, kesirYuvarlaCift,
    fmean, pvariance, variance, pstdev, stdev, median, ceyrekler,
    SIKLAR, CIFT, BOZUK, UYARI, EKSIK, DURUM_ADI, SORU_DURUMU_ADI, bicimle,
    yeniOkuyucu, yeniSoru, yeniAyarlar, yeniProje, projeyiTamamla,
    esitYuzdeler, dogruKume, ciktiDagilimi, kitapciklar, esleme, eslemeSorunlari, kitapcikIcin, anahtarMetinden, anahtarMetne,
    soruPuanlari, esitSoruPuanlari, soruDegerlendir, ogrenciPuanla, net, anahtarEksikleri,
    baytlariCoz, metinDosyasiOku, satirlaraBol, alanlar, satiriCoz, satirlariOku, soruSayisiOner, sablonOner,
    sade, numaraNormalle, eslemeTahminEt, sayfaSec, tablodanListe, pdfHucrelerindenTablo,
    duzeltilmisDegerler, duzeltilmisKitapcik, duzeltmeOlustur, numaraOnerileri, sinaviDegerlendir,
    puanCoz, puanListesiCoz, klasikYaz, klasikDegerlendir, tablodanKlasikPuanlar, dersPaketiCoz, dogalKarsilastir,
  });
})(typeof globalThis !== "undefined" ? globalThis : window);
