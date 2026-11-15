"""Madde analizini tamamlayan ek istatistikler (saf fonksiyonlar).

- Sınırdaki öğrenciler: puanı başarı eşiğine ölçmenin standart hatası kadar yakın olanlar.
- Finalde gereken puan: ara sınav ağırlığı ve geçme kuralıyla, her öğrencinin finalden alması gereken en düşük puan.
- Şans puanı: bütün sorulara rastgele işaret koyan birinin beklenen puanı (yalnızca test).
- Kitapçık eşdeğerliği: iki kitapçığın ortalama farkı için Welch t testi.
- Sınav tasarımı: anahtardaki şık sayıları, art arda aynı harf, soru sırası ile güçlük arasındaki sıra korelasyonu.
- Rasch modeli: soruların ve öğrencilerin aynı logit ölçeğinde konumu (birleşik en çok olabilirlik, (k-1)/k
  yanlılık düzeltmesi) ve sınavın bilgi eğrisi (hangi başarı düzeyini en iyi ölçtüğü). Yalnızca test.
- Arşiv: sınav özetini ders koduna göre saklar; aynı dersin önceki sınavlarıyla karşılaştırma için.
- Notu belirleyen sorular: not farklarının (toplam puan varyansının) ne kadarının hangi sorudan geldiği.
- Kısmi puan profili (klasik): her soruda tam, kısmi, sıfır ve boş sayısı.
- Okuma sırası etkisi (klasik): kâğıtların girildiği sıra ile puan arasındaki ilişki (okuyanın kayması).
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


# ---------------------------------------------------------------- ortak kavram yanılgıları
@dataclass
class KavramYanilgisi:
    soru1: int
    sik1: str
    soru2: int
    sik2: str
    birlikte: int  # ikisini birden seçen öğrenci
    secen1: int  # 1. yanlış şıkkı seçen
    secen2: int
    kosullu: float  # 1'i seçenlerin 2'yi de seçme oranı
    taban: float  # sınıfta 2'yi seçme oranı
    phi: float
    p: float  # Fisher kesin testi (tek yönlü): bu kadar çok birlikte seçimin şansla olma olasılığı


def _log_komb(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_ust(n11: int, n1: int, n2: int, n: int) -> float:
    """Hipergeometrik üst kuyruk: P(X >= n11), X ~ HG(n, n1, n2)."""
    toplam = 0.0
    for x in range(n11, min(n1, n2) + 1):
        toplam += math.exp(_log_komb(n1, x) + _log_komb(n - n1, n2 - x) - _log_komb(n, n2))
    return min(1.0, toplam)


def kavram_yanilgilari(sonuc: SinavSonucu, en_fazla: int = 15) -> list[KavramYanilgisi]:
    """Öğrencilerin birlikte seçtiği yanlış şıklar: iki farklı sorunun yanlış şıkları arasındaki phi ilişkisi.

    Yalnızca ana kitapçık öğrencileri; her yanlış şık en az max(3, %5) öğrenci tarafından seçilmiş olmalı.
    Listelenen çiftler: birlikte seçen ≥ max(3, %5), phi ≥ 0,30, koşullu oran tabandan en az 1,5 kat ve
    Fisher kesin testinde p ≤ 0,01 (çok sayıda çift sınandığı için sıkı eşik).
    """
    if sonuc.klasik:
        return []
    ana = sonuc.anahtar.ana_kitapcik
    ogr = [o for o in sonuc.ogrenciler if (o.kitapcik or ana) == ana]
    n = len(ogr)
    if n < 10:
        return []
    alt = max(3, math.ceil(0.05 * n))
    gostergeler: list[tuple[int, str, list[int]]] = []
    for i, s in enumerate(sonuc.anahtar.sorular):
        if s.durum == SoruDurumu.IPTAL or not s.dogru_kume():
            continue
        for sik in SIKLAR:
            if sik in s.dogru_kume():
                continue
            v = [1 if o.cevaplar[i] == sik else 0 for o in ogr]
            if sum(v) >= alt:
                gostergeler.append((i, sik, v))
    sonuclar = []
    for a in range(len(gostergeler)):
        for b in range(a + 1, len(gostergeler)):
            i1, s1, v1 = gostergeler[a]
            i2, s2, v2 = gostergeler[b]
            if i1 == i2:
                continue
            n11 = sum(1 for x, y in zip(v1, v2) if x and y)
            if n11 < alt:
                continue
            n1, n2 = sum(v1), sum(v2)
            payda = math.sqrt(n1 * (n - n1) * n2 * (n - n2))
            if payda == 0:
                continue
            phi = (n * n11 - n1 * n2) / payda
            kosullu = n11 / n1
            taban = n2 / n
            if phi >= 0.30 and kosullu >= 1.5 * taban:
                p = fisher_ust(n11, n1, n2, n)
                if p <= 0.01:
                    sonuclar.append(KavramYanilgisi(i1 + 1, s1, i2 + 1, s2, n11, n1, n2, kosullu, taban, phi, p))
    return sorted(sonuclar, key=lambda k: (-k.phi, -k.birlikte, k.soru1, k.soru2))[:en_fazla]


# ---------------------------------------------------------------- sınav yapısı (boyutluluk)
def _jacobi(a: list[list[float]], en_fazla: int = 500) -> tuple[list[float], list[list[float]]]:
    """Simetrik matrisin özdeğer ve özvektörleri (Jacobi dönüşümleri). Büyükten küçüğe sıralı."""
    n = len(a)
    a = [row[:] for row in a]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(en_fazla):
        enb, p, q = 0.0, 0, 1
        for i in range(n):
            for j in range(i + 1, n):
                if abs(a[i][j]) > enb:
                    enb, p, q = abs(a[i][j]), i, j
        if enb < 1e-12:
            break
        theta = 0.5 * math.atan2(2 * a[p][q], a[q][q] - a[p][p])
        c, s = math.cos(theta), math.sin(theta)
        for k in range(n):
            akp, akq = a[k][p], a[k][q]
            a[k][p] = c * akp - s * akq
            a[k][q] = s * akp + c * akq
        for k in range(n):
            apk, aqk = a[p][k], a[q][k]
            a[p][k] = c * apk - s * aqk
            a[q][k] = s * apk + c * aqk
        for k in range(n):
            vkp, vkq = v[k][p], v[k][q]
            v[k][p] = c * vkp - s * vkq
            v[k][q] = s * vkp + c * vkq
    degerler = [a[i][i] for i in range(n)]
    sira = sorted(range(n), key=lambda i: -degerler[i])
    vektorler = []
    for i in sira:
        vec = [v[k][i] for k in range(n)]
        if sum(vec) < 0:
            vec = [-x for x in vec]
        vektorler.append(vec)
    return [degerler[i] for i in sira], vektorler


@dataclass
class SinavYapisi:
    sorular: list[int]
    ozdegerler: list[float]
    ilk_pay: float  # ilk bileşenin açıkladığı varyans oranı
    oran_1_2: float | None  # birinci / ikinci özdeğer
    ortalama_korelasyon: float
    yukler: dict[int, float]  # soru no -> ilk bileşen yükü
    zayif_sorular: list[int]  # yükü 0,20'nin altında
    cikti_uyumu: list[tuple[str, float, float, int]]  # (çıktı, kendi içi ortalama r, dışarıyla ortalama r, soru sayısı)
    yorum: str


def sinav_yapisi(sonuc: SinavSonucu) -> SinavYapisi | None:
    """Soru puanları arasındaki korelasyon matrisinin temel bileşenleri.

    Birinci özdeğer ikinciden en az 3 kat büyükse sınav büyük ölçüde tek bir beceriyi ölçüyor kabul edilir.
    Öğrenme çıktısı uyumu: aynı çıktıya bağlı soruların kendi aralarındaki ortalama korelasyonu ile öteki
    sorularla ortalama korelasyonu.
    """
    tam = [float(p) for p in sonuc.soru_puanlari]
    sec = [i for i, s in enumerate(sonuc.anahtar.sorular)
           if s.durum != SoruDurumu.IPTAL and (sonuc.klasik or s.dogru_kume()) and tam[i] > 0]
    ogr = sonuc.ogrenciler
    if len(ogr) < 10:
        return None
    sutun = {i: [float(o.sorular[i].puan) / tam[i] for o in ogr] for i in sec}
    sec = [i for i in sec if statistics.pvariance(sutun[i]) > 0]
    k = len(sec)
    if k < 3:
        return None

    def r(x, y):
        mx, my = statistics.fmean(x), statistics.fmean(y)
        sxx = sum((a - mx) ** 2 for a in x)
        syy = sum((b - my) ** 2 for b in y)
        return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sxx * syy)

    m = [[1.0 if a == b else r(sutun[sec[a]], sutun[sec[b]]) for b in range(k)] for a in range(k)]
    degerler, vektorler = _jacobi(m)
    yukler = {sec[j] + 1: vektorler[0][j] * math.sqrt(max(degerler[0], 0.0)) for j in range(k)}
    ciftler = [m[a][b] for a in range(k) for b in range(a + 1, k)]
    ort_r = statistics.fmean(ciftler)
    oran = degerler[0] / degerler[1] if degerler[1] > 1e-12 else None
    zayif = sorted(no for no, y in yukler.items() if y < 0.20)
    uyum = []
    kodlar: dict[str, list[int]] = {}
    for j, i in enumerate(sec):
        for kod in sonuc.anahtar.sorular[i].ogrenme_ciktilari:
            kodlar.setdefault(kod, []).append(j)
    for kod in sorted(kodlar, key=_dogal):
        ic = kodlar[kod]
        dis = [j for j in range(k) if j not in ic]
        if len(ic) < 2 or not dis:
            continue
        ic_r = statistics.fmean(m[a][b] for x, a in enumerate(ic) for b in ic[x + 1:])
        dis_r = statistics.fmean(m[a][b] for a in ic for b in dis)
        uyum.append((kod, ic_r, dis_r, len(ic)))
    if oran is not None and oran >= 3:
        yorum = "Sınav büyük ölçüde tek bir beceriyi ölçüyor (birinci bileşen ikinciden en az 3 kat güçlü); toplam puan anlamlı bir özet."
    elif oran is not None and oran >= 1.5:
        yorum = "Sınavda baskın bir ortak beceri var ama sorular birkaç ayrı konuya da dağılıyor; öğrenme çıktısı bazında bakmak toplam puandan daha bilgilendirici olabilir."
    else:
        yorum = "Sorular büyük ölçüde birbirinden bağımsız davranıyor; sınav ortak bir beceriden çok ayrı ayrı konuları ölçüyor. Toplam puan bu durumda kaba bir özettir."
    return SinavYapisi([i + 1 for i in sec], degerler, degerler[0] / k, oran, ort_r, yukler, zayif, uyum, yorum)


def _dogal(s: str):
    import re

    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", s)]


# ---------------------------------------------------------------- notu belirleyen sorular
@dataclass
class SoruKatkisi:
    soru_no: int
    puan_payi: float  # sorunun tam puanı / sınavın toplamı
    katki_payi: float  # Cov(soru, toplam) / Var(toplam): not farklarının bu sorudan gelen payı (toplamı 1)
    oran: float | None  # katki_payi / puan_payi
    durum: str  # "fazla_belirleyici", "az_etkili" ya da ""


@dataclass
class NotBelirleyen:
    sorular: list[SoruKatkisi]
    yorum: str


def notu_belirleyen_sorular(sonuc: SinavSonucu) -> NotBelirleyen | None:
    """Toplam puanın varyansı soruların toplamla kovaryanslarına ayrılır: Var(T) = Σ Cov(x_i, T).

    Bir sorunun payı, puanı sınavdaki ağırlığından çok daha büyükse (oran ≥ 1,5 ve pay ≥ %15) notu o soru
    belirliyor demektir; çok küçükse (oran ≤ 0,5) soru öğrencileri ayırmıyor ya da öteki sorularla ters gidiyor.
    """
    ogr = sonuc.ogrenciler
    tam = [float(p) for p in sonuc.soru_puanlari]
    sec = [i for i, s in enumerate(sonuc.anahtar.sorular) if s.durum != SoruDurumu.IPTAL and tam[i] > 0]
    if len(ogr) < 5 or len(sec) < 2:
        return None
    x = {i: [float(o.sorular[i].puan) for o in ogr] for i in sec}
    t = [sum(x[i][j] for i in sec) for j in range(len(ogr))]
    mt = statistics.fmean(t)
    vt = sum((v - mt) ** 2 for v in t) / len(t)
    if vt <= 1e-12:
        return None
    toplam_tam = sum(tam[i] for i in sec)
    sorular = []
    for i in sec:
        mx = statistics.fmean(x[i])
        kov = sum((a - mx) * (b - mt) for a, b in zip(x[i], t)) / len(t)
        katki = kov / vt
        pay = tam[i] / toplam_tam
        oran = katki / pay if pay > 0 else None
        durum = ("fazla_belirleyici" if oran is not None and oran >= 1.5 and katki >= 0.15
                 else "az_etkili" if oran is not None and oran <= 0.5 else "")
        sorular.append(SoruKatkisi(i + 1, pay, katki, oran, durum))
    en = max(sorular, key=lambda k: k.katki_payi)
    yorum = (f"Öğrenciler arasındaki not farklarına en büyük katkı {en.soru_no}. sorudan geliyor: farkların payı "
             f"%{en.katki_payi * 100:.0f}, sorunun puan payı %{en.puan_payi * 100:.0f}.")
    fazla = [str(k.soru_no) for k in sorular if k.durum == "fazla_belirleyici"]
    az = [str(k.soru_no) for k in sorular if k.durum == "az_etkili"]
    if fazla:
        yorum += (f" Notu puanından çok daha fazla belirleyen {'soru' if len(fazla) == 1 else 'sorular'}: {', '.join(fazla)}. "
                  "Sınav fiilen bu sorulara dayanıyor olabilir; puanı bölmek ya da benzer ağırlıkta başka sorular eklemek notu daha dengeli kılar.")
    if az:
        yorum += (f" Puanına göre not farklarına az katkı veren {'soru' if len(az) == 1 else 'sorular'}: {', '.join(az)}. "
                  "Bu sorularda herkes benzer puan almış ya da soru öteki sorularla ters yönde gidiyor.")
    if not fazla and not az:
        yorum += " Soruların nota katkısı puan ağırlıklarıyla uyumlu."
    return NotBelirleyen(sorular, yorum)


# ---------------------------------------------------------------- kısmi puan profili (klasik)
@dataclass
class KismiProfil:
    soru_no: int
    tam: int
    kismi: int
    sifir: int
    bos: int
    ortalama_oran: float | None  # puanı girilenlerde ortalama puan / tam puan
    notlar: list[str]


def kismi_puan_profili(sonuc: SinavSonucu) -> list[KismiProfil] | None:
    """Klasik sınavda her soru için tam, kısmi, sıfır ve boş sayısı.

    Puanı girilenlerin en az %60'ı kısmi puan almışsa puanlama ölçütü belirsiz olabilir; kimse tam almadıysa
    soru çok zor ya da tam puanın ölçütü ulaşılmaz olabilir; herkes tam aldıysa soru öğrencileri ayırmıyor.
    """
    if not sonuc.klasik or not sonuc.ogrenciler:
        return None
    tam_p = [float(p) for p in sonuc.soru_puanlari]
    sonuclar = []
    for i, s in enumerate(sonuc.anahtar.sorular):
        d = [o.sorular[i].durum for o in sonuc.ogrenciler]
        tam = sum(1 for x in d if x == SoruSonucuDurumu.DOGRU)
        kismi = sum(1 for x in d if x == SoruSonucuDurumu.KISMI)
        sifir = sum(1 for x in d if x == SoruSonucuDurumu.YANLIS)
        bos = sum(1 for x in d if x == SoruSonucuDurumu.BOS)
        girilen = tam + kismi + sifir
        oranlar = [float(o.sorular[i].puan) / tam_p[i] for o in sonuc.ogrenciler
                   if o.sorular[i].durum != SoruSonucuDurumu.BOS and tam_p[i] > 0]
        notlar = []
        if girilen:
            if kismi / girilen >= 0.6:
                notlar.append("çoğu kısmi puan almış: puanlama ölçütü belirsiz olabilir")
            if tam == 0:
                notlar.append("kimse tam puan almamış")
            elif tam == girilen:
                notlar.append("herkes tam puan almış: soru öğrencileri ayırmıyor")
        sonuclar.append(KismiProfil(i + 1, tam, kismi, sifir, bos, statistics.fmean(oranlar) if oranlar else None, notlar))
    return sonuclar


# ---------------------------------------------------------------- okuma sırası etkisi (klasik)
@dataclass
class OkumaSirasi:
    n: int
    rho: float  # giriş sırası ile puan yüzdesi arasında Spearman sıra korelasyonu
    p: float
    ilk_ortalama: float  # ilk üçte birin ortalama puan yüzdesi
    son_ortalama: float  # son üçte birin
    yorum: str


def _vir(x: float, n: int) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def okuma_sirasi_etkisi(sonuc: SinavSonucu, giris_sirasi: list[str]) -> OkumaSirasi | None:
    """Kâğıtların girildiği sıra ile puan arasındaki ilişki (en az 10 kâğıt).

    Okuyan kişi yoruldukça ya da ölçütü kaydıkça puanlar sistematik olarak düşebilir ya da yükselebilir.
    Kâğıtlar başarıya göre sıralanmışsa (örneğin numaraya göre ve numara başarıyla ilişkiliyse) ilişki okumadan
    değil sıradan kaynaklanır; yorum bunu belirtir.
    """
    if not sonuc.klasik:
        return None
    toplam = float(sum(sonuc.soru_puanlari)) or 1.0
    puan = {o.no: float(o.puan) / toplam * 100 for o in sonuc.ogrenciler}
    sira, gorulen = [], set()
    for no in giris_sirasi:
        if no in puan and no not in gorulen:
            sira.append(no)
            gorulen.add(no)
    n = len(sira)
    if n < 10:
        return None
    y = [puan[no] for no in sira]
    rho = spearman(list(range(1, n + 1)), y)
    if rho is None:
        return None
    if abs(rho) >= 1 - 1e-12:
        p = 0.0
    else:
        t = rho * math.sqrt((n - 2) / (1 - rho * rho))
        p = t_iki_yonlu_p(t, n - 2)
    u = max(1, n // 3)
    ilk, son = statistics.fmean(y[:u]), statistics.fmean(y[-u:])
    if p < 0.05 and abs(rho) >= 0.3:
        yon = "düşüyor" if rho < 0 else "yükseliyor"
        yorum = (f"Okuma ilerledikçe puanlar {yon}: ilk {u} kâğıdın ortalaması %{ilk:.0f}, son {u} kâğıdınki %{son:.0f} "
                 f"(sıra korelasyonu {_vir(rho, 2)}, p = {_vir(p, 3)}). Okuyanın yorulması ya da puanlama ölçütünün kayması olabilir; "
                 "ilk ve son kâğıtlardan birkaçını yeniden okumak yararlı olur. Kâğıtlar başarıya göre sıralıysa "
                 "bu fark okumadan değil sıradan kaynaklanır.")
    else:
        yorum = (f"Okuma sırasına bağlı belirgin bir kayma yok (sıra korelasyonu {_vir(rho, 2)}, p = {_vir(p, 3)}; "
                 f"ilk {u} kâğıt %{ilk:.0f}, son {u} kâğıt %{son:.0f}).")
    return OkumaSirasi(n, rho, p, ilk, son, yorum)
