/* Optik Sınav — tarayıcı sürümü: ortak durum, yardımcılar, kabuk ve 1-3. adımlar.
 * Dosyalar yalnızca bu bilgisayarda, tarayıcının içinde okunur; hiçbir yere gönderilmez.
 */
(function () {
  "use strict";
  const OS = window.OS;
  const UI = (window.UI = {});

  // ------------------------------------------------------------------ yardımcılar
  const e = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const $ = (s, k = document) => k.querySelector(s);
  const $$ = (s, k = document) => [...k.querySelectorAll(s)];
  function bildir(m, sure = 3500) {
    document.querySelectorAll(".bildirim").forEach((x) => x.remove());
    const b = document.createElement("div");
    b.className = "bildirim";
    b.textContent = m;
    document.body.appendChild(b);
    setTimeout(() => b.remove(), sure);
  }
  /** Basit pencere. dugmeler: [{metin, deger, ana}] ; döndürür: Promise(deger) */
  function pencere(baslik, icerik, dugmeler = [{ metin: "Tamam", deger: true, ana: true }], hazir = null) {
    return new Promise((coz) => {
      const perde = document.createElement("div");
      perde.className = "perde";
      perde.innerHTML = `<div class="pencere" role="dialog" aria-modal="true"><h3>${baslik}</h3><div class="pi"></div><div class="dugmeler"></div></div>`;
      const pi = $(".pi", perde);
      if (typeof icerik === "string") pi.innerHTML = icerik; else pi.appendChild(icerik);
      const kapat = (d) => { perde.remove(); document.removeEventListener("keydown", tus); coz(d); };
      for (const d of dugmeler) {
        const b = document.createElement("button");
        b.textContent = d.metin;
        if (d.ana) b.className = "ana";
        b.onclick = () => { if (d.denetle && !d.denetle(perde)) return; kapat(typeof d.deger === "function" ? d.deger(perde) : d.deger); };
        $(".dugmeler", perde).appendChild(b);
      }
      const tus = (ev) => { if (ev.key === "Escape") kapat(null); };
      document.addEventListener("keydown", tus);
      perde.addEventListener("mousedown", (ev) => { if (ev.target === perde) kapat(null); });
      document.body.appendChild(perde);
      if (hazir) hazir(perde);
      const ilk = $("input, select, textarea", perde) || $("button.ana", perde);
      if (ilk) ilk.focus();
    });
  }
  const bilgi = (baslik, metin) => pencere(baslik, `<div style="white-space:pre-wrap">${e(metin)}</div>`);
  const onay = (baslik, metin) => pencere(baslik, `<div style="white-space:pre-wrap">${e(metin)}</div>`, [{ metin: "Vazgeç", deger: false }, { metin: "Evet", deger: true, ana: true }]);
  function dosyaSec(kabul, coklu = false) {
    return new Promise((coz) => {
      const i = document.createElement("input");
      i.type = "file";
      i.accept = kabul;
      i.multiple = coklu;
      i.onchange = () => coz(coklu ? [...i.files] : i.files[0] || null);
      i.click();
    });
  }
  const baytOku = (f) => f.arrayBuffer().then((b) => new Uint8Array(b));
  function indir(veri, ad, tur = "application/octet-stream") {
    const blob = veri instanceof Blob ? veri : new Blob([veri], { type: tur });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = ad;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
  }
  async function kopyala(metin) {
    try { await navigator.clipboard.writeText(metin); return true; } catch (_) { /* eski yol */ }
    const t = document.createElement("textarea");
    t.value = metin;
    t.style.position = "fixed";
    t.style.opacity = "0";
    document.body.appendChild(t);
    t.select();
    let tamam = false;
    try { tamam = document.execCommand("copy"); } catch (_) { tamam = false; }
    t.remove();
    return tamam;
  }
  const yerel = {
    al(k, varsayilan = null) { try { const v = localStorage.getItem(k); return v === null ? varsayilan : JSON.parse(v); } catch (_) { return varsayilan; } },
    koy(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (_) { return false; } },
    sil(k) { try { localStorage.removeItem(k); } catch (_) { /* yok */ } },
  };
  const b64 = {
    yaz(u8) { let s = ""; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode(...u8.subarray(i, i + 0x8000)); return btoa(s); },
    oku(t) { const s = atob(t); const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return u; },
  };
  /** Açılır menü: sık kullanılmayan işlemler için. ogeler: hazır <button> HTML'leri. */
  const acilirMenu = (etiket, ogeler, id = "") => `<details class="acilir"${id ? ` id="${id}"` : ""}><summary>${etiket} ▾</summary><div class="menu">${ogeler.join("")}</div></details>`;
  document.addEventListener("click", (ev) => {
    for (const d of document.querySelectorAll("details.acilir[open]")) {
      if (!d.contains(ev.target) || (ev.target.closest(".menu button"))) d.removeAttribute("open");
    }
  });
  Object.assign(UI, { e, $, $$, bildir, pencere, bilgi, onay, dosyaSec, baytOku, indir, kopyala, yerel, b64, acilirMenu });

  // ------------------------------------------------------------------ durum
  const D = (UI.D = {
    proje: OS.yeniProje(), okuma: null, datBayt: null, liste: null, listeBayt: null, ders: null, sonuc: null, adim: 0,
    anahtarKitapcik: null, etkin: 0,
  });
  UI.dersler = function () {
    const r = Object.assign({}, window.DERSLER || {});
    Object.assign(r, yerel.al("os_dersler", {}));
    return r;
  };
  UI.dersiYukle = function () {
    const kod = (D.proje.sinav.ders_kodu || "").toUpperCase().replace(/[^A-ZÇĞİÖŞÜ0-9]/g, "");
    D.ders = kod ? UI.dersler()[kod] || null : null;
    if (D.ders && !D.proje.sinav.ders_adi) D.proje.sinav.ders_adi = D.ders.ad;
    return D.ders;
  };
  UI.ogrenmeKodlari = () => (D.ders ? D.ders.ogrenme_ciktilari.map((c) => c.kod) : []);
  UI.programKodlari = () => (D.ders ? D.ders.program_ciktilari.map((c) => c.kod) : []);
  UI.aciklamalar = () => { const r = {}; if (D.ders) for (const c of [...D.ders.ogrenme_ciktilari, ...D.ders.program_ciktilari]) r[c.kod] = c.aciklama; return r; };
  UI.soruSayisi = () => (D.proje.bicim === "klasik" ? D.proje.klasik_soru_sayisi : D.proje.okuyucu.soru_sayisi);
  UI.anahtariBoyutla = function () {
    const n = UI.soruSayisi();
    const s = D.proje.anahtar.sorular;
    while (s.length < n) s.push(OS.yeniSoru(s.length + 1));
    if (s.length > n) s.splice(n);
    // Klasik sınavda hiç soru puanı yoksa toplam eşit dağıtılır (2. adım atlanırsa da puan girişi hemen açılsın)
    if (D.proje.bicim === "klasik" && s.length && s.every((x) => x.puan === null || x.puan === undefined || x.puan === "")) {
      try { OS.esitSoruPuanlari(D.proje.ayarlar.toplam_puan, s.length).forEach((x, i) => (s[i].puan = x)); } catch (_) { /* toplam puan geçersiz */ }
    }
  };
  UI.datYukle = function (bayt, ad, sablonuOner = true) {
    D.datBayt = bayt;
    D.proje.dat_yolu = ad;
    const m = OS.metinDosyasiOku(bayt);
    D.hamSatirlar = m.satirlar;
    if (sablonuOner) D.proje.okuyucu = OS.sablonOner(m.satirlar, D.proje.okuyucu);
    UI.datYenidenOku();
  };
  UI.datYenidenOku = function () {
    if (!D.datBayt) { D.okuma = null; UI.anahtariBoyutla(); return; }
    const m = OS.metinDosyasiOku(D.datBayt);
    const r = OS.satirlariOku(m.satirlar, D.proje.okuyucu);
    D.okuma = { kayitlar: r.kayitlar, kodlama: m.kodlama, satir_sonu: m.satir_sonu, bos: r.bos };
    UI.anahtariBoyutla();
    D.sonuc = null;
  };
  UI.listeYukle = function (bayt, ad, esleme = null) {
    if (!bayt) { D.liste = null; D.listeBayt = null; D.proje.liste_yolu = ""; return; }
    D.liste = OS.listeOku(window.XLSX, bayt, ad, esleme);
    D.listeBayt = bayt;
    D.proje.liste_yolu = ad;
    D.proje.liste_esleme = D.liste.esleme;
    D.sonuc = null;
  };
  // Sonucun hesaplanmasına engel olan eksikler (masaüstündeki Durum.hesap_eksikleri ile aynı)
  UI.hesapEksikleri = function () {
    const p = D.proje, kl = p.bicim === "klasik", e2 = [];
    if (kl) { if (!D.liste) e2.push("Klasik sınavda öğrenci listesi gerekli."); }
    else if (!D.okuma) e2.push(OS.EKSIK.dat);
    if (!isFinite(parseFloat(String(p.ayarlar.toplam_puan).replace(",", ".")))) { e2.push("Toplam puan sayı olmalı."); return e2; }
    if (D.okuma || kl) e2.push(...OS.anahtarEksikleri(p.anahtar, p.ayarlar, kl));
    return e2;
  };
  UI.degerlendir = function () {
    const p = D.proje;
    if (UI.hesapEksikleri().length) D.sonuc = null;
    else if (p.bicim === "klasik") D.sonuc = D.liste ? OS.klasikDegerlendir(D.liste, p.anahtar, p.ayarlar, p.klasik_puanlar, p.klasik_toplamlar, p.klasik_girmedi) : null;
    else D.sonuc = D.okuma ? OS.sinaviDegerlendir(D.okuma.kayitlar, p.anahtar, p.ayarlar, D.liste, p.duzeltmeler) : null;
    return D.sonuc;
  };
  UI.duzelt = function (satirNo, alan, yeni) {
    const k = D.okuma.kayitlar.find((x) => x.satir_no === satirNo);
    const d = OS.duzeltmeOlustur(k, alan, yeni, D.proje.duzeltmeler);
    if (d.eski === d.yeni) return;
    D.proje.duzeltmeler.push(d);
    UI.degerlendir();
  };
  UI.bicimDegistir = function (b) {
    D.proje.bicim = b;
    if (b === "klasik") { D.proje.ayarlar.yontem = "soru_bazli"; D.proje.ayarlar.yanlis_cezasi = false; }
    UI.anahtariBoyutla();
    D.sonuc = null;
  };
  UI.klasikSoruSayisi = function (n) {
    const s = D.proje.anahtar.sorular;
    const esit = OS.esitSoruPuanlari(D.proje.ayarlar.toplam_puan, s.length);
    if (s.map((x) => x.puan).join("|") === esit.join("|")) for (const x of s) x.puan = null;
    D.proje.klasik_soru_sayisi = Math.max(1, n);
    UI.anahtariBoyutla();
  };

  // ------------------------------------------------------------------ proje dosyası (.osd: masaüstü programla ortak)
  UI.projeVerisi = function (gomulu = true) {
    const p = JSON.parse(JSON.stringify(D.proje));
    if (gomulu) p.gomulu_dosyalar = { dat: D.datBayt ? b64.yaz(D.datBayt) : null, liste: D.listeBayt ? b64.yaz(D.listeBayt) : null };
    return p;
  };
  UI.projeAc = function (veri) {
    const g = veri.gomulu_dosyalar || {};
    D.proje = OS.projeyiTamamla(veri);
    D.datBayt = null; D.okuma = null; D.liste = null; D.listeBayt = null; D.sonuc = null; D.hamSatirlar = [];
    const eksik = [];
    if (g.dat) { D.datBayt = b64.oku(g.dat); D.hamSatirlar = OS.metinDosyasiOku(D.datBayt).satirlar; UI.datYenidenOku(); }
    else if (D.proje.dat_yolu && D.proje.bicim !== "klasik") eksik.push(D.proje.dat_yolu);
    if (g.liste && /\.pdf$/i.test(D.proje.liste_yolu || "")) {
      // masaüstünde PDF listesiyle kaydedilmiş sınav: PDF okuması zaman uyumsuz, bitince sayfa yenilenir
      UI.pdfListeYukle(b64.oku(g.liste), D.proje.liste_yolu).then(() => UI.ciz()).catch((h) => bilgi("Liste okunamadı", String(h.message || h)));
    } else if (g.liste) UI.listeYukle(b64.oku(g.liste), D.proje.liste_yolu, D.proje.liste_esleme && D.proje.liste_esleme.no_sutun ? D.proje.liste_esleme : null);
    else if (D.proje.liste_yolu) eksik.push(D.proje.liste_yolu);
    UI.anahtariBoyutla();
    UI.dersiYukle();
    return eksik;
  };
  UI.otomatikKaydet = function () { yerel.koy("os_son_proje", UI.projeVerisi(true)); };

  // ------------------------------------------------------------------ ders bilgi paketi PDF'i
  /** PDF belgesini açar. Baytların kopyası verilir: pdf.js veriyi işçiye devreder, aynı dosya ikinci kez okunabilsin. */
  UI.pdfBelgesi = async function (bayt) {
    const lib = window.pdfjsLib;
    if (!lib) throw new Error("PDF okuyucu yüklenemedi.");
    if (!lib.GlobalWorkerOptions.workerSrc) {
      if (!UI.pdfIsciKaynagi) throw new Error("PDF okuyucunun işçisi bulunamadı.");
      lib.GlobalWorkerOptions.workerSrc = URL.createObjectURL(new Blob([UI.pdfIsciKaynagi], { type: "text/javascript" }));
    }
    return lib.getDocument({ data: new Uint8Array(bayt).slice(), isEvalSupported: false }).promise;
  };
  UI.pdfMetni = async function (bayt) {
    const pdf = await UI.pdfBelgesi(bayt);
    const satirlar = [];
    for (let s = 1; s <= pdf.numPages; s++) {
      const sayfa = await pdf.getPage(s);
      const ic = await sayfa.getTextContent();
      const gruplar = [];
      for (const it of ic.items) {
        if (!it.str || !it.str.trim()) continue;
        const y = it.transform[5], x = it.transform[4];
        let g = gruplar.find((q) => Math.abs(q.y - y) < 2.5);
        if (!g) { g = { y, parca: [] }; gruplar.push(g); }
        g.parca.push([x, it.str, it.width || 0, Math.abs(it.transform[3]) || 10]);
      }
      gruplar.sort((a, b) => b.y - a.y);
      for (const g of gruplar) satirlar.push(UI.parcalariBirlestir(g.parca));
    }
    return satirlar.join("\n");
  };
  /** Aynı satırdaki metin parçalarını soldan sağa boşlukla birleştirir (Akademik Bilgi Sistemi PDF'lerinde denendi). */
  UI.parcalariBirlestir = function (parca) {
    parca.sort((a, b) => a[0] - b[0]);
    let m = "";
    let son = null;
    for (const [x, str, w, h] of parca) {
      if (son !== null) m += " ";
      m += str;
      son = x + w;
    }
    return m.replace(/\s+/g, " ").trim();
  };
  /** PDF'in her satırını hücrelere böler: aynı satırdaki parçalar arasında yazı boyunun 0,6 katından geniş boşluk sütun ayırır. */
  UI.pdfHucreleri = async function (bayt) {
    const pdf = await UI.pdfBelgesi(bayt);
    const satirlar = [];
    for (let s = 1; s <= pdf.numPages; s++) {
      const ic = await (await pdf.getPage(s)).getTextContent();
      const gruplar = [];
      for (const it of ic.items) {
        if (!it.str || !it.str.trim()) continue;
        const y = it.transform[5];
        let g = gruplar.find((q) => Math.abs(q.y - y) < 2.5);
        if (!g) { g = { y, parca: [] }; gruplar.push(g); }
        g.parca.push([it.transform[4], it.str, it.width || 0, Math.abs(it.transform[3]) || 10]);
      }
      gruplar.sort((a, b) => b.y - a.y);
      for (const g of gruplar) {
        g.parca.sort((a, b) => a[0] - b[0]);
        const hucreler = [];
        let son = null;
        for (const [x, str, w, h] of g.parca) {
          if (son === null || x - son > 0.6 * h) hucreler.push(str);
          else hucreler[hucreler.length - 1] += (x - son > 0.15 * h ? " " : "") + str;
          son = x + w;
        }
        satirlar.push(hucreler);
      }
    }
    return satirlar;
  };
  /** Öğrenci listesi PDF'ini tabloya çevirip sekmeyle ayrılmış metin olarak yükler (sınav dosyasına da öyle gömülür). */
  UI.pdfListeYukle = async function (bayt, ad) {
    const tablo = OS.pdfHucrelerindenTablo(await UI.pdfHucreleri(bayt));
    if (tablo.length < 2) throw new Error("Bu PDF'te öğrenci numarası bulunamadı. Taranmış (resim) PDF ise okunamaz; sistemden listeyi Excel olarak indirmeyi deneyin.");
    const metin = tablo.map((r) => r.join("\t")).join("\r\n") + "\r\n";
    UI.listeYukle(new TextEncoder().encode(metin), ad.replace(/\.pdf$/i, "") + " (PDF).txt");
  };
  UI.dersPdfYukle = async function (bayt) {
    const metin = await UI.pdfMetni(bayt);
    const d = OS.dersPaketiCoz(metin);
    if (!d.kod || !d.ogrenme_ciktilari.length) throw new Error("Bu PDF'te ders kodu ya da 'Dersin Öğrenme Çıktıları' bölümü bulunamadı. Akademik Bilgi Sistemi'nden indirilen ders bilgi paketini seçin.");
    const kayitli = yerel.al("os_dersler", {});
    kayitli[d.kod] = d;
    yerel.koy("os_dersler", kayitli);
    D.proje.sinav.ders_kodu = d.kod;
    D.proje.sinav.ders_adi = d.ad;
    D.ders = d;
    return d;
  };

  // ------------------------------------------------------------------ kabuk
  const ADIMLAR = ["Sınav ve dosyalar", "Cevap anahtarı", "Puanlama", "Kontrol ve düzeltme", "İstatistikler", "Dışa aktar"];
  UI.adimlar = [];
  UI.ciz = function () {
    const a = UI.adimlar[D.adim];
    $("#icerik").innerHTML = "";
    a.ciz($("#icerik"));
    UI.altGuncelle();
    // Hazırlık adımları (1-3): kendisi ve öncekiler eksiksizse listede ✓; sonuç adımlarında (4-6) eksikler üstte şerit
    const on = [0, 1, 2].map((j) => UI.adimlar[j].eksikler());
    let tamam = true;
    $$("nav.adimlar button[data-adim]").forEach((b) => {
      const j = Number(b.dataset.adim);
      b.classList.toggle("secili", j === D.adim);
      if (j < 3) { tamam = tamam && !on[j].length; b.querySelector(".tamam").textContent = tamam ? "✓" : ""; }
      if (j === 1) b.childNodes[1].textContent = D.proje.bicim === "klasik" ? "Sorular ve puanlar" : ADIMLAR[1];
    });
    if (D.adim >= 3 && !D.sonuc) {
      let sat = on.map((x, j) => (x.length ? `<a href="#" data-git="${j}">${j + 1}. adım</a>: ${e(x.join(" "))}` : "")).filter(Boolean);
      if (!sat.length) sat = [e(UI.hesapEksikleri().join(" "))].filter(Boolean);
      if (sat.length) {
        $("#icerik").insertAdjacentHTML("afterbegin", `<div class="serit"><b>Sonuç için önce bunlar tamamlanmalı.</b><br>${sat.join("<br>")}</div>`);
        $$("#icerik .serit a[data-git]").forEach((x) => (x.onclick = (ev) => { ev.preventDefault(); UI.git(Number(x.dataset.git)); }));
      }
    }
    UI.otomatikKaydet();
  };
  UI.altGuncelle = function () {
    const ek = UI.adimlar[D.adim].eksikler();
    $("#eksik").textContent = ek.length ? "Eksik: " + ek.join(" ") : "";
    $("#geri").disabled = D.adim === 0;
    $("#sonraki").disabled = D.adim === ADIMLAR.length - 1;  // eksikler gezinmeyi engellemez, yalnızca gösterilir
  };
  UI.git = function (i) {
    if (i < 0 || i >= ADIMLAR.length) return;
    D.adim = i;
    if (UI.adimlar[i].girildi) UI.adimlar[i].girildi();
    UI.ciz();
    $("#icerik").scrollTop = 0;
  };
  UI.kabuk = function () {
    const isci = document.getElementById("pdf-isci");
    if (isci) UI.pdfIsciKaynagi = isci.textContent;
    document.body.innerHTML = `
      <div class="ust">
        <h1>Optik Sınav Değerlendirme</h1>
        <button id="yeni">Yeni sınav</button>
        <button id="ac">Aç…</button>
        <button id="kaydet">Kaydet</button>
        <span class="bosluk"></span>
        <span class="not">Çevrim dışı çalışır; dosyalarınız bu bilgisayardan çıkmaz.</span>
        <button id="yardim">Yardım</button>
      </div>
      <div class="govde">
        <nav class="adimlar">${ADIMLAR.map((a, i) => `<button data-adim="${i}"><span class="no">${i + 1}.</span>${a}<span class="tamam"></span></button>`).join("")}
          <div class="gizlilik">Program internete bağlanmaz. Öğrenci verisi yalnızca bu tarayıcıda işlenir. Son çalışma bu tarayıcıda saklanır; ortak bilgisayarda işiniz bitince "Yeni sınav"a basın.</div>
        </nav>
        <main><div id="icerik"></div>
          <div class="alt"><span class="eksik" id="eksik"></span><button id="geri">Geri</button><button id="sonraki" class="ana">Sonraki</button></div>
        </main>
      </div>`;
    $$("nav.adimlar button[data-adim]").forEach((b) => (b.onclick = () => UI.git(Number(b.dataset.adim))));
    $("#geri").onclick = () => UI.git(D.adim - 1);
    $("#sonraki").onclick = () => UI.git(D.adim + 1);
    $("#yeni").onclick = async () => {
      if (!(await onay("Yeni sınav", "Açık sınav kapatılsın mı? Kaydetmediyseniz önce Kaydet'e basın."))) return;
      yerel.sil("os_son_proje");
      Object.assign(D, { proje: OS.yeniProje(), okuma: null, datBayt: null, liste: null, listeBayt: null, ders: null, sonuc: null, adim: 0, anahtarKitapcik: null, etkin: 0, hamSatirlar: [] });
      UI.ciz();
    };
    $("#ac").onclick = async () => { const f = await dosyaSec(".osd,.json"); if (f) UI.dosyaAc(f); };
    $("#kaydet").onclick = () => {
      indir(JSON.stringify(UI.projeVerisi(true), null, 1), OS.ciktiAdi(D.proje.sinav, "sinav", ".osd"), "application/json");
      bildir("Sınav dosyası indirildi. Optik dosya ve öğrenci listesi içine gömülüdür; açınca her şey geri gelir.");
    };
    $("#yardim").onclick = () => UI.yardim();
    document.addEventListener("keydown", (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter" && !$("#sonraki").disabled) { ev.preventDefault(); UI.git(D.adim + 1); }
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") { ev.preventDefault(); $("#kaydet").click(); }
    });
    // Pencereye bırakılan dosyalar
    window.addEventListener("dragover", (ev) => ev.preventDefault());
    window.addEventListener("drop", (ev) => {
      ev.preventDefault();
      for (const f of ev.dataTransfer.files) UI.dosyaAc(f);
    });
  };
  /** Uzantıya göre: .osd sınav, .pdf ders paketi, .xlsx/.xls/.csv liste, diğerleri optik dosya. */
  UI.dosyaAc = async function (f) {
    const uz = (f.name.split(".").pop() || "").toLowerCase();
    try {
      const bayt = await baytOku(f);
      if (uz === "osd" || uz === "json") {
        const eksik = UI.projeAc(JSON.parse(new TextDecoder().decode(bayt)));
        D.adim = 0;
        UI.ciz();
        if (eksik.length) bilgi("Eksik dosya", "Bu sınav dosyası masaüstü programda kaydedilmiş; içinde şu dosyalar yok, 1. adımda yeniden seçin:\n" + eksik.join("\n"));
      } else if (uz === "pdf") {
        // PDF ders bilgi paketi mi, öğrenci listesi mi? Önce ders paketi denenir, olmazsa liste.
        let d = null;
        try { d = await UI.dersPdfYukle(bayt); } catch (_) { d = null; }
        if (d) {
          UI.ciz();
          bildir(`${d.kod} ${d.ad}: ${d.ogrenme_ciktilari.length} öğrenme çıktısı okundu ve bu tarayıcıda saklandı.`, 5000);
        } else {
          await UI.pdfListeYukle(bayt, f.name);
          UI.ciz();
          bildir(`Öğrenci listesi PDF'ten okundu: ${D.liste.ogrenciler.length} öğrenci. Numara ve ad sütunlarını aşağıdaki listeden kontrol edin.`, 6000);
        }
      } else if (["xlsx", "xls", "csv", "xlsm"].includes(uz)) {
        UI.listeYukle(bayt, f.name);
        UI.ciz();
      } else {
        UI.datYukle(bayt, f.name);
        UI.ciz();
      }
    } catch (hata) {
      bilgi("Dosya açılamadı", `${f.name}\n\n${hata.message || hata}`);
    }
  };

  // ------------------------------------------------------------------ 1. adım
  const SINAV_TURLERI = ["Ara Sınav", "Yarıyıl Sonu", "Bütünleme", "Mazeret"];
  // durum: "zorunlu" (seçilmesi gereken, henüz seçilmemiş: yeşil, belirgin), "tamam" (seçildi) ya da boş
  function birakAlani(id, baslik, alt, bilgiMetni, durum = "") {
    const dugme = durum === "zorunlu" ? `<div><span class="zorunlu-dugme">Dosyayı seç…</span></div>` : "";
    return `<div class="birak ${durum}" id="${id}" tabindex="0"><div class="baslik">${durum === "tamam" ? "✓ " : ""}${baslik}</div><div class="soluk">${alt}</div>
      ${dugme}<div style="margin-top:8px">${bilgiMetni}</div></div>`;
  }
  function onizlemeHtml() {
    const o = D.proje.okuyucu;
    const renk = {};
    for (const [ad, bas, uz] of OS.alanlar(o)) for (let i = bas; i < bas + uz; i++) renk[i] = ad;
    const sat = D.hamSatirlar.slice(0, 8);
    const uzunluk = Math.max(0, ...sat.map((x) => x.length));
    const cetvel1 = Array.from({ length: uzunluk }, (_, i) => ((i + 1) % 10 === 0 ? String(Math.floor((i + 1) / 10) % 10) : " ")).join("");
    const cetvel2 = Array.from({ length: uzunluk }, (_, i) => String((i + 1) % 10)).join("");
    const satirlar = sat.map((x) => [...x].map((c, i) => {
      const r = renk[i + 1] || (/\S/.test(c) ? "disari" : null);
      return r ? `<span class="${r}">${e(c)}</span>` : e(c);
    }).join(""));
    return `<div class="soluk" style="font-size:12px">Renkler: <span style="background:#ddebf7;color:#000">&nbsp;ad&nbsp;</span> <span style="background:#e2efda;color:#000">&nbsp;numara&nbsp;</span> <span style="background:#fff2cc;color:#000">&nbsp;cevaplar&nbsp;</span> <span style="background:#ead1f5;color:#000">&nbsp;kitapçık&nbsp;</span> <span style="background:#f8cbad;color:#000">&nbsp;alan dışı işaret&nbsp;</span></div>
      <pre class="onizleme">${e(cetvel1)}\n${e(cetvel2)}\n${satirlar.join("\n")}</pre>`;
  }
  const adim1 = {
    eksikler() {
      const e2 = [];
      if (D.proje.bicim === "klasik") { if (!D.liste) e2.push("Klasik sınavda öğrenci listesi gerekli."); }
      else if (!D.okuma) e2.push(OS.EKSIK.dat);
      if (UI.soruSayisi() <= 0) e2.push(OS.EKSIK.soru_sayisi);
      return e2;
    },
    ciz(k) {
      const p = D.proje, s = p.sinav, kl = p.bicim === "klasik";
      UI.dersiYukle();
      const dersler = UI.dersler();
      const d = D.ders;
      const dersBilgi = d ? `<b>${e(d.kod)} ${e(d.ad)}</b> (${e(d.program)}): ${d.ogrenme_ciktilari.length} öğrenme çıktısı (${d.ogrenme_ciktilari.map((c) => e(c.kod)).join(", ")}), ${d.program_ciktilari.length} program çıktısı.${Object.keys(d.degerlendirme || {}).length ? " Değerlendirme: " + Object.entries(d.degerlendirme).map(([a, b]) => `${e(a)} %${b}`).join(", ") : ""}`
        : `<span class="soluk">Bu ders kodu için ders bilgi paketi yok. PDF'i yükleyin ya da çıktı kodlarını 2. adımda elle yazın.</span>`;
      const o = D.okuma;
      const uyarili = o ? o.kayitlar.filter((x) => x.uyarilar.length).length : 0;
      const datBilgi = o ? `<b>${e(p.dat_yolu)}</b><br>${o.kayitlar.length} öğrenci, ${p.okuyucu.soru_sayisi} soru okundu. Okuma uyarısı olan satır: ${uyarili}.`
        : `<span class="soluk">ya da dosyayı buraya sürükleyin</span>`;
      const l = D.liste;
      const listeBilgi = l ? `<b>${e(p.liste_yolu)}</b><br>${l.ogrenciler.length} öğrenci${l.ogrenciler[0] ? `; ilk: ${e(l.ogrenciler[0].no)} ${e(l.ogrenciler[0].ad)}` : ""} <button class="kucuk" id="listeKaldir">Kaldır</button>`
        : `<span class="soluk">Tıklayın ya da dosyayı buraya sürükleyin</span>`;
      const gelismisAcik = o && o.kayitlar.length && uyarili > o.kayitlar.length * 0.3;
      const r = p.okuyucu;
      const alanlar = [["ad_baslangic", "Ad başlangıcı"], ["ad_uzunluk", "Ad uzunluğu"], ["no_baslangic", "Numara başlangıcı"], ["no_uzunluk", "Numara uzunluğu"],
        ["cevap_baslangic", "Cevap başlangıcı"], ["soru_sayisi", "Soru sayısı"], ["kitapcik_baslangic", "Kitapçık başlangıcı (0 = yok)"]];
      let listeEsleme = "";
      if (l && l.sayfalar) {
        const es = l.esleme;
        const tablo = l.sayfalar[es.sayfa || Object.keys(l.sayfalar)[0]] || [];
        const gen = Math.max(0, ...tablo.map((x) => x.length));
        const bas = es.baslik_satiri ? tablo[es.baslik_satiri - 1] || [] : [];
        const secenek = (sec, yok) => (yok ? `<option value="">(yok)</option>` : "") + Array.from({ length: gen }, (_, j) => `<option value="${j + 1}" ${sec === j + 1 ? "selected" : ""}>${j + 1}. sütun${bas[j] ? ": " + e(bas[j]) : ""}</option>`).join("");
        listeEsleme = `<h3>Öğrenci listesi sütunları</h3><div class="satir">
          <label>Sayfa</label><select id="lSayfa">${Object.keys(l.sayfalar).map((a) => `<option ${a === es.sayfa ? "selected" : ""}>${e(a)}</option>`).join("")}</select>
          <label>Başlık satırı</label><input type="number" id="lBaslik" min="0" style="width:60px" value="${es.baslik_satiri || 0}">
          <label>Numara</label><select id="lNo">${secenek(es.no_sutun, false)}</select>
          <label>Ad (soyad)</label><select id="lAd">${secenek(es.ad_sutun, true)}</select>
          <label>Soyad</label><select id="lSoyad">${secenek(es.soyad_sutun, true)}</select></div>`;
      }
      k.innerHTML = `<h2>1. Sınav ve dosyalar</h2>
        <div class="kutu"><h3>Sınav <span class="soluk" style="font-weight:400;font-size:13px">bilgiler isteğe bağlı; raporlarda ve dosya adlarında görünür</span></h3>
          <div class="satir"><label>Biçim</label>
            <label><input type="radio" name="bicim" value="optik" ${!kl ? "checked" : ""}> Optik (test, optik okuyucu dosyası)</label>
            <label><input type="radio" name="bicim" value="klasik" ${kl ? "checked" : ""}> Klasik (yazılı; puanları siz girersiniz)</label>
            ${kl ? `<label>Soru sayısı</label><input type="number" id="klasikSayi" min="1" max="100" style="width:70px" value="${p.klasik_soru_sayisi}">` : ""}</div>
          <div class="satir"><label>Ders</label><input type="text" id="dersKodu" list="dersListesi" placeholder="Ders kodu, örnek: UTL4513" style="width:170px" value="${e(s.ders_kodu)}">
            <datalist id="dersListesi">${Object.values(dersler).map((x) => `<option value="${e(x.kod)}">${e(x.ad)}</option>`).join("")}</datalist>
            <input type="text" id="dersAdi" placeholder="Ders adı" style="flex:1;min-width:200px" value="${e(s.ders_adi)}"></div>
          <div class="satir"><label>Sınav türü</label><select id="sinavTuru">${[...new Set([...SINAV_TURLERI, s.sinav_turu])].map((t) => `<option ${t === s.sinav_turu ? "selected" : ""}>${e(t)}</option>`).join("")}</select>
            <label>Tarih</label><input type="date" id="tarih" value="${e(s.tarih)}">
            <label>Saat</label><input type="time" id="saat" value="${e(s.saat)}">
            <label>Etki oranı %</label><input type="text" id="etki" style="width:60px" placeholder="40" value="${e(s.etki_orani)}">
            <label>Dönem</label><input type="text" id="donem" placeholder="2026-2027 Güz" value="${e(s.donem)}"></div>
          <div class="satir"><button id="dersPdf">Ders bilgi paketini yükle (PDF)…</button><span style="flex:1">${dersBilgi}</span></div>
        </div>
        <div class="ikili">
          ${!kl ? birakAlani("birakDat", "Optik okuyucu dosyası", ".dat ya da .txt; puanlama için gerekli", datBilgi, o ? "tamam" : "zorunlu") : ""}
          ${birakAlani("birakListe", "Öğrenci listesi", kl ? "Excel, CSV ya da PDF; klasik sınavda gerekli" : "Excel, CSV ya da PDF; isteğe bağlı ama önerilir (sınava girmeyenler ve doğru adlar için)", listeBilgi, l ? "tamam" : kl ? "zorunlu" : "")}
        </div>
        ${kl && l && UI.soruSayisi() > 0 ? `<p><button class="zorunlu-dugme" id="giriseGec" title="4. adımda öğrenciler satır, sorular sütun olarak açılır. Girdiğiniz her puan bu tarayıcıda kendiliğinden saklanır.">Puan girişine geç: öğrenci listesi ve soru matrisi →</button></p>` : ""}
        <details class="kutu" id="gelismis" ${gelismisAcik ? "open" : ""}><summary>Gelişmiş ayarlar: okuyucu şablonu ve liste sütunları</summary>
          <p class="soluk">Okuyucu şablonu, optik dosyanın her satırında adın, numaranın ve cevapların hangi karakterlerde olduğunu söyler. Program bunu kendisi bulur; yalnızca farklı düzende bir optik formda değiştirmeniz gerekir.</p>
          ${!kl ? `<div class="satir">${alanlar.map(([a, t]) => `<label>${t}</label><input type="number" data-okuyucu="${a}" min="0" max="400" style="width:70px" value="${r[a] || 0}">`).join("")}</div>
          ${D.hamSatirlar && D.hamSatirlar.length ? onizlemeHtml() : ""}` : ""}
          ${listeEsleme}
        </details>`;
      // olaylar
      $$("input[name=bicim]", k).forEach((x) => (x.onchange = () => { UI.bicimDegistir(x.value); UI.ciz(); }));
      if ($("#klasikSayi", k)) $("#klasikSayi", k).onchange = (ev) => { UI.klasikSoruSayisi(parseInt(ev.target.value, 10) || 1); UI.altGuncelle(); };
      const bilgiAlani = { dersAdi: "ders_adi", sinavTuru: "sinav_turu", tarih: "tarih", saat: "saat", etki: "etki_orani", donem: "donem" };
      for (const [id, a] of Object.entries(bilgiAlani)) $("#" + id, k).oninput = (ev) => { s[a] = ev.target.value.trim(); UI.altGuncelle(); };
      $("#dersKodu", k).onchange = (ev) => {
        s.ders_kodu = ev.target.value.trim().toUpperCase();
        const once = s.ders_adi;
        UI.dersiYukle();
        if (D.ders && !once) s.ders_adi = D.ders.ad;
        UI.ciz();
      };
      $("#dersKodu", k).oninput = (ev) => { s.ders_kodu = ev.target.value.trim().toUpperCase(); UI.altGuncelle(); };
      $("#dersPdf", k).onclick = async () => { const f = await dosyaSec(".pdf"); if (f) UI.dosyaAc(f); };
      const birak = (id, kabul) => {
        const b = $("#" + id, k);
        if (!b) return;
        b.onclick = async (ev) => { if (ev.target.tagName === "BUTTON") return; const f = await dosyaSec(kabul); if (f) UI.dosyaAc(f); };
        b.onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === " ") b.click(); };
        b.ondragover = (ev) => { ev.preventDefault(); b.classList.add("uzerinde"); };
        b.ondragleave = () => b.classList.remove("uzerinde");
      };
      birak("birakDat", ".dat,.txt,.DAT,.TXT");
      birak("birakListe", ".xlsx,.xls,.csv,.pdf");
      if ($("#giriseGec", k)) $("#giriseGec", k).onclick = () => UI.git(3);
      if ($("#listeKaldir", k)) $("#listeKaldir", k).onclick = () => { UI.listeYukle(null); UI.ciz(); };
      $$("[data-okuyucu]", k).forEach((x) => (x.onchange = () => {
        const a = x.dataset.okuyucu, v2 = parseInt(x.value, 10) || 0;
        D.proje.okuyucu[a] = a === "kitapcik_baslangic" ? v2 || null : v2;
        UI.datYenidenOku();
        UI.ciz();
        $("#gelismis").open = true;
      }));
      const eslemeDegisti = () => {
        const es = { sayfa: $("#lSayfa").value, baslik_satiri: parseInt($("#lBaslik").value, 10) || null, no_sutun: parseInt($("#lNo").value, 10) || null,
          ad_sutun: parseInt($("#lAd").value, 10) || null, soyad_sutun: parseInt($("#lSoyad").value, 10) || null };
        if (!es.no_sutun) return;
        try { D.liste = Object.assign(OS.tablodanListe(D.liste.sayfalar[es.sayfa], es), { sayfalar: D.liste.sayfalar }); D.proje.liste_esleme = es; D.sonuc = null; }
        catch (h) { bilgi("Sütun eşlemesi", h.message); }
        UI.ciz();
        $("#gelismis").open = true;
      };
      for (const id of ["lSayfa", "lBaslik", "lNo", "lAd", "lSoyad"]) if ($("#" + id, k)) $("#" + id, k).onchange = eslemeDegisti;
    },
  };

  // ------------------------------------------------------------------ 2. adım: cevap anahtarı
  function kodNormalle(ham, bilinen, onek) {
    let t = ham.trim().toLocaleUpperCase("tr");
    if (onek === "Ö") t = t.replace(/O/g, "Ö");
    const sayi = t.replace(/\D/g, "");
    if (sayi) {
      for (const k2 of bilinen) { const ks = k2.replace(/\D/g, ""); if (ks && parseInt(ks, 10) === parseInt(sayi, 10)) return k2; }
      return `${onek}${String(parseInt(sayi, 10)).padStart(2, "0")}`;
    }
    return t;
  }
  function ciktilariCoz(metin, bilinen, onek = "Ö") {
    const kodlar = [], yuzde = {};
    for (let parca of metin.split(/[,;]+/)) {
      parca = parca.trim();
      if (!parca) continue;
      const m = /^([^\s%]+)\s*(?:%?\s*(\d{1,3})\s*%?)?$/.exec(parca);
      if (!m) throw new Error(`Anlaşılamadı: "${parca}". Örnek yazım: Ö01 %60, Ö02 %40`);
      const kod = kodNormalle(m[1], bilinen, onek);
      if (kodlar.includes(kod)) continue;
      kodlar.push(kod);
      if (m[2] !== undefined) yuzde[kod] = parseInt(m[2], 10);
    }
    const verilen = Object.keys(yuzde);
    if (verilen.length && verilen.length < kodlar.length) {
      const bos = kodlar.filter((x) => !(x in yuzde));
      const kalan = 100 - Object.values(yuzde).reduce((a, b) => a + b, 0);
      if (kalan < 0) throw new Error("Yazılan yüzdeler 100'ü aşıyor.");
      OS.esitYuzdeler(bos.length, kalan).forEach((y, i) => (yuzde[bos[i]] = y));
    }
    return [kodlar, verilen.length ? yuzde : {}];
  }
  function ciktilariYaz(s) {
    const d = OS.ciktiDagilimi(s);
    if ((s.ogrenme_ciktilari || []).length <= 1) return (s.ogrenme_ciktilari || []).join(", ");
    return s.ogrenme_ciktilari.map((k2) => `${k2} %${d.get(k2) || 0}`).join(", ");
  }
  UI.ciktilariCoz = ciktilariCoz;
  const anahtarDurum = () => {
    const a = D.proje.anahtar;
    const kitler = OS.kitapciklar(a);
    if (!kitler.includes(D.anahtarKitapcik)) D.anahtarKitapcik = a.ana_kitapcik;
    const kl = D.proje.bicim === "klasik";
    return { a, kitler, kl, ana: kl || D.anahtarKitapcik === a.ana_kitapcik, kit: D.anahtarKitapcik };
  };
  function kitHarfleri(a, kit) {
    const n = a.sorular.length;
    const h = [...(a.kitapcik_anahtarlari[kit] || "").toUpperCase()].filter((c) => !/\s/.test(c));
    while (h.length < n) h.push("-");
    return h.slice(0, n);
  }
  function soruSatiri(i, st) {
    const { a, kl, ana, kit } = st;
    const s = a.sorular[i];
    const puanlar = OS.soruPuanlari(a, D.proje.ayarlar);
    const dogrular = ana ? OS.dogruKume(s) : new Set([kitHarfleri(a, kit)[i]].filter((c) => OS.SIKLAR.includes(c)));
    const kabarcik = kl ? "" : `<td>${[...OS.SIKLAR].map((h) => `<button class="kabarcik ${dogrular.has(h) ? "secili" : ""}" data-sik="${h}" tabindex="-1" ${ana && s.durum === "iptal" ? "disabled" : ""}>${h}</button>`).join("")}</td>`;
    if (!ana) {
      const es = OS.esleme(a, kit).get(i + 1);
      return `<tr data-i="${i}" class="${i === D.etkin ? "etkin" : ""}"><td>${i + 1}</td>${kabarcik}<td><input type="number" class="esleme" min="1" max="${a.sorular.length}" value="${es}"></td><td class="soluk">${es !== i + 1 ? `ana kitapçığın ${es}. sorusu` : ""}</td></tr>`;
    }
    const durum = kl ? "" : `<td><select class="durum">${Object.entries(OS.SORU_DURUMU_ADI).map(([k2, t]) => `<option value="${k2}" ${s.durum === k2 ? "selected" : ""}>${t}</option>`).join("")}</select></td>`;
    const pv = puanlar.length ? Number(OS.ondalikMetni(OS.yuvarla(puanlar[i], 2), ".")) : 0;
    return `<tr data-i="${i}" class="${i === D.etkin && !kl ? "etkin" : ""}"><td>${i + 1}</td>${kabarcik}${durum}
      <td><input type="number" class="puan" min="0" step="0.01" value="${pv}"></td>
      <td><input type="text" class="cikti" placeholder="örnek: 1, 3  ya da  Ö01 %60, Ö02 %40" value="${e(ciktilariYaz(s))}"></td>
      <td><button class="kucuk ciktiSec">Seç…</button></td>
      <td><input type="text" class="pc" placeholder="P02, P07" value="${e((s.program_ciktilari || []).join(", "))}"></td></tr>`;
  }
  const BONUS_NOTU = "Bonus soru {no}: doğru cevaplayan öğrencinin bir yanlışını (yoksa bir boşunu) doğru sayar; bütün soruları doğru olan öğrencide sayılmaz, puan toplamı geçmez. Akademik Bilgi Sistemi'ne gönderilen soru tanımında ve aktarım dosyasında bonus görünmez; öteki sorular 1'den yeniden numaralanır.";
  function anahtarOzetHtml() {
    const p = D.proje, a = p.anahtar, kl = p.bicim === "klasik";
    let puanlar = [], toplam = OS.Kesir.SIFIR;
    try { puanlar = OS.soruPuanlari(a, p.ayarlar); toplam = OS.topla(puanlar); } catch (_) { /* geçersiz puan */ }
    let dogru = false;
    try { dogru = toplam.esit(OS.Kesir.ondaliktan(p.ayarlar.toplam_puan)); } catch (_) { dogru = false; }
    const yontem = p.ayarlar.yontem === "esit" && !kl ? "eşit puan" : "soru bazlı puan";
    let neden = "";
    try {
      const fark = OS.Kesir.ondaliktan(p.ayarlar.toplam_puan).cikar(toplam);
      if (!fark.sifirMi()) neden = `${OS.sayiYaz(fark.p < 0n ? new OS.Kesir(-fark.p, fark.q) : fark, 2)} puan ${fark.p > 0n ? "eksik" : "fazla"}`;
    } catch (_) { neden = ""; }
    const bos = kl || p.ayarlar.yontem !== "esit" ? a.sorular.filter((s) => s.puan === null || s.puan === undefined || s.puan === "").map((s) => s.no) : [];
    if (bos.length) neden = `puanı girilmemiş soru: ${bos.join(", ")}`;
    let m = `<div class="satir"><span><b>Soru puanlarının toplamı:</b> ${OS.sayiYaz(toplam)} / ${e(p.ayarlar.toplam_puan)} (${yontem}) ${dogru && !bos.length ? '<span class="yesil">✓</span>' : `<b class="kirmizi">toplam tutmuyor${neden ? ": " + neden : ""}</b>`}</span></div>`;
    const [hatalar, bilgiler] = OS.ciktiDenetimi(a, UI.ogrenmeKodlari().length ? UI.ogrenmeKodlari() : null);
    if (a.sorular.some((s) => (s.ogrenme_ciktilari || []).length) && puanlar.length) {
      const dag = OS.ciktiDagilimiSinav(a, puanlar);
      const t = OS.topla([...dag.values()]);
      m += `<div><b>Sınavın öğrenme çıktısı dağılımı:</b> ${[...dag].map(([k2, x]) => `${e(k2)} %${OS.sayiYaz(x, 1)}`).join(" · ")} = %${OS.sayiYaz(t, 1)}${!hatalar.length ? ' <span class="yesil">✓ her sorunun yüzdeleri 100</span>' : ""}</div>`;
    } else m += `<div><b>Öğrenme çıktıları:</b> <span class="soluk">henüz girilmedi (Akademik Bilgi Sistemi'ne soru tanımı aktarmak için gerekir).</span></div>`;
    for (const h of hatalar) m += `<div class="kirmizi">${e(h)}</div>`;
    for (const b of bilgiler) m += `<div class="soluk">${e(b)}</div>`;
    const bonuslar = a.sorular.filter((s) => s.durum === "bonus").map((s) => s.no);
    if (bonuslar.length && !kl) m += `<div style="color:var(--vurgu);margin-top:6px">${e(BONUS_NOTU.replace("{no}", bonuslar.join(", ")))}</div>`;
    return m;
  }
  const klasikPuanMetni = (a) => a.sorular.map((s) => (s.puan === null || s.puan === undefined || s.puan === "" ? "?" : String(s.puan).replace(".", ","))).join(" ");
  /** Klasik sınavda çıkarılacak sorulara puan girilmişse onay ister (puanlar silinmez, soru geri eklenirse geri gelir). */
  async function cikarmayiOnayla(yeniN) {
    const p = D.proje.klasik_puanlar || {};
    const etkilenen = [];
    for (let k2 = yeniN; k2 < D.proje.anahtar.sorular.length; k2++) {
      const say = Object.values(p).filter((d) => k2 < d.length && d[k2] !== null && d[k2] !== "").length;
      if (say) etkilenen.push(`${k2 + 1}. soruda ${say} öğrenci`);
    }
    if (!etkilenen.length) return true;
    return onay("Soru çıkarılsın mı?", `Çıkarılacak sorulara puan girilmiş: ${etkilenen.join(", ")}. Bu puanlar hesaba katılmaz ama silinmez; soruyu geri eklerseniz geri gelir. Devam edilsin mi?`);
  }
  const adim2 = {
    eksikler() {
      const { a, kl } = anahtarDurum();
      // Klasik sınavda soru puanları bu adımda girilir; optikte 3. adımda
      const e2 = OS.anahtarEksikleri(a, D.proje.ayarlar, kl).filter((x) => kl || !x.toLowerCase().includes("puan"));
      if (!kl) for (const k2 of OS.kitapciklar(a).slice(1)) {
        const h = [...(a.kitapcik_anahtarlari[k2] || "")].filter((c) => !/\s/.test(c));
        const es = OS.esleme(a, k2);
        const eksik = [];
        for (let i = 0; i < a.sorular.length; i++) if ((i >= h.length || !OS.SIKLAR.includes(h[i]) || !h[i]) && a.sorular[es.get(i + 1) - 1].durum !== "iptal") eksik.push(i + 1);
        if (eksik.length) e2.push(`${k2} kitapçığında anahtarı girilmemiş sorular: ${eksik.join(", ")}`);
        e2.push(...OS.eslemeSorunlari(a, k2));
      }
      return e2.concat(OS.ciktiDenetimi(a, UI.ogrenmeKodlari().length ? UI.ogrenmeKodlari() : null)[0]);
    },
    girildi() {
      const p = D.proje;
      if (p.bicim === "klasik" && p.anahtar.sorular.length && p.anahtar.sorular.every((s) => s.puan === null || s.puan === "")) {
        OS.esitSoruPuanlari(p.ayarlar.toplam_puan, p.anahtar.sorular.length).forEach((x, i) => (p.anahtar.sorular[i].puan = x));
      }
    },
    ciz(k) {
      adim2.girildi();
      const st = anahtarDurum();
      const { a, kitler, kl, ana, kit } = st;
      const n = a.sorular.length;
      const basliklar = ["Soru"].concat(kl ? [] : ["Doğru şık"]).concat(ana ? (kl ? [] : ["Durum"]).concat(["Puan", "Öğrenme çıktıları (yüzdeleriyle)", "", "Program çıktıları"]) : ["Ana kitapçıktaki karşılığı", ""]);
      const hizli = kl ? "" : ana ? (a.sorular.some((s) => s.dogru) ? OS.anahtarMetne(a) : "") : kitHarfleri(a, kit).some((h) => OS.SIKLAR.includes(h) && h) ? kitHarfleri(a, kit).join("") : "";
      const kodlar = UI.ogrenmeKodlari();
      k.innerHTML = `<h2>${kl ? "2. Sorular ve puanlar" : "2. Cevap anahtarı"}</h2>
        ${kl ? `<div class="satir"><label>Soru puanları</label><input type="text" id="klasikPuanlar" style="flex:1" placeholder="Sırayla yazın, örneğin 10 10 10 10 20 40; soru sayısı da buna göre ayarlanır. Enter ile uygulayın." value="${e(klasikPuanMetni(a))}"><button id="klasikPuanUygula">Uygula</button></div>
        <p class="soluk">Klasik sınav: her sorunun puanını ve ölçtüğü öğrenme çıktılarını girin. Öğrencilerin puanları 4. adımda girilir.</p>` : `
        <div class="sekmeler">${kitler.map((x) => `<button data-kit="${e(x)}" class="${x === kit ? "secili" : ""}">${e(x)} kitapçığı${x === a.ana_kitapcik && kitler.length > 1 ? " (ana)" : ""}</button>`).join("")}
          <button id="kitEkle" title="Farklı soru ya da şık sırası olan kitapçık ekler">+ Kitapçık ekle</button>
          ${!ana ? `<button id="kitSil">Bu kitapçığı sil</button>` : ""}</div>
        ${!ana ? `<p class="soluk">${e(kit)} kitapçığı: şıkları bu kitapçığın kendi soru sırasıyla işaretleyin. "Ana kitapçıktaki karşılığı" sütununa bu sorunun ana kitapçıkta kaçıncı soru olduğunu yazın (sıra aynıysa dokunmayın). Puan ve öğrenme çıktısı ana kitapçıktan gelir.</p>` : ""}
        <div class="satir"><label>Hızlı giriş</label><input type="text" id="hizli" style="flex:1;font-family:Menlo,Consolas,monospace" placeholder="Harfleri sırayla yazın, örneğin BEDAC DEDBC BEAAC ('-' soruyu atlar) ve Enter'a basın" value="${e(hizli)}"><button id="hizliUygula">Uygula</button></div>`}
        <div class="kutu izgara" id="izgara" tabindex="0">
          <table class="sorular"><thead><tr>${basliklar.map((b) => `<th>${b}</th>`).join("")}</tr></thead>
          <tbody>${Array.from({ length: n }, (_, i) => soruSatiri(i, st)).join("")}</tbody></table>
        </div>
        ${kl ? `<div class="satir"><button id="soruEkle">+ Soru ekle</button><button id="soruCikar">− Son soruyu çıkar</button></div>` : ""}
        <p class="soluk">${kl ? "Puanı değiştirmek için kutuya tıklayıp yazın ya da yukarıdaki satıra bütün puanları sırayla yazın. " : "Klavye: tabloya bir kez tıklayın, sonra A-E harflerine basın; her harf o sorunun şıkkını seçip sonraki soruya geçer (Boşluk ya da Sil temizler, oklar soru değiştirir). "}${kodlar.length ? `Dersin öğrenme çıktıları: ${kodlar.join(", ")}. Çıktı sütununa yalnızca numara yazabilirsiniz: "1, 3" yazmak Ö01 ve Ö03'e yarı yarıya demektir.` : "Ders bilgi paketini 1. adımda yüklerseniz çıktılar açıklamalarıyla seçilebilir."}</p>
        ${ana ? `<div class="kutu ozet-panel"><div id="anahtarOzet">${anahtarOzetHtml()}</div>
          <div class="satir" style="margin-top:8px"><button class="ana" id="sistemeKopyala" title="Sınav Akreditasyon İşlemleri > Toplu Aktarım Yap > Aktarım Kutusu'na yapıştırılır">Soru tanımını sistem için kopyala</button>
          <button id="esitDagit">Puanları eşit dağıt</button>
          ${UI.acilirMenu("Diğer işlemler", ['<button id="siraylaDagit">Çıktıları sorulara sırayla dağıt</button>',
            '<button id="eslemeKaydet">Ders eşlemesini kaydet</button>', '<button id="eslemeYukle">Kayıtlı ders eşlemesini yükle</button>'])}</div></div>` : ""}`;
      UI.anahtarOlaylari(k, st);
    },
  };
  UI.anahtarOlaylari = function (k, st) {
    const { a, kl, ana, kit } = st;
    const yenidenCiz = () => { const y = $("#icerik").scrollTop; UI.ciz(); $("#icerik").scrollTop = y; };
    const ozetGuncelle = () => { if ($("#anahtarOzet")) $("#anahtarOzet").innerHTML = anahtarOzetHtml(); UI.altGuncelle(); UI.otomatikKaydet(); };
    const satirGuncelle = (i) => {
      const tr = $(`tr[data-i="${i}"]`, k);
      const yeni = document.createElement("tbody");
      yeni.innerHTML = soruSatiri(i, anahtarDurum());
      tr.replaceWith(yeni.firstElementChild);
      satirOlaylari($(`tr[data-i="${i}"]`, k));
    };
    const hizliYaz = () => {
      if (!$("#hizli")) return;
      $("#hizli").value = ana ? (a.sorular.some((s) => s.dogru) ? OS.anahtarMetne(a) : "") : kitHarfleri(a, kit).join("");
    };
    const etkinGoster = () => { $$("tr[data-i]", k).forEach((tr) => tr.classList.toggle("etkin", Number(tr.dataset.i) === D.etkin && !kl)); };
    function sikSec(i, harf, tiklama) {
      if (ana) {
        const s = a.sorular[i];
        if (harf === null) s.dogru = "";
        else if (s.durum === "coklu") {
          const kume = OS.dogruKume(s);
          if (kume.has(harf)) kume.delete(harf); else kume.add(harf);
          s.dogru = [...OS.SIKLAR].filter((c) => kume.has(c)).join("");
        } else s.dogru = tiklama && s.dogru === harf ? "" : harf;
      } else {
        const h = kitHarfleri(a, kit);
        h[i] = harf === null || (tiklama && h[i] === harf) ? "-" : harf;
        a.kitapcik_anahtarlari[kit] = h.join("");
      }
      satirGuncelle(i);
      hizliYaz();
      ozetGuncelle();
    }
    function satirOlaylari(tr) {
      const i = Number(tr.dataset.i);
      const s = a.sorular[i];
      $$(".kabarcik", tr).forEach((b) => (b.onclick = () => { D.etkin = i; sikSec(i, b.dataset.sik, true); etkinGoster(); $("#izgara").focus({ preventScroll: true }); }));
      const durum = $(".durum", tr);
      if (durum) durum.onchange = () => { s.durum = durum.value; if (s.durum !== "coklu" && s.dogru.length > 1) s.dogru = s.dogru[0]; satirGuncelle(i); hizliYaz(); ozetGuncelle(); };
      const puan = $(".puan", tr);
      if (puan) puan.onchange = () => {
        const ay = D.proje.ayarlar;
        if (ay.yontem === "esit") { OS.esitSoruPuanlari(ay.toplam_puan, a.sorular.length).forEach((x, j) => (a.sorular[j].puan = x)); ay.yontem = "soru_bazli"; }
        const v2 = parseFloat(String(puan.value).replace(",", "."));
        s.puan = isFinite(v2) && v2 >= 0 ? String(Math.round(v2 * 100) / 100) : null;
        if ($("#klasikPuanlar", k)) $("#klasikPuanlar", k).value = klasikPuanMetni(a);
        ozetGuncelle();
      };
      const cikti = $(".cikti", tr);
      if (cikti) cikti.onchange = () => {
        try { [s.ogrenme_ciktilari, s.cikti_yuzdeleri] = ciktilariCoz(cikti.value, UI.ogrenmeKodlari(), "Ö"); }
        catch (h) { bilgi("Öğrenme çıktısı", h.message); return; }
        cikti.value = ciktilariYaz(s);
        ozetGuncelle();
      };
      const sec = $(".ciktiSec", tr);
      if (sec) sec.onclick = async () => {
        const r = await UI.ciktiPenceresi(i + 1, s);
        if (r) { [s.ogrenme_ciktilari, s.cikti_yuzdeleri] = r; cikti.value = ciktilariYaz(s); ozetGuncelle(); }
      };
      const pc = $(".pc", tr);
      if (pc) pc.onchange = () => {
        try { s.program_ciktilari = ciktilariCoz(pc.value.replace(/%/g, ""), UI.programKodlari(), "P")[0]; } catch (h) { bilgi("Program çıktısı", h.message); return; }
        pc.value = s.program_ciktilari.join(", ");
        ozetGuncelle();
      };
      const es = $(".esleme", tr);
      if (es) es.onchange = () => {
        const v2 = parseInt(es.value, 10);
        const t = (a.kitapcik_eslemesi[kit] = a.kitapcik_eslemesi[kit] || {});
        if (!v2 || v2 === i + 1) delete t[String(i + 1)]; else t[String(i + 1)] = v2;
        satirGuncelle(i);
        UI.altGuncelle();
      };
    }
    $$("tr[data-i]", k).forEach(satirOlaylari);
    if (kl) {
      const uygula = async () => {
        let puanlar;
        try { puanlar = OS.puanListesiCoz($("#klasikPuanlar", k).value); } catch (h) { bilgi("Soru puanları", `${h.message}\n\nPuanları boşlukla ayırarak yazın, örneğin: 10 10 10 10 20 40`); return; }
        if (!puanlar.length || !(await cikarmayiOnayla(puanlar.length))) return;
        D.proje.klasik_soru_sayisi = puanlar.length;
        UI.anahtariBoyutla();
        puanlar.forEach((x, j) => (D.proje.anahtar.sorular[j].puan = x));
        D.sonuc = null;
        yenidenCiz();
      };
      $("#klasikPuanlar", k).onkeydown = (ev) => { if (ev.key === "Enter") { ev.preventDefault(); uygula(); } };
      $("#klasikPuanUygula", k).onclick = uygula;
      $("#soruEkle", k).onclick = () => {
        UI.klasikSoruSayisi(a.sorular.length + 1);
        yenidenCiz();
        const son = $$("input.puan", $("#icerik")).pop();
        if (son) { son.focus(); son.select(); }
      };
      $("#soruCikar", k).onclick = async () => {
        const n2 = a.sorular.length;
        if (n2 <= 1 || !(await cikarmayiOnayla(n2 - 1))) return;
        UI.klasikSoruSayisi(n2 - 1);
        yenidenCiz();
      };
    }
    const izgara = $("#izgara", k);
    izgara.onkeydown = (ev) => {
      if (kl || ["INPUT", "SELECT", "BUTTON"].includes(ev.target.tagName) && !ev.target.classList.contains("kabarcik")) return;
      const n = a.sorular.length;
      const harf = ev.key.toLocaleUpperCase("tr");
      if (OS.SIKLAR.includes(harf) && harf.length === 1) {
        ev.preventDefault();
        const s = a.sorular[D.etkin];
        sikSec(D.etkin, harf, false);
        if (!(ana && s.durum === "coklu")) D.etkin = Math.min(n - 1, D.etkin + 1);
      } else if ([" ", "Backspace", "Delete", "-"].includes(ev.key)) { ev.preventDefault(); sikSec(D.etkin, null, false); D.etkin = Math.min(n - 1, D.etkin + 1); }
      else if (ev.key === "ArrowDown") { ev.preventDefault(); D.etkin = Math.min(n - 1, D.etkin + 1); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); D.etkin = Math.max(0, D.etkin - 1); }
      else return;
      etkinGoster();
      const tr = $(`tr[data-i="${D.etkin}"]`, k);
      if (tr) tr.scrollIntoView({ block: "nearest" });
    };
    $$("tr[data-i]", k).forEach((tr) => tr.addEventListener("mousedown", () => { D.etkin = Number(tr.dataset.i); etkinGoster(); }));
    $$("[data-kit]", k).forEach((b) => (b.onclick = () => { D.anahtarKitapcik = b.dataset.kit; D.etkin = 0; yenidenCiz(); }));
    if ($("#kitEkle", k)) $("#kitEkle", k).onclick = async () => {
      const mevcut = OS.kitapciklar(a);
      const oneri = [..."BCDEFGH"].find((c) => !mevcut.includes(c)) || "";
      const harf = await pencere("Kitapçık ekle", `<p>Optik formda işaretlenen kitapçık harfi:</p><input type="text" id="kitHarf" maxlength="1" style="width:60px" value="${oneri}">`,
        [{ metin: "Vazgeç", deger: null }, { metin: "Ekle", ana: true, deger: (p) => $("#kitHarf", p).value.trim().toLocaleUpperCase("tr") }]);
      if (!harf || !/\p{L}/u.test(harf)) return;
      if (mevcut.includes(harf)) { bilgi("Kitapçık", `${harf} kitapçığı zaten var.`); return; }
      a.kitapcik_anahtarlari[harf] = "-".repeat(a.sorular.length);
      D.anahtarKitapcik = harf;
      yenidenCiz();
    };
    if ($("#kitSil", k)) $("#kitSil", k).onclick = async () => {
      if (!(await onay("Kitapçık sil", `${kit} kitapçığının anahtarı ve eşlemesi silinsin mi?`))) return;
      delete a.kitapcik_anahtarlari[kit];
      delete a.kitapcik_eslemesi[kit];
      D.anahtarKitapcik = a.ana_kitapcik;
      yenidenCiz();
    };
    const hizliUygula = () => {
      const metin = $("#hizli").value;
      const harfSayisi = [...metin].filter((c) => !/\s/.test(c)).length;
      let yeni;
      try { yeni = OS.anahtarMetinden(metin, a.sorular.length); } catch (h) { bilgi("Cevap anahtarı", h.message); return; }
      if (ana) a.sorular.forEach((s, i) => { s.dogru = yeni[i].dogru; if (s.durum === "coklu") s.durum = "normal"; });
      else a.kitapcik_anahtarlari[kit] = yeni.map((s) => (s.dogru ? s.dogru : "-")).join("");
      yenidenCiz();
      if (harfSayisi !== a.sorular.length) bilgi("Cevap anahtarı", `${harfSayisi} harf girildi, soru sayısı ${a.sorular.length}. Eksik sorular anahtarsız bırakıldı, fazlası atıldı.`);
    };
    if ($("#hizli", k)) { $("#hizli", k).onkeydown = (ev) => { if (ev.key === "Enter") hizliUygula(); }; $("#hizliUygula", k).onclick = hizliUygula; }
    if ($("#esitDagit", k)) $("#esitDagit", k).onclick = () => {
      const ay = D.proje.ayarlar;
      if (kl) OS.esitSoruPuanlari(ay.toplam_puan, a.sorular.length).forEach((x, i) => (a.sorular[i].puan = x));
      else { ay.yontem = "esit"; for (const s of a.sorular) s.puan = null; }
      yenidenCiz();
    };
    if ($("#siraylaDagit", k)) $("#siraylaDagit", k).onclick = () => {
      const kodlar = UI.ogrenmeKodlari();
      if (!kodlar.length) { bilgi("Öğrenme çıktıları", "Önce 1. adımda ders bilgi paketini yükleyin."); return; }
      const n = a.sorular.length;
      a.sorular.forEach((s, i) => { s.ogrenme_ciktilari = [kodlar[Math.min(kodlar.length - 1, Math.floor((i * kodlar.length) / n))]]; s.cikti_yuzdeleri = {}; });
      yenidenCiz();
    };
    if ($("#eslemeKaydet", k)) $("#eslemeKaydet", k).onclick = () => {
      const t = yerel.al("os_ders_eslemeleri", {});
      t[D.proje.sinav.ders_kodu || "ders"] = Object.fromEntries(a.sorular.map((s) => [String(s.no), { ogrenme_ciktilari: s.ogrenme_ciktilari, program_ciktilari: s.program_ciktilari, cikti_yuzdeleri: s.cikti_yuzdeleri }]));
      yerel.koy("os_ders_eslemeleri", t);
      bildir("Eşleme bu ders kodu için bu tarayıcıda saklandı.");
    };
    if ($("#eslemeYukle", k)) $("#eslemeYukle", k).onclick = () => {
      const t = (yerel.al("os_ders_eslemeleri", {}) || {})[D.proje.sinav.ders_kodu || "ders"];
      if (!t) { bilgi("Ders eşlemesi", "Bu ders kodu için kayıtlı eşleme yok."); return; }
      for (const s of a.sorular) { const x = t[String(s.no)]; if (x) { s.ogrenme_ciktilari = [...(x.ogrenme_ciktilari || [])]; s.program_ciktilari = [...(x.program_ciktilari || [])]; s.cikti_yuzdeleri = Object.assign({}, x.cikti_yuzdeleri || {}); } }
      yenidenCiz();
    };
    if ($("#sistemeKopyala", k)) $("#sistemeKopyala", k).onclick = async () => {
      const sorun = OS.anahtarEksikleri(a, D.proje.ayarlar, true).filter((x) => x.toLowerCase().includes("puan"));
      let [hatalar] = OS.ciktiDenetimi(a, UI.ogrenmeKodlari().length ? UI.ogrenmeKodlari() : null);
      if (!a.sorular.some((s) => (s.ogrenme_ciktilari || []).length)) hatalar = ["Hiçbir soruya öğrenme çıktısı seçilmedi. Sistem her soru için öğrenme çıktısı istiyor."];
      if (sorun.length || hatalar.length) { bilgi("Önce düzeltin", sorun.concat(hatalar).join("\n")); return; }
      const metin = OS.soruTanimiMetni(a, D.proje.ayarlar, UI.ogrenmeKodlari().length ? UI.ogrenmeKodlari() : null);
      const tamam = await kopyala(metin);
      const adimlar = `Akademik Bilgi Sistemi'nde:\n1. Sınav Akreditasyon İşlemleri'nde dersi ve sınavı açın.\n2. "Toplu Sınav Soru Tanım" kutusunda "Toplu Aktarım Yap" seçin.\n3. "Kolon Ayracı" "Excel'den Kopyalandı" olsun.\n4. Sağdaki Aktarım Kutusu'na tıklayıp yapıştırın (Mac'te Cmd+V, Windows'ta Ctrl+V).\n5. "Aktar" düğmesine basın.`;
      if (tamam) bilgi("Panoya kopyalandı", `${a.sorular.length} sorunun tanımı kopyalandı.\n\n${adimlar}`);
      else pencere("Kopyalamak için seçin", `<p>Tarayıcı panoya yazmaya izin vermedi. Aşağıdaki metni seçip kopyalayın (Cmd+C ya da Ctrl+C):</p><textarea style="width:100%;height:220px;font-family:Menlo,monospace">${e(metin)}</textarea><p style="white-space:pre-wrap">${e(adimlar)}</p>`,
        [{ metin: "Kapat", deger: true, ana: true }], (p) => $("textarea", p).select());
    };
    if (!kl) setTimeout(() => izgara.focus({ preventScroll: true }), 0);
  };
  UI.ciktiPenceresi = function (no, s) {
    const kodlar = UI.ogrenmeKodlari();
    const ac = UI.aciklamalar();
    const tum = [...new Set([...kodlar, ...(s.ogrenme_ciktilari || [])])];
    const d = OS.ciktiDagilimi(s);
    const satirlar = tum.map((k2) => `<tr><td><label><input type="checkbox" data-kod="${e(k2)}" ${(s.ogrenme_ciktilari || []).includes(k2) ? "checked" : ""}> <b>${e(k2)}</b> ${e(ac[k2] || "")}</label></td>
      <td><input type="number" min="0" max="100" style="width:70px" data-yuzde="${e(k2)}" value="${d.get(k2) || 0}" ${(s.ogrenme_ciktilari || []).includes(k2) ? "" : "disabled"}> %</td></tr>`).join("");
    const icerik = `<p>Sorunun ölçtüğü çıktıları işaretleyin. Yüzdelerin toplamı 100 olmalı.</p>
      ${tum.length ? `<table>${satirlar}</table>` : `<p class="soluk">Ders bilgi paketi yüklenmedi. 1. adımda PDF'i yükleyin ya da kodları soru satırına elle yazın.</p>`}
      <div class="satir"><button id="esitYuzde">Eşit dağıt</button><b id="yuzdeToplam"></b></div>`;
    const topla2 = (p) => $$("[data-kod]", p).filter((c) => c.checked).reduce((t, c) => t + (parseInt($(`[data-yuzde="${CSS.escape(c.dataset.kod)}"]`, p).value, 10) || 0), 0);
    return pencere(`${no}. sorunun öğrenme çıktıları`, icerik, [
      { metin: "Vazgeç", deger: null },
      { metin: "Tamam", ana: true, denetle: (p) => { const t = topla2(p); const sec = $$("[data-kod]", p).some((c) => c.checked); if (sec && t !== 100) { bildir("Yüzdelerin toplamı 100 olmalı."); return false; } return true; },
        deger: (p) => { const sec = $$("[data-kod]", p).filter((c) => c.checked).map((c) => c.dataset.kod); return [sec, Object.fromEntries(sec.map((k2) => [k2, parseInt($(`[data-yuzde="${CSS.escape(k2)}"]`, p).value, 10) || 0]))]; } },
    ], (p) => {
      const guncelle = () => { const t = topla2(p); const sec = $$("[data-kod]", p).some((c) => c.checked); $("#yuzdeToplam", p).innerHTML = `Toplam: %${t}` + (sec && t !== 100 ? ' <span class="kirmizi">(100 olmalı)</span>' : ""); };
      const esit = () => { const sec = $$("[data-kod]", p).filter((c) => c.checked); OS.esitYuzdeler(sec.length).forEach((y, i) => ($(`[data-yuzde="${CSS.escape(sec[i].dataset.kod)}"]`, p).value = y)); guncelle(); };
      $$("[data-kod]", p).forEach((c) => (c.onchange = () => { const y = $(`[data-yuzde="${CSS.escape(c.dataset.kod)}"]`, p); y.disabled = !c.checked; if (!c.checked) y.value = 0; esit(); }));
      $$("[data-yuzde]", p).forEach((y) => (y.oninput = guncelle));
      $("#esitYuzde", p).onclick = esit;
      guncelle();
    });
  };

  // ------------------------------------------------------------------ 3. adım: puanlama
  const adim3 = {
    eksikler() {
      if (!isFinite(parseFloat(String(D.proje.ayarlar.toplam_puan).replace(",", ".")))) return ["Toplam puan sayı olmalı."];
      if (D.proje.bicim === "klasik") return [];  // klasik sınavda soru puanları 2. adımda
      try { return OS.anahtarEksikleri(D.proje.anahtar, D.proje.ayarlar, D.proje.bicim === "klasik").filter((x) => x.toLowerCase().includes("puan")); }
      catch (h) { return [h.message]; }
    },
    ciz(k) {
      const a = D.proje.ayarlar, kl = D.proje.bicim === "klasik";
      let soruPuani = "";
      try {
        const p = OS.soruPuanlari(D.proje.anahtar, a);
        soruPuani = a.yontem === "esit" && p.length ? `Soru puanı ${OS.sayiYaz(p[0], 4)} (kesir olarak tutulur; bütün sorular doğruysa tam ${OS.sayiYaz(OS.topla(p), 2)})` : `Girilen soru puanlarının toplamı ${OS.sayiYaz(OS.topla(p), 2)}`;
      } catch (_) { soruPuani = ""; }
      k.innerHTML = `<h2>3. Puanlama</h2>
        <div class="kutu"><h3>Puan yöntemi</h3>
          ${kl ? "" : `<div class="satir"><label><input type="radio" name="yontem" value="esit" ${a.yontem === "esit" ? "checked" : ""}> Eşit puan (toplam / soru sayısı; iptal sorular dahil)</label></div>`}
          <div class="satir"><label><input type="radio" name="yontem" value="soru_bazli" ${a.yontem !== "esit" || kl ? "checked" : ""}> Soru bazlı puan (her sorunun puanı 2. adımda girilir)</label></div>
          <div class="satir"><label>Toplam puan</label><input type="text" id="toplamPuan" style="width:80px" value="${e(a.toplam_puan)}"><span class="soluk">${e(soruPuani)}</span></div>
        </div>
        <div class="kutu"><h3>Kurallar</h3>
          ${kl ? "" : `<div class="satir"><label><input type="checkbox" id="ceza" ${a.yanlis_cezasi ? "checked" : ""}> Yanlışlar doğruyu götürsün:</label>
            <input type="number" id="cezaOrani" min="1" max="10" style="width:60px" value="${a.ceza_orani}" ${a.yanlis_cezasi ? "" : "disabled"}>
            <span class="soluk">yanlış bir doğruyu götürür (puan sıfırın altına düşmez)</span></div>
          <div class="satir"><label>Çift işaret (*)</label><select id="cift"><option value="bos" ${a.cift_isaret === "bos" ? "selected" : ""}>Boş say</option><option value="yanlis" ${a.cift_isaret === "yanlis" ? "selected" : ""}>Yanlış say</option></select></div>`}
          <div class="satir"><label>Yuvarlama (yalnızca en sonda)</label><select id="yuvarlama">${[["yarim_yukari", "Yarım yukarı"], ["asagi", "Aşağı"], ["yukari", "Yukarı"]].map(([x, t]) => `<option value="${x}" ${a.yuvarlama === x ? "selected" : ""}>${t}</option>`).join("")}</select>
            <label>Ondalık basamak</label><input type="number" id="ondalik" min="0" max="4" style="width:60px" value="${a.ondalik}"></div>
          <div class="satir"><label>Başarı eşiği</label><input type="number" id="esik" min="0" max="100" style="width:70px" value="${a.basari_esigi}"><span class="soluk">İstatistiklerde bu puan ve üstü başarılı, öğrenme çıktısında bu yüzde ve üstü "ulaştı" sayılır.</span></div>
          <div class="satir"><label>Dersi geçme kuralı</label><label>Geçme ortalaması</label><input type="number" id="gecme" min="0" max="100" style="width:70px" value="${a.gecme_ortalamasi}">
            <label>Final alt sınırı</label><input type="number" id="finalAlt" min="0" max="100" style="width:70px" value="${a.final_alt_siniri}"><span class="soluk">Yalnızca "finalde gereken puan" hesabı için; ara sınav ağırlığı 1. adımdaki etki oranından.</span></div>
        </div>`;
      const degisti = () => {
        const yontem = ($("input[name=yontem]:checked", k) || {}).value || "soru_bazli";
        a.yontem = kl ? "soru_bazli" : yontem;
        a.toplam_puan = $("#toplamPuan", k).value.trim().replace(",", ".") || "100";
        if (!kl) { a.yanlis_cezasi = $("#ceza", k).checked; a.ceza_orani = parseInt($("#cezaOrani", k).value, 10) || 4; a.cift_isaret = $("#cift", k).value; $("#cezaOrani", k).disabled = !a.yanlis_cezasi; }
        a.yuvarlama = $("#yuvarlama", k).value;
        a.ondalik = Math.max(0, Math.min(4, parseInt($("#ondalik", k).value, 10) || 0));
        a.basari_esigi = parseInt($("#esik", k).value, 10) || 0;
        a.gecme_ortalamasi = parseInt($("#gecme", k).value, 10) || 0;
        a.final_alt_siniri = parseInt($("#finalAlt", k).value, 10) || 0;
        D.sonuc = null;
        UI.altGuncelle();
        UI.otomatikKaydet();
      };
      $$("input, select", k).forEach((x) => (x.onchange = () => { const once = a.yontem; degisti(); if (once !== a.yontem) UI.ciz(); }));
    },
  };

  UI.adimlar.push(adim1, adim2, adim3);
})();
