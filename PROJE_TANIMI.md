# Optik Sınav Değerlendirme: Proje Tanımı

> Depodaki bu kopyada gerçek öğrenci adı ve numaraları uydurma değerlerle değiştirilmiştir; gerçek beklenen değerler depo dışındaki `ornek_veri/kabul_beklenen.json` dosyasındadır.

Bu belge Claude Code için hazırlanmıştır. Projenin amacı, kapsamı, girdi dosyalarının çözülmüş biçimi, üniversite sistemi hakkında bilinenler, puanlama kuralları, çıktılar ve kabul testleri buradadır. Belgeyi proje kök dizinine `PROJE_TANIMI.md` olarak koy ve önemli kararları `CLAUDE.md` dosyasına özetle.

Proje sahibi: Dr. Öğr. Üyesi Ali Osman Öztop, Muğla Sıtkı Koçman Üniversitesi, Fethiye İşletme Fakültesi.

---

## 1. Amaç

Optik okuyucudan çıkan ham `.dat` dosyası programa yüklendiğinde, program:

1. Dosyayı okur, cevap anahtarına göre puanlar.
2. Her öğrenci için **soru bazında** doğru, yanlış ve boş bilgisini ve her sorudan alınan puanı hesaplar.
3. Okuma hatalarını ve tutarsızlıkları gösterir, düzeltmeye izin verir.
4. Muğla Sıtkı Koçman Üniversitesi Akademik Bilgi Sistemi'ndeki **Sınav Akreditasyon İşlemleri** ve **Not Giriş** ekranlarına **doğrudan girilebilecek** toplu aktarım dosyalarını üretir.
5. Madde analizi ve öğrenme çıktısı başarı raporu üretir.

Program öğretim elemanının kendi bilgisayarında, **çevrim dışı** çalışır. Öğrenci verisi hiçbir sunucuya gönderilmez.

## 2. Hedef platformlar ve dağıtım

- **macOS** (Apple Silicon ve Intel) ve **Windows 10/11**. İkisinde de simgeli, çift tıklayınca açılan bir uygulama olmalı.
- Kaynak kod **GitHub'da açık kaynak** olarak yayımlanacak.
- Teknoloji: **Python 3.11+ ve PySide6** (Qt). Paketleme: **PyInstaller**.
  - macOS: `.app` paketi ve bunu içeren `.dmg` ya da `.zip`, simge `.icns`.
  - Windows: tek klasörlü ya da tek dosyalı `.exe`, simge `.ico`. İsteğe bağlı olarak Inno Setup kurulum dosyası.
- **GitHub Actions** iş akışı: bir sürüm etiketi (`v*`) gönderildiğinde macOS ve Windows çalıştırıcılarında testleri koşsun, iki platform için paketleri üretsin ve GitHub Releases sayfasına eklesin.
- İmzasız uygulama uyarıları README'de anlatılsın:
  - macOS'ta uygulamaya sağ tıklayıp "Aç" demek gerekir.
  - Windows'ta SmartScreen uyarısında "Ek bilgi" ve ardından "Yine de çalıştır" seçilir.
- Platformlar arası kurallar:
  - Bütün dosya yolları `pathlib` ile kurulsun.
  - Metin dosyaları okunurken satır sonu (CRLF ve LF) ve kodlama (UTF-8, Windows-1254) otomatik algılansın.
  - Excel çıktıları her iki platformda Microsoft Excel ve LibreOffice ile açılabilsin.
  - Ayarlar kullanıcıya özel uygulama veri klasöründe saklansın (`QStandardPaths.AppDataLocation`).
- Arayüz dili Türkçe. Metinler ileride çeviri yapılabilecek şekilde tek bir yerde toplansın.
- Lisans: MIT. Proje sahibi farklı bir lisans isterse değiştirilir.

## 3. Kişisel verilerin korunması (zorunlu)

- Gerçek öğrenci verisi (ad, numara, cevap) **asla** depoya girmeyecek.
  - `ornek_veri/`, `*.dat`, `*.xlsx` ve çıktı klasörleri `.gitignore` içinde olsun. İstisna: `tests/fixtures/` altındaki uydurma dosyalar.
- Testler için gerçek dosyanın biçimini birebir taklit eden, **uydurma ad ve numaralı** örnek dosyalar üret ve `tests/fixtures/` altına koy.
- Program ağ erişimi yapmayacak. Güncelleme denetimi, telemetri ve çevrim içi yazı tipi gibi hiçbir şey olmayacak.
- README'de Kişisel Verilerin Korunması Kanunu açısından verinin yalnızca yerel bilgisayarda işlendiği belirtilsin.

## 4. Üniversite sistemi hakkında bilinenler

Sistem adresi `obs.mu.edu.tr`, uygulama adı "Akademik Bilgi Sistemi". Program bu siteye **bağlanmayacak**. Yalnızca sitenin kabul ettiği dosyaları üretecek.

### 4.1 Sınav İşlemleri menüsü

Sınav Tanımla, Not Giriş, Sınav Akreditasyon İşlemleri (menüde iki ayrı bağlantı), Danışman Not Girişi, Danışman Staj Not Girişi, Öğrenci Bazlı Not Giriş, Sınav Takvimi.

### 4.2 Sınav Akreditasyon İşlemleri

- Ders listesi şu sütunlarla gelir: şube, ders kodu, ders adı, teorik ve uygulama saati, kredi, Avrupa Kredi Transfer Sistemi kredisi, fakülte/program ve kontenjan (kayıtlı / üst sınır). Örneğin UTL4513 Yatırım Analizi, Fethiye İşletme Fakültesi, Uluslararası Ticaret ve Lojistik, 63 öğrenci.
- Bir derse tıklayınca o dersin sınav tanımları listelenir. Sütunlar: İşlem, Durum, Sınav Adı, Kısa Adı, Ders, Tarih, Etki Oranı (%).
  - İşlem sütunundaki simgeler: Değiştir, Sil, Sınav Kilitli, Sınav Öğrenci Listesi.
  - Durum değerleri: "İlan Edildi", "Sonuçlanmadı".
- Menüdeki ilk bağlantıda dönem seçimi ve "Akr. Bilgilerini Kopyala" düğmesi vardır. İkincisinde "Sınav Ekle" düğmesi vardır.
- "Sınav Ekle" formundaki alanlar:
  - Sınav Tipi: bu dönem yalnızca "Ara Sınav".
  - Sınav Şablon Adı: örneğin "Ara Sınav / Vize".
  - Sınav Adı ve kısa adı: örneğin "Yazılı" ya da "Klasik".
  - Tarih ve Saat.
  - Etki Oranı %: ara sınavlar toplamı en fazla 50 ya da 60, derse göre değişiyor.
  - Açıklama, İlan Durumu ("Dersi alan öğrenciler sınav tarihini görebilir") ve Derslikler.
- Not giriş dönemi (2026-2027 Güz): 14.09.2026 08:30 ile 21.12.2026 23:59 arası.
- "Sınav Öğrenci Listesi" penceresinde her öğrenci için şu bilgiler var: Öğrenci No (örneğin 10 haneli `9900000001`), Adı, Soyadı, Sınıf, Önceki Dönem Notu, Alış Tipi, Sınav Listesinde (Evet/Hayır).

### 4.3 Not Giriş

- Ders listesinde şu sütunlar var: TSS (tanımlı sınav sayısı), İSS, İESS ve TEO.
- "Sorulandırılmamış Dersleri Göster" seçeneği var. Bu, sistemin **soru bazlı not girişini** desteklediğini gösteriyor.

### 4.4 Henüz bilinmeyen: toplu aktarım biçimi (AÇIK KONU)

Proje sahibinin şartı, programın ürettiği dosyanın **sisteme doğrudan girilebilmesi**. Ancak soru bazlı puanların girildiği ekran ve toplu aktarım dosyasının biçimi (Excel şablonu, sütun sırası, öğrenci numarası biçimi, ondalık ayırıcı, sınava girmeyenlerin gösterimi) henüz görülemedi. Bunun nedenleri:

- UTL4513 için sistemde henüz sınav tanımlı değil.
- Sınav Tanımla ekranı Öğrenci İşleri tarafından geçici olarak kapatılmış.

Bu yüzden:

1. Dışa aktarma **profil tabanlı** olacak. Her hedef ekran için bir profil dosyası (`profiles/*.json`) tanımlansın. Profil şunları belirlesin:
   - Dosya türü (`xlsx`, `xls`, `csv`, `txt`).
   - Sayfa adı, başlık satırları ve veri başlangıç satırı.
   - Sütun sırası ve başlık metinleri.
   - Öğrenci numarası biçimi: metin mi sayı mı, baştaki sıfırlar korunacak mı.
   - Ondalık ayırıcı (`,` ya da `.`) ve ondalık basamak sayısı.
   - Sınava girmeyen öğrenci gösterimi: boş, `G`, `GR`, `-1` gibi.
   - Kodlama, ayraç ve satır sonu.
2. **Şablondan profil üretme:** Kullanıcı sistemden indirdiği boş şablonu programa gösterdiğinde, program başlıkları ve öğrenci satırlarını tanıyıp profili önersin. Kullanıcı onaylayınca kaydedilsin. Program, şablondaki öğrenci sırasını koruyarak puanları **şablonun içine** yazabilsin. En güvenli "doğrudan giriş" yolu budur.
3. Proje sahibi ekran görüntüsünü ya da şablonu getirdiğinde gerçek profiller eklenecek. O zamana kadar şu varsayılan profiller kullanılsın:
   - `akreditasyon_soru_bazli_varsayilan`: Öğrenci No, Ad Soyad, S1..Sn puanları.
   - `not_giris_varsayilan`: Öğrenci No, Ad Soyad, Puan.
4. **Kopyala-yapıştır modu:** Web ekranında tablo halinde giriş varsa, program seçili sütunları sistemdeki öğrenci sırasıyla panoya sekmeyle ayrılmış biçimde kopyalasın.
5. Bu açık konu README'de ve `CLAUDE.md` dosyasında "yapılacaklar" olarak dursun.

## 5. Girdi 1: optik okuyucu `.dat` dosyası

Örnek: `ornek_veri/YATIRIM_61.dat`. Gerçek dosyadır, depoya girmez.

### 5.1 Çözülmüş biçim

- Sabit genişlikli düz metin, CRLF satır sonu, her öğrenci bir satır. Bu dosyada 61 satır var, her satır 136 karakter.
- **Başlık satırı yok. Cevap anahtarı dosyada yok. Kitapçık türü alanı yok.**
- Alanlar (karakter konumu 1'den sayılır):

| Konum | Uzunluk | Alan | Not |
|---|---|---|---|
| 1-25 | 25 | Ad Soyad | Sağdan boşlukla doldurulmuş. Türkçe harfler bozuk gelebilir. |
| 26-34 | 9 | Öğrenci No | Bu dosyada 9 hane, örneğin `990000001` |
| 35-36 | 2 | (boş) | |
| 37-51 | 15 | Cevaplar | Bu sınavda 15 soru. `A`-`E` şık, boşluk boş, `*` çift işaret |
| 52-136 | 85 | Kullanılmayan alan | Normalde boş. Doluysa "soru alanı dışında işaret" |

- Örnek satırlar (ad ve numara uydurmadır, biçim gerçektir):

```
AYSE YILMAZ              234700001  ACD BDACEB CEA
MEHMET DEMIR             234700002  CEBDA*ABDEACBED
```

### 5.2 Gözlenen sorunlar ve beklenen davranış

- **Bozuk Türkçe karakterler:** Dosya UTF-8 olarak okunduğunda Türkçe harflerin yerinde `U+FFFD` (�) var, örneğin `AY�E G�NE�` (uydurma örnek). Bozulma muhtemelen dosya aktarılırken oluşmuş. Okuyucunun asıl çıktısı büyük olasılıkla Windows-1254'tür.
  - Okuma sırası: önce katı UTF-8, olmazsa Windows-1254, olmazsa Latin-1.
  - Ad alanı **asıl kaynak sayılmaz**. Eşleştirme öğrenci numarasıyla yapılır, doğru ad öğrenci listesinden alınır.
- **Alan dışı işaret:** Bir satırda 67. karakterde fazladan `A` var. Program "Soru alanı dışında işaret var" uyarısı vermeli.
- **Kısa satır:** Bazı satırlar cevap alanının sonunda kesik ya da boş olabilir. Eksik kısım boş cevap sayılmalı.
- **Okunamayan rakam ya da harf:** Öğrenci numarasında ya da adda `*` gibi karakterler olabilir. Program bunu uyarıyla göstermeli.
- **Ad soyad boş** olabilir.

### 5.3 Esneklik

- Alan konumları ve soru sayısı bir **okuyucu şablonunda** (`readers/*.json`) tanımlansın. Varsayılan şablon yukarıdaki düzendir.
- İlk yüklemede program soru sayısını kendisi önersin: cevap alanında harf görülen en son sütuna bakarak.
- Kullanıcı arayüzden şunları değiştirebilsin: ad başlangıcı ve uzunluğu, numara başlangıcı ve uzunluğu, cevap başlangıcı, soru sayısı, kitapçık alanı (varsa).
- Dosyanın ilk birkaç satırı, alan sınırları renkli gösterilerek önizlenebilsin.

## 6. Girdi 2: öğrenci listesi

Doğru yazılmış adlar ve sınava girmesi gereken öğrenciler buradan alınır.

- Kabul edilen kaynaklar:
  - Akademik Bilgi Sistemi'nden indirilen Excel listesi.
  - Mevcut optik okuma yazılımının Excel çıktısı.
  - Akreditasyon şablonunun kendisi (bkz. 4.4).
- Örnek dosya: `ornek_veri/YATIRIM61.xlsx`. Bu, eski okuma programının çıktısıdır.
  - Sayfa adı `ktt`. 1. satırda `J1` hücresinde `AWRG` yazıyor.
  - 2. satır başlıklar: `Sınıf`, (boş), `Öğr.No`, `Adı Soyadı`, `Telefon`, `TEORİK`, `Pratik`, `PDÖ`, `TOPLAM`, `1D`, `1Y`, `1N`, `1puan`.
  - Veri 3. satırdan başlıyor, 61 öğrenci. `Öğr.No` sayı olarak tutulmuş. Adların sonunda boşluklar var. Türkçe harfler doğru.
  - `1D` doğru sayısı, `1Y` yanlış sayısı, `1N` net, `1puan` ve `TOPLAM` puan.
  - **Bu dosyada soru bazında bilgi yok.** Yeni programın varlık nedeni budur.
- Sütun eşlemesi (hangi sütun numara, hangisi ad) program tarafından tahmin edilsin, kullanıcı değiştirebilsin.
- Numaralar karşılaştırılırken boşluk temizlensin ve metin olarak karşılaştırılsın.
- Uzunluk farkı olabilir: optik dosyada 9 hane (`990000001`), sistemde 10 hane (`9900000001`) görülebilir. Birebir eşleşmeyenler için öneri sunulsun, otomatik eşleştirme yapılmasın.
- Ders kontenjanı 63, sınava giren 61. Listede olup dosyada olmayan öğrenciler "Sınava girmedi" olarak gösterilsin.

## 7. Girdi 3: cevap anahtarı ve sınav bilgileri

- Sınav bilgileri: ders kodu, ders adı, sınav türü (Ara Sınav, Yarıyıl Sonu, Bütünleme, Mazeret), tarih, saat, etki oranı.
- Cevap anahtarı iki yolla girilebilsin:
  - Hızlı giriş satırı: harfler sırayla yazılır, boşluklar yok sayılır, `-` soruyu atlar.
  - Tıklanabilir tablo: her soru için A-E düğmeleri.
- Her sorunun durumu seçilebilsin:
  - **Normal.**
  - **İptal:** herkese tam puan.
  - **Birden fazla doğru:** birden çok şık doğru kabul edilir.
- **Kitapçık:** Şimdilik tek test grubu varsayılıyor. Veri yapısı ileride A/B kitapçığı ve "B kitapçığının k. sorusu = A kitapçığının m. sorusu" eşlemesi eklenebilecek şekilde kurulsun. Tüm çıktılar ana kitapçığın soru numaralarıyla verilir.
- **Soru ile öğrenme çıktısı eşlemesi:**
  - Her soru bir ya da birden fazla öğrenme çıktısı ile program çıktısı numarasına bağlanabilsin.
  - Ders bazında kaydedilsin ve sonraki sınavlarda tekrar kullanılabilsin.
- Sınav ayarları tek bir proje dosyasında saklansın (`.osd` uzantılı JSON). Bu dosya cevap anahtarını, ayarları, düzeltmeleri ve kaynak dosya yollarını içerir. Kullanıcı daha sonra açıp devam edebilsin.

## 8. Puanlama kuralları

- **Eşit puan:**
  - Soru puanı = toplam puan / soru sayısı. İptal edilen sorular da sayıya dahildir, çünkü herkese verilir.
  - **Yuvarlama yalnızca en sonda yapılır.** Eski program soru başına 6,67 puan verdiği için 15 doğru 100,05 ederdi. Yeni programda 15 doğru tam 100 olmalı.
  - Varsayılan: öğrenci puanı iki ondalık basamakla gösterilsin, not girişi profiline göre tam sayıya yuvarlanabilsin. Yuvarlama yöntemi ayarlanabilsin: yarım yukarı, aşağı ya da yukarı.
- **Soru bazlı puan:** Her sorunun puanı ayrı girilir, toplamın 100 olduğu denetlenir.
- **Yanlışlar doğruyu götürsün** (varsayılan kapalı):
  - Oran ayarlanabilir, örneğin 4 yanlış 1 doğruyu götürür.
  - Net = doğru - yanlış / oran. Puan sıfırın altına düşmez.
  - Soru bazlı çıktılarda bu ceza ayrıca gösterilir, soru puanlarına dağıtılmaz. Akreditasyon için soru bazında ham puan kullanılır.
- **Çift işaret (`*`):** Varsayılan olarak boş sayılır. Ayarla yanlış da sayılabilsin.
  - Not: eski program çift işareti yanlış saymış. Ceza yoksa puan değişmez, ama yanlış ve boş sayıları farklı çıkar.
- **Sınava girmeyen:** Puan hesaplanmaz, çıktılarda profilde tanımlı "girmedi" gösterimi kullanılır.

## 9. Arayüz

Adım adım ilerleyen tek pencere. Sol tarafta adımlar, sağda içerik.

1. **Sınav ve dosyalar:** sınav bilgileri, `.dat` dosyası seçme ya da sürükle-bırak, öğrenci listesi seçme, okuyucu şablonu önizlemesi.
2. **Cevap anahtarı:** hızlı giriş, soru tablosu, soru durumları, öğrenme çıktısı eşlemesi.
3. **Puanlama:** eşit ya da soru bazlı puan, yanlış cezası, çift işaret kuralı, yuvarlama.
4. **Kontrol ve düzeltme:**
   - Renkli tablo: doğru yeşil, yanlış kırmızı, boş sarı, iptal gri.
   - Sütunlar: Sıra, Öğrenci No, Ad Soyad, soru sütunları, Doğru, Yanlış, Boş, Puan, Uyarı.
   - Uyarılı satırlar turuncu ile vurgulansın. "Yalnızca uyarılıları göster" süzgeci olsun.
   - Hücreye çift tıklayınca numara, ad ya da tek bir cevap düzeltilebilsin.
   - Özgün okuma hiçbir zaman silinmesin. Düzeltmeler "kim, ne zaman, eski değer, yeni değer" olarak kaydedilsin.
   - Ayrı sekmeler: "Sınava girmeyenler" ve "Listede olmayanlar".
5. **Dışa aktar:**
   - Profil seçimi ve önizleme.
   - "Sistem şablonunu doldur" düğmesi.
   - Panoya kopyalama.
   - Tüm raporları tek seferde bir klasöre yazma.

Genel arayüz kuralları:

- Görünüm sade olsun: düz renkler, gereksiz süs yok. Açık ve koyu tema işletim sistemine uysun.
- Klavye ile tam kullanım: Tab ile geçiş, Enter ile onay.
- Her adımda "Sonraki" düğmesi ancak zorunlu bilgiler tamamsa etkin olsun. Eksik bilginin ne olduğu yazılsın.
- Son açılan sınavlar listesi olsun.

## 10. Çıktılar

Excel çıktıları `openpyxl` ile yazılsın, Türkçe karakterler doğru görünsün. Dosya adında ders kodu, sınav türü ve tarih bulunsun, örneğin `UTL4513_AraSinav_2026-11-10_sonuc.xlsx`.

1. **Sonuç dosyası** (renkli, süzgeçli, ilk satır sabit):
   - Sayfa "Sonuç": Sıra, Öğrenci No, Ad Soyad, 1..n soru puanı, Doğru, Yanlış, Boş, Puan, Uyarı.
   - Sayfa "Cevaplar": öğrencinin işaretlediği şıklar.
   - Sayfa "Uyarılar".
   - Sayfa "Düzeltme Kaydı".
   - Sayfa "Anahtar ve Ayarlar".
2. **Akreditasyon aktarım dosyası:** soru bazlı puanlar, seçili profile göre (bkz. 4.4). Sistem şablonu verildiyse şablonun kendisi doldurulur.
3. **Not girişi aktarım dosyası:** öğrenci no ve puan, seçili profile göre.
4. **Madde analizi:**
   - Her soru için güçlük indeksi (doğru oranı).
   - Ayırt edicilik indeksi: puana göre sıralanmış öğrencilerin üst %27 ve alt %27 gruplarının doğru oranları farkı.
   - Nokta çift serili korelasyon.
   - Her şıkkın seçilme oranı ve boş oranı.
   - Sorunlu soru işareti, eşikleri ayarlanabilir. Varsayılan: ayırt edicilik 0,20'nin altında, güçlük 0,20'nin altında ya da 0,90'ın üstünde, ya da yanlış bir şık doğru şıktan çok seçilmiş.
   - Sınav geneli: ortalama, standart sapma, en düşük, en yüksek, medyan, KR-20 güvenirlik katsayısı.
5. **Öğrenme çıktısı raporu:** eşleme girilmişse her öğrenme çıktısı ve program çıktısı için sınıf başarı yüzdesi ve öğrenci bazında başarı.
6. **PDF özet** (isteğe bağlı): sınav bilgileri, dağılım grafiği, madde analizi tablosu. Arşiv ve bölüm dosyası için.

## 11. Mimari

```
optik-sinav/
  src/optik_sinav/
    io/        dat_okuyucu.py, liste_okuyucu.py, kodlama.py
    core/      modeller.py (dataclass), puanlama.py, dogrulama.py, madde_analizi.py, ciktilar.py
    export/    profil.py, xlsx_yazici.py, csv_yazici.py, sablon_doldurucu.py, pano.py
    ui/        ana_pencere.py, adimlar/*.py, tablolar.py, tema.py
    metinler.py
    __main__.py
  profiles/    not_giris_varsayilan.json, akreditasyon_soru_bazli_varsayilan.json
  readers/     varsayilan_136.json
  assets/      simge.svg, simge.icns, simge.ico
  tests/       fixtures/ (uydurma veri), test_*.py
  .github/workflows/  test.yml, release.yml
  pyproject.toml, README.md, LICENSE, CLAUDE.md, PROJE_TANIMI.md
```

- **Puanlama motoru arayüzden tamamen bağımsız** olacak ve saf fonksiyonlardan oluşacak. Tüm iş kuralları burada, testler burada.
- Arayüz olmadan çalışan bir komut satırı girişi de olsun. Örnek: `python -m optik_sinav puanla --dat x.dat --anahtar BEDAC... --liste y.xlsx --cikti klasor/`. Hem test hem toplu işlem için.
- Bağımlılıklar az tutulsun: `PySide6`, `openpyxl`, `xlrd` (eski `.xls` okuma için), `pytest`. Grafik için gerekirse `matplotlib`.
- Simge: sade bir optik form ve onay işareti, SVG'den `.icns` ve `.ico` üretilsin.

## 12. Kabul testleri

Gerçek dosyalarla (yerel, depoya girmez):

1. `YATIRIM_61.dat` okunduğunda 61 öğrenci, 15 soru bulunmalı.
2. Cevap anahtarı `BEDACDEDBCBEAAC`. Bu anahtar iki dosya karşılaştırılarak çıkarıldı; proje sahibi sınav kâğıdıyla doğrulayacak.
3. Çift işaret yanlış sayılarak çalıştırıldığında her öğrencinin doğru ve yanlış sayıları `YATIRIM61.xlsx` dosyasındaki `1D` ve `1Y` sütunlarıyla **61 öğrencinin hepsinde** tutmalı. Varsayılan ayarda (çift işaret boş) tek fark çift işaretli tek öğrencide (numarası `kabul_beklenen.json` içinde) olmalı: yanlış 7, boş 1.
4. Puanlar `1puan` sütunuyla en fazla 0,05 fark etmeli. Fark, eski programın 6,67 yuvarlamasından gelir. 14 doğru yeni programda 93,33 olmalı, eskide 93,38.
5. Satırında 67. karakterde işaret bulunan öğrenci için (numarası `kabul_beklenen.json` içinde) "Soru alanı dışında işaret var" uyarısı çıkmalı.
6. Öğrenci listesi olarak 63 kişilik ders listesi verildiğinde 2 öğrenci "Sınava girmedi" görünmeli.
7. Bozuk karakterli adlar, listeden gelen doğru adlarla değiştirilmeli.

Uydurma verilerle (`tests/fixtures/`, depoda):

- Her uyarı türü için en az bir satır:
  - numarada `*`
  - boş ad
  - kısa satır
  - alan dışı işaret
  - listede olmayan numara
  - aynı numara iki kez
  - CRLF ve LF
  - Windows-1254 ve UTF-8 kodlama
- İptal soru, birden fazla doğru, yanlış cezası, sıfırın altına düşmeme ve soru bazlı puan senaryoları.
- Dışa aktarma profillerinin bayt bayt beklenen çıktıyı ürettiği altın dosya testleri.
- GitHub Actions'ta testler hem `macos-latest` hem `windows-latest` üzerinde koşsun.

## 13. Çalışma sırası

1. `ornek_veri/` içindeki iki dosyayı incele, bu belgedeki biçimi doğrula, farklılık varsa sor.
2. Proje iskeleti, `pyproject.toml`, `.gitignore`, uydurma test verileri.
3. `.dat` okuyucu ve öğrenci listesi okuyucu, testleriyle.
4. Puanlama motoru ve doğrulama, testleriyle. Gerçek dosyalarla kabul testlerini (bölüm 12) geçir.
5. Çıktılar ve dışa aktarma profilleri, şablon doldurma.
6. Madde analizi ve öğrenme çıktısı raporu.
7. Arayüz.
8. Simge, PyInstaller yapılandırması, macOS ve Windows paketleri, GitHub Actions.
9. README: kurulum, kullanım (ekran görüntüleriyle), imzasız uygulama uyarıları, veri gizliliği, sistem şablonundan profil oluşturma.

Her adımın sonunda testler geçmeli. Arayüzden önce motorun komut satırından doğru sonuç verdiği gösterilmeli.

## 14. Açık konular

- [ ] Akreditasyon soru bazlı giriş ekranının biçimi ve şablonu (bölüm 4.4). Proje sahibi, UTL4513 ara sınavı sistemde tanımlandıktan sonra ekran görüntüsünü ya da şablonu verecek.
- [ ] Not Giriş ekranının toplu aktarım biçimi.
- [ ] Optik okuyucunun özgün dosya kodlaması: dosyanın okuyucudan doğrudan alınmış bir kopyası istenecek.
- [ ] A/B kitapçık desteği ve soru eşlemesi (sonraki sürüm).
- [ ] UTL4513 öğrenme çıktıları listesi: ders bilgi paketinden alınacak.

## 15. İlk gerçek kullanım

- Ders: UTL4513 Yatırım Analizi, Fethiye İşletme Fakültesi, Uluslararası Ticaret ve Lojistik.
- Dönem ve sınav: 2026-2027 Güz, Ara Sınav, 10.11.2026 saat 15:00.
- Optik dosya: `YATIRIM_61.dat` (61 öğrenci, 15 soru, tek kitapçık).
- Eski programın çıktısı: `YATIRIM61.xlsx`.
