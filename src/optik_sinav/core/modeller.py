"""Veri yapıları. Arayüzden bağımsızdır; yalnızca standart kitaplık kullanır.

Puanlar `fractions.Fraction` ile tam olarak tutulur, yuvarlama yalnızca en sonda yapılır.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from typing import Any

SIKLAR = "ABCDE"
CIFT_ISARET = "*"
BOS = " "


# ---------------------------------------------------------------- okuyucu şablonu
@dataclass
class OkuyucuSablonu:
    """Sabit genişlikli optik dosyanın alan konumları. Konumlar 1'den sayılır."""

    ad: str = "varsayilan_136"
    aciklama: str = ""
    ad_baslangic: int = 1
    ad_uzunluk: int = 25
    no_baslangic: int = 26
    no_uzunluk: int = 9
    cevap_baslangic: int = 37
    soru_sayisi: int = 15
    kitapcik_baslangic: int | None = None
    kitapcik_uzunluk: int = 1
    satir_uzunlugu: int = 136

    @property
    def cevap_bitis(self) -> int:
        """Cevap alanının son karakterinin konumu (1'den sayılır, dahil)."""
        return self.cevap_baslangic + self.soru_sayisi - 1

    def alanlar(self) -> list[tuple[str, int, int]]:
        """(alan adı, başlangıç, uzunluk) listesi; önizleme renklendirmesi için."""
        a = [
            ("ad", self.ad_baslangic, self.ad_uzunluk),
            ("no", self.no_baslangic, self.no_uzunluk),
            ("cevap", self.cevap_baslangic, self.soru_sayisi),
        ]
        if self.kitapcik_baslangic:
            a.append(("kitapcik", self.kitapcik_baslangic, self.kitapcik_uzunluk))
        return a

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "OkuyucuSablonu":
        bilinen = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**bilinen)


# ---------------------------------------------------------------- uyarılar
class UyariTuru(str, Enum):
    NUMARA_OKUNAMADI = "numara_okunamadi"
    NUMARA_BOS = "numara_bos"
    AD_OKUNAMADI = "ad_okunamadi"
    AD_BOS = "ad_bos"
    AD_BOZUK_KARAKTER = "ad_bozuk_karakter"
    KISA_SATIR = "kisa_satir"
    ALAN_DISI_ISARET = "alan_disi_isaret"
    CEVAPTA_GECERSIZ = "cevapta_gecersiz"
    CIFT_ISARET = "cift_isaret"
    TEKRAR_NUMARA = "tekrar_numara"
    LISTEDE_YOK = "listede_yok"
    KITAPCIK_OKUNAMADI = "kitapcik_okunamadi"


@dataclass
class Uyari:
    tur: UyariTuru
    mesaj: str
    satir_no: int | None = None  # .dat dosyasındaki satır (1'den)
    ayrinti: Any = None

    def to_dict(self) -> dict:
        return {"tur": self.tur.value, "mesaj": self.mesaj, "satir_no": self.satir_no}


# ---------------------------------------------------------------- ham okuma
@dataclass
class HamKayit:
    """Optik dosyadaki bir satırın özgün okuması. Hiçbir zaman değiştirilmez."""

    satir_no: int
    ham_satir: str
    ad: str
    ogrenci_no: str
    cevaplar: list[str]  # her soru için tek karakter: A-E, " " boş, "*" çift işaret, başka karakter geçersiz
    kitapcik: str = ""
    uyarilar: list[Uyari] = field(default_factory=list)


@dataclass
class DatOkumaSonucu:
    kayitlar: list[HamKayit]
    kodlama: str
    satir_sonu: str  # "CRLF", "LF", "CR" ya da "karışık"
    sablon: OkuyucuSablonu
    bos_satir_sayisi: int = 0


# ---------------------------------------------------------------- öğrenci listesi
@dataclass
class Ogrenci:
    no: str
    ad: str
    kaynak_satir: int | None = None  # listedeki satır (1'den)


@dataclass
class ListeEslemesi:
    sayfa: str | None = None
    baslik_satiri: int | None = None  # 1'den
    no_sutun: int | None = None  # 1'den
    ad_sutun: int | None = None
    soyad_sutun: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict | None) -> "ListeEslemesi":
        d = d or {}
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class OgrenciListesi:
    ogrenciler: list[Ogrenci]
    esleme: ListeEslemesi
    basliklar: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- cevap anahtarı
class SoruDurumu(str, Enum):
    NORMAL = "normal"
    IPTAL = "iptal"
    COKLU = "coklu"  # birden fazla doğru şık
    BONUS = "bonus"  # doğru cevaplanırsa öğrencinin bir yanlışını (yoksa bir boşunu) doğru sayar; kendisi puana ve aktarıma girmez


@dataclass
class Soru:
    no: int  # ana kitapçıktaki soru numarası (1'den)
    dogru: str = ""  # doğru şık(lar); çoklu durumda örneğin "AC"
    durum: SoruDurumu = SoruDurumu.NORMAL
    puan: str | None = None  # soru bazlı puanda bu sorunun puanı, ondalık metin ("6.5")
    ogrenme_ciktilari: list[str] = field(default_factory=list)
    program_ciktilari: list[str] = field(default_factory=list)
    # Öğrenme çıktısı kodu -> yüzde (tam sayı). Boşsa çıktılar arasında eşit (toplam 100) dağıtılır.
    cikti_yuzdeleri: dict[str, int] = field(default_factory=dict)

    def dogru_kume(self) -> set[str]:
        return {c for c in self.dogru.upper() if c in SIKLAR}

    def cikti_dagilimi(self) -> dict[str, int]:
        """Sorunun öğrenme çıktılarına yüzde dağılımı. Girilmemişse eşit dağıtılır, toplam tam 100 olur."""
        kodlar = [k for k in self.ogrenme_ciktilari if k]
        if not kodlar or self.durum == SoruDurumu.BONUS:  # bonus soru öğrenme çıktısına sayılmaz
            return {}
        if self.cikti_yuzdeleri and set(self.cikti_yuzdeleri) == set(kodlar):
            return {k: int(self.cikti_yuzdeleri[k]) for k in kodlar}
        return dict(zip(kodlar, esit_yuzdeler(len(kodlar))))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["durum"] = self.durum.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Soru":
        d = dict(d)
        d["durum"] = SoruDurumu(d.get("durum", "normal"))
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class CevapAnahtari:
    sorular: list[Soru] = field(default_factory=list)
    # Kitapçık eşlemesi: {"B": {B kitapçığındaki soru no: ana kitapçıktaki soru no}}. Boşsa sıra aynıdır.
    kitapcik_eslemesi: dict[str, dict[int, int]] = field(default_factory=dict)
    ana_kitapcik: str = "A"
    # Diğer kitapçıkların cevap anahtarı, o kitapçığın kendi soru sırasıyla: {"B": "CADBE..."}
    kitapcik_anahtarlari: dict[str, str] = field(default_factory=dict)

    def aktarim_sorulari(self) -> list[int]:
        """Akademik Bilgi Sistemi'ne giden sorular (0'dan sıra): bonus sorular hariç. Aktarımda 1'den yeniden numaralanır."""
        return [i for i, s in enumerate(self.sorular) if s.durum != SoruDurumu.BONUS]

    def kitapciklar(self) -> list[str]:
        return [self.ana_kitapcik] + sorted(k for k in self.kitapcik_anahtarlari if k != self.ana_kitapcik)

    def esleme(self, kitapcik: str) -> dict[int, int]:
        """Kitapçık soru no -> ana kitapçık soru no. Tanımsız sorular aynı numaraya eşlenir."""
        n = self.soru_sayisi
        e = {k: k for k in range(1, n + 1)}
        e.update({a: b for a, b in self.kitapcik_eslemesi.get(kitapcik, {}).items() if 1 <= a <= n and 1 <= b <= n})
        return e

    def esleme_sorunlari(self, kitapcik: str) -> list[str]:
        e = self.esleme(kitapcik)
        hedefler = list(e.values())
        tekrar = sorted({h for h in hedefler if hedefler.count(h) > 1})
        return [f"{kitapcik} kitapçığında ana kitapçığın {', '.join(map(str, tekrar))}. sorusuna birden fazla soru eşlenmiş."] if tekrar else []

    def kitapcik_icin(self, kitapcik: str) -> tuple["CevapAnahtari", dict[int, int]]:
        """Kitapçığın anahtarını ana kitapçık sırasına çevirir.

        Döndürür: (ana sıradaki anahtar kopyası, ana soru no -> kitapçık soru no).
        Soru durumu, puanı ve çıktıları ana kitapçıktan gelir; doğru şık kitapçığın kendi anahtarından.
        """
        if kitapcik in ("", self.ana_kitapcik) or kitapcik not in self.kitapcik_anahtarlari:
            return self, {k: k for k in range(1, self.soru_sayisi + 1)}
        harfler = [c for c in self.kitapcik_anahtarlari[kitapcik].upper() if not c.isspace()]
        ters = {b: a for a, b in self.esleme(kitapcik).items()}
        yeni = []
        for s in self.sorular:
            k = ters.get(s.no, s.no)
            harf = harfler[k - 1] if k - 1 < len(harfler) else ""
            kopya = Soru.from_dict(s.to_dict())
            if s.durum != SoruDurumu.COKLU:
                kopya.dogru = harf if harf in SIKLAR else ""
            else:
                kopya.dogru = "".join(c for c in harf if c in SIKLAR) or ""
            yeni.append(kopya)
        return CevapAnahtari(sorular=yeni, ana_kitapcik=self.ana_kitapcik), {a: k for a, k in ((s.no, ters.get(s.no, s.no)) for s in self.sorular)}

    @property
    def soru_sayisi(self) -> int:
        return len(self.sorular)

    @classmethod
    def metinden(cls, metin: str, soru_sayisi: int | None = None) -> "CevapAnahtari":
        """Hızlı giriş: harfler sırayla, boşluklar yok sayılır, '-' soruyu atlar (anahtarsız bırakır)."""
        harfler = [c for c in metin.upper() if not c.isspace()]
        sorular = []
        for i, c in enumerate(harfler, start=1):
            if c == "-":
                sorular.append(Soru(no=i, dogru=""))
            elif c in SIKLAR:
                sorular.append(Soru(no=i, dogru=c))
            else:
                raise ValueError(f"Cevap anahtarında geçersiz karakter: {c!r} ({i}. soru)")
        if soru_sayisi is not None:
            while len(sorular) < soru_sayisi:
                sorular.append(Soru(no=len(sorular) + 1))
            sorular = sorular[:soru_sayisi]
        return cls(sorular=sorular)

    def metne(self) -> str:
        return "".join((s.dogru[:1] if s.dogru else "-") for s in self.sorular)

    def to_dict(self) -> dict:
        return {
            "sorular": [s.to_dict() for s in self.sorular],
            "kitapcik_eslemesi": {k: {str(a): b for a, b in v.items()} for k, v in self.kitapcik_eslemesi.items()},
            "ana_kitapcik": self.ana_kitapcik,
            "kitapcik_anahtarlari": dict(self.kitapcik_anahtarlari),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CevapAnahtari":
        return cls(
            sorular=[Soru.from_dict(s) for s in d.get("sorular", [])],
            kitapcik_eslemesi={k: {int(a): int(b) for a, b in v.items()} for k, v in d.get("kitapcik_eslemesi", {}).items()},
            ana_kitapcik=d.get("ana_kitapcik", "A"),
            kitapcik_anahtarlari=dict(d.get("kitapcik_anahtarlari", {})),
        )


# ---------------------------------------------------------------- ayarlar
class PuanYontemi(str, Enum):
    ESIT = "esit"
    SORU_BAZLI = "soru_bazli"


class CiftIsaretKurali(str, Enum):
    BOS = "bos"
    YANLIS = "yanlis"


class Yuvarlama(str, Enum):
    YARIM_YUKARI = "yarim_yukari"
    ASAGI = "asagi"
    YUKARI = "yukari"


@dataclass
class PuanlamaAyarlari:
    toplam_puan: str = "100"
    yontem: PuanYontemi = PuanYontemi.ESIT
    yanlis_cezasi: bool = False
    ceza_orani: int = 4  # bu kadar yanlış bir doğruyu götürür
    cift_isaret: CiftIsaretKurali = CiftIsaretKurali.BOS
    yuvarlama: Yuvarlama = Yuvarlama.YARIM_YUKARI
    ondalik: int = 2
    basari_esigi: int = 50  # istatistiklerde "başarılı" sayılan en düşük puan ve öğrenme çıktısına "ulaştı" eşiği (%)
    gecme_ortalamasi: int = 50  # "finalde gereken puan" hesabı: dersi geçmek için gereken dönem sonu ortalaması
    final_alt_siniri: int = 50  # "finalde gereken puan" hesabı: finalden alınması gereken en düşük puan

    def to_dict(self) -> dict:
        return {
            "basari_esigi": self.basari_esigi,
            "gecme_ortalamasi": self.gecme_ortalamasi,
            "final_alt_siniri": self.final_alt_siniri,
            "toplam_puan": self.toplam_puan,
            "yontem": self.yontem.value,
            "yanlis_cezasi": self.yanlis_cezasi,
            "ceza_orani": self.ceza_orani,
            "cift_isaret": self.cift_isaret.value,
            "yuvarlama": self.yuvarlama.value,
            "ondalik": self.ondalik,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "PuanlamaAyarlari":
        d = d or {}
        a = cls()
        a.toplam_puan = str(d.get("toplam_puan", a.toplam_puan))
        a.yontem = PuanYontemi(d.get("yontem", a.yontem.value))
        a.yanlis_cezasi = bool(d.get("yanlis_cezasi", a.yanlis_cezasi))
        a.ceza_orani = int(d.get("ceza_orani", a.ceza_orani))
        a.cift_isaret = CiftIsaretKurali(d.get("cift_isaret", a.cift_isaret.value))
        a.yuvarlama = Yuvarlama(d.get("yuvarlama", a.yuvarlama.value))
        a.ondalik = int(d.get("ondalik", a.ondalik))
        a.basari_esigi = int(d.get("basari_esigi", a.basari_esigi))
        a.gecme_ortalamasi = int(d.get("gecme_ortalamasi", a.gecme_ortalamasi))
        a.final_alt_siniri = int(d.get("final_alt_siniri", a.final_alt_siniri))
        return a


SINAV_TURLERI = ["Ara Sınav", "Yarıyıl Sonu", "Bütünleme", "Mazeret"]


@dataclass
class SinavBilgisi:
    ders_kodu: str = ""
    ders_adi: str = ""
    sinav_turu: str = "Ara Sınav"
    tarih: str = ""  # YYYY-AA-GG
    saat: str = ""
    etki_orani: str = ""
    donem: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict | None) -> "SinavBilgisi":
        d = d or {}
        return cls(**{k: str(v) for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------- düzeltmeler
@dataclass
class Duzeltme:
    """Okumaya uygulanan düzeltme. Özgün okuma silinmez; düzeltmeler üstüne uygulanır.

    alan: "no", "ad" ya da "cevap:<soru no>". Soru numarası 1'den sayılır.
    """

    satir_no: int
    alan: str
    eski: str
    yeni: str
    kim: str = ""
    zaman: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Duzeltme":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------- sonuçlar
class SoruSonucuDurumu(str, Enum):
    DOGRU = "D"
    YANLIS = "Y"
    BOS = "B"
    IPTAL = "I"  # iptal edilen soru: herkese tam puan, doğru sayılır
    ANAHTARSIZ = "-"  # anahtarı girilmemiş soru: puan verilmez
    KISMI = "K"  # klasik sınavda tam puandan az, sıfırdan çok


@dataclass
class SoruSonucu:
    isaret: str
    durum: SoruSonucuDurumu
    puan: Fraction  # bu sorudan alınan ham puan (ceza dağıtılmaz)
    bonus_ile: bool = False  # yanlış ya da boş iken bonus soru sayesinde doğru sayıldı (durum özgün kalır)


@dataclass
class OgrenciSonucu:
    kayit: HamKayit
    no: str  # düzeltmeler uygulanmış numara
    ad: str  # listeden gelen ad; listede yoksa okunan ad
    okunan_ad: str
    cevaplar: list[str]  # düzeltmeler uygulanmış cevaplar
    sorular: list[SoruSonucu]
    dogru: int
    yanlis: int
    bos: int
    ham_puan: Fraction
    ceza: Fraction
    puan: Fraction  # ceza düşülmüş, sıfırın altına inmeyen, yuvarlanmamış puan
    listede: bool = True
    uyarilar: list[Uyari] = field(default_factory=list)
    oneriler: list[str] = field(default_factory=list)  # listede yoksa olası numaralar
    kitapcik: str = ""
    # Ana kitapçık soru indeksi (0'dan) -> öğrencinin kendi kitapçığındaki soru no (1'den); düzeltme için
    kaynak_soru: list[int] = field(default_factory=list)

    @property
    def uyarili(self) -> bool:
        return bool(self.uyarilar)


@dataclass
class SinavSonucu:
    ogrenciler: list[OgrenciSonucu]  # optik dosyadaki sırayla
    girmeyenler: list[Ogrenci]  # listede olup dosyada olmayanlar
    listede_olmayanlar: list[OgrenciSonucu]
    soru_puanlari: list[Fraction]
    anahtar: CevapAnahtari
    ayarlar: PuanlamaAyarlari
    liste_var: bool = False
    liste: OgrenciListesi | None = None
    klasik: bool = False  # klasik (yazılı) sınav: şık yok, kısmi puan var

    def no_ile(self) -> dict[str, OgrenciSonucu]:
        return {o.no: o for o in self.ogrenciler}


def esit_yuzdeler(n: int, toplam: int = 100) -> list[int]:
    """Toplamı tam `toplam` olan tam sayı yüzdeler (en büyük kalan yöntemi; fazlalar baştaki öğelere)."""
    if n <= 0:
        return []
    taban, kalan = divmod(toplam, n)
    return [taban + (1 if i < kalan else 0) for i in range(n)]


def fraction_decimal(x: Fraction | Decimal | int | str) -> Fraction:
    if isinstance(x, Fraction):
        return x
    if isinstance(x, str):
        x = x.strip().replace(",", ".")
    return Fraction(Decimal(x)) if not isinstance(x, int) else Fraction(x)
