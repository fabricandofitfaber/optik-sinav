/* Optik Sınav — tarayıcı sürümü: Excel dosyaları (ExcelJS ile). Masaüstü programdaki dosyalarla aynı sayfalar;
 * Excel grafikleri yerine grafikler yazdırılabilir raporda yer alır. */
(function () {
  "use strict";
  const OS = window.OS, UI = window.UI;
  const X = (UI.excel = {});
  const RENK = { D: "FFC6EFCE", Y: "FFFFC7CE", B: "FFFFEB9C", I: "FFD9D9D9", "-": "FFEDEDED", K: "FFDDEBF7", uyari: "FFFCD5B4", baslik: "FFDDEBF7" };
  const dolgu = (r) => ({ type: "pattern", pattern: "solid", fgColor: { argb: r } });
  const bicim = (n) => (n <= 0 ? "0" : "0." + "0".repeat(n));

  function baslik(ws, satir, basliklar) {
    basliklar.forEach((b, j) => {
      const c = ws.getCell(satir, j + 1);
      c.value = b;
      c.font = { bold: true };
      c.fill = dolgu(RENK.baslik);
      c.alignment = { horizontal: "center", vertical: "middle", wrapText: true };
    });
  }
  function genislik(ws, g, varsayilan = 9) {
    const n = Math.max(ws.columnCount, ...Object.keys(g).map(Number));
    for (let j = 1; j <= n; j++) ws.getColumn(j).width = g[j] || varsayilan;
  }
  function bitir(ws, sonSutun, g) {
    ws.views = [{ state: "frozen", ySplit: 1 }];
    if (ws.rowCount >= 1 && sonSutun >= 1) ws.autoFilter = { from: { row: 1, column: 1 }, to: { row: Math.max(ws.rowCount, 1), column: sonSutun } };
    genislik(ws, g || {});
  }
  function yazdirma(wb) {
    for (const ws of wb.worksheets) ws.pageSetup = Object.assign(ws.pageSetup || {}, { orientation: "landscape", fitToPage: true, fitToWidth: 1, fitToHeight: 0 });
  }
  function puan(ws, r, c, deger, ondalik = 2, yontem = "yarim_yukari") {
    const cell = ws.getCell(r, c);
    cell.value = OS.ondalikSayi(OS.yuvarla(deger, ondalik, yontem));
    cell.numFmt = bicim(ondalik);
    return cell;
  }
  function sayi(ws, r, c, v, numFmt = "0.00") {
    const cell = ws.getCell(r, c);
    cell.value = v === null || v === undefined || Number.isNaN(v) ? null : typeof v === "number" ? Math.round(v * 10000) / 10000 : v;
    if (typeof v === "number") cell.numFmt = numFmt;
    return cell;
  }
  function metin(ws, r, c, v) { const cell = ws.getCell(r, c); cell.value = v === undefined ? null : v; return cell; }
  function no(ws, r, c, v) { const cell = metin(ws, r, c, v); cell.numFmt = "@"; return cell; }
  function not(ws, r, m, sutun = 8) {
    ws.mergeCells(r, 1, r, sutun);
    const c = ws.getCell(r, 1);
    c.value = m;
    c.alignment = { wrapText: true, vertical: "top" };
    ws.getRow(r).height = Math.max(15, 15 * (Math.floor(m.length / 110) + 1));
  }
  const kitabe = async (wb) => new Blob([await wb.xlsx.writeBuffer()], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  const yeni = () => { const wb = new window.ExcelJS.Workbook(); wb.creator = "Optik Sınav Değerlendirme"; return wb; };

  // ------------------------------------------------------------------ sonuç dosyası
  X.sonuc = async function (sonuc, sinav, duzeltmeler, kaynaklar) {
    const a = sonuc.ayarlar, n = sonuc.anahtar.sorular.length;
    const wb = yeni();
    let ws = wb.addWorksheet("Sonuç");
    const b = ["Sıra", "Öğrenci No", "Ad Soyad", ...Array.from({ length: n }, (_, k) => String(k + 1)), "Doğru", "Yanlış", "Boş"];
    if (a.yanlis_cezasi) b.push("Net", "Ham Puan", "Yanlış Cezası");
    b.push("Puan", "Uyarı");
    const coklu = new Set(sonuc.ogrenciler.map((o) => o.kitapcik).filter((x) => x)).size > 1 || Object.keys(sonuc.anahtar.kitapcik_anahtarlari || {}).length > 0;
    if (coklu) b.push("Kitapçık");
    baslik(ws, 1, b);
    let r = 2;
    sonuc.ogrenciler.forEach((o, i) => {
      metin(ws, r, 1, i + 1); no(ws, r, 2, o.no); metin(ws, r, 3, o.ad);
      o.sorular.forEach((s, k) => { puan(ws, r, 4 + k, s.puan, a.ondalik, a.yuvarlama).fill = dolgu(RENK[s.durum]); });
      let c0 = 4 + n;
      metin(ws, r, c0, o.dogru); metin(ws, r, c0 + 1, o.yanlis); metin(ws, r, c0 + 2, o.bos);
      c0 += 3;
      if (a.yanlis_cezasi) { puan(ws, r, c0, OS.net(o.dogru, o.yanlis, a), 2); puan(ws, r, c0 + 1, o.ham_puan, a.ondalik, a.yuvarlama); puan(ws, r, c0 + 2, o.ceza, a.ondalik, a.yuvarlama); c0 += 3; }
      puan(ws, r, c0, o.puan, a.ondalik, a.yuvarlama).font = { bold: true };
      metin(ws, r, c0 + 1, o.uyarilar.map((u) => u.mesaj).join("; "));
      if (coklu) metin(ws, r, c0 + 2, o.kitapcik);
      if (o.uyarilar.length) for (const j of [1, 2, 3, c0 + 1]) ws.getCell(r, j).fill = dolgu(RENK.uyari);
      r++;
    });
    for (const g of sonuc.girmeyenler) { no(ws, r, 2, g.no); metin(ws, r, 3, g.ad); metin(ws, r, b.length - (coklu ? 1 : 0), "Sınava girmedi"); r++; }
    bitir(ws, b.length, { 1: 6, 2: 13, 3: 28, [b.length - (coklu ? 1 : 0)]: 45 });
    for (let k = 0; k < n; k++) ws.getColumn(4 + k).width = sonuc.klasik ? 7 : 6;

    ws = wb.addWorksheet("Cevaplar");
    baslik(ws, 1, ["Sıra", "Öğrenci No", "Ad Soyad", ...Array.from({ length: n }, (_, k) => String(k + 1))]);
    metin(ws, 2, 3, sonuc.klasik ? "Soru puanı" : "Cevap anahtarı").font = { bold: true };
    sonuc.anahtar.sorular.forEach((s, k) => { metin(ws, 2, 4 + k, sonuc.klasik ? OS.klasikYaz(sonuc.soru_puanlari[k]) : s.durum === "iptal" ? "İptal" : s.dogru).font = { bold: true }; });
    sonuc.ogrenciler.forEach((o, i) => {
      metin(ws, i + 3, 1, i + 1); no(ws, i + 3, 2, o.no); metin(ws, i + 3, 3, o.ad);
      o.sorular.forEach((s, k) => { const c = metin(ws, i + 3, 4 + k, String(s.isaret).trim() || null); c.fill = dolgu(RENK[s.durum]); c.alignment = { horizontal: "center" }; });
    });
    bitir(ws, 3 + n, { 1: 6, 2: 13, 3: 28 });
    for (let k = 0; k < n; k++) ws.getColumn(4 + k).width = sonuc.klasik ? 6 : 4;

    ws = wb.addWorksheet("Uyarılar");
    baslik(ws, 1, ["Dosya satırı", "Öğrenci No", "Okunan ad", "Uyarı türü", "Açıklama"]);
    r = 2;
    for (const o of sonuc.ogrenciler) for (const u of o.uyarilar) { [o.kayit.satir_no, o.no, o.okunan_ad, u.tur, u.mesaj].forEach((x, j) => metin(ws, r, j + 1, x)); r++; }
    for (const g of sonuc.girmeyenler) { [null, g.no, g.ad, "girmedi", "Sınava girmedi"].forEach((x, j) => metin(ws, r, j + 1, x)); r++; }
    bitir(ws, 5, { 1: 12, 2: 13, 3: 28, 4: 20, 5: 70 });

    ws = wb.addWorksheet("Düzeltme Kaydı");
    baslik(ws, 1, ["Dosya satırı", "Alan", "Eski değer", "Yeni değer", "Kim", "Ne zaman"]);
    (duzeltmeler || []).forEach((d, i) => [d.satir_no, d.alan, d.eski, d.yeni, d.kim, d.zaman].forEach((x, j) => metin(ws, i + 2, j + 1, x)));
    bitir(ws, 6, { 1: 12, 2: 12, 3: 20, 4: 20, 5: 14, 6: 20 });

    ws = wb.addWorksheet("Anahtar ve Ayarlar");
    const bil = [["Ders kodu", sinav.ders_kodu], ["Ders adı", sinav.ders_adi], ["Sınav türü", sinav.sinav_turu], ["Tarih", sinav.tarih], ["Saat", sinav.saat],
      ["Etki oranı (%)", sinav.etki_orani], ["Dönem", sinav.donem], ["Sınav biçimi", sonuc.klasik ? "Klasik" : "Optik"],
      ["Puanlama", a.yontem === "esit" ? "Eşit puan" : "Soru bazlı puan"], ["Toplam puan", a.toplam_puan],
      ["Yanlış cezası", a.yanlis_cezasi ? `${a.ceza_orani} yanlış 1 doğruyu götürür` : "Yok"], ["Çift işaret", a.cift_isaret === "yanlis" ? "Yanlış say" : "Boş say"],
      ["Yuvarlama", `${{ yarim_yukari: "Yarım yukarı", asagi: "Aşağı", yukari: "Yukarı" }[a.yuvarlama]}, ${a.ondalik} basamak`],
      ["Sınava giren", sonuc.ogrenciler.length], ["Sınava girmeyen (listede olup sonuçta olmayan)", sonuc.girmeyenler.length], ["Listede olmayan numara", sonuc.listede_olmayanlar.length],
      ...Object.entries(kaynaklar || {})];
    bil.forEach(([x, y], i) => { metin(ws, i + 1, 1, x).font = { bold: true }; metin(ws, i + 1, 2, y); });
    r = bil.length + 2;
    baslik(ws, r, ["Soru", "Doğru şık", "Durum", "Puan", "Öğrenme çıktıları", "Program çıktıları"]);
    sonuc.anahtar.sorular.forEach((s, k) => {
      const rr = r + 1 + k;
      metin(ws, rr, 1, s.no); metin(ws, rr, 2, s.dogru); metin(ws, rr, 3, OS.SORU_DURUMU_ADI[s.durum]);
      puan(ws, rr, 4, sonuc.soru_puanlari[k], 4);
      metin(ws, rr, 5, [...OS.ciktiDagilimi(s)].map(([x, y]) => `${x} %${y}`).join(", ")); metin(ws, rr, 6, (s.program_ciktilari || []).join(", "));
    });
    genislik(ws, { 1: 40, 2: 30, 3: 24, 4: 10, 5: 26, 6: 20 });
    yazdirma(wb);
    return kitabe(wb);
  };

  // ------------------------------------------------------------------ istatistik dosyası
  X.istatistik = async function (sonuc, sinav, araAgirlik, arsiv) {
    const esik = sonuc.ayarlar.basari_esigi;
    const [maddeler, g] = OS.maddeAnalizi(sonuc, { basari_esigi: esik, cikti_esigi: esik });
    const kl = sonuc.klasik;
    const wb = yeni();
    let ws = wb.addWorksheet("Özet");
    metin(ws, 1, 1, `${sinav.ders_kodu} ${sinav.ders_adi} — ${sinav.sinav_turu} ${sinav.tarih}`).font = { bold: true, size: 13 };
    let r = 3;
    metin(ws, r++, 1, "Yorum").font = { bold: true };
    for (const y of g.yorumlar) not(ws, r++, "• " + y);
    r++;
    const satirlar = [["Sınava giren öğrenci", g.ogrenci_sayisi, "0"], ["Sınava girmeyen", sonuc.girmeyenler.length, "0"], ["Ortalama", g.ortalama], ["Ortanca (medyan)", g.medyan],
      ["Standart sapma (örneklem)", g.standart_sapma], ["En düşük", g.en_dusuk], ["En yüksek", g.en_yuksek],
      ["Birinci çeyrek (öğrencilerin dörtte biri bunun altında)", g.birinci_ceyrek], ["Üçüncü çeyrek (öğrencilerin dörtte biri bunun üstünde)", g.ucuncu_ceyrek],
      [`${esik} ve üstü alanların oranı`, g.basari_orani, "0%"], ["Çarpıklık (artı: puanlar düşükte yığılmış)", g.carpiklik], ["Basıklık (normal dağılımda 0)", g.basiklik],
      ["Cronbach alfa güvenirlik katsayısı", g.alfa], ...(kl ? [] : [["Kuder-Richardson 20 güvenirlik katsayısı", g.kr20]]), ["Ölçmenin standart hatası (puan)", g.olcme_hatasi],
      ["Ortalama güçlük (doğru oranı)", g.ortalama_guclik], ["Ortalama ayırt edicilik", g.ortalama_ayirt_edicilik], ["Analizdeki soru sayısı", g.analizdeki_soru_sayisi, "0"]];
    for (const [ad, v, f] of satirlar) { metin(ws, r, 1, ad).font = { bold: true }; sayi(ws, r, 2, v, f || "0.00"); r++; }
    r++;
    not(ws, r, "Okuma rehberi: Güçlük, soruyu doğru yapanların oranıdır (0,30-0,70 arası ideal). Ayırt edicilik, en başarılı %27 ile en başarısız %27'nin o sorudaki başarı farkıdır (0,40 üstü çok iyi, 0,30-0,39 iyi, 0,20-0,29 düzeltilebilir, 0,20 altı sorunlu). Güvenirlik katsayısı 0,70 ve üstü sınıf içi sınavlar için yeterli kabul edilir. Ölçmenin standart hatası, bir öğrencinin puanının ölçme hatası yüzünden ne kadar oynayabileceğini gösterir. Grafikler programdaki yazdırılabilir raporda yer alır.");
    genislik(ws, { 1: 58, 2: 16 });

    ws = wb.addWorksheet("Madde Analizi");
    const b = ["Soru", kl ? "Tam puan" : "Doğru şık", "Güçlük", "Ayırt edicilik", "Nokta çift serili", "Düzeltilmiş madde-toplam", "Soru çıkarılırsa alfa", "Üst grup", "Alt grup",
      ...(kl ? [] : ["A", "B", "C", "D", "E", "Çift", "Boş"]), "Sorunlu", "Açıklama"];
    baslik(ws, 1, b);
    maddeler.forEach((m, i) => {
      const rr = i + 2, s = sonuc.anahtar.sorular[m.soru_no - 1];
      metin(ws, rr, 1, m.soru_no);
      if (kl) sayi(ws, rr, 2, m.tam_puan, "0.##"); else metin(ws, rr, 2, s.durum === "iptal" ? "İptal" : m.dogru_sik);
      [m.guclik, m.ayirt_edicilik, m.nokta_cift_serili, m.duzeltilmis_r, m.alfa_cikarilirsa, m.ust_grup, m.alt_grup].forEach((x, j) => sayi(ws, rr, 3 + j, x));
      let j = 10;
      if (!kl) for (const sik of ["A", "B", "C", "D", "E", "Çift", "Boş"]) {
        const c = sayi(ws, rr, j++, m.sik_oranlari[sik], "0%");
        if (OS.dogruKume(s).has(sik)) { c.fill = dolgu(RENK.D); c.font = { bold: true }; }
      }
      metin(ws, rr, j, m.sorunlar.length ? "Evet" : "");
      metin(ws, rr, j + 1, m.analiz_disi ? "Analiz dışı" : m.sorunlar.join("; "));
      if (m.sorunlar.length) for (const jj of [1, j, j + 1]) ws.getCell(rr, jj).fill = dolgu(RENK.uyari);
      if (m.ayirt_edicilik !== null) ws.getCell(rr, 4).fill = dolgu(m.ayirt_edicilik >= 0.3 ? RENK.D : m.ayirt_edicilik >= 0.2 ? RENK.B : RENK.Y);
    });
    bitir(ws, b.length, { 1: 6, 2: 9, 4: 11, 5: 11, 6: 13, 7: 12, [b.length]: 70 });

    if (!kl) {
      ws = wb.addWorksheet("Çeldiriciler");
      baslik(ws, 1, ["Soru", "Doğru şık", "Yanlış şık", "Seçilme oranı", "Üst grupta", "Alt grupta", "Değerlendirme"]);
      r = 2;
      for (const m of maddeler) for (const c of m.celdiriciler) {
        metin(ws, r, 1, m.soru_no); metin(ws, r, 2, m.dogru_sik); metin(ws, r, 3, c.sik);
        sayi(ws, r, 4, c.oran, "0%"); sayi(ws, r, 5, c.ust, "0%"); sayi(ws, r, 6, c.alt, "0%");
        const cc = metin(ws, r, 7, c.sorunlar.join("; ") || "işliyor");
        if (c.sorunlar.length) cc.fill = dolgu(RENK.uyari);
        r++;
      }
      bitir(ws, 7, { 1: 6, 2: 9, 3: 9, 4: 13, 5: 11, 6: 11, 7: 42 });
    }
    ws = wb.addWorksheet("Beş Grup");
    baslik(ws, 1, ["Soru", "1. grup (en düşük)", "2. grup", "3. grup", "4. grup", "5. grup (en yüksek)"]);
    r = 2;
    for (const m of maddeler) {
      if (m.analiz_disi || !m.bes_grup.length) continue;
      metin(ws, r, 1, `Soru ${m.soru_no}`);
      m.bes_grup.forEach((x, j) => { const c = sayi(ws, r, j + 2, x, "0%"); if (x !== null) c.fill = dolgu(x >= 0.7 ? RENK.D : x >= 0.4 ? RENK.B : RENK.Y); });
      r++;
    }
    bitir(ws, 6, { 1: 10, 2: 18, 6: 20 });
    if (g.bos_orani_sirayla.length) {
      ws = wb.addWorksheet("Boş Bırakma");
      baslik(ws, 1, ["Kitapçıktaki sıra", "Boş bırakma oranı"]);
      g.bos_orani_sirayla.forEach((x, k) => { metin(ws, k + 2, 1, k + 1); sayi(ws, k + 2, 2, x, "0%"); });
      not(ws, g.bos_orani_sirayla.length + 3, g.hiz_uyarisi || "Son sorularda belirgin bir boş bırakma artışı yok; süre yeterli görünüyor.", 3);
      genislik(ws, { 1: 18, 2: 18 });
    }
    if (!kl) {
      ws = wb.addWorksheet("Kişi Uyumu");
      baslik(ws, 1, ["Öğrenci No", "Ad Soyad", "Puan", "Uyum indeksi", "Beklenmedik sorular"]);
      g.kisi_uyumu.forEach((k, i) => { no(ws, i + 2, 1, k.no); metin(ws, i + 2, 2, k.ad); sayi(ws, i + 2, 3, k.puan); sayi(ws, i + 2, 4, k.indeks); metin(ws, i + 2, 5, k.beklenmedik.join(", ")); });
      bitir(ws, 5, { 1: 13, 2: 28, 4: 13, 5: 30 });
      ws = wb.addWorksheet("Benzer Cevaplar");
      baslik(ws, 1, ["1. öğrenci no", "1. öğrenci", "2. öğrenci no", "2. öğrenci", "Aynı yanlış şık", "İkisinin de yanlışı", "Bütün aynı cevaplar", "Sınıf ortalamasından uzaklık (standart sapma)", "Sorular"]);
      g.benzer_ciftler.forEach((c, i) => { [c.no1, c.ad1, c.no2, c.ad2, c.ayni_yanlis, c.ikisi_yanlis, c.ayni_cevap].forEach((x, j) => metin(ws, i + 2, j + 1, x)); sayi(ws, i + 2, 8, c.z, "0.0"); metin(ws, i + 2, 9, c.sorular.join(", ")); });
      not(ws, g.benzer_ciftler.length + 3, g.benzer_ciftler.length ? "Aynı kitapçıktaki öğrenci çiftlerinden sınıf geneline göre olağandışı sayıda aynı yanlış şıkkı işaretleyenler. Bu bir istatistiksel işarettir, kopya kanıtı değildir; oturma düzeni ve kâğıtlarla birlikte değerlendirilmelidir." : "Olağandışı benzerlik gösteren öğrenci çifti bulunmadı.", 9);
      bitir(ws, 9, { 1: 13, 2: 24, 3: 13, 4: 24, 8: 16, 9: 30 });
    }
    // Ek Analizler
    ws = wb.addWorksheet("Ek Analizler");
    r = 1;
    const bolum = (t) => { r++; metin(ws, r++, 1, t).font = { bold: true, size: 12 }; };
    const t = OS.tasarimDenetimi(sonuc, maddeler.map((m) => m.guclik));
    const sans = OS.sansPuani(sonuc);
    if (t || sans !== null) {
      bolum("Sınav tasarımı");
      if (t) { metin(ws, r, 1, "Anahtarda şıkların sayısı"); metin(ws, r++, 2, Object.entries(t.sik_sayilari).map(([x, y]) => `${x}: ${y}`).join(", "));
        metin(ws, r, 1, "Soru sırası ile güçlük sıra korelasyonu"); sayi(ws, r++, 2, t.sira_guclik_korelasyonu); for (const x of t.notlar) not(ws, r++, "• " + x, 6); }
      if (sans !== null) { metin(ws, r, 1, "Rastgele işaretleyenin beklenen puanı (şans puanı)"); sayi(ws, r++, 2, sans); metin(ws, r, 1, "Şans puanının altında kalan öğrenci"); metin(ws, r++, 2, sonuc.ogrenciler.filter((o) => o.puan.sayi() < sans).length); }
    }
    const kk = OS.kitapcikKarsilastirma(sonuc);
    if (kk) {
      bolum("Kitapçıklar eşdeğer mi? (Welch t testi)");
      for (const [ad, x, f] of [[`${kk.kitapcik1} ortalaması (${kk.n1} kişi)`, kk.ortalama1], [`${kk.kitapcik2} ortalaması (${kk.n2} kişi)`, kk.ortalama2], ["Fark", kk.fark], ["t", kk.t], ["Serbestlik derecesi", kk.serbestlik, "0.0"], ["p değeri", kk.p, "0.000"], ["Etki büyüklüğü (Cohen d)", kk.etki]]) { metin(ws, r, 1, ad); sayi(ws, r++, 2, x, f || "0.00"); }
      not(ws, r++, kk.p < 0.05 ? "p değeri 0,05'ten küçük: kitapçıklardan biri ötekinden anlamlı biçimde zor ya da kolay olmuş olabilir." : "Kitapçıklar arasında anlamlı bir fark yok (p ≥ 0,05).", 6);
    }
    const sinir = OS.sinirdakiOgrenciler(sonuc, esik, g.olcme_hatasi);
    bolum(`Sınırdaki öğrenciler (puanı ${esik} eşiğine ölçme hatası kadar yakın)`);
    baslik(ws, r++, ["Öğrenci No", "Ad Soyad", "Puan", "Eşiğe uzaklık"]);
    for (const x of sinir) { no(ws, r, 1, x.no); metin(ws, r, 2, x.ad); sayi(ws, r, 3, x.puan); sayi(ws, r, 4, x.fark).fill = dolgu(x.fark < 0 ? RENK.Y : RENK.D); r++; }
    const a = sonuc.ayarlar;
    const f = OS.finalGereken(sonuc, araAgirlik, a.gecme_ortalamasi, a.final_alt_siniri);
    if (f.length) {
      bolum(`Finalde gereken puan (ara sınav %${araAgirlik}, final %${100 - araAgirlik}; geçme ortalaması ${a.gecme_ortalamasi}, final alt sınırı ${a.final_alt_siniri})`);
      baslik(ws, r++, ["Öğrenci No", "Ad Soyad", "Ara sınav", "Finalde en az"]);
      for (const x of f) { no(ws, r, 1, x.no); metin(ws, r, 2, x.ad); sayi(ws, r, 3, x.puan); const c = x.gereken === null ? metin(ws, r, 4, "100 de yetmez") : sayi(ws, r, 4, x.gereken); if (x.gereken === null || x.gereken > 80) c.fill = dolgu(RENK.Y); r++; }
      not(ws, r++, "Geçme kuralı ders yönetmeliğine göre farklı olabilir; geçme ortalaması ve final alt sınırı 3. adımda değiştirilebilir. Bütünleme ve harf notu dönüşümü hesaba katılmamıştır.", 6);
    }
    const rs = OS.rasch(sonuc);
    if (rs) {
      bolum("Rasch modeli: soruların zorluk ölçeği (logit; 0 = ortalama soru, artı = zor)");
      baslik(ws, r++, ["Soru", "Zorluk (logit)", "Standart hata"]);
      for (const [s, b2] of [...rs.soru_zorluklari].sort((p, q) => p[1] - q[1])) { metin(ws, r, 1, s); sayi(ws, r, 2, b2); sayi(ws, r, 3, rs.soru_hatalari.get(s)); r++; }
      not(ws, r++, `Sınav en iyi, yaklaşık %${OS.pyOndalik(rs.en_iyi_puan, 0)} başarı düzeyindeki öğrencileri ayırt ediyor. Bu düzeyin çok altındaki ve üstündeki öğrencileri ayırmakta sınav daha az bilgi verir.`, 6);
    }
    if (arsiv && arsiv.length) {
      bolum("Aynı dersin önceki sınavlarıyla karşılaştırma");
      const kodlar = [...new Set(arsiv.flatMap((x) => Object.keys(x.cikti_basarilari || {})))].sort(OS.dogalKarsilastir);
      baslik(ws, r++, ["Tarih", "Sınav", "Öğrenci", "Ortalama", "Başarılı oranı", "Güvenirlik", ...kodlar]);
      for (const x of arsiv) { [x.tarih, x.sinav_turu, x.ogrenci_sayisi].forEach((y, j) => metin(ws, r, j + 1, y)); sayi(ws, r, 4, x.ortalama); sayi(ws, r, 5, x.basari_orani, "0%"); sayi(ws, r, 6, x.guvenirlik); kodlar.forEach((k2, j) => sayi(ws, r, 7 + j, (x.cikti_basarilari || {})[k2])); r++; }
    }
    genislik(ws, { 1: 50, 2: 28, 3: 14, 4: 16, 5: 14, 6: 14 });

    ws = wb.addWorksheet("Standart Puanlar");
    baslik(ws, 1, ["Öğrenci No", "Ad Soyad", "Puan", "Sıra", "Yüzdelik sıra", "z puanı", "T puanı"]);
    const sirali = [...sonuc.ogrenciler].sort((p, q) => q.puan.kars(p.puan));
    const ort = g.ortalama || 0, sd = g.standart_sapma || 0;
    sirali.forEach((o, i) => {
      const p = o.puan.sayi();
      no(ws, i + 2, 1, o.no); metin(ws, i + 2, 2, o.ad); sayi(ws, i + 2, 3, p);
      metin(ws, i + 2, 4, 1 + sirali.filter((x) => x.puan.kars(o.puan) > 0).length);
      sayi(ws, i + 2, 5, sirali.filter((x) => x.puan.kars(o.puan) < 0).length / sirali.length, "0%");
      const z = sd ? (p - ort) / sd : null;
      sayi(ws, i + 2, 6, z); sayi(ws, i + 2, 7, z === null ? null : 50 + 10 * z, "0.0");
    });
    bitir(ws, 7, { 1: 13, 2: 28, 4: 7, 5: 13 });
    yazdirma(wb);
    return kitabe(wb);
  };

  // ------------------------------------------------------------------ öğrenme çıktısı dosyası
  X.cikti = async function (sonuc, aciklamalar, dersKodlari) {
    const esik = sonuc.ayarlar.basari_esigi;
    const rapor = OS.ogrenmeCiktisiRaporu(sonuc, esik, aciklamalar);
    if (!rapor.length) return null;
    const wb = yeni();
    let ws = wb.addWorksheet("Soru-Çıktı Eşlemesi");
    const kodlar = [...new Set(sonuc.anahtar.sorular.flatMap((s) => s.ogrenme_ciktilari || []))].sort(OS.dogalKarsilastir);
    baslik(ws, 1, ["Soru", "Soru puanı", ...kodlar, "Toplam %", "Program çıktıları"]);
    sonuc.anahtar.sorular.forEach((s, i) => {
      metin(ws, i + 2, 1, s.no); puan(ws, i + 2, 2, sonuc.soru_puanlari[i], 2);
      const d = OS.ciktiDagilimi(s);
      kodlar.forEach((k2, j) => metin(ws, i + 2, 3 + j, d.has(k2) ? d.get(k2) : null));
      const t = [...d.values()].reduce((x, y) => x + y, 0);
      const c = metin(ws, i + 2, 3 + kodlar.length, d.size ? t : null);
      if (d.size && t !== 100) c.fill = dolgu(RENK.Y);
      metin(ws, i + 2, 4 + kodlar.length, (s.program_ciktilari || []).join(", "));
    });
    bitir(ws, 4 + kodlar.length, { 1: 7, 2: 11, [3 + kodlar.length]: 10, [4 + kodlar.length]: 22 });
    ws = wb.addWorksheet("Sisteme Aktarım");
    let satirlar = [];
    try { satirlar = OS.soruTanimiSatirlari(sonuc.anahtar, sonuc.ayarlar, dersKodlari); } catch (_) { satirlar = []; }
    const enFazla = Math.max(3, ...satirlar.map((x) => x.length));
    const bb = ["Soru No", "Soru Puan", "Soru metni"];
    for (let i = 0; i < (enFazla - 3) / 2; i++) bb.push("DÇ Sıra", "Etki Oran");
    baslik(ws, 1, bb);
    satirlar.forEach((s, i) => s.forEach((x, j) => metin(ws, i + 2, j + 1, x)));
    not(ws, satirlar.length + 3, "Başlık satırı dışındaki hücreleri seçip kopyalayın; Sınav Akreditasyon İşlemleri > Toplu Aktarım Yap > Aktarım Kutusu'na yapıştırıp Aktar'a basın (Kolon Ayracı: Excel'den Kopyalandı). DÇ Sıra, dersin öğrenme çıktısı sırasıdır (Ö05 için 5).", Math.max(6, enFazla));
    genislik(ws, { 1: 9, 2: 10, 3: 12 });
    ws = wb.addWorksheet("Sınav Dağılımı");
    const dag = OS.ciktiDagilimiSinav(sonuc.anahtar, sonuc.soru_puanlari);
    const tam = OS.tamSayiDagilim(dag);
    baslik(ws, 1, ["Öğrenme çıktısı", "Açıklama", "Sınavdaki payı (%)", "Tam sayı (%)"]);
    let r = 2;
    for (const [k2, x] of dag) { metin(ws, r, 1, k2); metin(ws, r, 2, aciklamalar[k2] || ""); sayi(ws, r, 3, x.sayi()); metin(ws, r, 4, tam.get(k2)); r++; }
    metin(ws, r, 1, "Toplam").font = { bold: true }; sayi(ws, r, 3, OS.topla([...dag.values()]).sayi()).font = { bold: true }; metin(ws, r, 4, [...tam.values()].reduce((x, y) => x + y, 0)).font = { bold: true };
    genislik(ws, { 1: 16, 2: 70, 3: 18, 4: 13 });
    ws = wb.addWorksheet("Sınıf Başarısı");
    baslik(ws, 1, ["Tür", "Kod", "Açıklama", "Sorular", "Sınavdaki payı (%)", "Sınıf başarı yüzdesi", `%${esik} ve üstüne ulaşan öğrenci`]);
    rapor.forEach((c, i) => {
      metin(ws, i + 2, 1, c.tur); metin(ws, i + 2, 2, c.kod); metin(ws, i + 2, 3, c.aciklama); metin(ws, i + 2, 4, c.sorular.join(", "));
      sayi(ws, i + 2, 5, c.tur.startsWith("Öğrenme") ? c.sinav_agirligi : null);
      const h = sayi(ws, i + 2, 6, c.sinif_yuzdesi);
      if (c.sinif_yuzdesi !== null) h.fill = dolgu(c.sinif_yuzdesi >= esik + 10 ? RENK.D : c.sinif_yuzdesi >= esik ? RENK.B : RENK.Y);
      sayi(ws, i + 2, 7, c.ulasan_orani, "0%");
    });
    bitir(ws, 7, { 1: 18, 2: 8, 3: 60, 4: 16, 5: 16, 6: 16, 7: 20 });
    ws = wb.addWorksheet("Öğrenci Bazında");
    baslik(ws, 1, ["Öğrenci No", "Ad Soyad", ...rapor.map((c) => c.kod)]);
    sonuc.ogrenciler.forEach((o, i) => {
      no(ws, i + 2, 1, o.no); metin(ws, i + 2, 2, o.ad);
      rapor.forEach((c, j) => { const x = c.ogrenci_yuzdeleri.get(o.no); const h = sayi(ws, i + 2, 3 + j, Math.round(x * 100) / 100); if (x < esik) h.fill = dolgu(RENK.Y); });
    });
    bitir(ws, 2 + rapor.length, { 1: 13, 2: 28 });
    yazdirma(wb);
    return kitabe(wb);
  };

  // ------------------------------------------------------------------ aktarım profili ve klasik şablon
  X.profil = async function (profil, sonuc) {
    const [bas, veri] = OS.tabloUret(profil, sonuc);
    const wb = yeni();
    const ws = wb.addWorksheet(profil.sayfa_adi || "Sayfa1");
    bas.forEach((b, j) => (ws.getCell(1, j + 1).value = b));
    ws.getRow(1).font = { bold: true };
    veri.forEach((s, i) => s.forEach((h, j) => {
      const c = ws.getCell(i + 2, j + 1);
      if (h.tur === "sayi") { c.value = OS.ondalikSayi(h.deger); c.numFmt = bicim(h.ondalik); }
      else if (h.tur === "tamsayi") { c.value = h.deger; c.numFmt = "0"; }
      else if (h.tur === "girmedi") c.value = h.deger === "" ? null : h.deger;
      else { c.value = h.deger === "" ? null : h.deger; c.numFmt = "@"; }
    }));
    genislik(ws, Object.fromEntries(bas.map((b, j) => [j + 1, /^ad/i.test(b) ? 30 : /no/i.test(b) ? 14 : Math.max(8, Math.min(40, b.length + 2))])));
    return kitabe(wb);
  };
  X.klasikSablon = async function (ogrenciler, n, puanlar) {
    const wb = yeni();
    const ws = wb.addWorksheet("Puanlar");
    baslik(ws, 1, ["Öğrenci No", "Ad Soyad", ...Array.from({ length: n }, (_, k) => `S${k + 1}`)]);
    ogrenciler.forEach((o, i) => { no(ws, i + 2, 1, o.no); metin(ws, i + 2, 2, o.ad); (puanlar[o.no] || []).forEach((x, k) => metin(ws, i + 2, 3 + k, x)); });
    ws.views = [{ state: "frozen", xSplit: 2, ySplit: 1 }];
    genislik(ws, { 1: 14, 2: 28 }, 7);
    return kitabe(wb);
  };
})();
