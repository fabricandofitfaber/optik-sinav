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

  Object.assign(OS, { dosyaAdiParcasi, ciktiAdi, soruTanimiSatirlari, soruTanimiMetni, PROFILLER, tabloUret, hucreMetni, panoMetni });
})(typeof globalThis !== "undefined" ? globalThis : window);
