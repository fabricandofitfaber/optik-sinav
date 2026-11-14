"""Madde analizini tamamlayan ek istatistikler (saf fonksiyonlar).

- Sınırdaki öğrenciler: puanı başarı eşiğine ölçmenin standart hatası kadar yakın olanlar.
- Finalde gereken puan: ara sınav ağırlığı ve geçme kuralıyla, her öğrencinin finalden alması gereken en düşük puan.
- Şans puanı: bütün sorulara rastgele işaret koyan birinin beklenen puanı (yalnızca test).
- Kitapçık eşdeğerliği: iki kitapçığın ortalama farkı için Welch t testi.
- Sınav tasarımı: anahtardaki şık sayıları, art arda aynı harf, soru sırası ile güçlük arasındaki sıra korelasyonu.
- Rasch modeli: soruların ve öğrencilerin aynı logit ölçeğinde konumu (birleşik en çok olabilirlik, (k-1)/k
  yanlılık düzeltmesi) ve sınavın bilgi eğrisi (hangi başarı düzeyini en iyi ölçtüğü). Yalnızca test.
- Arşiv: sınav özetini ders koduna göre saklar; aynı dersin önceki sınavlarıyla karşılaştırma için.
"""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .modeller import SIKLAR, SinavSonucu, SoruDurumu, SoruSonucuDurumu


# ---------------------------------------------------------------- sınırdaki öğrenciler ve final
@dataclass
class SinirdakiOgrenci:
    no: str
    ad: str
    puan: float
    fark: float  # puan - eşik


def sinirdaki_ogrenciler(sonuc: SinavSonucu, esik: float, olcme_hatasi: float | None) -> list[SinirdakiOgrenci]:
    """Puanı eşiğe ölçme hatası (yoksa 5 puan) kadar yakın öğrenciler; kâğıtlarına bir daha bakmaya değer."""
    pay = olcme_hatasi if olcme_hatasi and olcme_hatasi > 0 else 5.0
    liste = [SinirdakiOgrenci(o.no, o.ad, float(o.puan), float(o.puan) - esik) for o in sonuc.ogrenciler
             if abs(float(o.puan) - esik) <= pay]
    return sorted(liste, key=lambda s: s.fark)


@dataclass
class FinalGereken:
    no: str
    ad: str
    puan: float
    gereken: float | None  # None: 100 alsa bile geçemez


def final_gereken(sonuc: SinavSonucu, ara_agirlik: float, gecme_ortalamasi: float = 50.0, final_alt_siniri: float = 50.0) -> list[FinalGereken]:
    """Ortalama = puan × ara ağırlık + final × (100 - ara ağırlık). Geçmek için ortalama ≥ geçme ortalaması ve
    final ≥ final alt sınırı. Ara ağırlık yüzde olarak verilir (örneğin 40)."""
    if not 0 < ara_agirlik < 100:
        return []
    fw = (100 - ara_agirlik) / 100
    sonuclar = []
    for o in sonuc.ogrenciler:
        p = float(o.puan)
        gereken = max(final_alt_siniri, (gecme_ortalamasi - p * ara_agirlik / 100) / fw, 0.0)
        gereken = math.ceil(gereken * 100 - 1e-9) / 100
        sonuclar.append(FinalGereken(o.no, o.ad, p, None if gereken > 100 else gereken))
    return sorted(sonuclar, key=lambda f: (f.gereken is None, -(f.gereken or 0)), reverse=False)


# ---------------------------------------------------------------- şans puanı
def sans_puani(sonuc: SinavSonucu, sik_sayisi: int = 5) -> float | None:
    """Rastgele işaretleyen birinin beklenen puanı (yanlış cezası varsa ceza dahil, sıfırın altına inmeden yaklaşık)."""
    if sonuc.klasik:
        return None
    a = sonuc.ayarlar
    beklenen = 0.0
    for s, p in zip(sonuc.anahtar.sorular, sonuc.soru_puanlari):
        p = float(p)
        if s.durum == SoruDurumu.IPTAL:
            beklenen += p
            continue
        olasilik = len(s.dogru_kume()) / sik_sayisi
        beklenen += p * olasilik
        if a.yanlis_cezasi and a.ceza_orani > 0:
            beklenen -= p / a.ceza_orani * (1 - olasilik)
    return max(0.0, beklenen)


# ---------------------------------------------------------------- kitapçık eşdeğerliği
def _beta_duzenli(a: float, b: float, x: float) -> float:
    """Düzenlileştirilmiş eksik beta fonksiyonu (Lentz sürekli kesri)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x > (a + 1) / (a + b + 2):
        return 1.0 - _beta_duzenli(b, a, 1 - x)
    kucuk = 1e-300
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1)
    d = 1.0 / (d if abs(d) > kucuk else kucuk)
    f = d
    for m in range(1, 300):
        for cift in (True, False):
            if cift:
                k = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
            else:
                k = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
            d = 1.0 + k * d
            d = 1.0 / (d if abs(d) > kucuk else kucuk)
            c = 1.0 + k / c
            c = c if abs(c) > kucuk else kucuk
            f *= c * d
        if abs(c * d - 1.0) < 1e-12:
            break
    return math.exp(ln) * f / a


def t_iki_yonlu_p(t: float, sd: float) -> float:
    return _beta_duzenli(sd / 2, 0.5, sd / (sd + t * t))


@dataclass
class KitapcikKarsilastirma:
    kitapcik1: str
    kitapcik2: str
    n1: int
    n2: int
    ortalama1: float
    ortalama2: float
    fark: float
    t: float
    serbestlik: float
    p: float
    etki: float  # Cohen d (birleşik standart sapma)


def kitapcik_karsilastirma(sonuc: SinavSonucu) -> KitapcikKarsilastirma | None:
    gruplar: dict[str, list[float]] = {}
    for o in sonuc.ogrenciler:
        gruplar.setdefault(o.kitapcik or sonuc.anahtar.ana_kitapcik, []).append(float(o.puan))
    adlar = sorted(k for k, v in gruplar.items() if len(v) >= 2)
    if len(adlar) < 2:
        return None
    a, b = gruplar[adlar[0]], gruplar[adlar[1]]
    m1, m2 = statistics.fmean(a), statistics.fmean(b)
    v1, v2 = statistics.variance(a), statistics.variance(b)
    se = math.sqrt(v1 / len(a) + v2 / len(b))
    if se == 0:
        return None
    t = (m1 - m2) / se
    sd = (v1 / len(a) + v2 / len(b)) ** 2 / ((v1 / len(a)) ** 2 / (len(a) - 1) + (v2 / len(b)) ** 2 / (len(b) - 1))
    birlesik = math.sqrt(((len(a) - 1) * v1 + (len(b) - 1) * v2) / (len(a) + len(b) - 2))
    return KitapcikKarsilastirma(adlar[0], adlar[1], len(a), len(b), m1, m2, m1 - m2, t, sd, t_iki_yonlu_p(t, sd),
                                 (m1 - m2) / birlesik if birlesik else 0.0)


# ---------------------------------------------------------------- sınav tasarımı
@dataclass
class TasarimDenetimi:
    sik_sayilari: dict[str, int]
    en_uzun_seri: int
    seri_harfi: str
    seri_baslangic: int
    sira_guclik_korelasyonu: float | None  # Spearman: artı = sonlara doğru kolaylaşıyor
    notlar: list[str] = field(default_factory=list)


def _sirala(x: list[float]) -> list[float]:
    sira = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(sira):
        j = i
        while j + 1 < len(sira) and x[sira[j + 1]] == x[sira[i]]:
            j += 1
        for t in range(i, j + 1):
            r[sira[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3:
        return None
    rx, ry = _sirala(x), _sirala(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if not sxx or not syy:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sxx * syy)


def tasarim_denetimi(sonuc: SinavSonucu, guclukler: list[float | None]) -> TasarimDenetimi | None:
    if sonuc.klasik:
        return None
    harfler = [s.dogru[:1] if s.durum != SoruDurumu.IPTAL else "" for s in sonuc.anahtar.sorular]
    sayilar = {h: sum(1 for x in harfler if x == h) for h in SIKLAR}
    en_uzun, harf, bas, i = 0, "", 0, 0
    while i < len(harfler):
        j = i
        while j + 1 < len(harfler) and harfler[j + 1] == harfler[i] and harfler[i]:
            j += 1
        if harfler[i] and j - i + 1 > en_uzun:
            en_uzun, harf, bas = j - i + 1, harfler[i], i + 1
        i = j + 1
    cift = [(k + 1, g) for k, g in enumerate(guclukler) if g is not None]
    r = spearman([k for k, _ in cift], [g for _, g in cift]) if len(cift) >= 3 else None
    notlar = []
    n = len([h for h in harfler if h])
    if n >= 10:
        beklenen = n / 5
        az = [h for h, c in sayilar.items() if c < beklenen / 2]
        cok = [h for h, c in sayilar.items() if c > beklenen * 1.8]
        if az or cok:
            notlar.append("Doğru şıklar dengesiz dağılmış: " + ", ".join(f"{h} {sayilar[h]} kez" for h in SIKLAR)
                          + ". Öğrenciler en çok ya da en az kullanılan harfe göre tahmin yürütebilir.")
    if en_uzun >= 3:
        notlar.append(f"{bas}. sorudan başlayarak {en_uzun} soru art arda {harf} şıkkı doğru.")
    if r is not None:
        if r < -0.4:
            notlar.append("Sorular sona doğru zorlaşıyor (kolaydan zora sıralanmış).")
        elif r > 0.4:
            notlar.append("Sorular sona doğru kolaylaşıyor; zor sorular başta öğrencinin moralini bozabilir.")
        else:
            notlar.append("Soru sırası ile güçlük arasında belirgin bir ilişki yok (karışık sıralanmış).")
    return TasarimDenetimi(sayilar, en_uzun, harf, bas, r, notlar)


# ---------------------------------------------------------------- Rasch modeli
@dataclass
class RaschSonucu:
    soru_zorluklari: dict[int, float]  # soru no -> logit (ortalama 0)
    soru_hatalari: dict[int, float]
    kisi_yetenekleri: dict[str, float]  # öğrenci no -> logit (uç puanlılar hariç)
    bilgi_egrisi: list[tuple[float, float]]  # (yetenek logiti, sınav bilgisi)
    en_iyi_olctugu: float  # bilginin en yüksek olduğu yetenek
    en_iyi_puan: float  # o yeteneğin beklenen sınav puanı (yüzde)
    disarida_kalan_ogrenci: int
    disarida_kalan_soru: list[int]
    yakinsadi: bool


def rasch(sonuc: SinavSonucu, en_fazla_dongu: int = 200) -> RaschSonucu | None:
    if sonuc.klasik:
        return None
    sorular = [i for i, s in enumerate(sonuc.anahtar.sorular) if s.durum != SoruDurumu.IPTAL and s.dogru_kume()]
    x = {o.no: [1 if o.sorular[i].durum == SoruSonucuDurumu.DOGRU else 0 for i in sorular] for o in sonuc.ogrenciler}
    # Uç değerler: hepsini doğru ya da hepsini yanlış yapan öğrenci, herkesin bildiği ya da kimsenin bilmediği soru
    disarida_soru: list[int] = []
    while True:
        k = len(sorular)
        kisiler = {no: v for no, v in x.items() if 0 < sum(v) < k}
        if len(kisiler) < 3 or k < 3:
            return None
        sutun = [sum(v[j] for v in kisiler.values()) for j in range(k)]
        uc = [j for j in range(k) if sutun[j] in (0, len(kisiler))]
        if not uc:
            break
        disarida_soru += [sorular[j] + 1 for j in uc]
        sorular = [s for j, s in enumerate(sorular) if j not in uc]
        x = {no: [v[j] for j in range(k) if j not in uc] for no, v in x.items()}
    k = len(sorular)
    no_listesi = list(kisiler)
    toplam = {no: sum(v) for no, v in kisiler.items()}
    b = [math.log((len(kisiler) - sutun[j]) / sutun[j]) for j in range(k)]
    ort = statistics.fmean(b)
    b = [v - ort for v in b]
    th = {no: math.log(toplam[no] / (k - toplam[no])) for no in no_listesi}
    yakinsadi = False
    for _ in range(en_fazla_dongu):
        en_buyuk = 0.0
        for no in no_listesi:
            p = [1 / (1 + math.exp(b[j] - th[no])) for j in range(k)]
            beklenen = sum(p)
            var = sum(q * (1 - q) for q in p)
            adim = max(-1.0, min(1.0, (toplam[no] - beklenen) / var))
            th[no] += adim
            en_buyuk = max(en_buyuk, abs(adim))
        for j in range(k):
            p = [1 / (1 + math.exp(b[j] - th[no])) for no in no_listesi]
            beklenen = sum(p)
            var = sum(q * (1 - q) for q in p)
            adim = max(-1.0, min(1.0, (beklenen - sutun[j]) / var))
            b[j] += adim
            en_buyuk = max(en_buyuk, abs(adim))
        ort = statistics.fmean(b)
        b = [v - ort for v in b]
        if en_buyuk < 1e-4:
            yakinsadi = True
            break
    duzelt = (k - 1) / k
    b = [v * duzelt for v in b]
    hatalar = []
    for j in range(k):
        var = sum((lambda q: q * (1 - q))(1 / (1 + math.exp(b[j] - th[no] * duzelt))) for no in no_listesi)
        hatalar.append(1 / math.sqrt(var) if var > 0 else float("nan"))
    egri = []
    for t10 in range(-40, 41):
        t = t10 / 10
        egri.append((t, sum((lambda q: q * (1 - q))(1 / (1 + math.exp(bj - t))) for bj in b)))
    en_iyi = max(egri, key=lambda e: e[1])[0]
    # O yetenekteki öğrencinin beklenen puanı (analizdeki sorular, eşit ağırlık)
    beklenen_yuzde = statistics.fmean(1 / (1 + math.exp(bj - en_iyi)) for bj in b) * 100
    return RaschSonucu(
        soru_zorluklari={sorular[j] + 1: b[j] for j in range(k)},
        soru_hatalari={sorular[j] + 1: hatalar[j] for j in range(k)},
        kisi_yetenekleri={no: th[no] * duzelt for no in no_listesi},
        bilgi_egrisi=egri, en_iyi_olctugu=en_iyi, en_iyi_puan=beklenen_yuzde,
        disarida_kalan_ogrenci=len(sonuc.ogrenciler) - len(kisiler), disarida_kalan_soru=sorted(disarida_soru),
        yakinsadi=yakinsadi,
    )


# ---------------------------------------------------------------- arşiv
@dataclass
class ArsivKaydi:
    ders_kodu: str
    sinav_turu: str
    tarih: str
    donem: str
    ogrenci_sayisi: int
    ortalama: float
    medyan: float
    standart_sapma: float | None
    basari_orani: float
    guvenirlik: float | None
    cikti_basarilari: dict[str, float]  # öğrenme çıktısı kodu -> sınıf başarı yüzdesi

    @property
    def anahtar(self) -> str:
        return f"{self.tarih}_{self.sinav_turu}"


def arsiv_kaydi_olustur(sonuc: SinavSonucu, sinav, genel, cikti_raporu) -> ArsivKaydi:
    return ArsivKaydi(
        ders_kodu=sinav.ders_kodu, sinav_turu=sinav.sinav_turu, tarih=sinav.tarih, donem=sinav.donem,
        ogrenci_sayisi=genel.ogrenci_sayisi, ortalama=genel.ortalama or 0.0, medyan=genel.medyan or 0.0,
        standart_sapma=genel.standart_sapma, basari_orani=genel.basari_orani or 0.0,
        guvenirlik=genel.alfa if genel.alfa is not None else genel.kr20,
        cikti_basarilari={c.kod: c.sinif_yuzdesi for c in cikti_raporu if c.tur.startswith("Öğrenme") and c.sinif_yuzdesi is not None},
    )


def arsive_yaz(klasor: Path, kayit: ArsivKaydi) -> Path:
    kod = "".join(c for c in kayit.ders_kodu if c.isalnum()) or "ders"
    hedef = Path(klasor) / kod / f"{''.join(c if c.isalnum() or c in '-_' else '_' for c in kayit.anahtar)}.json"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps(asdict(kayit), ensure_ascii=False, indent=1), encoding="utf-8")
    return hedef


def arsivi_oku(klasor: Path, ders_kodu: str) -> list[ArsivKaydi]:
    kod = "".join(c for c in ders_kodu if c.isalnum()) or "ders"
    k = Path(klasor) / kod
    if not k.exists():
        return []
    kayitlar = []
    for p in sorted(k.glob("*.json")):
        try:
            kayitlar.append(ArsivKaydi(**json.loads(p.read_text(encoding="utf-8"))))
        except (ValueError, TypeError):
            continue
    return sorted(kayitlar, key=lambda r: (r.tarih, r.sinav_turu))


def ara_agirligi(sinav, ders=None) -> float:
    """Ara sınavın dönem sonu ortalamasındaki ağırlığı (%): önce sınav bilgisindeki etki oranı, sonra ders bilgi paketi, yoksa 40."""
    try:
        v = float(str(sinav.etki_orani).replace(",", "."))
        if 0 < v < 100:
            return v
    except (ValueError, AttributeError):
        pass
    if ders is not None and getattr(ders, "degerlendirme", None):
        v = ders.degerlendirme.get("Ara Sınav")
        if v and 0 < v < 100:
            return float(v)
    return 40.0
