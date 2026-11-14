# CLAUDE.md

Ayrıntılı tanım `PROJE_TANIMI.md` dosyasındadır. Bu dosya önemli kararların özetidir.

## Kesin kurallar

- Gerçek öğrenci verisi (ad, numara, cevap) **asla** depoya girmez. Gerçek dosyalar `ornek_veri/` altındadır ve `.gitignore` ile dışarıdadır. Test ve ekran görüntüleri yalnızca `tests/fixtures/` altındaki uydurma verilerle (`tools/fixture_uret.py`) üretilir.
- Program ağa erişmez. Yeni bağımlılık eklerken bunu bozmayın.
- Kullanıcıya görünen metinler `src/optik_sinav/metinler.py` içindedir.
- Puanlama motoru (`core/`) saf fonksiyonlardır, arayüze bağlanmaz. İş kuralı değişikliği önce `core/` ve testlerde yapılır.

## Mimari

- `io/`: `kodlama.py` (UTF-8 katı, sonra Windows-1254, sonra Latin-1; CRLF, LF ve CR), `dat_okuyucu.py` (sabit genişlik, uyarılar, soru sayısı önerisi), `liste_okuyucu.py` (xlsx, xls, csv; sütun tahmini).
- `core/`: `modeller.py`, `puanlama.py`, `dogrulama.py` (düzeltme, liste eşleştirme, numara önerisi, kitapçık çevirisi), `klasik.py` (klasik sınav puanlaması ve Excel'den puan alma), `madde_analizi.py` (madde analizi, istatistikler, öğrenme çıktısı dağılımı ve denetimi), `proje.py` (`.osd`), `ciktilar.py` (dosya adları).
- `io/ders_paketi.py`: ders bilgi paketi PDF'ini (pypdf) çözer; `dersler/<KOD>.json` (paketle gelen) ve kullanıcı klasöründeki `dersler/`.
- `export/`: `profil.py` (profil şeması ve satır üretimi), `xlsx_yazici.py`, `csv_yazici.py`, `sablon_doldurucu.py`, `pano.py`, `raporlar.py` (sonuç, madde analizi, öğrenme çıktısı, özet).
- `ui/`: `ana_pencere.py`, `durum.py` (ortak durum), `adimlar/*.py` (altı adım: dosyalar, anahtar, puanlama, kontrol, istatistik, dışa aktar), `tablolar.py` (sonuç modeli, klasik puan giriş modeli), `tema.py`.
- `cli.py`: `python -m optik_sinav puanla|onizle`. Komutsuz çalıştırma arayüzü açar.
- `kaynaklar.py`: `profiles/`, `readers/`, `assets/` kaynak ağacında depo kökünde, PyInstaller paketinde `sys._MEIPASS` altında. Kullanıcı verisi `QStandardPaths.AppDataLocation` (testlerde `OPTIK_SINAV_VERI` ortam değişkeni).

## Tarayıcı sürümü (`web/`)

- Tek dosya: `python tools/web_derle.py` → `web/dist/OptikSinav.html` (git dışında). İçine gömülenler: `web/src/stil.css`, `web/vendor/` altındaki SheetJS 0.18.5, ExcelJS 4.4.0, PDF.js 3.11.174 (sürümler sabit, `SHA256SUMS` derlemede denetlenir), `dersler/*.json` ve `web/src/*.js`.
- Sayfanın Content-Security-Policy kuralı ağ bağlantısını yasaklar (connect-src ve img-src yalnızca blob/data). Yeni kod dışarıdan hiçbir şey yüklememeli.
- Motor (`cekirdek.js`, `istatistik.js`, `ciktilar.js`, `dosya.js`) Python motorunun birebir karşılığıdır: kesirler BigInt ile, ondalık biçimlendirme Python'daki gibi (`pyOndalik`), anahtar sırası önemli sözlükler için `Map`. **İş kuralı değişirse iki tarafa da işlenir** ve `python tools/web_parite.py` ile beklenen değerler yenilenip `node web/test/parite.mjs` (ya da `pytest tests/test_web_parite.py`) çalıştırılır. Gerçek sınav senaryosu `ornek_veri/web_parite_gercek.json` (git dışında).
- Arayüz: `arayuz.js` (durum, kabuk, 1-3. adımlar), `arayuz2.js` (4-6. adımlar, yazdırılabilir rapor, karne), `donem.js` (kavram yanılgıları, sınav yapısı, dönem sonu, karne motoru), `excel.js` (ExcelJS; grafik yok, grafikler yazdırılabilir raporda SVG).
- `.osd` dosyası masaüstüyle ortaktır; tarayıcı sürümü ek olarak `gomulu_dosyalar` (optik dosya ve liste, base64) yazar, masaüstü bu alanı yok sayar.
- PDF işçisi `<head>` içindeki `text/plain` betikten Blob olarak başlatılır; `kabuk()` gövdeyi yeniden yazdığı için gövdeye konmamalı.
- PDF metni satır satır, parçalar boşlukla birleştirilerek kurulur (Akademik Bilgi Sistemi ders bilgi paketlerinde pypdf ile aynı sonuç). Boşluk aralığına göre birleştirme denendi, gerçek paketleri bozdu.
- Tarayıcıda saklananlar (localStorage): son çalışma `os_son_proje`, ders paketleri `os_dersler`, ders eşlemeleri `os_ders_eslemeleri`, arşiv `os_arsiv`.

## Verilen kararlar

- Puanlar `fractions.Fraction` ile tam tutulur; `yuvarla()` tek yuvarlama noktasıdır (yarım yukarı sıfırdan uzağa, aşağı taban, yukarı tavan).
- İptal soru: herkese tam puan, **doğru** sayısına eklenir, yanlış cezası uygulanmaz, madde analizinde analiz dışıdır.
- Anahtarı girilmemiş soru ("-") puanlamayı engeller (eksik olarak gösterilir).
- Geçersiz işaret (A-E, boşluk ve `*` dışı) boş sayılır ve uyarı verir. Küçük harf büyütülür.
- Yanlış cezası soru bazlı puanda her yanlış için o sorunun puanı / oran olarak hesaplanır; eşit puanda net formülüyle aynıdır.
- Sınava girmeyen = listede olup düzeltilmiş numaralar arasında olmayan. Listede olmayan numara otomatik eşleştirilmez; öneri sondan ortak hane, kapsama ve düzenleme uzaklığına göre verilir.
- Aynı numara iki satırda varsa ikisi de uyarılır; aktarımda son satır kullanılır (5. adım uyarır).
- Ad her zaman listeden alınır; listede yoksa okunan ad kullanılır.
- Düzeltmeler `Duzeltme` kayıtlarıdır; `HamKayit` hiç değişmez. Düzeltilen alanın okuma uyarıları kalkar.
- Madde analizi: güçlük = doğru oranı; ayırt edicilik üst ve alt %27 (en az 1 kişi, puana göre sıralı); nokta çift serili korelasyon toplam doğru sayısıyla (soru dahil); Kuder-Richardson 20 kitle varyansıyla; sınav geneli standart sapması örneklem (n-1).
- Altın dosya testleri: csv ve txt bayt bayt; xlsx hücre değeri, türü ve sayı biçimi düzeyinde (zip zaman damgası yüzünden). Yenilemek için `ALTIN_GUNCELLE=1 pytest tests/test_export.py`.
- `.xls` okunur ama yazılmaz; `.xls` şablon doldurulursa çıktı `.xlsx` olur.
- Qt bağımlılığı `PySide6-Essentials` (6.9.2 ve 6.11.3 ile denendi). Tam PySide6 gereksiz yere büyüktür.
- **Sanal ortam iCloud dışında olmalı.** `~/Documents` iCloud ile eşitleniyor; eşitleme `.venv` içindeki dosyalara "gizli" bayrağı koyuyor ve Qt gizli eklenti dosyalarını görmediği için "Could not find the Qt platform plugin" hatasıyla çöküyor. Ortam `~/.venvs/optik-sinav` içindedir, `.venv` ona bağlantıdır. Paket de iCloud dışında derlenir: `--distpath ~/.venvs/optik-sinav-paket/dist --workpath ~/.venvs/optik-sinav-paket/build`.
- Gerçek `.dat` kopyası (13 Kasım 2026'da alınan) temiz Windows-1254 kodlamalıdır; belgede anlatılan bozuk karakterler o kopyada yok. Bozuk karakter durumu uydurma `uydurma_bozuk_utf8.dat` ile test edilir.
- **Öğrenme çıktısı yüzdeleri:** `Soru.cikti_yuzdeleri` (tam sayı); boşsa çıktılar arasında eşit (`esit_yuzdeler`, fazlalık baştakilere, toplam tam 100). Akademik Bilgi Sistemi %100 olmayan dağılımı kabul etmediği için 2. adım, çıktı girilmişse her sorunun 100 etmesini ve her sorunun en az bir çıktısı olmasını zorunlu tutar (`cikti_denetimi`). Çıktı başarısı puan × yüzde ile ağırlıklıdır. Sınav dağılımı `cikti_dagilimi` (toplam 100), tam sayıya `tam_sayi_dagilim` (en büyük kalan).
- **Kitapçık:** `CevapAnahtari.kitapcik_anahtarlari` (kitapçığın kendi sırasıyla harfler) ve `kitapcik_eslemesi` (kitapçık soru no → ana soru no; tanımsızlar aynı numara). `kitapcik_icin` ana sıraya çevrilmiş anahtar döndürür. `OgrenciSonucu.cevaplar` ana sıradadır; `kaynak_soru` öğrencinin kendi soru numarasını tutar (cevap düzeltmesi `cevap:<kendi no>`). Kitapçık düzeltmesi `Duzeltme(alan="kitapcik")`. Bilinmeyen kitapçık ana sayılır ve uyarılır. Çeldirici analizi ana kitapçık öğrencileriyle yapılır.
- **Klasik sınav:** `SinavProjesi.bicim == "klasik"`, `klasik_puanlar` (no → metin puanlar), liste zorunlu. Hiç puanı olmayan öğrenci girmedi sayılır. Durum: tam = D, 0 = Y, boş = B, arası = K (kısmi). Madde puanı alınan/tam oranıdır; Kuder-Richardson 20 yalnızca testte, Cronbach alfa ikisinde de.
- **İstatistik eşikleri:** kişi uyumu (Harnisch ve Linn) 0,50 üstü; benzer yanlış örüntüsü: aynı kitapçık, z ≥ 4 ve aynı yanlış ≥ max(4, soruların %30'u); üst grubu yanıltan çeldirici farkı ≥ 0,10. 15 soruluk gerçek sınavda daha gevşek eşikler çok fazla işaret üretti.
- **Sistemin soru tanımı biçimi (13 Kasım 2026, kullanıcının ekran görüntülerinden):** Sınav Akreditasyon İşlemleri > sınav > "Toplu Sınav Soru Tanım: Toplu Aktarım Yap", Kolon Ayracı "Excel'den Kopyalandı", Aktarım Kutusu'na sekmeyle ayrılmış satırlar: `Soru No, Soru Puan, Soru metni, DÇ Sıra, Etki Oran, DÇ Sıra, Etki Oran…`. DÇ Sıra = ders öğrenme çıktısı sırası. Sistem kuralları: soru puanları toplamı %100; her soru için en az bir öğrenme çıktısı, etki oranları toplamı %100; boş puan ya da etki oranını sistem otomatik hesaplar. Programdaki karşılığı `export/soru_tanimi.py` ve 2. adımdaki "Soru tanımını sistem için kopyala" düğmesi. Öğrenci puanlarının girildiği ekran (sorular tanımlandıktan sonra açılan) henüz görülmedi.
- **Ek istatistikler** (`core/ek_istatistik.py`): sınırdaki öğrenciler (eşiğe ölçme hatası kadar yakın), finalde gereken puan (ara ağırlık: sınav etki oranı, yoksa ders paketi, yoksa 40; geçme ortalaması ve final alt sınırı `PuanlamaAyarlari`), şans puanı, kitapçık Welch t testi, sınav tasarımı (şık dengesi, art arda aynı harf, sıra-güçlük Spearman), Rasch (birleşik en çok olabilirlik, (k-1)/k düzeltmesi, bilgi eğrisi), arşiv (masaüstünde `kullanici_klasoru()/arsiv/<ders>/`). Olası anahtar hatası madde analizindedir: üst grubun en az %40'ı aynı yanlış şıkkı seçmiş ve bu doğru şıktan çoksa.
- **Kavram yanılgıları:** ana kitapçık, her yanlış şık ≥ max(3, %5 öğrenci); çift: birlikte ≥ aynı eşik, phi ≥ 0,30, koşullu oran ≥ 1,5 × taban ve Fisher üst kuyruk p ≤ 0,01 (gerçek UTL4513 sınavında 2 çift).
- **Sınav yapısı:** madde puanı (oran) korelasyon matrisi, Jacobi özdeğerleri; birinci/ikinci ≥ 3 tek boyut, ≥ 1,5 baskın; yük < 0,20 zayıf; çıktı uyumu kendi içi ve dış ortalama korelasyon.
- **Dönem sonu notu** (`core/donem_sonu.py`): `SinavProjesi.final_puanlar`, `harf_ayarlari`. Ham = ara × w + final × (1 − w) kesirle; final alt sınırı altı en düşük harf; bağılda T = 50 + 10 (ham − ort)/örneklem sd, grup final alt sınırını geçenler, grup < `bagil_en_az` ise mutlak. Harf tabloları ÖRNEK; yönetmelik doğrulanmadı.
- **Karne:** `export/karne.py` ve `web/src/donem.js` aynı HTML'i üretir; güçlü/gelişmeli = sınıftan ±10 puan, yoksa en yüksek/en düşük fark.
- **Kâğıt sırasıyla giriş (klasik):** `ui/adimlar/kagit.py` ve `arayuz2.js` (`kagitPaneli`); numara ya da Türkçe harf duyarsız ad parçasıyla arama. `SinavProjesi.klasik_toplamlar`: kâğıttaki toplam; `klasik_degerlendir(..., toplamlar)` tutmazsa uyarır (iki motorda, paritede).
- **Dağıtım:** Sürüm dosya adları sürümsüzdür (`OptikSinav.html`, `OptikSinav-Mac-AppleSilicon.dmg`, `OptikSinav-Mac-Intel.dmg`, `OptikSinav-Windows-Kurulum.exe`, `OptikSinav-Windows-Tasinabilir.zip`); README ve indirme sayfası `releases/latest/download/<dosya>` bağlantılarını kullanır. İndirme sayfası `site/index.html`, GitHub Pages'e `.github/workflows/sayfa.yml` ile yayımlanır (uygulama da `uygulama.html` olarak).
- Masaüstünde her adım `QScrollArea` içindedir ve uzun açıklamalar satıra kayar; altı adım 900×600 pencereye yatay kaydırmasız sığar. Yeni uzun `QLabel` eklerken `setWordWrap(True)` verin, uzun düğme sıralarını ızgaraya dizin.
- Okuyucu şablonu 1. adımda "Gelişmiş ayarlar" düğmesinin arkasındadır; okunan satırların %30'undan çoğu uyarılıysa kendiliğinden açılır.
- Rapor dosyası adı `madde_analizi` yerine `istatistik` oldu (grafikli, çok sayfalı).
- Kabul testi 6 (63 kişilik liste) için gerçek 63 kişilik liste yok; mevcut 61 kişilik listeye iki uydurma öğrenci eklenerek denenir.

## Komutlar

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python tools/fixture_uret.py
QT_QPA_PLATFORM=offscreen .venv/bin/python tools/simge_uret.py
QT_QPA_PLATFORM=offscreen .venv/bin/python tools/ekran_goruntusu.py
.venv/bin/python tools/web_derle.py            # tek dosyalık tarayıcı sürümü
.venv/bin/python tools/web_parite.py           # tarayıcı motoru için beklenen değerler
node web/test/parite.mjs                       # tarayıcı motoru = Python motoru mu?
.venv/bin/pyinstaller --noconfirm --distpath ~/.venvs/optik-sinav-paket/dist --workpath ~/.venvs/optik-sinav-paket/build optik_sinav.spec
```

Yerel macOS derlemesinde imza `com.apple.provenance` öznitelikleri yüzünden düşer: `xattr -cr "<dist>/Optik Sinav.app" && codesign -s - --force --deep "<dist>/Optik Sinav.app"`.

## Yapılacaklar (açık konular)

- [ ] Sınav Akreditasyon soru bazlı giriş ekranının biçimi ve şablonu. Proje sahibi UTL4513 ara sınavı sistemde tanımlandıktan sonra ekran görüntüsünü ya da şablonu verecek; gerçek profil `profiles/` altına eklenecek, `taslak: false` yapılacak ve altın dosya testi yazılacak.
- [ ] Not Giriş ekranının toplu aktarım biçimi.
- [ ] Optik okuyucunun özgün dosya kodlaması: okuyucudan doğrudan alınmış kopya istenecek.
- [ ] Gerçek A/B kitapçıklı bir `.dat` ile kitapçık alanının konumu (UTL4513 formunda 35-36. sütunlar boş; kitapçık alanı olabilir).
- [ ] Karma sınav (optik + klasik bölüm).
- [ ] Komut satırı (`cli.py`) klasik sınavı ve kitapçığı henüz desteklemiyor.
- [ ] Bu liste geliştirici içindir; README'de yalnızca kullanıcıya dönük "Bilinen sınırlamalar" vardır, ikisi birlikte güncellenir.
- [x] GitHub Actions Intel macOS çalıştırıcısı (`macos-15-intel`) v1.0.0 sürümünde çalıştı (14 Kasım 2026).
