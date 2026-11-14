/* Optik Sınav — tarayıcı sürümü: Excel ve metin tablolarını okuma (SheetJS ile). */
(function (kok) {
  "use strict";
  const OS = kok.OS;

  /** Bütün sayfaları {ad: satırlar} olarak döndürür; satırlar A1'den başlar (masaüstü programdaki gibi). */
  function sayfalariOku(XLSX, bayt, dosyaAdi = "") {
    const uz = (dosyaAdi.split(".").pop() || "").toLowerCase();
    if (uz === "csv" || uz === "txt") {
      const [metin] = OS.baytlariCoz(bayt instanceof Uint8Array ? bayt : new Uint8Array(bayt));
      const ornek = metin.slice(0, 4096);
      const sayilar = [";", ",", "\t", "|"].map((a) => [a, ornek.split("\n").filter((s) => s.trim()).slice(0, 10).map((s) => s.split(a).length - 1)]);
      let ayrac = ",";
      let enIyi = -1;
      for (const [a, s] of sayilar) {
        const tutarli = s.length && s.every((x) => x === s[0]) && s[0] > 0 ? s[0] * 10 : Math.min(...s);
        if (tutarli > enIyi) { enIyi = tutarli; ayrac = a; }
      }
      const satirlar = OS.satirlaraBol(metin).map((s) => csvSatiri(s, ayrac));
      return { [dosyaAdi.replace(/\.[^.]+$/, "") || "Sayfa1"]: satirlar };
    }
    const wb = XLSX.read(bayt, { type: bayt instanceof Uint8Array ? "array" : "buffer", cellDates: false });
    const sonuc = {};
    for (const ad of wb.SheetNames) {
      const ws = wb.Sheets[ad];
      if (!ws["!ref"]) { sonuc[ad] = []; continue; }
      const r = XLSX.utils.decode_range(ws["!ref"]);
      const satirlar = [];
      for (let i = 0; i <= r.e.r; i++) {
        const s = [];
        for (let j = 0; j <= r.e.c; j++) {
          const c = ws[XLSX.utils.encode_cell({ r: i, c: j })];
          s.push(c === undefined || c.v === undefined || c.v === "" ? null : c.v);
        }
        satirlar.push(s);
      }
      sonuc[ad] = satirlar;
    }
    return sonuc;
  }
  function csvSatiri(s, a) {
    const r = [];
    let h = "", tirnak = false;
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (tirnak) { if (c === '"' && s[i + 1] === '"') { h += '"'; i++; } else if (c === '"') tirnak = false; else h += c; }
      else if (c === '"') tirnak = true;
      else if (c === a) { r.push(h); h = ""; }
      else h += c;
    }
    r.push(h);
    return r;
  }
  function listeOku(XLSX, bayt, dosyaAdi = "", esleme = null) {
    const sayfalar = sayfalariOku(XLSX, bayt, dosyaAdi);
    if (esleme && esleme.no_sutun) {
      const sayfa = esleme.sayfa in sayfalar ? esleme.sayfa : Object.keys(sayfalar)[0];
      return Object.assign(OS.tablodanListe(sayfalar[sayfa], esleme), { sayfalar });
    }
    const sayfa = OS.sayfaSec(sayfalar);
    return Object.assign(OS.tablodanListe(sayfalar[sayfa], OS.eslemeTahminEt(sayfalar[sayfa], sayfa)), { sayfalar });
  }
  Object.assign(OS, { sayfalariOku, listeOku });
})(typeof globalThis !== "undefined" ? globalThis : window);
