// Tarayıcı motorunun Python motoruyla aynı sonucu verdiğini denetler.
// Beklenen değerler: python tools/web_parite.py  ->  tests/web/parite_*.json (ve varsa ornek_veri/web_parite_gercek.json)
import { createRequire } from "node:module";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const KOK = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
require(join(KOK, "web/src/cekirdek.js"));
require(join(KOK, "web/src/istatistik.js"));
require(join(KOK, "web/src/ciktilar.js"));
const XLSX = require(join(KOK, "web/vendor/xlsx_0.18.5_dist_xlsx.full.min.js"));
const OS = globalThis.OS;
require(join(KOK, "web/src/dosya.js"));

const kesir = (k) => `${k.p}/${k.q}`;
const mapObj = (m) => (m instanceof Map ? Object.fromEntries([...m].map(([k, v]) => [k, mapObj(v)])) : m);

function hesapla(sen, proje, sonuc) {
  const esik = proje.ayarlar.basari_esigi;
  const [m, g] = OS.maddeAnalizi(sonuc, { basari_esigi: esik, cikti_esigi: esik });
  const rapor = OS.ogrenmeCiktisiRaporu(sonuc, esik);
  const dag = OS.ciktiDagilimiSinav(sonuc.anahtar, sonuc.soru_puanlari);
  const rs = OS.rasch(sonuc);
  const kk = OS.kitapcikKarsilastirma(sonuc);
  const t = OS.tasarimDenetimi(sonuc, m.map((x) => x.guclik));
  const yuzdeler = (r) => Object.fromEntries(r.ogrenci_yuzdeleri);
  return {
    ogrenciler: sonuc.ogrenciler.map((o) => ({ no: o.no, ad: o.ad, puan: kesir(o.puan), ham: kesir(o.ham_puan), ceza: kesir(o.ceza),
      durum: o.sorular.map((s) => s.durum).join(""), cevaplar: o.cevaplar, dogru: o.dogru, yanlis: o.yanlis, bos: o.bos, kitapcik: o.kitapcik,
      kaynak: o.kaynak_soru, listede: o.listede, oneriler: o.oneriler, uyarilar: o.uyarilar.map((u) => [u.tur, u.mesaj]) })),
    girmeyenler: sonuc.girmeyenler.map((x) => x.no),
    soru_puanlari: sonuc.soru_puanlari.map(kesir),
    maddeler: m.map((x) => ({ soru_no: x.soru_no, analiz_disi: x.analiz_disi, guclik: x.guclik, ayirt: x.ayirt_edicilik, r: x.nokta_cift_serili,
      r_duz: x.duzeltilmis_r, alfa_c: x.alfa_cikarilirsa, bes: x.bes_grup, sik: x.sik_oranlari, sorunlar: x.sorunlar,
      celdirici: x.celdiriciler.map((c) => [c.sik, c.oran, c.ust, c.alt, c.sorunlar]) })),
    genel: Object.fromEntries(["ogrenci_sayisi", "ortalama", "standart_sapma", "en_dusuk", "en_yuksek", "medyan", "kr20", "birinci_ceyrek", "ucuncu_ceyrek",
      "carpiklik", "basiklik", "alfa", "olcme_hatasi", "basari_orani", "ortalama_guclik", "ortalama_ayirt_edicilik", "bos_orani_sirayla", "hiz_uyarisi", "yorumlar"].map((k) => [k, g[k]])),
    kisi_uyumu: g.kisi_uyumu.map((k) => [k.no, k.indeks, k.beklenmedik]),
    benzer: g.benzer_ciftler.map((c) => [c.no1, c.no2, c.ayni_yanlis, c.ikisi_yanlis, c.ayni_cevap, c.z]),
    cikti_raporu: rapor.map((c) => [c.tur, c.kod, c.sorular, c.sinif_yuzdesi, c.sinav_agirligi, c.ulasan_orani, yuzdeler(c)]),
    cikti_dagilimi: Object.fromEntries([...dag].map(([k, x]) => [k, kesir(x)])),
    tam_sayi_dagilim: Object.fromEntries(OS.tamSayiDagilim(dag)),
    cikti_denetimi: OS.ciktiDenetimi(proje.anahtar, sen.ders_kodlari),
    anahtar_eksikleri: OS.anahtarEksikleri(proje.anahtar, proje.ayarlar, proje.bicim === "klasik"),
    soru_tanimi: proje.anahtar.sorular.some((s) => s.ogrenme_ciktilari.length) ? OS.soruTanimiMetni(proje.anahtar, proje.ayarlar, sen.ders_kodlari) : "",
    sinir: OS.sinirdakiOgrenciler(sonuc, esik, g.olcme_hatasi).map((x) => [x.no, x.fark]),
    final: OS.finalGereken(sonuc, 40, proje.ayarlar.gecme_ortalamasi, proje.ayarlar.final_alt_siniri).map((x) => [x.no, x.gereken]),
    sans: OS.sansPuani(sonuc),
    tasarim: t === null ? null : [t.sik_sayilari, t.en_uzun_seri, t.seri_harfi, t.sira_guclik_korelasyonu, t.notlar],
    kitapcik: kk === null ? null : [kk.ortalama1, kk.ortalama2, kk.t, kk.serbestlik, kk.p, kk.etki],
    rasch: rs === null ? null : [mapObj(rs.soru_zorluklari), rs.en_iyi_olctugu, rs.en_iyi_puan, rs.disarida_kalan_ogrenci, rs.disarida_kalan_soru],
  };
}

function karsilastir(a, b, yol, farklar) {
  if (farklar.length > 25) return;
  if (typeof a === "number" && typeof b === "number") {
    if (!(Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b)))) farklar.push(`${yol}: python=${a} js=${b}`);
    return;
  }
  if (a === null || b === null || typeof a !== "object" || typeof b !== "object") {
    if (a !== b) farklar.push(`${yol}: python=${JSON.stringify(a)} js=${JSON.stringify(b)}`);
    return;
  }
  if (Array.isArray(a) !== Array.isArray(b)) { farklar.push(`${yol}: tür farklı`); return; }
  const anahtarlar = new Set([...Object.keys(a), ...Object.keys(b)]);
  if (Array.isArray(a) && a.length !== b.length) farklar.push(`${yol}: uzunluk python=${a.length} js=${b.length}`);
  for (const k of anahtarlar) karsilastir(a[k], b[k], `${yol}.${k}`, farklar);
}

let hata = 0;
const dosyalar = readdirSync(join(KOK, "tests/web")).filter((f) => f.startsWith("parite_")).map((f) => join(KOK, "tests/web", f));
const gercek = join(KOK, "ornek_veri/web_parite_gercek.json");
if (existsSync(gercek)) dosyalar.push(gercek);
for (const f of dosyalar) {
  const sen = JSON.parse(readFileSync(f, "utf8"));
  const proje = OS.projeyiTamamla(sen.proje);
  const liste = sen.liste ? OS.listeOku(XLSX, readFileSync(join(KOK, sen.liste)), sen.liste) : null;
  let sonuc;
  const farklar = [];
  if (sen.dat) {
    const m = OS.metinDosyasiOku(new Uint8Array(readFileSync(join(KOK, sen.dat))));
    const oner = OS.sablonOner(m.satirlar, OS.yeniOkuyucu());
    karsilastir(sen.okuyucu_onerisi, oner, "okuyucu", farklar);
    if (m.kodlama !== sen.kodlama) farklar.push(`kodlama: ${sen.kodlama} / ${m.kodlama}`);
    const { kayitlar } = OS.satirlariOku(m.satirlar, proje.okuyucu);
    sonuc = OS.sinaviDegerlendir(kayitlar, proje.anahtar, proje.ayarlar, liste, proje.duzeltmeler);
  } else {
    sonuc = OS.klasikDegerlendir(liste, proje.anahtar, proje.ayarlar, proje.klasik_puanlar);
  }
  karsilastir(sen.beklenen, hesapla(sen, proje, sonuc), sen.ad, farklar);
  if (farklar.length) { hata++; console.log(`✗ ${sen.ad}: ${farklar.length} fark`); for (const x of farklar.slice(0, 25)) console.log("   " + x); }
  else console.log(`✓ ${sen.ad}: ${sonuc.ogrenciler.length} öğrenci, bütün değerler aynı`);
}
process.exit(hata ? 1 : 0);
