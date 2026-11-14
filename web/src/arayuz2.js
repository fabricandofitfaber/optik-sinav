/* Optik Sınav — tarayıcı sürümü: 4-6. adımlar (kontrol, istatistikler, dışa aktar), yardım, yazdırılabilir rapor ve açılış. */
(function () {
  "use strict";
  const OS = window.OS, UI = window.UI, D = UI.D;
  const { e, $, $$, bildir, pencere, bilgi, dosyaSec, baytOku, indir, kopyala, yerel } = UI;
  const v = OS.v;
  const pct = (x) => (x === null || x === undefined ? "-" : `%${OS.pyOndalik(x * 100, 0)}`);
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
        if (t === "soru") { const q = o.sorular[kk]; return `<td class="${q.durum} tik" data-alan="soru" data-k="${kk}" title="${kk + 1}. soru: ${OS.DURUM_ADI[q.durum]}, puan ${OS.sayiYaz(q.puan, 2)}">${e(String(q.isaret).trim())}</td>`; }
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
      return `<tr data-no="${e(og.no)}"><td>${i + 1}</td><td>${e(og.no)}</td><td class="sol">${e(og.ad)}</td>${Array.from({ length: n }, (_, k) => `<td class="${hucreSinifi(d[k], tam[k])}"><input class="hucre" data-k="${k}" value="${e(d[k] ?? "")}" inputmode="decimal"></td>`).join("")}<td class="kalin toplam">${klasikToplam(d)}</td></tr>`;
    };
    return `<div class="tablo-kap"><table class="veri" id="klasikTablo"><thead><tr><th>Sıra</th><th>Öğrenci No</th><th class="sol">Ad Soyad</th>${Array.from({ length: n }, (_, k) => `<th>S${k + 1}${tam[k] ? ` (${OS.klasikYaz(tam[k])})` : ""}</th>`).join("")}<th>Toplam</th></tr></thead><tbody>${L.map(satir).join("")}</tbody></table></div>`;
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
    return var_ ? OS.sayiYaz(t, 2) : '<span class="soluk">girmedi</span>';
  }
  function klasikYaz(no, k, deger) {
    const p = D.proje.klasik_puanlar;
    const s = (p[no] = p[no] || []);
    while (s.length <= k) s.push(null);
    s[k] = String(deger ?? "").trim() || null;
    if (s.every((x) => x === null)) delete p[no];
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
      if (!s) { k.innerHTML = "<h2>4. Kontrol ve düzeltme</h2><p>Değerlendirilecek okuma yok.</p>"; return; }
      const uyarili = s.ogrenciler.filter((o) => o.uyarilar.length).length;
      const ort = s.ogrenciler.length ? OS.sayiYaz(OS.topla(s.ogrenciler.map((o) => o.puan)).bol(s.ogrenciler.length), 2) : "-";
      const kits = [...new Set(s.ogrenciler.map((o) => o.kitapcik).filter((x) => x))].sort();
      const sek = [...(kl ? [["giris", "Puan girişi"]] : []), ["sonuc", "Sonuçlar"], ["girmeyen", `Sınava girmeyenler (${s.girmeyenler.length})`],
        ...(kl ? [] : [["olmayan", `Listede olmayanlar (${s.listede_olmayanlar.length})`], ["duzeltme", `Düzeltme kaydı (${D.proje.duzeltmeler.length})`]])];
      let icerik = "";
      if (K.sekme === "giris") icerik = `<div class="satir"><button id="exceldenAl">Excel'den puan al…</button><button id="sablonIndir">Boş puan şablonu indir</button>
          <span class="soluk">Hücreye tıklayıp puanı yazın (Enter alttaki öğrenciye geçer). Excel'den bir bloğu kopyalayıp bir hücreye yapıştırabilirsiniz. Hiç puanı girilmeyen öğrenci sınava girmemiş sayılır.</span></div>${klasikTablo()}`;
      else if (K.sekme === "sonuc") icerik = `<div class="satir"><label><input type="checkbox" id="yalnizUyarili" ${K.yalnizUyarili ? "checked" : ""}> Yalnızca uyarılıları göster</label>
          <span class="efsane"><span style="background:var(--dogru)">doğru</span><span style="background:var(--yanlis)">yanlış</span><span style="background:var(--bos)">boş</span><span style="background:var(--iptal)">iptal</span>${kl ? '<span style="background:var(--kismi)">kısmi</span>' : ""}<span style="background:var(--uyari)">uyarılı</span></span>
          <span class="soluk">${kl ? "Puanı değiştirmek için Puan girişi sekmesini kullanın." : "Numara, ad, tek bir cevap ya da kitapçığı düzeltmek için hücreye tıklayın. Özgün okuma silinmez."} Sütun başlığına tıklayarak sıralayın.</span></div>${sonucTablosu(s)}`;
      else if (K.sekme === "girmeyen") icerik = basitTablo(["Öğrenci No", "Ad Soyad", "Listedeki satır"], s.girmeyenler.map((g) => [e(g.no), e(g.ad), g.kaynak_satir]));
      else if (K.sekme === "olmayan") icerik = `<p class="soluk">Birebir eşleşmeyen numaralar otomatik eşleştirilmez. Numarayı düzeltmek için satıra tıklayın.</p>` +
        basitTablo(["Dosya satırı", "Okunan numara", "Okunan ad", "Olası numaralar", "Puan"], s.listede_olmayanlar.map((o) => [o.kayit.satir_no, e(o.no), e(o.okunan_ad), e(o.oneriler.join(", ")), OS.sayiYaz(o.puan, s.ayarlar.ondalik)]), "olmayan");
      else icerik = basitTablo(["Dosya satırı", "Alan", "Eski değer", "Yeni değer", "Kim", "Ne zaman"], D.proje.duzeltmeler.map((d) => [d.satir_no, e(d.alan), e(d.eski), e(d.yeni), e(d.kim), e(d.zaman)]));
      k.innerHTML = `<h2>4. Kontrol ve düzeltme</h2>
        <p id="kontrolOzet">${kontrolOzeti(s)}</p>
        <div class="sekmeler">${sek.map(([id, t]) => `<button data-sekme="${id}" class="${K.sekme === id ? "secili" : ""}">${t}</button>`).join("")}</div>${icerik}`;
      $$("[data-sekme]", k).forEach((b) => (b.onclick = () => { K.sekme = b.dataset.sekme; UI.ciz(); }));
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
    if (!s) return;
    const p = $("#kontrolOzet");
    if (p) p.innerHTML = kontrolOzeti(s);
    const b = $('[data-sekme="girmeyen"]');
    if (b) b.textContent = `Sınava girmeyenler (${s.girmeyenler.length})`;
    UI.altGuncelle();
    UI.otomatikKaydet();
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
      $(".toplam", tr).innerHTML = klasikToplam(d);
    };
    const yaz = (i) => { const tr = i.closest("tr"); klasikYaz(tr.dataset.no, Number(i.dataset.k), i.value); satirGuncelle(tr); klasikOzetGuncelle(); };
    $$("input.hucre", tablo).forEach((i) => {
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
        const [p, notlar] = OS.tablodanKlasikPuanlar(sayfalar[OS.sayfaSec(sayfalar)], D.proje.anahtar.sorular.length);
        const listede = new Set(D.liste.ogrenciler.map((o) => o.no));
        const yabanci = Object.keys(p).filter((x) => !listede.has(x));
        for (const [no, d] of Object.entries(p)) if (listede.has(no) && d.some((x) => x !== null)) D.proje.klasik_puanlar[no] = d;
        UI.degerlendir();
        UI.ciz();
        bilgi("Excel'den puan", `${Object.keys(p).filter((x) => listede.has(x)).length} öğrencinin puanı alındı.${yabanci.length ? `\nListede olmayan numaralar alınmadı: ${yabanci.slice(0, 10).join(", ")}` : ""}${notlar.length ? "\n" + notlar.join("\n") : ""}`);
      } catch (h) { bilgi("Okunamadı", h.message || String(h)); }
    };
    $("#sablonIndir", k).onclick = async () => indir(await UI.excel.klasikSablon(D.liste.ogrenciler, D.proje.anahtar.sorular.length, D.proje.klasik_puanlar), OS.ciktiAdi(D.proje.sinav, "puan_girisi"));
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
      h.push(`<h3>Finalde gereken puan</h3><p>Ara sınav %${ara}, final %${100 - ara}; geçme ortalaması ${a.gecme_ortalamasi}, final alt sınırı ${a.final_alt_siniri} (3. adımda değiştirilebilir). Finalden 80'in üstünde alması gereken ya da 100 alsa da yetişemeyecek öğrenci: <b>${zor.length}</b>.</p>`);
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
      : `<p class="soluk">Bu ders için bu tarayıcıda arşiv kaydı yok. 6. adımda "Bütün Excel dosyalarını indir" her kullanıldığında sınavın özeti burada saklanır; sonraki dönemlerde karşılaştırma görünür.</p>`);
    return h.join("");
  }
  const adim5 = {
    girildi() { if (!D.sonuc) UI.degerlendir(); },
    eksikler: () => [],
    ciz(k) {
      const x = istatistikVerisi();
      if (!x) { k.innerHTML = "<h2>5. İstatistikler</h2><p>Değerlendirilecek sonuç yok.</p>"; return; }
      const { s, m, g, esik } = x;
      const kl = s.klasik;
      const r = g.alfa !== null ? g.alfa : g.kr20;
      let ust = 100;
      try { ust = OS.Kesir.ondaliktan(s.ayarlar.toplam_puan).sayi(); } catch (_) { ust = 100; }
      const kart = (d, b) => `<div class="k"><b>${d}</b><span>${b}</span></div>`;
      const rapor = OS.ogrenmeCiktisiRaporu(s, esik, UI.aciklamalar()).filter((c) => c.tur.startsWith("Öğrenme"));
      const sek = [["madde", "Madde analizi"], ["cikti", "Öğrenme çıktıları"], ...(kl ? [] : [["uyum", `Kişi uyumu (${g.kisi_uyumu.length})`], ["benzer", `Benzer cevaplar (${g.benzer_ciftler.length})`]]), ["ek", "Ek analizler"]];
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
      else icerik = ekAnalizHtml(s, m, g, esik);
      k.innerHTML = `<h2>5. İstatistikler</h2>
        <div class="kutu"><b>Kısaca:</b><ul class="yorum">${g.yorumlar.map((y) => `<li>${e(y)}</li>`).join("")}</ul></div>
        <div class="ist-ust"><div class="kartlar">${kart(sayi(g.ortalama, 1), "Ortalama")}${kart(sayi(g.medyan, 1), "Ortanca")}${kart(sayi(g.standart_sapma, 1), "Standart sapma")}${kart(pct(g.basari_orani), `${esik} ve üstü alan`)}
          ${kart(sayi(r), "Güvenirlik (alfa)")}${kart(sayi(g.olcme_hatasi, 1), "Ölçme hatası (±puan)")}${kart(sayi(g.ortalama_guclik), "Ortalama güçlük")}${kart(sayi(g.ortalama_ayirt_edicilik), "Ortalama ayırt edicilik")}</div>
          <div class="kutu" style="margin:0"><b>Puan dağılımı</b> <span class="soluk">(kırmızı: eşiğin altı)</span>${histogramSvg(s.ogrenciler.map((o) => o.puan.sayi()), ust, esik)}</div></div>
        <div class="sekmeler" style="margin-top:14px">${sek.map(([id, t]) => `<button data-ist="${id}" class="${I.sekme === id ? "secili" : ""}">${t}</button>`).join("")}</div>
        <div>${icerik}</div>
        <p class="soluk">Tablolar 6. adımdaki istatistik Excel dosyasına, grafikler yazdırılabilir rapora girer.</p>`;
      $$("[data-ist]", k).forEach((b) => (b.onclick = () => { I.sekme = b.dataset.ist; UI.ciz(); }));
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
  const adim6 = {
    girildi() { if (!D.sonuc) UI.degerlendir(); },
    eksikler: () => [],
    ciz(k) {
      const s = D.sonuc || UI.degerlendir();
      if (!s) { k.innerHTML = "<h2>6. Dışa aktar</h2><p>Sonuç yok.</p>"; return; }
      const p = OS.PROFILLER[X.profil];
      const [bas, veri] = OS.tabloUret(p, s);
      const notlar = [];
      if (s.ogrenciler.some((o) => o.uyarilar.some((u) => u.tur === "tekrar_numara"))) notlar.push("Aynı numara birden çok satırda var; aktarımda yalnızca sonuncusu kullanılır. 4. adımda düzeltin.");
      if (s.listede_olmayanlar.length) notlar.push(`Listede olmayan ${s.listede_olmayanlar.length} numara aktarım dosyalarına yazılmaz.`);
      k.innerHTML = `<h2>6. Dışa aktar</h2>
        <div class="kutu"><h3>Dosyalar</h3>
          <div class="satir"><button class="ana" id="hepsi">Bütün Excel dosyalarını indir</button><button id="rapor">Yazdırılabilir rapor (grafikli)</button></div>
          <div class="satir"><button data-dosya="sonuc">Sonuç</button><button data-dosya="istatistik">İstatistik</button><button data-dosya="cikti">Öğrenme çıktısı</button>
            <button data-dosya="akreditasyon">Akreditasyon (soru bazlı)</button><button data-dosya="not">Not girişi</button></div>
          <p class="soluk">Sonuç: soru bazlı puanlar, cevaplar, uyarılar, düzeltme kaydı. İstatistik: özet ve yorum, madde analizi, çeldiriciler, beş grup, boş bırakma, kişi uyumu, benzer cevaplar, ek analizler, standart puanlar. Öğrenme çıktısı: soru-çıktı eşlemesi, sisteme aktarım tablosu, sınav dağılımı, sınıf ve öğrenci başarısı.</p>
          ${notlar.map((x) => `<p class="kirmizi">${e(x)}</p>`).join("")}</div>
        <div class="kutu"><h3>Akademik Bilgi Sistemi'ne aktarım</h3>
          <p>Soru tanımı (puanlar ve öğrenme çıktısı yüzdeleri) 2. adımdaki <b>"Soru tanımını sistem için kopyala"</b> düğmesiyle aktarılır. Öğrenci puanlarının girildiği ekranın biçimi henüz doğrulanmadı; aşağıdaki biçimler geçicidir.</p>
          <div class="satir"><label>Biçim</label><select id="profil">${Object.values(OS.PROFILLER).map((x) => `<option value="${x.ad}" ${x.ad === X.profil ? "selected" : ""}>${e(x.baslik)}</option>`).join("")}</select>
            <button id="pano">Puanları panoya kopyala</button><span class="soluk">Sistemde tablo halinde giriş varsa ilk hücreye yapıştırın (öğrenci listesi sırasıyla).</span></div>
          <div class="tablo-kap" style="max-height:340px"><table class="veri"><thead><tr>${bas.map((b) => `<th>${e(b)}</th>`).join("")}</tr></thead>
          <tbody>${veri.slice(0, 200).map((r) => `<tr>${r.map((h) => `<td>${e(OS.hucreMetni(h, p))}</td>`).join("")}</tr>`).join("")}</tbody></table></div></div>`;
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
        if (tur === "istatistik") return [await UI.excel.istatistik(s, sn, OS.araAgirligi(sn, D.ders), (yerel.al("os_arsiv", {}) || {})[sn.ders_kodu] || []), OS.ciktiAdi(sn, "istatistik")];
        if (tur === "cikti") { const b = await UI.excel.cikti(s, UI.aciklamalar(), UI.ogrenmeKodlari().length ? UI.ogrenmeKodlari() : null); return b ? [b, OS.ciktiAdi(sn, "ogrenme_ciktisi")] : null; }
        if (tur === "akreditasyon") return [await UI.excel.profil(OS.PROFILLER.akreditasyon_soru_bazli_varsayilan, s), OS.ciktiAdi(sn, "akreditasyon")];
        if (tur === "not") return [await UI.excel.profil(OS.PROFILLER.not_giris_varsayilan, s), OS.ciktiAdi(sn, "not_giris")];
        return null;
      };
      $$("[data-dosya]", k).forEach((b) => (b.onclick = async () => {
        const r = await dosya(b.dataset.dosya);
        if (r) indir(r[0], r[1]); else bilgi("Öğrenme çıktısı", "Sorulara öğrenme çıktısı atanmadığı için bu dosya yazılmadı.");
      }));
      $("#hepsi", k).onclick = async () => {
        arsiveEkle(s);
        const adlar = [];
        for (const t of ["sonuc", "istatistik", "cikti", "akreditasyon", "not"]) {
          const r = await dosya(t);
          if (!r) continue;
          indir(r[0], r[1]);
          adlar.push(r[1]);
          await new Promise((c) => setTimeout(c, 400));
        }
        bilgi("Dosyalar indirildi", adlar.join("\n") + "\n\nDosyalar tarayıcının İndirilenler klasörüne kaydedildi. Sınavın özeti bu tarayıcıdaki arşive eklendi.");
      };
      $("#rapor", k).onclick = () => UI.yazdirilabilirRapor(s);
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
      <li><b>Cevap anahtarı:</b> yuvarlak şıklara tıklayın ya da tabloya bir kez tıklayıp klavyeden harfleri yazın. Her soruya puan ve öğrenme çıktısı girin; yüzdeler 100 etmelidir. "Soru tanımını sistem için kopyala" ile Akademik Bilgi Sistemi'ne aktarın.</li>
      <li><b>Puanlama:</b> yanlış cezası, çift işaret, yuvarlama ve eşikler.</li>
      <li><b>Kontrol:</b> renkli tablo; okuma hatasını hücreye tıklayarak düzeltin. Klasik sınavda puanlar burada girilir.</li>
      <li><b>İstatistikler:</b> yorum, madde analizi, öğrenme çıktısı başarısı, sınırdaki öğrenciler, finalde gereken puan ve daha fazlası.</li>
      <li><b>Dışa aktar:</b> Excel dosyaları ve yazdırılabilir rapor.</li></ol>
      <p><b>Kaydet</b> düğmesi sınavı tek bir <code>.osd</code> dosyasına kaydeder (optik dosya ve liste içine gömülüdür). Aynı dosya masaüstü programda da açılır.</p>
      <p><b>Gizlilik:</b> program internete bağlanmaz; dosyalar yalnızca bu tarayıcıda işlenir. Son çalışma bu tarayıcıda saklanır; ortak bilgisayarda işiniz bitince "Yeni sınav"a basın.</p>
      <p class="soluk">Kısayollar: Ctrl+Enter (Mac'te Cmd+Enter) sonraki adım, Ctrl+S (Cmd+S) kaydet.</p>`);
  };

  UI.adimlar.push(adim4, adim5, adim6);

  // ------------------------------------------------------------------ açılış
  function baslat() {
    UI.kabuk();
    const son = yerel.al("os_son_proje");
    if (son) { try { UI.projeAc(son); } catch (_) { D.proje = OS.yeniProje(); } }
    UI.ciz();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", baslat); else baslat();
})();
