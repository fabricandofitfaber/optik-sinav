/* Optik Sınav — tarayıcı sürümü: 3-5. adımlar (kontrol, sisteme aktar, istatistikler), yardım, yazdırılabilir rapor ve açılış. */
(function () {
  "use strict";
  const OS = window.OS, UI = window.UI, D = UI.D;
  const { e, $, $$, bildir, pencere, bilgi, dosyaSec, baytOku, indir, kopyala, yerel } = UI;
  const v = OS.v;
  const pct = (x) => {
    if (x === null || x === undefined) return "-";
    const m = OS.pyOndalik(Math.abs(x) * 100, 0);
    return (x < 0 && m !== "0" ? "-" : "") + `%${m}`;  // Türkçe yazım: -%1
  };
  const sayi = (x, n = 2) => (x === null || x === undefined || Number.isNaN(x) ? "-" : v(x, n));

  // ------------------------------------------------------------------ 4. adım: kontrol ve düzeltme
  const K = { sekme: null, sira: { sutun: 0, artan: true }, yalnizUyarili: false };
  function sonucSutunlari(s) {
    const n = s.anahtar.sorular.length;
    const kit = Object.keys(s.anahtar.kitapcik_anahtarlari || {}).length > 0 || new Set(s.ogrenciler.map((o) => o.kitapcik)).size > 1;
    const c = [["sira", "Sıra"], ["no", "Öğrenci No"], ["ad", "Ad Soyad"]];
    for (let k = 0; k < n; k++) c.push(["soru", String(k + 1), k]);
    c.push(["dogru", "Doğru"], ["yanlis", "Yanlış"], ["bos", "Boş"], ["puan", "Puan"]);
    if (kit) c.push(["kitapcik", "Kitapçık"]);
    c.push(["uyari", "Uyarı"]);
    return c;
  }
  function sonucTablosu(s) {
    const c = sonucSutunlari(s);
    let satirlar = s.ogrenciler.map((o, i) => ({ o, i }));
    if (K.yalnizUyarili) satirlar = satirlar.filter((x) => x.o.uyarilar.length);
    const [tur, , k] = c[K.sira.sutun] || c[0];
    const anahtar = (x) => tur === "sira" ? x.i : tur === "puan" ? x.o.puan.sayi() : tur === "soru" ? x.o.sorular[k].durum : tur === "uyari" ? x.o.uyarilar.length : tur === "dogru" || tur === "yanlis" || tur === "bos" ? x.o[tur] : String(x.o[tur] ?? "");
    satirlar.sort((p, q) => { const a = anahtar(p), b = anahtar(q); const r = a < b ? -1 : a > b ? 1 : 0; return K.sira.artan ? r : -r; });
    const ondalik = s.ayarlar.ondalik;
    const govde = satirlar.map(({ o, i }) => {
      const uy = o.uyarilar.length ? " uy" : "";
      return `<tr data-o="${i}">${c.map(([t, , kk]) => {
        if (t === "sira") return `<td class="${uy}">${i + 1}</td>`;
        if (t === "no") return `<td class="tik${uy}" data-alan="no" title="Dosya satırı ${o.kayit.satir_no}. Düzeltmek için tıklayın.">${e(o.no)}</td>`;
        if (t === "ad") return `<td class="sol tik${uy}" data-alan="ad" title="${o.okunan_ad !== o.ad ? "Optik dosyada okunan: " + e(o.okunan_ad) : ""}">${e(o.ad)}</td>`;
        if (t === "soru") { const q = o.sorular[kk]; return `<td class="${q.bonus_ile ? "K" : q.durum} tik" data-alan="soru" data-k="${kk}" title="${kk + 1}. soru: ${q.bonus_ile ? "bonus soru sayesinde doğru sayıldı" : OS.DURUM_ADI[q.durum]}, puan ${OS.sayiYaz(q.puan, 2)}">${e(String(q.isaret).trim())}</td>`; }
        if (t === "puan") return `<td class="kalin">${OS.sayiYaz(o.puan, ondalik)}</td>`;
        if (t === "kitapcik") return `<td class="tik" data-alan="kitapcik">${e(o.kitapcik)}</td>`;
        if (t === "uyari") return `<td class="sol uzun${uy}">${e(o.uyarilar.map((u) => u.mesaj).join("; "))}</td>`;
        return `<td>${o[t]}</td>`;
      }).join("")}</tr>`;
    }).join("");
    return `<div class="tablo-kap"><table class="veri" id="sonucTablo"><thead><tr>${c.map(([t, b], j) => `<th data-j="${j}" class="${t === "ad" || t === "uyari" ? "sol" : ""}">${e(b)}${K.sira.sutun === j ? (K.sira.artan ? " ▲" : " ▼") : ""}</th>`).join("")}</tr></thead><tbody>${govde}</tbody></table></div>`;
  }
  function basitTablo(basliklar, satirlar, sinif = "") {
    return `<div class="tablo-kap"><table class="veri ${sinif}"><thead><tr>${basliklar.map((b) => `<th class="sol">${e(b)}</th>`).join("")}</tr></thead><tbody>${satirlar.map((s, i) => `<tr data-i="${i}">${s.map((x) => `<td class="sol">${x}</td>`).join("")}</tr>`).join("") || `<tr><td class="sol soluk" colspan="${basliklar.length}">Yok</td></tr>`}</tbody></table></div>`;
  }
  function klasikTablo() {
    const L = D.liste ? D.liste.ogrenciler : [];
    const a = D.proje.anahtar, n = a.sorular.length;
    let tam = [];
    try { tam = OS.soruPuanlari(a, D.proje.ayarlar); } catch (_) { tam = []; }
    const satir = (og, i) => {
      const d = D.proje.klasik_puanlar[og.no] || [];
      const kt = (D.proje.klasik_toplamlar || {})[og.no];
      const gm = girmediMi(og.no);
      return `<tr data-no="${e(og.no)}" class="${gm ? "girmedi" : ""}"><td>${i + 1}</td><td>${e(og.no)}</td><td class="sol">${e(og.ad)}</td>${Array.from({ length: n }, (_, k) => `<td class="${hucreSinifi(d[k], tam[k])}"><input class="hucre" data-k="${k}" value="${e(d[k] ?? "")}" inputmode="decimal"></td>`).join("")}<td class="kalin toplam">${klasikToplam(d)}</td><td class="${toplamSinifi(d, kt)}"><input class="hucre kagit" value="${e(kt ?? "")}" inputmode="decimal" title="Kâğıdın üstüne yazdığınız toplam (isteğe bağlı, kontrol için)"></td><td><input type="checkbox" class="girmediKutu" ${gm ? "checked" : ""} title="İşaretlerseniz öğrenci sınava girmemiş sayılır; girilmiş puanları silinmez, hesaba katılmaz."></td></tr>`;
    };
    return `<div class="tablo-kap"><table class="veri" id="klasikTablo"><thead><tr><th>Sıra</th><th>Öğrenci No</th><th class="sol">Ad Soyad</th>${Array.from({ length: n }, (_, k) => `<th>S${k + 1}${tam[k] ? ` (${OS.klasikYaz(tam[k])})` : ""}</th>`).join("")}<th>Toplam</th><th title="Kâğıdın üstündeki toplam; tutmazsa kırmızı">Kâğıttaki toplam</th><th title="Sınava girmeyen öğrenciyi işaretleyin">Girmedi</th></tr></thead><tbody>${L.map(satir).join("")}</tbody></table></div>`;
  }
  const girmediMi = (no) => (D.proje.klasik_girmedi || []).includes(no);
  function girmediIsaretle(no, isaret) {
    const g = (D.proje.klasik_girmedi = D.proje.klasik_girmedi || []);
    const i = g.indexOf(no);
    if (isaret && i < 0) g.push(no);
    else if (!isaret && i >= 0) g.splice(i, 1);
  }
  function ilerlemeMetni() {
    const L = D.liste ? D.liste.ogrenciler : [];
    const gm = L.filter((o) => girmediMi(o.no)).length;
    const gi = L.filter((o) => !girmediMi(o.no) && (D.proje.klasik_puanlar[o.no] || []).some((x) => x !== null && x !== "")).length;
    return `Girilen: ${gi} · Girmedi: ${gm} · Kalan: ${L.length - gi - gm}`;
  }
  function toplamSinifi(d, kt) {
    if (kt === null || kt === undefined || kt === "") return "";
    let k2, t = OS.Kesir.SIFIR;
    try { k2 = OS.puanCoz(kt); for (const x of d || []) { const p = OS.puanCoz(x); if (p !== null) t = t.ekle(p); } } catch (_) { return "Y"; }
    return k2 !== null && k2.esit(t) ? "D" : "Y";
  }
  function kagitPaneli() {
    const a = D.proje.anahtar, n = a.sorular.length;
    let tam = [];
    try { tam = OS.soruPuanlari(a, D.proje.ayarlar); } catch (_) { tam = []; }
    const L = D.liste ? D.liste.ogrenciler : [];
    return `<div class="kutu" id="kagitPaneli"><h3>Kâğıt sırasıyla giriş</h3>
      <div class="satir"><label>Öğrenci</label><input type="text" id="kagitAra" placeholder="Numaranın ya da adın birkaç harfi, sonra Enter" style="width:300px" autocomplete="off">
        <span id="kagitKim" class="kalin"></span><span id="kagitKalan" class="soluk">${ilerlemeMetni()}</span></div>
      <div id="kagitOneri" class="satir" style="min-height:8px"></div>
      <div class="satir" id="kagitKutular">${Array.from({ length: n }, (_, k) => `<label>S${k + 1}${tam[k] ? ` (${OS.klasikYaz(tam[k])})` : ""}</label><input type="text" class="kagitPuan" data-k="${k}" style="width:62px" inputmode="decimal" disabled>`).join("")}
        <label>Kâğıttaki toplam</label><input type="text" id="kagitToplam" style="width:70px" inputmode="decimal" disabled title="İsteğe bağlı: kâğıdın üstüne yazdığınız toplam; tutmazsa uyarılır">
        <button id="kagitKaydet" class="ana" disabled>Kaydet, sonraki kâğıt</button>
        <button id="kagitGirmedi" disabled title="Seçili öğrenciyi sınava girmedi diye işaretler ve sonraki kâğıda geçer">Sınava girmedi</button></div>
      <p class="soluk" style="margin:4px 0 0">Kâğıtlar elinizdeki sırayla gelsin: öğrenciyi bulun, puanları yazın (Enter bir sonraki kutuya geçer), son kutuda Enter kaydeder ve yeni kâğıda hazırlar.</p></div>`;
  }
  function hucreSinifi(x, tam) {
    if (x === null || x === undefined || x === "") return "";
    let p;
    try { p = OS.puanCoz(x); } catch (_) { return "Y"; }
    if (p === null) return "";
    if (p.kars(0) < 0 || (tam && p.kars(tam) > 0)) return "uy";
    if (tam && p.kars(tam) >= 0) return "D";
    return p.sifirMi() ? "Y" : "K";
  }
  function klasikToplam(d) {
    let t = OS.Kesir.SIFIR, var_ = false;
    for (const x of d || []) { let p; try { p = OS.puanCoz(x); } catch (_) { return "hata"; } if (p !== null) { t = t.ekle(p); var_ = true; } }
    return var_ ? OS.sayiYaz(t, 2) : '<span class="soluk" title="henüz girilmedi">—</span>';
  }
  function klasikYaz(no, k, deger) {
    const p = D.proje.klasik_puanlar;
    const s = (p[no] = p[no] || []);
    while (s.length <= k) s.push(null);
    s[k] = String(deger ?? "").trim() || null;
    if (s.every((x) => x === null)) delete p[no];
    else {
      // okuma sırası etkisi için: öğrencinin ilk puanının girildiği sıra
      const g = (D.proje.klasik_giris_sirasi = D.proje.klasik_giris_sirasi || []);
      if (!g.includes(no)) g.push(no);
    }
  }
  const adim4 = {
    girildi() { UI.degerlendir(); if (D.proje.bicim === "klasik" && !Object.keys(D.proje.klasik_puanlar).length) K.sekme = "giris"; },
    eksikler() {
      if (D.proje.bicim === "klasik" && D.sonuc && !D.sonuc.ogrenciler.length) return ["Henüz hiçbir öğrenciye puan girilmedi."];
      return D.sonuc ? [] : ["Önce değerlendirme yapılmalı."];
    },
    ciz(k) {
      const s = D.sonuc || UI.degerlendir();
      const kl = D.proje.bicim === "klasik";
      if (!K.sekme || (K.sekme === "giris" && !kl)) K.sekme = kl ? "giris" : "sonuc";
      // Klasik sınavda puan girişi, sonuç hesaplanamasa da (ör. soru puanları 100 etmiyor) açık kalır.
      const baslik = `<h2>3. ${UI.adimAdi(2)}</h2>`;
      if (!s && !(kl && D.liste)) { k.innerHTML = `${baslik}<p>Değerlendirilecek okuma yok.</p>`; return; }
      if (!s) K.sekme = "giris";
      const sek = !s ? [["giris", "Puan girişi"]] : [...(kl ? [["giris", "Puan girişi"]] : []), ["sonuc", "Sonuçlar"], ["girmeyen", `Sınava girmeyenler (${s.girmeyenler.length})`],
        ...(kl ? [] : [["olmayan", `Listede olmayanlar (${s.listede_olmayanlar.length})`], ["duzeltme", `Düzeltme kaydı (${D.proje.duzeltmeler.length})`]])];
      let icerik = "";
      if (K.sekme === "giris") icerik = `${kagitPaneli()}<div class="satir"><button id="exceldenAl">Excel'den puan al…</button><button id="sablonIndir" title="Aşağıdaki tabloyu (girilen puanlar, toplam ve Girmedi işaretiyle) Excel'e yazar; Excel'de doldurup geri de yükleyebilirsiniz">Puan tablosunu Excel'e kaydet</button>
          <span class="soluk">Ya da tabloda hücreye tıklayıp yazın (Enter alttaki öğrenciye geçer; soru soru puanlamaya uygun). Excel'den bir bloğu kopyalayıp bir hücreye yapıştırabilirsiniz. Sınava girmeyenleri en sağdaki "Girmedi" kutusuyla işaretleyin (hiç puanı girilmeyen öğrenci de girmemiş sayılır).</span></div>${klasikTablo()}`;
      else if (K.sekme === "sonuc") icerik = `<div class="satir"><label><input type="checkbox" id="yalnizUyarili" ${K.yalnizUyarili ? "checked" : ""}> Yalnızca uyarılıları göster</label>
          <span class="efsane"><span style="background:var(--dogru)">doğru</span><span style="background:var(--yanlis)">yanlış</span><span style="background:var(--bos)">boş</span><span style="background:var(--iptal)">iptal</span>${kl ? '<span style="background:var(--kismi)">kısmi</span>' : D.proje.anahtar.sorular.some((x) => x.durum === "bonus") ? '<span style="background:var(--kismi)">bonusla doğru</span>' : ""}<span style="background:var(--uyari)">uyarılı</span></span>
          <span class="soluk">${kl ? "Puanı değiştirmek için Puan girişi sekmesini kullanın." : "Numara, ad, tek bir cevap ya da kitapçığı düzeltmek için hücreye tıklayın. Özgün okuma silinmez."} Sütun başlığına tıklayarak sıralayın.</span></div>${sonucTablosu(s)}`;
      else if (K.sekme === "girmeyen") icerik = basitTablo(["Öğrenci No", "Ad Soyad", "Listedeki satır"], s.girmeyenler.map((g) => [e(g.no), e(g.ad), g.kaynak_satir]));
      else if (K.sekme === "olmayan") icerik = `<p class="soluk">Birebir eşleşmeyen numaralar otomatik eşleştirilmez. Numarayı düzeltmek için satıra tıklayın.</p>` +
        basitTablo(["Dosya satırı", "Okunan numara", "Okunan ad", "Olası numaralar", "Puan"], s.listede_olmayanlar.map((o) => [o.kayit.satir_no, e(o.no), e(o.okunan_ad), e(o.oneriler.join(", ")), OS.sayiYaz(o.puan, s.ayarlar.ondalik)]), "olmayan");
      else icerik = basitTablo(["Dosya satırı", "Alan", "Eski değer", "Yeni değer", "Kim", "Ne zaman"], D.proje.duzeltmeler.map((d) => [d.satir_no, e(d.alan), e(d.eski), e(d.yeni), e(d.kim), e(d.zaman)]));
      // Düzeltilmesi gerekenler (optik): uyarılı satırlar okunur listede; tıklayınca tabloda o satır vurgulanır
      const uyarili = s && !kl ? s.ogrenciler.map((o, i) => [o, i]).filter(([o]) => o.uyarilar.length) : [];
      const duzeltilecek = !s || kl ? "" : uyarili.length
        ? `<div class="kutu duzeltilecek"><h3>Düzeltilmesi gerekenler (${uyarili.length})</h3><ul>${uyarili.map(([o, i]) => `<li><a href="#" data-git-o="${i}">Satır ${o.kayit.satir_no} · ${e(o.no)} ${e(o.ad)}</a>: ${e(o.uyarilar.map((u) => u.mesaj).join("; "))}</li>`).join("")}</ul>
          <p class="soluk">Satıra tıklayınca tabloda o öğrenci vurgulanır; hücresine tıklayarak düzeltin. Okunan dosyada sorun yoksa bu bölümü geçebilirsiniz.</p></div>`
        : `<p class="yesil"><b>✓ Düzeltilmesi gereken satır yok.</b></p>`;
      k.innerHTML = `${baslik}${duzeltilecek}
        <p id="kontrolOzet">${s ? kontrolOzeti(s) : "Puanları şimdiden girebilirsiniz; sonuç, üstteki eksikler tamamlanınca hesaplanır."}</p>
        <div class="sekmeler">${sek.map(([id, t]) => `<button data-sekme="${id}" class="${K.sekme === id ? "secili" : ""}">${t}</button>`).join("")}</div>${icerik}`;
      $$("[data-sekme]", k).forEach((b) => (b.onclick = () => { K.sekme = b.dataset.sekme; UI.ciz(); }));
      $$("[data-git-o]", k).forEach((a2) => (a2.onclick = (ev) => {
        ev.preventDefault();
        K.sekme = "sonuc"; K.yalnizUyarili = false; K.vurgu = Number(a2.dataset.gitO);
        UI.ciz();
        const tr = $(`#sonucTablo tr[data-o="${K.vurgu}"]`);
        if (tr) { tr.classList.add("vurgu"); tr.scrollIntoView({ block: "center" }); }
      }));
      if ($("#yalnizUyarili", k)) $("#yalnizUyarili", k).onchange = (ev) => { K.yalnizUyarili = ev.target.checked; UI.ciz(); };
      $$("#sonucTablo th", k).forEach((th) => (th.onclick = () => { const j = Number(th.dataset.j); K.sira = { sutun: j, artan: K.sira.sutun === j ? !K.sira.artan : true }; UI.ciz(); }));
      if (!kl) $$("#sonucTablo td.tik", k).forEach((td) => (td.onclick = () => duzeltmePenceresi(s.ogrenciler[Number(td.parentElement.dataset.o)], td.dataset.alan, Number(td.dataset.k))));
      if (K.sekme === "olmayan") $$("table.olmayan tr[data-i]", k).forEach((tr) => (tr.onclick = () => s.listede_olmayanlar[Number(tr.dataset.i)] && duzeltmePenceresi(s.listede_olmayanlar[Number(tr.dataset.i)], "no")));
      if (K.sekme === "giris") klasikOlaylari(k);
    },
  };
  function kontrolOzeti(s) {
    const kl = s.klasik;
    const uyarili = s.ogrenciler.filter((o) => o.uyarilar.length).length;
    const ort = s.ogrenciler.length ? OS.sayiYaz(OS.topla(s.ogrenciler.map((o) => o.puan)).bol(s.ogrenciler.length), 2) : "-";
    const kits = [...new Set(s.ogrenciler.map((o) => o.kitapcik).filter((x) => x))].sort();
    return `<b>${s.ogrenciler.length}</b> öğrenci ${kl ? "puanlandı" : "okundu"}, ortalama ${ort}. Uyarılı satır: <b>${uyarili}</b>.${s.liste_var ? ` Sınava girmeyen: <b>${s.girmeyenler.length}</b>.${kl ? "" : ` Listede olmayan numara: <b>${s.listede_olmayanlar.length}</b>.`}` : ""}${kits.length > 1 ? " Kitapçık: " + kits.map((x) => `${x} ${s.ogrenciler.filter((o) => o.kitapcik === x).length}`).join(", ") + "." : ""}`;
  }
  function klasikOzetGuncelle() {
    const s = UI.degerlendir();
    UI.otomatikKaydet();  // sonuç hesaplanamasa da (ör. soru puanı eksik) girilen puan kaybolmasın
    if (!s) return;
    const p = $("#kontrolOzet");
    if (p) p.innerHTML = kontrolOzeti(s);
    const b = $('[data-sekme="girmeyen"]');
    if (b) b.textContent = `Sınava girmeyenler (${s.girmeyenler.length})`;
    UI.altGuncelle();
    UI.otomatikKaydet();
  }
  function kagitOlaylari(k, satirGuncelle) {
    const ara = $("#kagitAra", k);
    if (!ara) return;
    const L = D.liste ? D.liste.ogrenciler : [];
    const kutular = $$(".kagitPuan", k), toplam = $("#kagitToplam", k), kaydet = $("#kagitKaydet", k), girmediB = $("#kagitGirmedi", k);
    let secili = null;
    const sadeAd = (x) => String(x || "").toLocaleLowerCase("tr").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/ı/g, "i");
    const bul = (m) => {
      const t = m.trim();
      if (!t) return [];
      const ts = sadeAd(t);
      return L.filter((o) => o.no.includes(t) || sadeAd(o.ad).includes(ts));
    };
    const sec = (o) => {
      secili = o;
      const d = D.proje.klasik_puanlar[o.no] || [];
      $("#kagitKim", k).textContent = `${o.no} ${o.ad}${girmediMi(o.no) ? " (sınava girmedi işaretli; puan kaydederseniz işaret kalkar)" : d.some((x) => x !== null && x !== "") ? " (daha önce girilmiş; üzerine yazılır)" : ""}`;
      $("#kagitOneri", k).innerHTML = "";
      kutular.forEach((b) => { b.disabled = false; b.value = d[Number(b.dataset.k)] ?? ""; });
      toplam.disabled = false;
      toplam.value = (D.proje.klasik_toplamlar || {})[o.no] ?? "";
      kaydet.disabled = false;
      girmediB.disabled = false;
      kutular[0].focus();
      kutular[0].select();
    };
    const temizle = () => {
      secili = null;
      ara.value = "";
      $("#kagitKim", k).textContent = "";
      kutular.forEach((b) => { b.value = ""; b.disabled = true; });
      toplam.value = ""; toplam.disabled = true; kaydet.disabled = true; girmediB.disabled = true;
      ara.focus();
    };
    const oneriGoster = () => {
      const r = bul(ara.value);
      $("#kagitOneri", k).innerHTML = r.slice(0, 8).map((o, i) => `<button class="kucuk" data-i="${i}">${e(o.no)} ${e(o.ad)}</button>`).join("") + (r.length > 8 ? `<span class="soluk">+${r.length - 8} öğrenci daha; biraz daha yazın</span>` : "") + (ara.value.trim() && !r.length ? '<span class="kirmizi">Listede bulunamadı</span>' : "");
      $$("#kagitOneri button", k).forEach((b) => (b.onclick = () => sec(r[Number(b.dataset.i)])));
      return r;
    };
    ara.oninput = oneriGoster;
    ara.onkeydown = (ev) => { if (ev.key === "Enter") { ev.preventDefault(); const r = oneriGoster(); if (r.length >= 1) sec(r[0]); } };
    const kaydetVeSonraki = () => {
      if (!secili) return;
      kutular.forEach((b) => klasikYaz(secili.no, Number(b.dataset.k), b.value));
      if (kutular.some((b) => b.value.trim())) girmediIsaretle(secili.no, false);
      const t = (D.proje.klasik_toplamlar = D.proje.klasik_toplamlar || {});
      if (toplam.value.trim()) t[secili.no] = toplam.value.trim(); else delete t[secili.no];
      const tr = $(`#klasikTablo tr[data-no="${CSS.escape(secili.no)}"]`, k);
      if (tr) {
        const d = D.proje.klasik_puanlar[secili.no] || [];
        $$("input.hucre:not(.kagit)", tr).forEach((i) => (i.value = d[Number(i.dataset.k)] ?? ""));
        const kg = $("input.kagit", tr);
        if (kg) kg.value = t[secili.no] ?? "";
        const gk = $("input.girmediKutu", tr);
        if (gk) gk.checked = girmediMi(secili.no);
        satirGuncelle(tr);
      }
      klasikOzetGuncelle();
      const s = D.sonuc;
      const o = s && s.ogrenciler.find((x) => x.no === secili.no);
      const uy = o ? o.uyarilar.filter((u) => /toplam|büyük|eksi|sayı/.test(u.mesaj)).map((u) => u.mesaj) : [];
      bildir(uy.length ? `${secili.ad}: kaydedildi, ama dikkat: ${uy.join("; ")}` : `${secili.ad}: kaydedildi (${o ? OS.sayiYaz(o.puan, 2) : "-"} puan).`, uy.length ? 7000 : 2500);
      $("#kagitKalan", k).textContent = ilerlemeMetni();
      temizle();
    };
    girmediB.onclick = () => {
      if (!secili) return;
      girmediIsaretle(secili.no, true);
      const tr = $(`#klasikTablo tr[data-no="${CSS.escape(secili.no)}"]`, k);
      if (tr) { const gk = $("input.girmediKutu", tr); if (gk) gk.checked = true; satirGuncelle(tr); }
      klasikOzetGuncelle();
      bildir(`${secili.ad}: sınava girmedi olarak işaretlendi.`, 2500);
      $("#kagitKalan", k).textContent = ilerlemeMetni();
      temizle();
    };
    kutular.forEach((b, j) => (b.onkeydown = (ev) => { if (ev.key === "Enter") { ev.preventDefault(); (kutular[j + 1] || toplam).focus(); (kutular[j + 1] || toplam).select(); } }));
    toplam.onkeydown = (ev) => { if (ev.key === "Enter") { ev.preventDefault(); kaydetVeSonraki(); } };
    kaydet.onclick = kaydetVeSonraki;
    setTimeout(() => ara.focus(), 0);
  }
  async function duzeltmePenceresi(o, alan, k) {
    let r = null;
    if (alan === "no") {
      r = await pencere("Numara düzelt", `<p>Dosya satırı ${o.kayit.satir_no}, okunan: <b>${e(o.kayit.ogrenci_no)}</b></p>
        ${o.oneriler.length ? `<p>Olası numaralar: ${o.oneriler.map((x) => `<button class="kucuk oneri">${e(x)}</button>`).join(" ")}</p>` : ""}
        <input type="text" id="yeniNo" value="${e(o.oneriler[0] || o.no)}" style="width:200px">`,
        [{ metin: "Vazgeç", deger: null }, { metin: "Kaydet", ana: true, deger: (p) => $("#yeniNo", p).value.trim(), denetle: (p) => { const x = $("#yeniNo", p).value.trim(); if (!/^\d+$/.test(x)) { bildir("Numara yalnızca rakamlardan oluşmalı."); return false; } return true; } }],
        (p) => $$(".oneri", p).forEach((b) => (b.onclick = () => ($("#yeniNo", p).value = b.textContent))));
      if (r) UI.duzelt(o.kayit.satir_no, "no", r);
    } else if (alan === "ad") {
      r = await pencere("Ad düzelt", `<p>Okunan: <b>${e(o.okunan_ad)}</b></p><input type="text" id="yeniAd" value="${e(o.okunan_ad)}" style="width:320px">`,
        [{ metin: "Vazgeç", deger: null }, { metin: "Kaydet", ana: true, deger: (p) => $("#yeniAd", p).value }]);
      if (r !== null) UI.duzelt(o.kayit.satir_no, "ad", r);
    } else if (alan === "soru") {
      const mevcut = o.cevaplar[k];
      const kendi = o.kaynak_soru ? o.kaynak_soru[k] : k + 1;
      const sec = [...OS.SIKLAR, "Boş", "Çift işaret (*)"];
      const deger = OS.SIKLAR.includes(mevcut) && mevcut ? mevcut : mevcut === "*" ? "Çift işaret (*)" : "Boş";
      r = await pencere("Cevap düzelt", `<p>${e(o.no)} ${e(o.ad)}<br>${k + 1}. soru${kendi !== k + 1 ? ` (${e(o.kitapcik)} kitapçığında ${kendi}. soru)` : ""}, okunan: <b>${e(String(mevcut).trim() || "boş")}</b></p>
        <div class="satir">${sec.map((x) => `<label><input type="radio" name="cvp" value="${e(x)}" ${x === deger ? "checked" : ""}> ${e(x)}</label>`).join("")}</div>`,
        [{ metin: "Vazgeç", deger: null }, { metin: "Kaydet", ana: true, deger: (p) => $("input[name=cvp]:checked", p).value }]);
      if (r) UI.duzelt(o.kayit.satir_no, `cevap:${kendi}`, OS.SIKLAR.includes(r) ? r : r === "Boş" ? " " : "*");
    } else if (alan === "kitapcik") {
      const sec = OS.kitapciklar(D.proje.anahtar);
      r = await pencere("Kitapçık", `<p>${e(o.no)} ${e(o.ad)}<br>Okunan kitapçık: <b>${e(o.kayit.kitapcik || "yok")}</b></p><select id="kit">${sec.map((x) => `<option ${x === o.kitapcik ? "selected" : ""}>${e(x)}</option>`).join("")}</select>`,
        [{ metin: "Vazgeç", deger: null }, { metin: "Kaydet", ana: true, deger: (p) => $("#kit", p).value }]);
      if (r) UI.duzelt(o.kayit.satir_no, "kitapcik", r);
    }
    if (r !== null && r !== undefined) { const y = $("#icerik").scrollTop; UI.ciz(); $("#icerik").scrollTop = y; }
  }
  function klasikOlaylari(k) {
    const tablo = $("#klasikTablo", k);
    const tam = (() => { try { return OS.soruPuanlari(D.proje.anahtar, D.proje.ayarlar); } catch (_) { return []; } })();
    const satirGuncelle = (tr) => {
      const no = tr.dataset.no;
      const d = D.proje.klasik_puanlar[no] || [];
      $$("input.hucre", tr).forEach((i) => (i.parentElement.className = hucreSinifi(d[Number(i.dataset.k)], tam[Number(i.dataset.k)])));
      $(".toplam", tr).innerHTML = girmediMi(no) ? '<span class="soluk">sınava girmedi</span>' : klasikToplam(d);
      const kg = $("input.kagit", tr);
      if (kg) kg.parentElement.className = toplamSinifi(d, (D.proje.klasik_toplamlar || {})[no]);
      tr.classList.toggle("girmedi", girmediMi(no));
    };
    const yaz = (i) => { const tr = i.closest("tr"); klasikYaz(tr.dataset.no, Number(i.dataset.k), i.value); satirGuncelle(tr); klasikOzetGuncelle(); };
    $$("input.kagit", tablo).forEach((i) => {
      i.onchange = () => { const tr = i.closest("tr"); const t = (D.proje.klasik_toplamlar = D.proje.klasik_toplamlar || {}); const x = i.value.trim(); if (x) t[tr.dataset.no] = x; else delete t[tr.dataset.no]; satirGuncelle(tr); klasikOzetGuncelle(); };
    });
    $$("input.girmediKutu", tablo).forEach((c) => {
      c.onchange = () => { const tr = c.closest("tr"); girmediIsaretle(tr.dataset.no, c.checked); satirGuncelle(tr); klasikOzetGuncelle(); if ($("#kagitKalan", k)) $("#kagitKalan", k).textContent = ilerlemeMetni(); };
    });
    $$("#klasikTablo tr[data-no]", k).forEach((tr) => { if (girmediMi(tr.dataset.no)) $(".toplam", tr).innerHTML = '<span class="soluk">sınava girmedi</span>'; });
    kagitOlaylari(k, satirGuncelle);
    $$("input.hucre:not(.kagit)", tablo).forEach((i) => {
      i.onchange = () => yaz(i);
      i.onkeydown = (ev) => {
        const tr = i.closest("tr"), kk = Number(i.dataset.k);
        let hedef = null;
        if (ev.key === "Enter" || ev.key === "ArrowDown") hedef = tr.nextElementSibling && $(`input[data-k="${kk}"]`, tr.nextElementSibling);
        else if (ev.key === "ArrowUp") hedef = tr.previousElementSibling && $(`input[data-k="${kk}"]`, tr.previousElementSibling);
        if (hedef) { ev.preventDefault(); if (i.value !== (D.proje.klasik_puanlar[tr.dataset.no] || [])[kk]) yaz(i); hedef.focus(); hedef.select(); }
      };
      i.onfocus = () => i.select();
      i.onpaste = (ev) => {
        const m = (ev.clipboardData || window.clipboardData).getData("text");
        if (!/[\t\n]/.test(m.trim())) return;
        ev.preventDefault();
        const bas = i.closest("tr"), k0 = Number(i.dataset.k);
        let tr = bas, sayac = 0;
        for (const satir of m.replace(/\r/g, "").replace(/\n$/, "").split("\n")) {
          if (!tr) break;
          satir.split("\t").forEach((x, j) => { const h = $(`input[data-k="${k0 + j}"]`, tr); if (h) { h.value = x.trim(); klasikYaz(tr.dataset.no, k0 + j, x); sayac++; } });
          satirGuncelle(tr);
          tr = tr.nextElementSibling;
        }
        klasikOzetGuncelle();
        bildir(`${sayac} hücre yapıştırıldı.`);
      };
    });
    $("#exceldenAl", k).onclick = async () => {
      const f = await dosyaSec(".xlsx,.xls,.csv");
      if (!f) return;
      try {
        const sayfalar = OS.sayfalariOku(window.XLSX, await baytOku(f), f.name);
        const tablo = sayfalar[OS.sayfaSec(sayfalar)];
        const [p, notlar] = OS.tablodanKlasikPuanlar(tablo, D.proje.anahtar.sorular.length);
        const girmeyen = OS.tablodanGirmedi(tablo);
        const listede = new Set(D.liste.ogrenciler.map((o) => o.no));
        const yabanci = Object.keys(p).filter((x) => !listede.has(x));
        const g = (D.proje.klasik_giris_sirasi = D.proje.klasik_giris_sirasi || []);
        for (const [no, d] of Object.entries(p)) if (listede.has(no) && d.some((x) => x !== null)) { D.proje.klasik_puanlar[no] = d; if (!g.includes(no)) g.push(no); }
        const gIsaret = girmeyen.filter((x) => listede.has(x));
        gIsaret.forEach((x) => girmediIsaretle(x, true));
        UI.degerlendir();
        UI.ciz();
        bilgi("Excel'den puan", `${Object.keys(p).filter((x) => listede.has(x) && !gIsaret.includes(x)).length} öğrencinin puanı alındı.${gIsaret.length ? ` ${gIsaret.length} öğrenci sınava girmedi olarak işaretlendi.` : ""}${yabanci.length ? `\nListede olmayan numaralar alınmadı: ${yabanci.slice(0, 10).join(", ")}` : ""}${notlar.length ? "\n" + notlar.join("\n") : ""}`);
      } catch (h) { bilgi("Okunamadı", h.message || String(h)); }
    };
    $("#sablonIndir", k).onclick = async () => indir(await UI.excel.klasikSablon(D.liste.ogrenciler, D.proje.anahtar.sorular.length, D.proje.klasik_puanlar, D.proje.klasik_girmedi || [], (() => { try { return OS.soruPuanlari(D.proje.anahtar, D.proje.ayarlar); } catch (_) { return []; } })()), OS.ciktiAdi(D.proje.sinav, "puan_tablosu"));
  }

  // ------------------------------------------------------------------ grafikler (SVG)
  function histogramSvg(puanlar, ust, esik) {
    const adim = ust / 10 || 10;
    const say = Array.from({ length: 10 }, (_, k2) => puanlar.filter((p) => (p >= k2 * adim && p < (k2 + 1) * adim) || (k2 === 9 && p === ust)).length);
    const enCok = Math.max(1, ...say);
    const W = 420, H = 190, sol = 10, alt = 22, ustB = 18, g = (W - sol * 2) / 10;
    const cub = say.map((n, i) => {
      const y = (H - alt - ustB) * (n / enCok);
      const x = sol + i * g;
      const renk = (i + 1) * adim > esik ? "var(--vurgu)" : "var(--hata)";
      return `<rect x="${x + 3}" y="${H - alt - y}" width="${g - 6}" height="${y}" fill="${renk}" rx="2"><title>${OS.pyOndalik(i * adim, 0)}-${OS.pyOndalik((i + 1) * adim, 0)}: ${n} öğrenci</title></rect>
        ${n ? `<text x="${x + g / 2}" y="${H - alt - y - 4}" text-anchor="middle">${n}</text>` : ""}<text x="${x + 2}" y="${H - 6}">${OS.pyOndalik(i * adim, 0)}</text>`;
    }).join("");
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Puan dağılımı"><line x1="${sol}" y1="${H - alt}" x2="${W - sol}" y2="${H - alt}" stroke="var(--cizgi)"/>${cub}</svg>`;
  }
  function egriSvg(egri, enIyi) {
    const W = 420, H = 160, sol = 30, alt = 22, ust = 10;
    const enCok = Math.max(...egri.map((x) => x[1]));
    const px = (t) => sol + ((t + 4) / 8) * (W - sol - 10), py = (y) => H - alt - (y / enCok) * (H - alt - ust);
    const yol = egri.map(([t, y], i) => `${i ? "L" : "M"}${px(t).toFixed(1)},${py(y).toFixed(1)}`).join(" ");
    const etiket = [-4, -2, 0, 2, 4].map((t) => `<text x="${px(t)}" y="${H - 6}" text-anchor="middle">${t}</text>`).join("");
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Sınav bilgi eğrisi"><line x1="${sol}" y1="${H - alt}" x2="${W - 10}" y2="${H - alt}" stroke="var(--cizgi)"/>
      <path d="${yol}" fill="none" stroke="var(--vurgu)" stroke-width="2"/><line x1="${px(enIyi)}" y1="${ust}" x2="${px(enIyi)}" y2="${H - alt}" stroke="var(--hata)" stroke-dasharray="3 3"/>${etiket}
      <text x="${sol}" y="${ust + 4}">bilgi</text><text x="${W - 10}" y="${H - alt - 4}" text-anchor="end">öğrenci yeteneği (logit)</text></svg>`;
  }

  // ------------------------------------------------------------------ 5. adım: istatistikler
  const I = { sekme: "madde" };
  function istatistikVerisi() {
    const s = D.sonuc || UI.degerlendir();
    if (!s || !s.ogrenciler.length) return null;
    const esik = s.ayarlar.basari_esigi;
    const [m, g] = OS.maddeAnalizi(s, { basari_esigi: esik, cikti_esigi: esik });
    return { s, m, g, esik };
  }
  function ekAnalizHtml(s, m, g, esik) {
    const a = s.ayarlar;
    const h = [];
    const t = OS.tasarimDenetimi(s, m.map((x) => x.guclik));
    const sans = OS.sansPuani(s);
    const anahtarHatasi = m.filter((x) => x.sorunlar.some((y) => y.startsWith("Olası anahtar hatası")));
    h.push("<h3>Sınav tasarımı</h3><ul class='yorum'>");
    for (const x of anahtarHatasi) h.push(`<li><b class="kirmizi">${x.soru_no}. soru — ${e(x.sorunlar.find((y) => y.startsWith("Olası")))}</b>. Anahtarı kontrol edin.</li>`);
    if (t) { h.push(`<li>Anahtarda şıklar: ${Object.entries(t.sik_sayilari).map(([x, y]) => `${x} ${y}`).join(", ")}</li>`); for (const n of t.notlar) h.push(`<li>${e(n)}</li>`); }
    if (sans !== null) h.push(`<li>Rastgele işaretleyen birinin beklenen puanı ${v(sans, 1)}. Bunun altında kalan öğrenci: ${s.ogrenciler.filter((o) => o.puan.sayi() < sans).length}.</li>`);
    h.push("</ul>");
    const kk = OS.kitapcikKarsilastirma(s);
    if (kk) h.push(`<h3>Kitapçıklar eşdeğer mi?</h3><p>${e(kk.kitapcik1)}: ${v(kk.ortalama1)} (${kk.n1} kişi), ${e(kk.kitapcik2)}: ${v(kk.ortalama2)} (${kk.n2} kişi). Fark ${v(kk.fark)}, p = ${v(kk.p, 3)}. ${kk.p < 0.05 ? "<b>Fark anlamlı: kitapçıklardan biri daha zor olmuş olabilir.</b>" : "Fark anlamlı değil."}</p>`);
    const sinir = OS.sinirdakiOgrenciler(s, esik, g.olcme_hatasi);
    h.push(`<h3>Sınırdaki öğrenciler</h3><p>Puanı ${esik} eşiğine ölçme hatası (±${v(g.olcme_hatasi || 5)}) kadar yakın <b>${sinir.length}</b> öğrenci var; özellikle eşiğin hemen altındakilerin kâğıdına bir daha bakmak adil olur.</p>`);
    const alt = sinir.filter((x) => x.fark < 0).slice(-12);
    if (alt.length) h.push(basitTablo(["Öğrenci No", "Ad Soyad", "Puan", "Eşiğe uzaklık"], alt.map((x) => [e(x.no), e(x.ad), sayi(x.puan), `<span class="kirmizi">${v(x.fark)}</span>`])));
    const ara = OS.araAgirligi(D.proje.sinav, D.ders);
    const f = OS.finalGereken(s, ara, a.gecme_ortalamasi, a.final_alt_siniri);
    if (f.length) {
      const zor = f.filter((x) => x.gereken === null || x.gereken > 80);
      h.push(`<h3>Finalde gereken puan</h3><p>Ara sınav %${ara}, final %${100 - ara}; geçme ortalaması ${a.gecme_ortalamasi}, final alt sınırı ${a.final_alt_siniri} (2. adımdaki "Puanlama ayarları" bölümünde değiştirilebilir). Finalden 80'in üstünde alması gereken ya da 100 alsa da yetişemeyecek öğrenci: <b>${zor.length}</b>.</p>`);
      h.push(`<details><summary>Bütün liste</summary>${basitTablo(["Öğrenci No", "Ad Soyad", "Ara sınav", "Finalde en az"], f.map((x) => [e(x.no), e(x.ad), sayi(x.puan), x.gereken === null ? '<b class="kirmizi">100 de yetmez</b>' : sayi(x.gereken)]))}</details>`);
    }
    const rs = OS.rasch(s);
    if (rs) {
      const sira = [...rs.soru_zorluklari].sort((p, q) => p[1] - q[1]);
      h.push(`<h3>Rasch modeli</h3><p>Sınav en iyi, yaklaşık %${OS.pyOndalik(rs.en_iyi_puan, 0)} başarı düzeyindeki öğrencileri ayırt ediyor (kırmızı çizgi). En kolay soru ${sira[0][0]}, en zor soru ${sira[sira.length - 1][0]}.</p>${egriSvg(rs.bilgi_egrisi, rs.en_iyi_olctugu)}
        <details><summary>Soruların zorluk ölçeği</summary>${basitTablo(["Soru", "Zorluk (logit)", "Standart hata"], sira.map(([q, b]) => [q, sayi(b), sayi(rs.soru_hatalari.get(q))]))}</details>`);
    }
    const arsiv = (yerel.al("os_arsiv", {}) || {})[D.proje.sinav.ders_kodu] || [];
    h.push("<h3>Önceki sınavlar</h3>");
    h.push(arsiv.length ? basitTablo(["Tarih", "Sınav", "Öğrenci", "Ortalama", "Başarılı"], arsiv.map((x) => [e(x.tarih), e(x.sinav_turu), x.ogrenci_sayisi, sayi(x.ortalama, 1), pct(x.basari_orani)]))
      : `<p class="soluk">Bu ders için bu tarayıcıda arşiv kaydı yok. 4. adımda "Diğer raporlar" ile istatistik her indirildiğinde sınavın özeti burada saklanır; sonraki dönemlerde karşılaştırma görünür.</p>`);
    return h.join("");
  }
  function kavramHtml(k) {
    if (!k.length) return `<p class="soluk">Sınıf geneline göre belirgin biçimde birlikte seçilen yanlış şık çifti bulunmadı.</p>`;
    return `<p class="soluk">İki farklı sorunun yanlış şıklarını birlikte seçen öğrenciler. Aynı yanlış düşünce iki soruda birden yanıltıyor olabilir; o iki sorunun ortak konusunu sınıfla yeniden ele almak yararlı olur. Yalnızca şansla açıklanamayacak (Fisher kesin testi, p ≤ 0,01) çiftler listelenir.</p>
      <ul class="yorum">${k.map((x) => `<li><b>${x.soru1}. sorunun ${x.sik1} şıkkını</b> seçen ${x.secen1} öğrencinin <b>${pct(x.kosullu)}</b>'i <b>${x.soru2}. sorunun ${x.sik2} şıkkını</b> da seçmiş (sınıfın tamamında bu oran ${pct(x.taban)}).</li>`).join("")}</ul>` +
      basitTablo(["Soru", "Yanlış şık", "Birlikte seçilen soru", "Yanlış şık", "Birlikte seçen", "Phi", "p değeri"], k.map((x) => [x.soru1, x.sik1, x.soru2, x.sik2, x.birlikte, sayi(x.phi), v(x.p, 4)]));
  }
  // 5. adım: sık bakılan üç sekme önde; öteki analizler "Diğer analizler" menüsünde (seçilen, önde sekme olarak görünür)
  const ANA_SEKMELER = ["madde", "cikti", "donem"];
  function sekmeCubugu(sek) {
    const ad = new Map(sek);
    const dugme = (id) => `<button data-ist="${id}" class="${I.sekme === id ? "secili" : ""}">${ad.get(id)}</button>`;
    const diger = sek.filter(([id]) => !ANA_SEKMELER.includes(id));
    const secili = diger.find(([id]) => id === I.sekme);
    return ANA_SEKMELER.filter((id) => ad.has(id)).map(dugme).join("") + (secili ? dugme(secili[0]) : "")
      + `<span class="bosluk"></span>` + UI.acilirMenu("Diğer analizler", diger.map(([id, t]) => `<button data-ist="${id}">${t}</button>`));
  }
  function belirleyenHtml(s) {
    const nb = OS.notuBelirleyenSorular(s);
    if (!nb) return `<p class="soluk">Bu analiz için en az 5 öğrenci, 2 soru ve öğrenciler arasında puan farkı gerekir.</p>`;
    const en = Math.max(...nb.sorular.map((k) => k.katki_payi), 0) || 1;
    const ad = { fazla_belirleyici: "notu puanından fazla belirliyor", az_etkili: "notu puanından az belirliyor" };
    return `<p><b>${e(nb.yorum)}</b></p>
      <p class="soluk">Öğrencilerin toplam puanları arasındaki farkların (varyansın) her sorudan gelen payı. Bir sorunun nota katkısı puan payıyla aynıysa oran 1'dir; 1,5 ve üstü soru notu puanından fazla belirliyor, 0,5 ve altı az belirliyor demektir. Paylar toplamı %100'dür. Bir soru öteki sorularla ters yönde gidiyorsa payı eksi çıkar; o zaman başka bir sorunun payı %100'ü aşabilir.</p>
      <div class="tablo-kap"><table class="veri"><thead><tr><th>Soru</th><th>Puan payı</th><th>Nota katkı payı</th><th class="sol"></th><th>Oran</th><th class="sol">Değerlendirme</th></tr></thead><tbody>
      ${nb.sorular.map((k) => `<tr><td>${k.soru_no}</td><td>${pct(k.puan_payi)}</td><td><b>${pct(k.katki_payi)}</b></td>
        <td class="sol"><div class="cubuk"><i style="width:${Math.max(0, Math.min(100, (100 * k.katki_payi) / en))}%;background:${k.durum === "fazla_belirleyici" ? "var(--hata)" : k.durum === "az_etkili" ? "var(--uyari)" : "var(--vurgu)"}"></i></div></td>
        <td>${k.oran === null ? "-" : v(k.oran, 2)}</td><td class="sol ${k.durum ? "uy" : ""}">${ad[k.durum] || ""}</td></tr>`).join("")}</tbody></table></div>`;
  }
  function puanlamaHtml(s) {
    const ok = OS.okumaSirasiEtkisi(s, D.proje.klasik_giris_sirasi || []);
    const kp = OS.kismiPuanProfili(s) || [];
    return `<h3>Okuma sırası etkisi</h3>${ok ? `<p><b>${e(ok.yorum)}</b></p>` : `<p class="soluk">En az 10 kâğıdın girildiği sıra gerekir. Sıra, 3. adımda bir öğrenciye ilk puan girildiğinde kendiliğinden kaydedilir (Excel'den alınan puanlarda dosyadaki sıra).</p>`}
      <h3>Kısmi puan profili</h3><p class="soluk">Her soruda tam puan, kısmi puan, sıfır ve boş sayısı. Çoğu öğrencinin kısmi puan aldığı soruda puanlama ölçütü belirsiz olabilir.</p>
      ${basitTablo(["Soru", "Tam", "Kısmi", "Sıfır", "Boş", "Ortalama başarı", "Not"], kp.map((k) => [k.soru_no, k.tam, k.kismi, k.sifir, k.bos, k.ortalama_oran === null ? "-" : pct(k.ortalama_oran), e(k.notlar.join("; "))]))}`;
  }
  function yapiHtml(s) {
    const y = OS.sinavYapisi(s);
    if (!y) return `<p class="soluk">Bu analiz için en az 10 öğrenci ve 3 analiz edilebilir soru gerekir.</p>`;
    const W = 420, H = 140, sol = 26, alt = 20;
    const enb = Math.max(...y.ozdegerler, 1);
    const g2 = (W - sol - 10) / y.ozdegerler.length;
    const cubuk = y.ozdegerler.map((d, i) => { const h = Math.max(0, (H - alt - 10) * (d / enb)); return `<rect x="${sol + i * g2 + 2}" y="${H - alt - h}" width="${g2 - 4}" height="${h}" fill="${i === 0 ? "var(--vurgu)" : "var(--soluk)"}"><title>${i + 1}. bileşen: ${v(d, 2)}</title></rect>`; }).join("");
    const svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:520px"><line x1="${sol}" y1="${H - alt}" x2="${W - 10}" y2="${H - alt}" stroke="var(--cizgi)"/><line x1="${sol}" y1="${H - alt - (H - alt - 10) / enb}" x2="${W - 10}" y2="${H - alt - (H - alt - 10) / enb}" stroke="var(--hata)" stroke-dasharray="3 3"/>${cubuk}<text x="${sol}" y="${H - 4}">bileşenler (büyükten küçüğe); kesikli çizgi: 1</text></svg>`;
    return `<div class="kutu"><b>${e(y.yorum)}</b><p class="soluk">Birinci bileşenin açıkladığı pay ${pct(y.ilk_pay)}, birinci / ikinci özdeğer ${y.oran_1_2 === null ? "-" : v(y.oran_1_2, 2)}, sorular arası ortalama korelasyon ${v(y.ortalama_korelasyon, 3)}.</p>${svg}</div>
      ${y.zayif_sorular.length ? `<p>Sınavın geri kalanından farklı bir şey ölçen sorular (ortak bileşene yükü 0,20'nin altında): <b>${y.zayif_sorular.join(", ")}</b>. Bu sorular ya ayrı bir konuyu ölçüyor ya da öğrencileri ayırmıyor; madde analiziyle birlikte bakın.</p>` : ""}
      ${y.cikti_uyumu.length ? `<h3>Öğrenme çıktısı eşlemesi verilerle uyumlu mu?</h3><p class="soluk">Aynı çıktıya bağlı soruların kendi aralarındaki ilişkisi ötekilerle ilişkisinden yüksekse eşleme verilerle uyumludur.</p>` +
        basitTablo(["Çıktı", "Soru sayısı", "Kendi soruları arasında", "Öteki sorularla", "Değerlendirme"], y.cikti_uyumu.map(([kod, ic, dis, n]) => [e(kod), n, v(ic, 3), v(dis, 3), ic > dis + 0.05 ? '<span class="yesil">uyumlu</span>' : '<span class="soluk">ayrışmıyor</span>'])) : ""}
      <details><summary>Soruların ortak bileşene yükleri</summary>${basitTablo(["Soru", "Yük"], y.sorular.map((no) => [no, sayi(y.yukler.get(no))]))}</details>`;
  }
  function donemHtml(s) {
    const p = D.proje, a = p.ayarlar;
    const h = OS.harfAyarlari(p.harf_ayarlari);
    const ara = OS.araAgirligi(p.sinav, D.ders);
    const fin = p.final_puanlar || {};
    const girilen = s.ogrenciler.filter((o) => fin[o.no] !== undefined && fin[o.no] !== null && fin[o.no] !== "").length;
    let sonucHtml = "";
    if (girilen) {
      try {
        const d = OS.donemSonu(s, fin, ara, a.final_alt_siniri, a.gecme_ortalamasi, h);
        const toplam = Object.values(d.dagilim).reduce((x, y) => x + y, 0) || 1;
        sonucHtml = `<div class="kutu"><b>Uygulanan: ${d.uygulanan === "bagil" ? "bağıl (T-puanı)" : "mutlak"} değerlendirme.</b>
          ${d.uygulanan === "bagil" ? ` Bağıl grup ${d.bagil_grup} öğrenci, ham not ortalaması ${v(d.ortalama, 2)}, standart sapma ${v(d.standart_sapma, 2)}.` : ""} ${d.notlar_metin.map(e).join(" ")}
          <div class="satir" style="align-items:flex-end;gap:6px;margin-top:10px">${Object.entries(d.dagilim).map(([hr, n]) => `<div style="text-align:center"><div style="height:${8 + 90 * (n / toplam)}px;width:34px;background:${["FF", "FD"].includes(hr) ? "var(--hata)" : "var(--vurgu)"};border-radius:3px"></div><b>${hr}</b><br>${n}</div>`).join("")}</div>
          <p>Geçen: <b>${d.notlar.filter((n) => n.gecti).length}</b>, kalan: <b>${d.notlar.filter((n) => n.gecti === false).length}</b>, finali girilmeyen: <b>${d.notlar.filter((n) => n.gecti === null).length}</b>. Bir üst harfe 1 puandan az kalan: <b>${d.notlar.filter((n) => n.sinirda).length}</b>.</p></div>`;
        var tablo = d.notlar;
        var uyg = d.uygulanan;
      } catch (hata) { sonucHtml = `<p class="kirmizi">${e(hata.message)}</p>`; }
    }
    const notMap = new Map((typeof tablo !== "undefined" ? tablo : []).map((n) => [n.no, n]));
    const satirlar = s.ogrenciler.map((o) => {
      const n = notMap.get(o.no);
      return `<tr data-no="${e(o.no)}"><td>${e(o.no)}</td><td class="sol">${e(o.ad)}</td><td>${OS.sayiYaz(o.puan, 2)}</td><td><input class="hucre final" value="${e(fin[o.no] ?? "")}" inputmode="decimal"></td>
        <td>${n && n.ham !== null ? v(n.ham, 2) : ""}</td>${uyg === "bagil" ? `<td>${n && n.t !== null ? v(n.t, 1) : ""}</td>` : ""}<td class="kalin">${n ? e(n.harf) : ""}</td>
        <td class="${n && n.gecti === true ? "D" : n && n.gecti === false ? "Y" : ""}">${n && n.gecti !== null ? (n.gecti ? "Geçti" : "Kaldı") : ""}</td><td class="sol">${n ? e(n.aciklama) : ""}</td><td class="${n && n.sinirda ? "uy" : ""}">${n ? e(n.sinirda) : ""}</td></tr>`;
    }).join("");
    return `<p class="soluk">Final puanlarını girin ya da Excel'den alın; ara sınav bu sınavdan gelir. Ağırlıklar: ara sınav %${ara}, final %${100 - ara} (1. adımdaki etki oranı). Final alt sınırı ${a.final_alt_siniri}, geçme ortalaması ${a.gecme_ortalamasi} (2. adımdaki "Puanlama ayarları" bölümünde değiştirilir). <b>Harf tabloları örnektir; üniversitenizin yönetmeliğiyle karşılaştırın.</b></p>
      <div class="kutu"><div class="satir"><label>Değerlendirme</label><label><input type="radio" name="hy" value="mutlak" ${h.yontem !== "bagil" ? "checked" : ""}> Mutlak</label><label><input type="radio" name="hy" value="bagil" ${h.yontem === "bagil" ? "checked" : ""}> Bağıl (T-puanı)</label>
        <label>Bağıl için en az öğrenci</label><input type="number" id="bagilEnAz" min="2" style="width:70px" value="${h.bagil_en_az}"></div>
        <div class="satir"><label>Mutlak tablo (ham not)</label><input type="text" id="tabloMutlak" style="flex:1" value="${e(h.mutlak)}"></div>
        <div class="satir"><label>Bağıl tablo (T-puanı)</label><input type="text" id="tabloBagil" style="flex:1" value="${e(h.bagil)}"></div>
        <div class="satir"><label>Geçer harfler</label><input type="text" id="gecenHarf" style="flex:1" value="${e(h.gecen)}"><button id="harfUygula">Uygula</button></div>
        <div class="satir"><button id="finalExcel">Final puanlarını Excel'den al…</button><span class="soluk">Numara ve "Final" ya da "Puan" sütunu olan bir dosya; Akademik Bilgi Sistemi'nden indirdiğiniz liste de olur.</span></div></div>
      ${sonucHtml}
      <div class="tablo-kap"><table class="veri" id="donemTablo"><thead><tr><th>Öğrenci No</th><th class="sol">Ad Soyad</th><th>Ara sınav</th><th>Final</th><th>Ham not</th>${uyg === "bagil" ? "<th>T puanı</th>" : ""}<th>Harf</th><th>Durum</th><th class="sol">Açıklama</th><th>Sınırda</th></tr></thead><tbody>${satirlar}</tbody></table></div>`;
  }
  function donemOlaylari(k, s) {
    const p = D.proje;
    const yeniden = () => { const y = $("#icerik").scrollTop; UI.ciz(); $("#icerik").scrollTop = y; };
    const ayar = () => {
      p.harf_ayarlari = { yontem: ($("input[name=hy]:checked", k) || {}).value || "mutlak", mutlak: $("#tabloMutlak", k).value, bagil: $("#tabloBagil", k).value,
        bagil_en_az: parseInt($("#bagilEnAz", k).value, 10) || 30, gecen: $("#gecenHarf", k).value };
      yeniden();
    };
    $$("input[name=hy]", k).forEach((r) => (r.onchange = ayar));
    $("#harfUygula", k).onclick = ayar;
    $$("#donemTablo input.final", k).forEach((i) => {
      i.onchange = () => { const no = i.closest("tr").dataset.no; const x = i.value.trim(); if (x) p.final_puanlar[no] = x; else delete p.final_puanlar[no]; yeniden(); };
      i.onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === "ArrowDown") { const tr = i.closest("tr").nextElementSibling; if (tr) { ev.preventDefault(); const no = i.closest("tr").dataset.no; const x = i.value.trim(); if (x) p.final_puanlar[no] = x; else delete p.final_puanlar[no]; const sonraki = tr.dataset.no; yeniden(); const h = document.querySelector(`#donemTablo tr[data-no="${CSS.escape(sonraki)}"] input.final`); if (h) { h.focus(); h.select(); } } } };
      i.onpaste = (ev) => {
        const m = (ev.clipboardData || window.clipboardData).getData("text");
        if (!/\n/.test(m.trim())) return;
        ev.preventDefault();
        let tr = i.closest("tr");
        for (const x of m.replace(/\r/g, "").trim().split("\n")) { if (!tr) break; const d = x.split("\t")[0].trim(); if (d) p.final_puanlar[tr.dataset.no] = d; tr = tr.nextElementSibling; }
        yeniden();
      };
    });
    $("#finalExcel", k).onclick = async () => {
      const f = await dosyaSec(".xlsx,.xls,.csv");
      if (!f) return;
      try {
        const sayfalar = OS.sayfalariOku(window.XLSX, await baytOku(f), f.name);
        const [fin, notlar] = OS.tablodanFinalPuanlari(sayfalar[OS.sayfaSec(sayfalar)]);
        const var_ = new Set(s.ogrenciler.map((o) => o.no));
        let n = 0;
        for (const [no, x] of Object.entries(fin)) if (var_.has(no)) { if (x === null) delete p.final_puanlar[no]; else { p.final_puanlar[no] = x; n++; } }
        yeniden();
        bilgi("Final puanları", `${n} öğrencinin final puanı alındı.${notlar.length ? "\n" + notlar.join("\n") : ""}`);
      } catch (h) { bilgi("Okunamadı", h.message || String(h)); }
    };
  }

  const adim5 = {
    girildi() { if (!D.sonuc) UI.degerlendir(); },
    eksikler: () => [],
    ciz(k) {
      const x = istatistikVerisi();
      if (!x) { k.innerHTML = "<h2>5. İstatistikler (isteğe bağlı)</h2><p>Değerlendirilecek sonuç yok.</p>"; return; }
      const { s, m, g, esik } = x;
      const kl = s.klasik;
      const r = g.alfa !== null ? g.alfa : g.kr20;
      let ust = 100;
      try { ust = OS.Kesir.ondaliktan(s.ayarlar.toplam_puan).sayi(); } catch (_) { ust = 100; }
      const kart = (d, b) => `<div class="k"><b>${d}</b><span>${b}</span></div>`;
      const rapor = OS.ogrenmeCiktisiRaporu(s, esik, UI.aciklamalar()).filter((c) => c.tur.startsWith("Öğrenme"));
      const kavram = kl ? [] : OS.kavramYanilgilari(s);
      const sek = [["madde", "Madde analizi"], ["cikti", "Öğrenme çıktıları"], ...(kl ? [] : [["uyum", `Kişi uyumu (${g.kisi_uyumu.length})`], ["benzer", `Benzer cevaplar (${g.benzer_ciftler.length})`],
        ["kavram", `Kavram yanılgıları (${kavram.length})`]]), ["yapi", "Sınav yapısı"], ["belirleyen", "Notu belirleyen sorular"],
        ...(kl ? [["puanlama", "Puanlama (klasik)"]] : []), ["donem", "Dönem sonu notu"], ["ek", "Ek analizler"]];
      if (!sek.some(([id]) => id === I.sekme)) I.sekme = "madde";
      let icerik = "";
      const renk = (d) => (d === null ? "" : d >= 0.3 ? "D" : d >= 0.2 ? "B" : "Y");
      if (I.sekme === "madde") icerik = `<div class="tablo-kap"><table class="veri"><thead><tr><th>Soru</th><th>${kl ? "Tam puan" : "Doğru"}</th><th>Güçlük</th><th>Ayırt edicilik</th><th>Düzeltilmiş madde-toplam</th><th>Çıkarılırsa alfa</th><th>En düşük beşte bir → en yüksek beşte bir</th><th class="sol">Değerlendirme</th></tr></thead><tbody>
        ${m.map((q) => q.analiz_disi ? `<tr><td>${q.soru_no}</td><td>${kl ? OS.pyOndalik(q.tam_puan, 2) : e(q.dogru_sik || "-")}</td><td colspan="6" class="sol soluk">analiz dışı</td></tr>` :
          `<tr><td>${q.soru_no}</td><td>${kl ? v(q.tam_puan, 2) : e(q.dogru_sik)}</td><td class="${q.guclik >= 0.3 && q.guclik <= 0.7 ? "D" : q.guclik >= 0.2 && q.guclik <= 0.9 ? "B" : "Y"}">${sayi(q.guclik)}</td>
          <td class="${renk(q.ayirt_edicilik)}">${sayi(q.ayirt_edicilik)}</td><td class="${q.duzeltilmis_r !== null && q.duzeltilmis_r < 0.1 ? "Y" : ""}">${sayi(q.duzeltilmis_r)}</td>
          <td class="${q.alfa_cikarilirsa !== null && r !== null && q.alfa_cikarilirsa > r + 0.01 ? "uy" : ""}">${sayi(q.alfa_cikarilirsa)}</td><td>${q.bes_grup.length ? q.bes_grup.map(pct).join(" → ") : "-"}</td>
          <td class="sol uzun ${q.sorunlar.length ? "uy" : ""}">${e(q.sorunlar.join("; ") || "iyi")}</td></tr>`).join("")}</tbody></table></div>`;
      else if (I.sekme === "cikti") icerik = rapor.length ? `<div class="tablo-kap"><table class="veri"><thead><tr><th>Çıktı</th><th class="sol">Açıklama</th><th>Sınavdaki payı</th><th class="sol">Sınıf başarısı</th><th>Eşiğe ulaşan öğrenci</th></tr></thead><tbody>
        ${rapor.map((c) => `<tr><td>${e(c.kod)}</td><td class="sol uzun">${e(c.aciklama)}</td><td>%${v(c.sinav_agirligi, 1)}</td><td class="sol"><div class="satir" style="margin:0"><div class="cubuk"><i style="width:${Math.max(0, Math.min(100, c.sinif_yuzdesi || 0))}%;background:${(c.sinif_yuzdesi || 0) >= esik ? "var(--vurgu)" : "var(--hata)"}"></i></div>%${v(c.sinif_yuzdesi || 0, 1)}</div></td><td>${pct(c.ulasan_orani)}</td></tr>`).join("")}</tbody></table></div>`
        : `<p class="soluk">Sorulara öğrenme çıktısı atanmadı (2. adım).</p>`;
      else if (I.sekme === "uyum") icerik = `<p class="soluk">Kolay soruları kaçırıp zor soruları bilen öğrenciler (Harnisch ve Linn uyarı indeksi 0,50 üstü). Okuma hatası (bir satır kaydırarak işaretleme), dikkatsizlik ya da şans olabilir; kâğıda bakılması önerilir.</p>` +
        basitTablo(["Öğrenci No", "Ad Soyad", "Puan", "Uyum indeksi", "Beklenmedik sorular"], g.kisi_uyumu.map((x) => [e(x.no), e(x.ad), sayi(x.puan), sayi(x.indeks), x.beklenmedik.join(", ")]));
      else if (I.sekme === "benzer") icerik = `<p class="soluk">Aynı kitapçıktaki öğrenci çiftlerinden sınıf geneline göre olağandışı sayıda aynı yanlış şıkkı işaretleyenler. Bu yalnızca istatistiksel bir işarettir, kopya kanıtı değildir; oturma düzeni ve kâğıtlarla birlikte değerlendirin.</p>` +
        basitTablo(["1. öğrenci", "2. öğrenci", "Aynı yanlış şık", "İkisinin de yanlışı", "Uzaklık (standart sapma)", "Sorular"], g.benzer_ciftler.map((c) => [`${e(c.no1)} ${e(c.ad1)}`, `${e(c.no2)} ${e(c.ad2)}`, c.ayni_yanlis, c.ikisi_yanlis, v(c.z, 1), c.sorular.join(", ")]));
      else if (I.sekme === "kavram") icerik = kavramHtml(kavram);
      else if (I.sekme === "yapi") icerik = yapiHtml(s);
      else if (I.sekme === "belirleyen") icerik = belirleyenHtml(s);
      else if (I.sekme === "puanlama") icerik = puanlamaHtml(s);
      else if (I.sekme === "donem") icerik = donemHtml(s);
      else icerik = ekAnalizHtml(s, m, g, esik);
      k.innerHTML = `<h2>5. İstatistikler <span class="soluk" style="font-weight:400;font-size:15px">isteğe bağlı</span></h2>
        <div class="kutu"><b>Kısaca:</b><ul class="yorum">${g.yorumlar.map((y) => `<li>${e(y)}</li>`).join("")}</ul></div>
        <div class="ist-ust"><div class="kartlar">${kart(sayi(g.ortalama, 1), "Ortalama")}${kart(sayi(g.medyan, 1), "Ortanca")}${kart(sayi(g.standart_sapma, 1), "Standart sapma")}${kart(pct(g.basari_orani), `${esik} ve üstü alan`)}
          ${kart(sayi(r), "Güvenirlik (alfa)")}${kart(sayi(g.olcme_hatasi, 1), "Ölçme hatası (±puan)")}${kart(sayi(g.ortalama_guclik), "Ortalama güçlük")}${kart(sayi(g.ortalama_ayirt_edicilik), "Ortalama ayırt edicilik")}</div>
          <div class="kutu" style="margin:0"><b>Puan dağılımı</b> <span class="soluk">(kırmızı: eşiğin altı)</span>${histogramSvg(s.ogrenciler.map((o) => o.puan.sayi()), ust, esik)}</div></div>
        <div class="sekmeler" style="margin-top:14px">${sekmeCubugu(sek)}</div>
        <div>${icerik}</div>
        <p class="soluk">Tablolar 4. adımdaki istatistik Excel dosyasına, grafikler yazdırılabilir rapora girer.</p>`;
      $$("[data-ist]", k).forEach((b) => (b.onclick = () => { I.sekme = b.dataset.ist; UI.ciz(); }));
      if (I.sekme === "donem") donemOlaylari(k, s);
    },
  };

  // ------------------------------------------------------------------ 6. adım: dışa aktar
  const X = { profil: "akreditasyon_soru_bazli_varsayilan" };
  function arsiveEkle(s) {
    const esik = s.ayarlar.basari_esigi;
    const [, g] = OS.maddeAnalizi(s, { basari_esigi: esik, cikti_esigi: esik });
    const kayit = OS.arsivKaydi(s, D.proje.sinav, g, OS.ogrenmeCiktisiRaporu(s, esik));
    const t = yerel.al("os_arsiv", {}) || {};
    const l = (t[kayit.ders_kodu] || []).filter((x) => !(x.tarih === kayit.tarih && x.sinav_turu === kayit.sinav_turu));
    l.push(kayit);
    l.sort((p, q) => (p.tarih + p.sinav_turu < q.tarih + q.sinav_turu ? -1 : 1));
    t[kayit.ders_kodu] = l;
    yerel.koy("os_arsiv", t);
    return l;
  }
  function donemVerisi(s) {
    const p = D.proje;
    if (!Object.values(p.final_puanlar || {}).some((x) => x !== null && x !== "")) return null;
    try { return OS.donemSonu(s, p.final_puanlar, OS.araAgirligi(p.sinav, D.ders), p.ayarlar.final_alt_siniri, p.ayarlar.gecme_ortalamasi, OS.harfAyarlari(p.harf_ayarlari)); }
    catch (_) { return null; }
  }
  const adim6 = {
    girildi() { if (!D.sonuc) UI.degerlendir(); },
    eksikler: () => [],
    ciz(k) {
      const s = D.sonuc || UI.degerlendir();
      if (!s) { k.innerHTML = "<h2>4. Sisteme aktar ve raporlar</h2><p>Sonuç yok.</p>"; return; }
      const p = OS.PROFILLER[X.profil];
      const [bas, veri] = OS.tabloUret(p, s);
      const notlar = [];
      if (s.ogrenciler.some((o) => o.uyarilar.some((u) => u.tur === "tekrar_numara"))) notlar.push("Aynı numara birden çok satırda var; aktarımda yalnızca sonuncusu kullanılır. 3. adımda düzeltin.");
      if (!D.proje.anahtar.sorular.some((q) => (q.ogrenme_ciktilari || []).length)) notlar.push("Soru tanımı için her soruya bir öğrenme çıktısı gerekiyor: dosyaları indirirken ya da soruları kopyalarken dersin öğrenme çıktısı sayısı sorulacak (ders bilgi paketini 1. adımda yüklediyseniz sorulmaz).");
      if (s.listede_olmayanlar.length) notlar.push(`Listede olmayan ${s.listede_olmayanlar.length} numara sisteme aktarılmaz (önce 3. adımda numarasını düzeltin).`);
      const adim = (id, metin, aciklama) => `<div class="aktar-satir"><button class="aktar-dugme" id="${id}">${metin}</button><span class="soluk">${aciklama}</span></div>`;
      k.innerHTML = `<h2>4. Sisteme aktar ve raporlar</h2>
        ${notlar.length ? `<div class="serit">${notlar.map((x) => e(x)).join("<br>")}</div>` : ""}
        <div class="kutu"><h3>Akademik Bilgi Sistemi'ne aktarım (sırasıyla)</h3>
          ${adim("sorulariKopyala", "1. Soruları kopyala", "Sınav Akreditasyon İşlemleri'nde sınavı açın → \"Toplu Sınav Soru Tanım\" → \"Toplu Aktarım Yap\". Kolon Ayracı \"Excel'den Kopyalandı\" olsun; Aktarım Kutusu'na yapıştırıp \"Aktar\"a basın. Soru puanları ve öğrenme çıktısı oranları gider; bonus soru gitmez.")}
          ${adim("puanlariKopyala", "2. Öğrenci puanlarını kopyala", "Sorular tanımlandıktan sonra aynı dersin ve sınavın öğrenci puanı toplu aktarım ekranını açın; Kolon Ayracı \"Excel'den Kopyalandı\" olsun, Aktarım Kutusu'na yapıştırıp \"Aktar\"a basın. Her satırda öğrenci numarası ve soru puanları (sınava girenler; bonus soru yok). Not girişi için ayrıca bir şey gerekmez.")}
        </div>
        <div class="kutu"><h3>Dosyalar</h3>
          <div class="aktar-satir"><button class="zorunlu-dugme" id="girisDosyalari">Sisteme giriş dosyalarını indir</button>
            <span class="soluk">İki dosya: <b>soru tanımı</b> (Excel; açıp ilk sayfanın hepsini seçin, kopyalayın, Toplu Sınav Soru Tanım → Aktarım Kutusu'na yapıştırın) ve <b>akreditasyon</b> (öğrenci soru puanları; sorular tanımlandıktan sonra aynı yolla öğrenci puanı Aktarım Kutusu'na). Düğmelerle panoya kopyalamanın dosya hâlidir.</span></div>
          <div class="satir"><button id="digerRaporlar">Diğer raporlar…</button><button id="rapor">Yazdırılabilir rapor (grafikli)</button><button id="karne">Öğrenci karneleri</button></div></div>
        <details class="kutu" id="aktarGelismis" ${X.gelismisAcik ? "open" : ""}><summary class="soluk">Gelişmiş: aktarım biçimi, tek tek dosyalar ve önizleme</summary>
          <div class="satir"><label>Biçim</label><select id="profil">${Object.values(OS.PROFILLER).map((x) => `<option value="${x.ad}" ${x.ad === X.profil ? "selected" : ""}>${e(x.baslik)}</option>`).join("")}</select>
            <button id="pano">Sütun seçerek panoya kopyala</button><button id="sistemDosyasi">Sistemin puan dosyasını (CSV) doldur</button><button id="notlariKopyala">Not girişi için puanları kopyala</button>
            ${UI.acilirMenu("Tek tek indir", ['<button data-dosya="sonuc">Sonuç</button>', '<button data-dosya="istatistik">İstatistik</button>',
              '<button data-dosya="cikti">Öğrenme çıktısı</button>', '<button data-dosya="soru_tanimi">Soru tanımı</button>', '<button data-dosya="akreditasyon">Akreditasyon (soru bazlı)</button>', '<button data-dosya="not">Not girişi</button>'])}</div>
          <div class="tablo-kap" style="max-height:340px"><table class="veri"><thead><tr>${bas.map((b) => `<th>${e(b)}</th>`).join("")}</tr></thead>
          <tbody>${veri.slice(0, 200).map((r) => `<tr>${r.map((h) => `<td>${e(OS.hucreMetni(h, p))}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>`;
      $("#aktarGelismis", k).ontoggle = (ev) => { X.gelismisAcik = ev.target.open; };
      $("#sorulariKopyala", k).onclick = () => UI.soruTanimiKopyala();
      $("#sistemDosyasi", k).onclick = async () => {
        const f = await dosyaSec(".csv,.txt");
        if (!f) return;
        let r;
        try { r = OS.sistemDosyasiniDoldur(new Uint8Array(await baytOku(f)), s); } catch (err) { bilgi("Dosya doldurulamadı", err.message); return; }
        const ad = OS.ciktiAdi(D.proje.sinav, "sistem_puanlari").replace(/\.[^.]+$/, "") + ".csv";
        indir(r.bayt, ad, "text/csv");
        const x = r.rapor, m = [UI.sinavKisaAdi(), "", `Puanı yazılan öğrenci: ${x.yazilan}`];
        if (x.girmedi.length) m.push(`"Girmedi" yapılan (dosyada var, sınavda yok): ${x.girmedi.length}`);
        if (x.dosyada_olmayan.length) m.push(`Sınava girmiş ama dosyada olmayan numaralar: ${x.dosyada_olmayan.join(", ")}`);
        bilgi("Puan dosyası dolduruldu", m.concat(x.notlar.length ? [""].concat(x.notlar) : [], ["", `İndirildi: ${ad}`, "", "Bu dosyayı sistemde aynı ekrana yükleyin. İlk kullanımda bir öğrencinin satırını programdaki puanla karşılaştırın."]).join("\n"));
      };
      const sutunKopyala = async (sut, ne, profilAdi = "akreditasyon_soru_bazli_varsayilan") => {
        const pr = Object.assign({}, OS.PROFILLER[profilAdi], { sutunlar: sut });
        const metin = OS.panoMetni(pr, s);
        if (await kopyala(metin)) bildir(`${UI.sinavKisaAdi()} için panoya ${metin.split("\n").length} ${ne} kopyalandı (${s.liste_var ? "öğrenci listesi sırası" : "optik dosya sırası"}). Sistemde aynı dersin ekranında olduğunuzdan emin olun; tablonun ilk hücresine yapıştırın.`, 7000);
        else bilgi("Kopyalanamadı", "Tarayıcı panoya yazmaya izin vermedi.");
      };
      $("#puanlariKopyala", k).onclick = async () => {
        let metin;
        try { metin = OS.akreditasyonMetni(s); } catch (err) { bilgi("Kopyalanamadı", err.message); return; }
        const n = metin ? metin.split("\n").length : 0;
        const adimlar = "Akademik Bilgi Sistemi'nde aynı dersin ve sınavın öğrenci puanı toplu aktarım ekranında:\n1. \"Kolon Ayracı\" \"Excel'den Kopyalandı\" olsun.\n2. Aktarım Kutusu'na yapıştırın (Cmd+V ya da Ctrl+V).\n3. \"Aktar\" düğmesine basın.";
        if (await kopyala(metin)) bilgi("Panoya kopyalandı", `${UI.sinavKisaAdi()} için ${n} öğrencinin soru puanları kopyalandı.\n\n${adimlar}`);
        else pencere("Kopyalamak için seçin", `<p>Tarayıcı panoya yazmaya izin vermedi. Aşağıdaki metni seçip kopyalayın:</p><textarea style="width:100%;height:220px;font-family:Menlo,monospace">${e(metin)}</textarea><p style="white-space:pre-wrap">${e(adimlar)}</p>`);
      };
      $("#notlariKopyala", k).onclick = () => sutunKopyala([{ alan: "ogrenci_no", baslik: "Öğrenci No" }, { alan: "puan", baslik: "Puan" }], "öğrencinin numarası ve puanı", "not_giris_varsayilan");
      $("#profil", k).onchange = (ev) => { X.profil = ev.target.value; UI.ciz(); };
      $("#pano", k).onclick = async () => {
        const secenek = await pencere("Panoya kopyala", `<p>Kopyalanacak sütunlar:</p>${["Soru puanları (S1..Sn)", "Puan", "Öğrenci No ve puan", "Öğrenci No ve soru puanları"].map((x, i) => `<label style="display:block"><input type="radio" name="pk" value="${i}" ${i === 0 ? "checked" : ""}> ${x}</label>`).join("")}`,
          [{ metin: "Vazgeç", deger: null }, { metin: "Kopyala", ana: true, deger: (q) => Number($("input[name=pk]:checked", q).value) }]);
        if (secenek === null) return;
        const sut = [[{ alan: "soru_puanlari", baslik: "S{n}" }], [{ alan: "puan", baslik: "Puan" }], [{ alan: "ogrenci_no", baslik: "Öğrenci No" }, { alan: "puan", baslik: "Puan" }], [{ alan: "ogrenci_no", baslik: "Öğrenci No" }, { alan: "soru_puanlari", baslik: "S{n}" }]][secenek];
        const pr = Object.assign({}, OS.PROFILLER.akreditasyon_soru_bazli_varsayilan, { sutunlar: sut });
        const metin = OS.panoMetni(pr, s);
        if (await kopyala(metin)) bildir(`Panoya ${metin.split("\n").length} satır kopyalandı (${s.liste_var ? "öğrenci listesi sırası" : "optik dosya sırası"}).`);
        else bilgi("Kopyalanamadı", "Tarayıcı panoya yazmaya izin vermedi.");
      };
      const dosya = async (tur) => {
        const sn = D.proje.sinav;
        if (tur === "sonuc") return [await UI.excel.sonuc(s, sn, D.proje.duzeltmeler, { "Sınav biçimi": s.klasik ? "Klasik" : "Optik", "Optik dosya": D.proje.dat_yolu, "Öğrenci listesi": D.proje.liste_yolu }), OS.ciktiAdi(sn, "sonuc")];
        if (tur === "istatistik") return [await UI.excel.istatistik(s, sn, OS.araAgirligi(sn, D.ders), (yerel.al("os_arsiv", {}) || {})[sn.ders_kodu] || [], donemVerisi(s)), OS.ciktiAdi(sn, "istatistik")];
        if (tur === "cikti") { const b = await UI.excel.cikti(s, UI.aciklamalar(), UI.ogrenmeKodlari().length ? UI.ogrenmeKodlari() : null); return b ? [b, OS.ciktiAdi(sn, "ogrenme_ciktisi")] : null; }
        if (tur === "soru_tanimi") {
          const a = D.proje.anahtar, kodlar = UI.ogrenmeKodlari().length ? UI.ogrenmeKodlari() : null;
          if (!a.sorular.some((x) => (x.ogrenme_ciktilari || []).length)) return { not: "Soru tanımı indirilmedi: sorulara öğrenme çıktısı seçilmedi (2. adım). Sistem her soru için öğrenme çıktısı istiyor." };
          const [hatalar] = OS.ciktiDenetimi(a, kodlar);
          if (hatalar.length) return { not: "Soru tanımı indirilmedi: " + hatalar.join(" ") };
          return [await UI.excel.soruTanimi(a, D.proje.ayarlar, kodlar), OS.ciktiAdi(sn, "soru_tanimi")];
        }
        if (tur === "sistem_puanlari") {
          try { return [await UI.excel.akreditasyon(s), OS.ciktiAdi(sn, "akreditasyon")]; } catch (err) { return { not: "Akreditasyon (öğrenci soru puanları) dosyası indirilmedi: " + err.message }; }
        }
        if (tur === "akreditasyon") return [await UI.excel.profil(OS.PROFILLER.akreditasyon_soru_bazli_varsayilan, s), OS.ciktiAdi(sn, "soru_puanlari")];
        if (tur === "not") return [await UI.excel.profil(OS.PROFILLER.not_giris_varsayilan, s), OS.ciktiAdi(sn, "not_giris")];
        return null;
      };
      $$("[data-dosya]", k).forEach((b) => (b.onclick = async () => {
        const r = await dosya(b.dataset.dosya);
        if (r && r.not) bilgi("İndirilmedi", r.not);
        else if (r) indir(r[0], r[1]); else bilgi("Öğrenme çıktısı", "Sorulara öğrenme çıktısı atanmadığı için bu dosya yazılmadı.");
      }));
      const toplu = async (turler, baslik) => {
        const adlar = [], notlar = [];
        const aciklama = { soru_tanimi: "soruları tanımlamak için: Toplu Sınav Soru Tanım → Toplu Aktarım Yap; dosyayı açıp ilk sayfanın hepsini seçin, kopyalayın, Aktarım Kutusu'na yapıştırın",
          akreditasyon: "öğrenci soru puanları (programın Excel biçimi)", sistem_puanlari: "akreditasyon: öğrenci soru puanları; sorular tanımlandıktan sonra açıp ilk sayfanın hepsini seçin, kopyalayın, öğrenci puanı Aktarım Kutusu'na yapıştırın", not: "Not Giriş ekranı için öğrenci numarası ve puan" };
        for (const t of turler) {
          const r = await dosya(t);
          if (!r) { if (t === "cikti") notlar.push("Sorulara öğrenme çıktısı atanmadığı için öğrenme çıktısı raporu indirilmedi."); continue; }
          if (r.not) { notlar.push(r.not); continue; }
          indir(r[0], r[1]);
          adlar.push(`• ${r[1]}${aciklama[t] ? "\n   " + aciklama[t] : ""}`);
          await new Promise((c) => setTimeout(c, 400));
        }
        bilgi(baslik, `${UI.sinavKisaAdi()}\n\n${adlar.join("\n")}${notlar.length ? "\n\n" + notlar.join("\n") : ""}\n\nDosyalar tarayıcının İndirilenler klasörüne kaydedildi.`);
      };
      $("#girisDosyalari", k).onclick = async () => { await UI.ciktilariHazirla(); UI.otomatikKaydet(); toplu(["soru_tanimi", "sistem_puanlari"], "Sisteme giriş dosyaları indirildi"); };
      $("#digerRaporlar", k).onclick = async () => {
        const secenek = [["akreditasyon", "Öğrenci soru puanları (programın Excel biçimi)", false], ["not", "Not girişi (öğrenci numarası ve puan)", false], ["sonuc", "Sonuç (ayrıntılı: cevaplar, uyarılar, düzeltme kaydı)"], ["istatistik", "İstatistik (madde analizi, çeldiriciler ve ötekiler)"], ["cikti", "Öğrenme çıktısı raporu"]];
        const secim = await pencere("Diğer raporlar", `<p>İndirilecek raporları işaretleyin:</p>${secenek.map(([id, t, acik]) => `<label style="display:block;margin:4px 0"><input type="checkbox" data-rapor="${id}" ${acik === false ? "" : "checked"}> ${t}</label>`).join("")}
          <p class="soluk">Yazdırılabilir rapor ve öğrenci karneleri için bu adımdaki ayrı düğmeleri kullanın.</p>`,
          [{ metin: "Vazgeç", deger: null }, { metin: "İndir", ana: true, deger: (q) => $$("[data-rapor]", q).filter((x) => x.checked).map((x) => x.dataset.rapor) }]);
        if (!secim || !secim.length) return;
        if (secim.includes("istatistik")) arsiveEkle(s);
        toplu(secim, "Raporlar indirildi");
      };
      $("#rapor", k).onclick = () => UI.yazdirilabilirRapor(s);
      $("#karne", k).onclick = () => {
        const html = OS.karneHtml(s, D.proje.sinav, UI.aciklamalar()).replace("</body>", "<script>setTimeout(function(){window.print()},400)<\/script></body>");
        const w = window.open("", "_blank");
        if (!w) { indir(html, OS.ciktiAdi(D.proje.sinav, "karneler", ".html"), "text/html"); bildir("Karneler indirildi; açıp yazdırın."); return; }
        w.document.open(); w.document.write(html); w.document.close();
      };
    },
  };

  // ------------------------------------------------------------------ yazdırılabilir rapor
  UI.yazdirilabilirRapor = function (s) {
    const esik = s.ayarlar.basari_esigi;
    const [m, g] = OS.maddeAnalizi(s, { basari_esigi: esik, cikti_esigi: esik });
    const sn = D.proje.sinav;
    const rapor = OS.ogrenmeCiktisiRaporu(s, esik, UI.aciklamalar()).filter((c) => c.tur.startsWith("Öğrenme"));
    let ust = 100;
    try { ust = OS.Kesir.ondaliktan(s.ayarlar.toplam_puan).sayi(); } catch (_) { ust = 100; }
    const r = g.alfa !== null ? g.alfa : g.kr20;
    const html = `<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>${e(sn.ders_kodu)} ${e(sn.sinav_turu)} raporu</title>
      <style>${document.querySelector("style").textContent} body{background:#fff;color:#000;padding:20px;max-width:1000px;margin:auto} .tablo-kap{max-height:none;overflow:visible} @page{size:A4;margin:14mm}</style></head><body>
      <h2>${e(sn.ders_kodu)} ${e(sn.ders_adi)} — ${e(sn.sinav_turu)} ${e(sn.tarih)}</h2>
      <div class="kutu"><b>Kısaca:</b><ul class="yorum">${g.yorumlar.map((y) => `<li>${e(y)}</li>`).join("")}</ul></div>
      <div class="ist-ust"><div class="kartlar">${[[sayi(g.ortalama, 1), "Ortalama"], [sayi(g.medyan, 1), "Ortanca"], [sayi(g.standart_sapma, 1), "Standart sapma"], [pct(g.basari_orani), `${esik} ve üstü`], [sayi(r), "Güvenirlik"], [sayi(g.olcme_hatasi, 1), "Ölçme hatası"], [String(g.ogrenci_sayisi), "Sınava giren"], [String(s.girmeyenler.length), "Girmeyen"]].map(([a, b]) => `<div class="k"><b>${a}</b><span>${b}</span></div>`).join("")}</div>
      <div class="kutu">${histogramSvg(s.ogrenciler.map((o) => o.puan.sayi()), ust, esik)}</div></div>
      <h3>Madde analizi</h3><table class="veri"><thead><tr><th>Soru</th><th>Güçlük</th><th>Ayırt edicilik</th><th>Düzeltilmiş madde-toplam</th><th class="sol">Değerlendirme</th></tr></thead><tbody>
      ${m.map((q) => `<tr><td>${q.soru_no}</td><td>${sayi(q.guclik)}</td><td>${sayi(q.ayirt_edicilik)}</td><td>${sayi(q.duzeltilmis_r)}</td><td class="sol uzun">${e(q.analiz_disi ? "analiz dışı" : q.sorunlar.join("; ") || "iyi")}</td></tr>`).join("")}</tbody></table>
      ${rapor.length ? `<h3>Öğrenme çıktıları</h3><table class="veri"><thead><tr><th>Çıktı</th><th class="sol">Açıklama</th><th>Payı</th><th>Sınıf başarısı</th><th>Ulaşan</th></tr></thead><tbody>${rapor.map((c) => `<tr><td>${e(c.kod)}</td><td class="sol uzun">${e(c.aciklama)}</td><td>%${v(c.sinav_agirligi, 1)}</td><td>%${v(c.sinif_yuzdesi || 0, 1)}</td><td>${pct(c.ulasan_orani)}</td></tr>`).join("")}</tbody></table>` : ""}
      ${ekAnalizHtml(s, m, g, esik).replace(/<details>/g, "<details open>")}
      <p class="soluk">Optik Sınav Değerlendirme ile hazırlandı.</p><script>setTimeout(function(){window.print()},400)<\/script></body></html>`;
    const w = window.open("", "_blank");
    if (!w) { indir(html, OS.ciktiAdi(sn, "rapor", ".html"), "text/html"); bildir("Rapor indirildi; açıp yazdırın."); return; }
    w.document.open();
    w.document.write(html);
    w.document.close();
  };

  // ------------------------------------------------------------------ yardım
  UI.yardim = function () {
    pencere("Nasıl kullanılır?", `<ol>
      <li><b>Sınav ve dosyalar:</b> biçimi (optik ya da klasik) seçin, ders kodunu yazın, optik okuyucu dosyasını ve öğrenci listesini sürükleyip bırakın. Ders bilgi paketi PDF'ini bırakırsanız öğrenme çıktıları okunur.</li>
      <li><b>Cevap anahtarı</b> (klasikte <b>Sorular ve puanlar</b>): yuvarlak şıklara tıklayın ya da tabloya bir kez tıklayıp klavyeden harfleri yazın; her soruya öğrenme çıktısı girin. Yanlış cezası, yuvarlama ve eşikler alttaki "Puanlama ayarları" bölümündedir.</li>
      <li><b>Kontrol</b> (klasikte <b>Puan girişi</b>): üstteki "Düzeltilmesi gerekenler" listesinden okuma hatalarını düzeltin. Klasik sınavda puanlar burada girilir.</li>
      <li><b>Sisteme aktar ve raporlar:</b> sırasıyla soruları ve öğrenci puanlarını kopyalayıp Akademik Bilgi Sistemi'ne yapıştırın; Excel dosyalarını ve karneleri indirin.</li>
      <li><b>İstatistikler</b> (isteğe bağlı): yorum, madde analizi, öğrenme çıktısı başarısı, dönem sonu notu ve diğer analizler.</li></ol>
      <p><b>Kaydet</b> düğmesi sınavı tek bir <code>.osd</code> dosyasına kaydeder (optik dosya ve liste içine gömülüdür). Aynı dosya masaüstü programda da açılır.</p>
      <p><b>Gizlilik:</b> program internete bağlanmaz; dosyalar yalnızca bu tarayıcıda işlenir. Son çalışma bu tarayıcıda saklanır; ortak bilgisayarda işiniz bitince "Yeni sınav"a basın.</p>
      <p class="soluk">Kısayollar: Ctrl+Enter (Mac'te Cmd+Enter) sonraki adım, Ctrl+S (Cmd+S) kaydet.</p>`);
  };

  UI.adimlar.push(adim4, adim6, adim5);  // 3. kontrol, 4. sisteme aktar, 5. istatistikler (isteğe bağlı)

  // ------------------------------------------------------------------ açılış
  function baslat() {
    UI.kabuk();
    const son = yerel.al("os_son_proje");
    if (son) { try { UI.projeAc(son); } catch (_) { D.proje = OS.yeniProje(); } }
    UI.ciz();
    const n = Object.keys(D.proje.klasik_puanlar || {}).length;
    if (son && (D.liste || D.okuma)) bildir("Son çalışmanız geri yüklendi" + (D.proje.bicim === "klasik" && n ? `: ${n} öğrencinin puanı girilmiş.` : ".") + " Baştan başlamak için \"Yeni sınav\".", 6000);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", baslat); else baslat();
})();
