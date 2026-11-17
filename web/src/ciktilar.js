/* Optik Sınav — tarayıcı sürümü: dosya adları, aktarım profilleri ve Akademik Bilgi Sistemi soru tanımı metni.
 * Python karşılıkları: core/ciktilar.py, export/profil.py, export/soru_tanimi.py.
 */
(function (kok) {
  "use strict";
  const OS = kok.OS;

  function dosyaAdiParcasi(m) {
    let s = String(m || "").replace(/[ıİğĞüÜşŞöÖçÇ]/g, (c) => ({ ı: "i", İ: "I", ğ: "g", Ğ: "G", ü: "u", Ü: "U", ş: "s", Ş: "S", ö: "o", Ö: "O", ç: "c", Ç: "C" })[c]);
    s = s.normalize("NFKD").replace(/[̀-ͯ]/g, "");
    if (s.includes(" ")) s = s.replace(/\S+/g, (w) => w[0].toUpperCase() + w.slice(1).toLowerCase()).replace(/ /g, "");
    return s.replace(/[^A-Za-z0-9_-]/g, "");
  }
  function ciktiAdi(sinav, ek, uzanti = ".xlsx") {
    const p = [dosyaAdiParcasi(sinav.ders_kodu) || "SINAV", dosyaAdiParcasi(sinav.sinav_turu) || "Sinav"];
    if (sinav.tarih) p.push(String(sinav.tarih).replace(/[^0-9-]/g, ""));
    p.push(ek);
    return p.filter((x) => x).join("_") + uzanti;
  }

  // ------------------------------------------------------------------ soru tanımı (sisteme toplu aktarım)
  function ciktiSirasi(kod, dersKodlari) {
    if (dersKodlari && dersKodlari.includes(kod)) return String(dersKodlari.indexOf(kod) + 1);
    const s = kod.replace(/\D/g, "");
    return s ? String(parseInt(s, 10)) : kod;
  }
  function puanMetni(d, ayirici) {
    let s = String(d).trim().replace(",", ".");
    if (s.includes(".")) s = s.replace(/0+$/, "").replace(/\.$/, "");
    return s.replace(".", ayirici);
  }
  function soruTanimiSatirlari(anahtar, ayar, dersKodlari = null, ayirici = ",") {
    const sorular = OS.aktarimSorulari(anahtar).map((i) => anahtar.sorular[i]);  // bonus soru sisteme gitmez
    const n = sorular.length;
    let puanlar;
    if (ayar.yontem === "esit") puanlar = OS.esitSoruPuanlari(ayar.toplam_puan, n);
    else { puanlar = sorular.map((s) => s.puan || "0"); OS.soruPuanlari(anahtar, ayar); }
    return sorular.map((s, i) => {
      const satir = [String(i + 1), puanMetni(puanlar[i], ayirici), `Soru ${i + 1}`];
      for (const [kod, y] of OS.ciktiDagilimi(s)) satir.push(ciktiSirasi(kod, dersKodlari), String(y));
      return satir;
    });
  }
  const soruTanimiMetni = (a, ayar, kodlar = null, ayirici = ",") => soruTanimiSatirlari(a, ayar, kodlar, ayirici).map((s) => s.join("\t")).join("\n");

  // ------------------------------------------------------------------ aktarım profilleri
  const PROFILLER = {
    akreditasyon_soru_bazli_varsayilan: { ad: "akreditasyon_soru_bazli_varsayilan", baslik: "Akreditasyon: soru bazlı puan (geçici)", sayfa_adi: "Soru Puanları",
      sutunlar: [{ alan: "ogrenci_no", baslik: "Öğrenci No" }, { alan: "ad_soyad", baslik: "Ad Soyad" }, { alan: "soru_puanlari", baslik: "S{n}" }],
      ondalik_basamak: 2, yuvarlama: "yarim_yukari", girmedi_gosterimi: "G", girmeyenleri_dahil_et: true, listede_olmayanlari_dahil_et: false, sira: "liste", ondalik_ayirici: "," },
    not_giris_varsayilan: { ad: "not_giris_varsayilan", baslik: "Not Giriş: öğrenci numarası ve puan (geçici)", sayfa_adi: "Notlar",
      sutunlar: [{ alan: "ogrenci_no", baslik: "Öğrenci No" }, { alan: "ad_soyad", baslik: "Ad Soyad" }, { alan: "puan", baslik: "Puan" }],
      ondalik_basamak: 0, yuvarlama: "yarim_yukari", girmedi_gosterimi: "G", girmeyenleri_dahil_et: true, listede_olmayanlari_dahil_et: false, sira: "liste", ondalik_ayirici: "," },
  };
  function basliklar(profil, n) {
    const b = [];
    for (const s of profil.sutunlar) if (s.alan === "soru_puanlari") for (let k = 1; k <= n; k++) b.push((s.baslik || "S{n}").replace("{n}", k)); else b.push(s.baslik);
    return b;
  }
  /** Hücre: {deger, tur: "metin"|"sayi"|"tamsayi"|"girmedi", ondalik} */
  function ogrenciHucreleri(profil, o, og, sonuc) {
    const no = o ? o.no : og.no;
    const ad = (o ? o.ad : og.ad) || "";
    const sira = OS.aktarimSorulari(sonuc.anahtar);  // bonus soru aktarımda görünmez
    const sayi = (d) => ({ deger: OS.yuvarla(d, profil.ondalik_basamak, profil.yuvarlama), tur: "sayi", ondalik: profil.ondalik_basamak });
    const girmedi = { deger: profil.girmedi_gosterimi, tur: "girmedi" };
    const h = [];
    for (const s of profil.sutunlar) {
      const a = s.alan;
      if (a === "ogrenci_no") h.push({ deger: no, tur: "metin" });
      else if (a === "ad_soyad") h.push({ deger: ad, tur: "metin" });
      else if (a === "soru_puanlari") for (const k of sira) h.push(o ? sayi(o.sorular[k].puan) : girmedi);
      else if (!o) h.push(girmedi);
      else if (a === "puan") h.push(sayi(o.puan));
      else if (["dogru", "yanlis", "bos"].includes(a)) h.push({ deger: o[a], tur: "tamsayi" });
    }
    return h;
  }
  function ogrenciSirasi(profil, sonuc, sira = null) {
    const okunan = new Map(sonuc.ogrenciler.map((o) => [o.no, o]));
    if (sira) {
      const la = new Map((sonuc.liste ? sonuc.liste.ogrenciler : []).map((o) => [o.no, o]));
      return sira.map((no) => [okunan.get(no) || null, la.get(no) || { no, ad: "" }]);
    }
    const r = [];
    if (sonuc.liste_var && sonuc.liste && profil.sira === "liste") {
      for (const og of sonuc.liste.ogrenciler) { const o = okunan.get(og.no) || null; if (!o && !profil.girmeyenleri_dahil_et) continue; r.push([o, og]); }
      if (profil.listede_olmayanlari_dahil_et) for (const o of sonuc.listede_olmayanlar) r.push([o, null]);
      return r;
    }
    for (const o of sonuc.ogrenciler) { if (!o.listede && !profil.listede_olmayanlari_dahil_et) continue; r.push([o, null]); }
    if (profil.girmeyenleri_dahil_et) for (const g of sonuc.girmeyenler) r.push([null, g]);
    return r;
  }
  function tabloUret(profil, sonuc, sira = null) {
    return [basliklar(profil, OS.aktarimSorulari(sonuc.anahtar).length), ogrenciSirasi(profil, sonuc, sira).map(([o, og]) => ogrenciHucreleri(profil, o, og, sonuc))];
  }
  function hucreMetni(h, profil) {
    if (h.tur === "sayi") return OS.ondalikMetni(h.deger, profil.ondalik_ayirici);
    return h.deger === null || h.deger === undefined ? "" : String(h.deger);
  }
  function panoMetni(profil, sonuc, sira = null) {
    return tabloUret(profil, sonuc, sira)[1].map((s) => s.map((h) => hucreMetni(h, profil)).join("\t")).join("\n");
  }

  // ---------------------------------------------------------------- sistemin soru bazlı puan dosyası (Python: sistem_puan_dosyasi)
  let cp1254 = null;
  function cp1254Kodla(m) {
    if (!cp1254) {
      cp1254 = new Map();
      const d = new TextDecoder("windows-1254").decode(Uint8Array.from({ length: 256 }, (_, i) => i));
      [...d].forEach((c, i) => { if (!cp1254.has(c)) cp1254.set(c, i); });
    }
    return Uint8Array.from([...m].map((c) => (cp1254.has(c) ? cp1254.get(c) : 63)));
  }
  function sayiMetni(y) {
    let s = OS.ondalikMetni(y, ".");
    if (s.includes(".")) s = s.replace(/0+$/, "").replace(/\.$/, "");
    if (s === "-0" || s === "") s = "0";
    return s.replace(".", ",");
  }
  const SORU_DESENI = /^\s*soru\s*(\d+)\s*\(\s*%?\s*([0-9]+(?:[.,][0-9]+)?)\s*\)\s*$/i;
  function sistemDosyasiniCoz(metin) {
    const ilk = metin.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n")[0];
    const say = (c) => ilk.split(c).length - 1;
    const ayirici = [";", "\t", ","].reduce((a, c) => (say(c) > say(a) ? c : a));
    const basliklar = ilk.split(ayirici);
    let no = null, durum = null, not = null;
    const sorular = [];
    basliklar.forEach((b, j) => {
      const m = SORU_DESENI.exec(b.trim().replace(/^"|"$/g, ""));
      if (m) { sorular.push([parseInt(m[1], 10), j, OS.Kesir.ondaliktan(m[2].replace(",", "."))]); return; }
      const s = OS.sade(b);
      if (no === null && ["ogrencino", "ogrencinumarasi", "numara", "ogrno", "no"].includes(s)) no = j;
      else if (durum === null && s.startsWith("girme")) durum = j;
      else if (not === null && ["sinavnotu", "not", "notu", "puan", "sinavpuani"].includes(s)) not = j;
    });
    if (no === null) throw new Error("Dosyada \"Öğrenci No\" sütunu bulunamadı. Sistemden indirilen soru bazlı puan dosyasını seçin.");
    if (!sorular.length) throw new Error("Dosyada \"Soru1(%…)\" biçiminde soru sütunu bulunamadı. Önce soruları sisteme tanımlayın, sonra sistemden puan dosyasını indirin.");
    sorular.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    return { basliklar, no_sutun: no, durum_sutun: durum, not_sutun: not, soru_sutunlari: sorular.map((x) => x[1]), agirliklar: sorular.map((x) => x[2]), ayirici };
  }
  /** Baytları alır; { bayt, rapor } döndürür. Dosyanın geri kalanı (kodlama, ayırıcı, satır sonu, öteki hücreler) korunur. */
  function sistemDosyasiniDoldur(veri, sonuc) {
    const [metin, kodlama] = OS.baytlariCoz(veri);
    const d = sistemDosyasiniCoz(metin);
    const sira = OS.aktarimSorulari(sonuc.anahtar);
    if (sira.length !== d.soru_sutunlari.length) throw new Error(`Dosyada ${d.soru_sutunlari.length} soru var, programda sisteme giden ${sira.length} soru var. Sistemde tanımlanan sorular bu sınavla aynı olmalı (önce soruları yeniden tanımlayın).`);
    const rapor = { yazilan: 0, girmedi: [], dosyada_olmayan: [], notlar: [] };
    const toplamW = d.agirliklar.reduce((a, w) => a.ekle(w), new OS.Kesir(0n));
    if (!toplamW.esit(100)) rapor.notlar.push(`Dosyadaki soru ağırlıklarının toplamı ${sayiMetni(OS.yuvarla(toplamW, 2))} (100 değil).`);
    if (!sonuc.klasik && sonuc.ayarlar.yanlis_cezasi) rapor.notlar.push("Yanlış cezası soru puanlarına dağıtılamaz: dosyadaki soru puanları ve sınav notu cezasızdır.");
    const okunan = new Map(sonuc.ogrenciler.map((o) => [o.no, o]));
    const satirSonu = metin.includes("\r\n") ? "\r\n" : (metin.includes("\r") && !metin.includes("\n") ? "\r" : "\n");
    const satirlar = metin.split(satirSonu);
    const dosyadaki = new Set();
    const en = Math.max(d.no_sutun, ...d.soru_sutunlari, ...[d.durum_sutun, d.not_sutun].filter((x) => x !== null));
    for (let r = 1; r < satirlar.length; r++) {
      if (!satirlar[r].trim()) continue;
      const h = satirlar[r].split(d.ayirici);
      while (h.length < en + 1) h.push("");
      const no = h[d.no_sutun].replace(/\s/g, "").replace(/^"|"$/g, "");
      if (!/^\d+$/.test(no)) continue;
      dosyadaki.add(no);
      const o = okunan.get(no);
      if (!o) {
        rapor.girmedi.push(no);
        for (const j of d.soru_sutunlari) h[j] = "";
        if (d.not_sutun !== null) h[d.not_sutun] = "";
        if (d.durum_sutun !== null) h[d.durum_sutun] = "Girmedi";
      } else {
        let toplam = 0n;
        d.soru_sutunlari.forEach((j, k) => {
          const i = sira[k];
          const tam = sonuc.soru_puanlari[i];
          const pay = tam.sifirMi() ? new OS.Kesir(0n) : OS.Kesir.of(o.sorular[i].puan).bol(tam);
          const y = OS.yuvarla(pay.carp(d.agirliklar[k]), 2);
          toplam += y.n;
          h[j] = sayiMetni(y);
        });
        if (d.not_sutun !== null) h[d.not_sutun] = sayiMetni({ n: toplam, ondalik: 2 });
        if (d.durum_sutun !== null) h[d.durum_sutun] = "Girdi";
        rapor.yazilan++;
      }
      satirlar[r] = h.join(d.ayirici);
    }
    rapor.dosyada_olmayan = sonuc.ogrenciler.filter((o) => !dosyadaki.has(o.no)).map((o) => o.no);
    if (dosyadaki.size && !rapor.yazilan) throw new Error(`Dosyadaki ${dosyadaki.size} öğrencinin hiçbiri bu sınavda yok. Sistemde başka bir dersin ya da sınavın puan dosyası indirilmiş olabilir: dersi ve sınavı kontrol edip dosyayı yeniden indirin.`);
    const yeni = satirlar.join(satirSonu);
    let bayt;
    if (kodlama === "windows-1254") bayt = cp1254Kodla(yeni);
    else { const u = new TextEncoder().encode(yeni); bayt = kodlama === "utf-8-sig" ? Uint8Array.from([0xef, 0xbb, 0xbf, ...u]) : u; }
    return { bayt, rapor };
  }

  Object.assign(OS, { sistemDosyasiniCoz, sistemDosyasiniDoldur, dosyaAdiParcasi, ciktiAdi, soruTanimiSatirlari, soruTanimiMetni, PROFILLER, tabloUret, hucreMetni, panoMetni });
})(typeof globalThis !== "undefined" ? globalThis : window);
