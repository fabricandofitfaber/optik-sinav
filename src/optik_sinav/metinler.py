"""Kullanıcıya görünen bütün metinler. İleride çeviri için tek yerde toplanmıştır."""

UYGULAMA_ADI = "Optik Sınav Değerlendirme"
KURULUS = "OptikSinav"

UYARI = {
    "kisa_satir": "Kısa satır ({uzunluk} karakter): son {eksik} cevap boş sayıldı",
    "numara_bos": "Öğrenci numarası boş",
    "numara_okunamadi": "Öğrenci numarasında okunamayan karakter: {no}",
    "ad_bos": "Ad soyad boş",
    "ad_okunamadi": "Ad soyadda okunamayan karakter: {ad}",
    "ad_bozuk_karakter": "Ad soyadda bozuk Türkçe karakter var; doğru ad öğrenci listesinden alınmalı",
    "cevapta_gecersiz": "Cevap alanında geçersiz işaret (boş sayıldı), soru: {sorular}",
    "cift_isaret": "Çift işaret, soru: {sorular}",
    "tekrar_numara": "Aynı numara başka satırda da var (satır {satirlar})",
    "alan_disi_isaret": "Soru alanı dışında işaret var (konum {konumlar})",
    "listede_yok": "Numara öğrenci listesinde yok",
    "listede_yok_oneri": "Numara öğrenci listesinde yok. Olası numaralar: {oneriler}",
    "otomatik_numara": "Okunan numara {eski} listede yok; okunan ad ({okunan}) listedeki {ad} ile eşleştiği için numara {yeni} yapıldı. Yanlışsa geri alın.",
    "otomatik_numara_baskasi": "Okunan numara {eski} listede başka öğrenciye ({sahibi}) ait; okunan ad ({okunan}) listedeki {ad} ile eşleştiği için numara {yeni} yapıldı. Yanlışsa geri alın.",
    "ad_uyusmuyor": "Okunan ad ({okunan}) listede bu numaradaki öğrenciyle ({ad}) uyuşmuyor: öğrenci başkasının numarasını kodlamış olabilir.",
    "kitapcik_okunamadi": "Kitapçık türü okunamadı: {k!r}",
    "kitapcik_bilinmiyor": "Anahtarı girilmemiş kitapçık {k!r}; {ana} kitapçığı sayıldı",
    "klasik_fazla": "{soru}. soruda girilen puan ({puan}) sorunun puanından ({en_fazla}) büyük",
    "klasik_eksi": "{soru}. soruda eksi puan girilmiş",
    "klasik_eksik": "Puanı girilmemiş soru: {sorular} (sıfır sayıldı)",
    "klasik_toplam": "Kâğıttaki toplam ({kagit}) soru puanlarının toplamıyla ({hesap}) tutmuyor",
}

DURUM_ADI = {"D": "Doğru", "Y": "Yanlış", "B": "Boş", "I": "İptal", "-": "Anahtarsız", "K": "Kısmi puan"}
SORU_DURUMU_ADI = {"normal": "Normal", "iptal": "İptal (herkese tam puan)", "coklu": "Birden fazla doğru",
                   "bonus": "Bonus (bir yanlışı siler)"}
CIFT_ISARET_ADI = {"bos": "Boş say", "yanlis": "Yanlış say"}
YUVARLAMA_ADI = {"yarim_yukari": "Yarım yukarı", "asagi": "Aşağı", "yukari": "Yukarı"}
YONTEM_ADI = {"esit": "Eşit puan", "soru_bazli": "Soru bazlı puan"}

ADIM_KLASIK_2 = "2. Sorular ve puanlar"
# Sade düzen (17 Kasım 2026): zorunlu dört adım ve isteğe bağlı istatistikler. Puanlama ayarları 2. adımda katlanır bölümdedir.
ADIMLAR = [
    "1. Sınav ve dosyalar",
    "2. Cevap anahtarı",
    "3. Kontrol ve düzeltme",
    "4. Sisteme aktar ve raporlar",
    "5. İstatistikler (isteğe bağlı)",
]
ADIM_KLASIK_3 = "3. Puan girişi"
PUANLAMA_AYARLARI = "Puanlama ayarları"

EKSIK = {
    "dat": "Optik okuyucu dosyası seçilmedi.",
    "ders_kodu": "Ders kodu girilmedi.",
    "soru_sayisi": "Soru sayısı sıfır.",
    "anahtar": "Anahtarı girilmemiş sorular var: {sorular}",
    "soru_puan_toplam": "Soru puanlarının toplamı {toplam}, olması gereken {beklenen}.",
    "soru_puan_eksik": "Puanı girilmemiş sorular var: {sorular}",
    "coklu_tek": "'Birden fazla doğru' seçilen sorularda en az iki şık işaretlenmeli: {sorular}",
}

SUTUN = {
    "sira": "Sıra",
    "no": "Öğrenci No",
    "ad": "Ad Soyad",
    "dogru": "Doğru",
    "yanlis": "Yanlış",
    "bos": "Boş",
    "ham_puan": "Ham Puan",
    "ceza": "Yanlış Cezası",
    "puan": "Puan",
    "uyari": "Uyarı",
}

GIRMEDI = "Sınava girmedi"
