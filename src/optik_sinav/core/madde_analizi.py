"""Madde analizi, sınav istatistikleri ve öğrenme çıktısı başarı raporu (saf fonksiyonlar).

Madde puanı, sorudan alınan puanın sorunun tam puanına oranıdır: test sorusunda 1 ya da 0, klasik
sınavda 0 ile 1 arası. Böylece aynı hesaplar iki sınav biçiminde de çalışır.

- Güçlük indeksi: madde puanlarının ortalaması (testte doğru yanıtlayanların oranı).
- Ayırt edicilik: puana göre sıralanmış öğrencilerin üst %27 ve alt %27 gruplarının ortalama madde puanı farkı.
- Nokta çift serili korelasyon: madde puanı ile toplam doğru sayısı (testte) ya da toplam puan (klasikte)
  arasında; toplam, sorunun kendisini içerir.
- Düzeltilmiş madde-toplam korelasyonu: madde puanı ile sorunun kendisi çıkarılmış toplam puan arasında.
- Kuder-Richardson 20 (yalnızca test): k/(k-1) * (1 - Σpq / σ²), σ² toplam doğru sayısının kitle varyansı.
- Cronbach alfa: soru puanları üzerinden; eşit puanlı testte Kuder-Richardson 20 ile aynıdır.
- Ölçmenin standart hatası: puanların standart sapması * √(1 - alfa).
- Kişi uyum indeksi (Harnisch ve Linn düzeltilmiş uyarı indeksi): kolay soruları kaçırıp zor soruları
  bilen öğrencide büyür (0 ile 1 arası; burada 0,50 üstü beklenmedik örüntü sayılır).
- Benzer yanlış örüntüsü: iki öğrencinin aynı yanlış şıkkı işaretlediği soru sayısı. Kopya kanıtı değildir.
İptal ve anahtarsız sorular analiz dışıdır.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations

from .modeller import CIFT_ISARET, SIKLAR, SinavSonucu, SoruDurumu, SoruSonucuDurumu, esit_yuzdeler


@dataclass
class MaddeEsikleri:
    ayirt_edicilik_alt: float = 0.20
    guclik_alt: float = 0.20
    guclik_ust: float = 0.90
    grup_orani: float = 0.27
    celdirici_alt: float = 0.05  # bu orandan az seçilen yanlış şık işlemiyor
    uyum_ust: float = 0.50  # kişi uyum indeksi bunun üstündeyse beklenmedik örüntü (kısa testlerde 0,30 çok gürültülü)
    celdirici_fark: float = 0.10  # üst grup bir yanlış şıkkı alt gruptan en az bu kadar çok seçerse uyarılır
    basari_esigi: float = 50.0  # sınav puanı bu değer ve üstündeyse başarılı sayılır
    cikti_esigi: float = 50.0  # öğrenme çıktısında bu yüzde ve üstü "ulaştı"


@dataclass
class Celdirici:
    sik: str
    oran: float
    ust: float
    alt: float
    sorunlar: list[str] = field(default_factory=list)


@dataclass
class MaddeSonucu:
    soru_no: int
    dogru_sik: str
    analiz_disi: bool
    guclik: float | None
    ayirt_edicilik: float | None
    nokta_cift_serili: float | None
    sik_oranlari: dict[str, float]  # "A".."E", "Boş", "Çift" (ana kitapçık)
    sorunlar: list[str] = field(default_factory=list)
    tam_puan: float = 0.0
    ortalama_puan: float | None = None
    duzeltilmis_r: float | None = None
    alfa_cikarilirsa: float | None = None
    ust_grup: float | None = None
    alt_grup: float | None = None
    celdiriciler: list[Celdirici] = field(default_factory=list)
    bes_grup: list[float | None] = field(default_factory=list)  # en düşük beşte birlikten en yükseğe
    kitapcik_sik_oranlari: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def sorunlu(self) -> bool:
        return bool(self.sorunlar)


@dataclass
class KisiUyumu:
    no: str
    ad: str
    puan: float
    indeks: float
    beklenmedik: list[int]  # bildiği zor sorular ve kaçırdığı kolay sorular (soru no)


@dataclass
class BenzerCift:
    no1: str
    ad1: str
    no2: str
    ad2: str
    ayni_yanlis: int  # aynı yanlış şık
    ikisi_yanlis: int  # ikisinin de yanlış yaptığı soru
    ayni_cevap: int  # boş dahil bütün aynı cevaplar
    z: float
    sorular: list[int]


@dataclass
class GenelIstatistik:
    ogrenci_sayisi: int
    ortalama: float | None
    standart_sapma: float | None  # örneklem (n-1)
    en_dusuk: float | None
    en_yuksek: float | None
    medyan: float | None
    kr20: float | None
    analizdeki_soru_sayisi: int
    birinci_ceyrek: float | None = None
    ucuncu_ceyrek: float | None = None
    carpiklik: float | None = None
    basiklik: float | None = None
    alfa: float | None = None
    olcme_hatasi: float | None = None
    basari_orani: float | None = None
    basari_esigi: float = 50.0
    ortalama_guclik: float | None = None
    ortalama_ayirt_edicilik: float | None = None
    kitapcik_sayilari: dict[str, int] = field(default_factory=dict)
    kitapcik_ortalamalari: dict[str, float] = field(default_factory=dict)
    bos_orani_sirayla: list[float] = field(default_factory=list)  # öğrencinin kendi kitapçığındaki sıraya göre
    hiz_uyarisi: str = ""
    kisi_uyumu: list[KisiUyumu] = field(default_factory=list)
    benzer_ciftler: list[BenzerCift] = field(default_factory=list)
    yorumlar: list[str] = field(default_factory=list)


def _grup_boyu(n: int, oran: float) -> int:
    return max(1, int(math.floor(n * oran + 0.5))) if n else 0


def _pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx <= 0 or syy <= 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sxx * syy)


def _alfa(sutunlar: list[list[float]]) -> float | None:
    k = len(sutunlar)
    if k < 2 or not sutunlar[0]:
        return None
    toplam = [sum(s[j] for s in sutunlar) for j in range(len(sutunlar[0]))]
    var_t = statistics.pvariance(toplam)
    if var_t <= 0:
        return None
    return (k / (k - 1)) * (1 - sum(statistics.pvariance(s) for s in sutunlar) / var_t)


def _carpiklik(x: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    m = statistics.fmean(x)
    m2 = sum((a - m) ** 2 for a in x) / n
    if m2 <= 0:
        return None
    m3 = sum((a - m) ** 3 for a in x) / n
    return (m3 / m2 ** 1.5) * math.sqrt(n * (n - 1)) / (n - 2)


def _basiklik(x: list[float]) -> float | None:
    """Fazla basıklık (normal dağılımda 0)."""
    n = len(x)
    if n < 4:
        return None
    m = statistics.fmean(x)
    m2 = sum((a - m) ** 2 for a in x) / n
    if m2 <= 0:
        return None
    m4 = sum((a - m) ** 4 for a in x) / n
    g2 = m4 / m2 ** 2 - 3
    return ((n + 1) * g2 + 6) * (n - 1) / ((n - 2) * (n - 3))


def madde_analizi(sonuc: SinavSonucu, esikler: MaddeEsikleri | None = None) -> tuple[list[MaddeSonucu], GenelIstatistik]:
    esikler = esikler or MaddeEsikleri()
    ogr = sonuc.ogrenciler
    n = len(ogr)
    anahtar = sonuc.anahtar
    k_toplam = anahtar.soru_sayisi
    klasik = sonuc.klasik
    tam = [float(p) for p in sonuc.soru_puanlari]

    analizde = [
        i for i, s in enumerate(anahtar.sorular)
        if s.durum != SoruDurumu.IPTAL and (klasik or s.dogru_kume()) and tam[i] > 0
    ]
    # Madde puanı (0..1) ve sorudan alınan puan
    x = [[(float(o.sorular[i].puan) / tam[i] if tam[i] else 0.0) for i in range(k_toplam)] for o in ogr]
    if not klasik:
        x = [[1.0 if o.sorular[i].durum == SoruSonucuDurumu.DOGRU else 0.0 for i in range(k_toplam)] for o in ogr]
    puan_m = [[float(o.sorular[i].puan) for i in range(k_toplam)] for o in ogr]
    toplam_dogru = [sum(satir[i] for i in analizde) for satir in x]
    toplam_puan = [sum(satir[i] for i in analizde) for satir in puan_m]

    # Üst ve alt gruplar: puana göre (eşitlikte doğru sayısı, sonra dosya sırası)
    sirali = sorted(range(n), key=lambda j: (ogr[j].puan, toplam_dogru[j]), reverse=True)
    g = _grup_boyu(n, esikler.grup_orani)
    ust, alt = (sirali[:g], sirali[-g:]) if g else ([], [])
    # Beş grup: en düşükten en yükseğe
    artan = list(reversed(sirali))
    besler = [artan[(n * q) // 5:(n * (q + 1)) // 5] for q in range(5)] if n >= 5 else []

    sd_t = statistics.pstdev(toplam_dogru) if n else 0.0
    sutun_tumu = {i: [puan_m[j][i] for j in range(n)] for i in analizde}
    alfa = _alfa([sutun_tumu[i] for i in analizde]) if n > 1 else None

    # Kitapçık grupları ve her kitapçığın doğru şıkları
    kitapciklar: dict[str, list[int]] = {}
    for j, o in enumerate(ogr):
        kitapciklar.setdefault(o.kitapcik or anahtar.ana_kitapcik, []).append(j)
    ana = anahtar.ana_kitapcik if anahtar.ana_kitapcik in kitapciklar else (next(iter(kitapciklar)) if kitapciklar else anahtar.ana_kitapcik)
    dogru_sik = {b: [s.dogru_kume() for s in anahtar.kitapcik_icin(b)[0].sorular] for b in kitapciklar}

    def oranlar(isaretler: list[str]) -> dict[str, float]:
        m = len(isaretler)
        o = {s: (sum(1 for c in isaretler if c == s) / m if m else 0.0) for s in SIKLAR}
        o["Çift"] = sum(1 for c in isaretler if c == CIFT_ISARET) / m if m else 0.0
        o["Boş"] = sum(1 for c in isaretler if c not in SIKLAR and c != CIFT_ISARET) / m if m else 0.0
        return o

    maddeler: list[MaddeSonucu] = []
    pq_toplam = 0.0
    for i, soru in enumerate(anahtar.sorular):
        isaretler = [o.cevaplar[i] if i < len(o.cevaplar) else " " for o in ogr]
        kitapcik_oran = {} if klasik else {b: oranlar([isaretler[j] for j in js]) for b, js in kitapciklar.items()}
        oran = kitapcik_oran.get(ana, oranlar(isaretler)) if not klasik else {}
        if i not in analizde or n == 0:
            maddeler.append(MaddeSonucu(soru.no, soru.dogru, True, None, None, None, oran, tam_puan=tam[i],
                                        kitapcik_sik_oranlari=kitapcik_oran if len(kitapcik_oran) > 1 else {}))
            continue
        sutun = [satir[i] for satir in x]
        p = statistics.fmean(sutun)
        pq_toplam += p * (1 - p)
        ust_o = statistics.fmean(sutun[j] for j in ust) if ust else None
        alt_o = statistics.fmean(sutun[j] for j in alt) if alt else None
        d = (ust_o - alt_o) if ust_o is not None and alt_o is not None else None
        r = None
        if not klasik:
            if sd_t > 0 and 0 < p < 1:
                m1 = statistics.fmean(toplam_dogru[j] for j in range(n) if sutun[j])
                m0 = statistics.fmean(toplam_dogru[j] for j in range(n) if not sutun[j])
                r = (m1 - m0) / sd_t * math.sqrt(p * (1 - p))
        else:
            r = _pearson(sutun, toplam_puan)
        kalan = [toplam_puan[j] - puan_m[j][i] for j in range(n)]
        r_duz = _pearson(sutun, kalan)
        alfa_c = _alfa([sutun_tumu[t] for t in analizde if t != i]) if n > 1 else None
        bes = [statistics.fmean(sutun[j] for j in grup) if grup else None for grup in besler]

        sorunlar = []
        if d is not None and d < esikler.ayirt_edicilik_alt:
            sorunlar.append(f"Ayırt edicilik düşük ({_v(d, 2)})")
        if p < esikler.guclik_alt:
            sorunlar.append(f"Çok zor (güçlük {_v(p, 2)})")
        elif p > esikler.guclik_ust:
            sorunlar.append(f"Çok kolay (güçlük {_v(p, 2)})")
        if alfa is not None and alfa_c is not None and alfa_c > alfa + 0.01:
            sorunlar.append(f"Soru çıkarılırsa güvenirlik artıyor ({_v(alfa, 2)} → {_v(alfa_c, 2)})")
        celdiriciler: list[Celdirici] = []
        if not klasik:
            dogrular = dogru_sik[ana][i]
            en_cok_dogru = max((oran[s] for s in dogrular), default=0.0)
            yanlis_cok = [s for s in SIKLAR if s not in dogrular and oran[s] > en_cok_dogru]
            if yanlis_cok:
                sorunlar.append("Yanlış şık doğrudan çok seçilmiş: " + ", ".join(yanlis_cok))
            ana_js = set(kitapciklar.get(ana, []))
            ust_a = [j for j in ust if j in ana_js]
            alt_a = [j for j in alt if j in ana_js]
            islemeyen = []
            for s in SIKLAR:
                if s in dogrular:
                    continue
                uo = sum(1 for j in ust_a if isaretler[j] == s) / len(ust_a) if ust_a else 0.0
                ao = sum(1 for j in alt_a if isaretler[j] == s) / len(alt_a) if alt_a else 0.0
                c = Celdirici(s, oran[s], uo, ao)
                if oran[s] < esikler.celdirici_alt:
                    c.sorunlar.append("işlemiyor (çok az seçilmiş)")
                    islemeyen.append(s)
                if uo - ao >= esikler.celdirici_fark and oran[s] >= esikler.celdirici_alt:
                    c.sorunlar.append("üst grup alt gruptan çok seçmiş")
                celdiriciler.append(c)
            # Olası anahtar hatası: üst grubun en az %40'ı aynı yanlış şıkkı seçmiş ve bu, doğru şıktan çok
            ust_dogru = (sum(1 for j in ust_a if isaretler[j] in dogrular) / len(ust_a)) if ust_a else 0.0
            for c in celdiriciler:
                if c.ust >= 0.40 and c.ust > ust_dogru:
                    c.sorunlar.append("olası anahtar hatası")
                    sorunlar.insert(0, f"Olası anahtar hatası: en başarılı öğrencilerin %{c.ust * 100:.0f}'i {c.sik} şıkkını seçmiş, "
                                       f"anahtardaki {''.join(sorted(dogrular))} şıkkını %{ust_dogru * 100:.0f}")
            ters = [c.sik for c in celdiriciler if "üst grup alt gruptan çok seçmiş" in c.sorunlar]
            if ters:
                sorunlar.append("Üst grubu yanıltan çeldirici: " + ", ".join(ters))
        maddeler.append(MaddeSonucu(
            soru.no, soru.dogru, False, p, d, r, oran, sorunlar, tam_puan=tam[i],
            ortalama_puan=statistics.fmean(sutun_tumu[i]), duzeltilmis_r=r_duz, alfa_cikarilirsa=alfa_c,
            ust_grup=ust_o, alt_grup=alt_o, celdiriciler=celdiriciler, bes_grup=bes,
            kitapcik_sik_oranlari=kitapcik_oran if len(kitapcik_oran) > 1 else {},
        ))

    puanlar = [float(o.puan) for o in ogr]
    k = len(analizde)
    var_t = sd_t ** 2
    kr20 = (k / (k - 1)) * (1 - pq_toplam / var_t) if (not klasik and k > 1 and var_t > 0) else None
    sd = statistics.stdev(puanlar) if n > 1 else None
    ceyrek = statistics.quantiles(puanlar, n=4, method="inclusive") if n > 1 else None
    analizli = [m for m in maddeler if not m.analiz_disi]
    genel = GenelIstatistik(
        ogrenci_sayisi=n,
        ortalama=statistics.fmean(puanlar) if n else None,
        standart_sapma=sd,
        en_dusuk=min(puanlar) if n else None,
        en_yuksek=max(puanlar) if n else None,
        medyan=statistics.median(puanlar) if n else None,
        kr20=kr20,
        analizdeki_soru_sayisi=k,
        birinci_ceyrek=ceyrek[0] if ceyrek else None,
        ucuncu_ceyrek=ceyrek[2] if ceyrek else None,
        carpiklik=_carpiklik(puanlar),
        basiklik=_basiklik(puanlar),
        alfa=alfa,
        olcme_hatasi=(sd * math.sqrt(max(0.0, 1 - alfa))) if (sd is not None and alfa is not None) else None,
        basari_orani=(sum(1 for p in puanlar if p >= esikler.basari_esigi) / n) if n else None,
        basari_esigi=esikler.basari_esigi,
        ortalama_guclik=statistics.fmean(m.guclik for m in analizli) if analizli else None,
        ortalama_ayirt_edicilik=statistics.fmean(m.ayirt_edicilik for m in analizli if m.ayirt_edicilik is not None)
        if any(m.ayirt_edicilik is not None for m in analizli) else None,
        kitapcik_sayilari={b: len(js) for b, js in sorted(kitapciklar.items())},
        kitapcik_ortalamalari={b: statistics.fmean(puanlar[j] for j in js) for b, js in sorted(kitapciklar.items()) if js},
    )
    genel.bos_orani_sirayla, genel.hiz_uyarisi = _hiz_analizi(sonuc)
    if not klasik and k >= 4:
        p_soru = {i: statistics.fmean(x[j][i] for j in range(n)) for i in analizde} if n else {}
        genel.kisi_uyumu = _kisi_uyumu(sonuc, x, analizde, p_soru, esikler.uyum_ust)
        genel.benzer_ciftler = _benzer_ciftler(sonuc, analizde, dogru_sik)
    genel.yorumlar = _yorumlar(genel, maddeler, sonuc, esikler)
    return maddeler, genel


def _hiz_analizi(sonuc: SinavSonucu) -> tuple[list[float], str]:
    """Öğrencinin kendi kitapçığındaki soru sırasına göre boş bırakma oranı; sonlarda belirgin artış süre darlığına işarettir."""
    n = sonuc.anahtar.soru_sayisi
    if not sonuc.ogrenciler or n < 4:
        return [], ""
    bos = [0] * n
    for o in sonuc.ogrenciler:
        kaynak = o.kaynak_soru or list(range(1, n + 1))
        for i, s in enumerate(o.sorular):
            if s.durum == SoruSonucuDurumu.BOS and s.isaret != CIFT_ISARET:
                bos[kaynak[i] - 1] += 1
    oran = [b / len(sonuc.ogrenciler) for b in bos]
    ceyrek = max(1, n // 4)
    son = statistics.fmean(oran[-ceyrek:])
    once = statistics.fmean(oran[:-ceyrek]) if n > ceyrek else 0.0
    uyari = ""
    if son >= 0.10 and son >= 2 * max(once, 0.01):
        uyari = (f"Son {ceyrek} soruda boş bırakma oranı %{son * 100:.0f}, öncekilerde %{once * 100:.0f}. "
                 "Süre yetmemiş olabilir.")
    return oran, uyari


def _kisi_uyumu(sonuc: SinavSonucu, x, analizde: list[int], p_soru: dict[int, float], esik: float) -> list[KisiUyumu]:
    sira = sorted(analizde, key=lambda i: -p_soru[i])  # kolaydan zora
    ps = [p_soru[i] for i in sira]
    sonuc_listesi = []
    for j, o in enumerate(sonuc.ogrenciler):
        u = [x[j][i] for i in sira]
        r = int(sum(u))
        if r == 0 or r == len(sira):
            continue
        payda = sum(ps[:r]) - sum(ps[-r:])
        if payda <= 0:
            continue
        pay = sum((1 - u[t]) * ps[t] for t in range(r)) - sum(u[t] * ps[t] for t in range(r, len(sira)))
        indeks = pay / payda
        if indeks > esik:
            beklenmedik = sorted({sira[t] + 1 for t in range(r) if not u[t]} | {sira[t] + 1 for t in range(r, len(sira)) if u[t]})
            sonuc_listesi.append(KisiUyumu(o.no, o.ad, float(o.puan), indeks, beklenmedik))
    return sorted(sonuc_listesi, key=lambda k: -k.indeks)


def _benzer_ciftler(sonuc: SinavSonucu, analizde: list[int], dogru_sik: dict[str, list[set[str]]], en_fazla: int = 15) -> list[BenzerCift]:
    """Aynı kitapçıktaki öğrenci çiftlerinde aynı yanlış şık sayısı. Sınıf dağılımına göre aşırı olanlar listelenir."""
    ogr = sonuc.ogrenciler
    ana = sonuc.anahtar.ana_kitapcik
    kayitlar = []
    for a, b in combinations(range(len(ogr)), 2):
        oa, ob = ogr[a], ogr[b]
        if (oa.kitapcik or ana) != (ob.kitapcik or ana):
            continue
        dogru = dogru_sik.get(oa.kitapcik or ana) or dogru_sik[next(iter(dogru_sik))]
        ayni_yanlis, ikisi_yanlis, ayni, sorular = 0, 0, 0, []
        for i in analizde:
            ca, cb = oa.cevaplar[i], ob.cevaplar[i]
            ya = ca in SIKLAR and ca not in dogru[i]
            yb = cb in SIKLAR and cb not in dogru[i]
            if ca == cb:
                ayni += 1
            if ya and yb:
                ikisi_yanlis += 1
                if ca == cb:
                    ayni_yanlis += 1
                    sorular.append(i + 1)
        kayitlar.append((a, b, ayni_yanlis, ikisi_yanlis, ayni, sorular))
    if len(kayitlar) < 10:
        return []
    degerler = [k[2] for k in kayitlar]
    ort, sd = statistics.fmean(degerler), statistics.pstdev(degerler)
    if sd <= 0:
        return []
    alt_sinir = max(4, math.ceil(0.3 * len(analizde)))
    secilen = []
    for a, b, ay, iy, ac, sorular in kayitlar:
        z = (ay - ort) / sd
        if ay >= alt_sinir and z >= 4:
            secilen.append(BenzerCift(ogr[a].no, ogr[a].ad, ogr[b].no, ogr[b].ad, ay, iy, ac, z, sorular))
    return sorted(secilen, key=lambda c: (-c.ayni_yanlis, -c.z))[:en_fazla]


def _yorumlar(g: GenelIstatistik, maddeler: list[MaddeSonucu], sonuc: SinavSonucu, e: MaddeEsikleri) -> list[str]:
    """Sayıları sade cümlelere çevirir."""
    y = []
    if not g.ogrenci_sayisi:
        return y
    y.append(f"Sınıf ortalaması {_v(g.ortalama)}, ortanca {_v(g.medyan)}. {e.basari_esigi:g} ve üstü alan öğrenci oranı "
             f"%{g.basari_orani * 100:.0f}.")
    if g.carpiklik is not None:
        if g.carpiklik > 0.5:
            y.append("Puanlar düşük tarafta yığılmış (sağa çarpık): sınav sınıf için zor gelmiş.")
        elif g.carpiklik < -0.5:
            y.append("Puanlar yüksek tarafta yığılmış (sola çarpık): sınav sınıf için kolay gelmiş.")
        else:
            y.append("Puan dağılımı ortaya göre dengeli.")
    r = g.alfa if g.alfa is not None else g.kr20
    if r is not None:
        if r >= 0.80:
            d = "yüksek"
        elif r >= 0.70:
            d = "kabul edilebilir"
        elif r >= 0.60:
            d = "sınırda"
        else:
            d = "düşük"
        y.append(f"Güvenirlik katsayısı {_v(r, 2)} ({d}). Ölçmenin standart hatası yaklaşık ±{_v(g.olcme_hatasi or 0)} puan; "
                 f"bir öğrencinin puanı ölçme hatası yüzünden bu kadar oynayabilir.")
    sorunlu = [m.soru_no for m in maddeler if m.sorunlu]
    if sorunlu:
        y.append(f"Gözden geçirilmesi önerilen sorular: {', '.join(map(str, sorunlu))} (ayrıntı Madde Analizi sayfasında).")
    if g.hiz_uyarisi:
        y.append(g.hiz_uyarisi)
    if len(g.kitapcik_ortalamalari) > 1:
        y.append("Kitapçık ortalamaları: " + ", ".join(f"{b} {_v(v)} ({g.kitapcik_sayilari[b]} kişi)" for b, v in g.kitapcik_ortalamalari.items()) + ".")
    if g.kisi_uyumu:
        y.append(f"{len(g.kisi_uyumu)} öğrencide beklenmedik cevap örüntüsü var (kolay soruları kaçırıp zorları bilmiş). "
                 "Okuma hatası, dikkatsizlik ya da şans olabilir; Kişi Uyumu sayfasına bakın.")
    if g.benzer_ciftler:
        y.append(f"{len(g.benzer_ciftler)} öğrenci çiftinde sınıf geneline göre olağandışı sayıda aynı yanlış şık var. "
                 "Bu tek başına kopya kanıtı değildir; oturma düzeniyle birlikte değerlendirin.")
    return y


def _v(x: float, basamak: int = 1) -> str:
    return f"{x:.{basamak}f}".replace(".", ",")


# ---------------------------------------------------------------- öğrenme çıktısı
@dataclass
class CiktiBasarisi:
    kod: str
    tur: str  # "Öğrenme çıktısı" ya da "Program çıktısı"
    sorular: list[int]
    sinif_yuzdesi: float | None
    ogrenci_yuzdeleri: dict[str, float]  # öğrenci no -> yüzde
    sinav_agirligi: float = 0.0  # sınavın toplam puanı içindeki payı (yüzde)
    ulasan_orani: float | None = None  # eşik ve üstü başarıya ulaşan öğrenci oranı
    aciklama: str = ""


def cikti_dagilimi(sonuc_veya_anahtar, soru_puanlari: list[Fraction] | None = None) -> dict[str, Fraction]:
    """Sınavın öğrenme çıktılarına yüzde dağılımı: her çıktının, sorulardaki yüzdesiyle ağırlıklı puan payı.

    Bütün sorular en az bir çıktıya bağlıysa ve her sorunun yüzdeleri 100 ise toplam tam 100'dür.
    """
    anahtar = getattr(sonuc_veya_anahtar, "anahtar", sonuc_veya_anahtar)
    puanlar = soru_puanlari if soru_puanlari is not None else sonuc_veya_anahtar.soru_puanlari
    toplam = sum(puanlar, Fraction(0))
    pay: dict[str, Fraction] = {}
    if not toplam:
        return pay
    for s, p in zip(anahtar.sorular, puanlar):
        for kod, y in s.cikti_dagilimi().items():
            pay[kod] = pay.get(kod, Fraction(0)) + p * Fraction(y, 100)
    return {k: v / toplam * 100 for k, v in sorted(pay.items(), key=lambda kv: _dogal_sira(kv[0]))}


def tam_sayi_dagilim(dagilim: dict[str, Fraction]) -> dict[str, int]:
    """Yüzdeleri toplamı tam 100 olan tam sayılara yuvarlar (en büyük kalan yöntemi)."""
    if not dagilim:
        return {}
    toplam = sum(dagilim.values(), Fraction(0))
    hedef = round(toplam)
    taban = {k: math.floor(v) for k, v in dagilim.items()}
    kalan = hedef - sum(taban.values())
    for k in sorted(dagilim, key=lambda k: -(dagilim[k] - taban[k]))[:max(0, kalan)]:
        taban[k] += 1
    return taban


def cikti_denetimi(anahtar, ders_ciktilari: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Öğrenme çıktısı eşlemesinin sisteme girilebilirliği.

    Döndürür: (hatalar, bilgiler). Hata: çıktısı olmayan soru, yüzdeleri 100 etmeyen soru, derste olmayan kod.
    Bilgi: sınavda hiç ölçülmeyen ders çıktıları.
    """
    hatalar, bilgiler = [], []
    if not any(s.ogrenme_ciktilari for s in anahtar.sorular):
        return hatalar, bilgiler
    ciktisiz = [s.no for s in anahtar.sorular if not s.ogrenme_ciktilari and s.durum not in (SoruDurumu.IPTAL, SoruDurumu.BONUS)]
    if ciktisiz:
        hatalar.append("Öğrenme çıktısı seçilmemiş sorular: " + ", ".join(map(str, ciktisiz)))
    yuz_etmeyen = []
    for s in anahtar.sorular:
        d = s.cikti_dagilimi()
        if d and sum(d.values()) != 100:
            yuz_etmeyen.append(f"{s.no} (%{sum(d.values())})")
        if any(v < 0 for v in d.values()):
            yuz_etmeyen.append(f"{s.no} (eksi yüzde)")
    if yuz_etmeyen:
        hatalar.append("Çıktı yüzdeleri 100 etmeyen sorular: " + ", ".join(yuz_etmeyen))
    if ders_ciktilari:
        bilinen = set(ders_ciktilari)
        yabanci = sorted({k for s in anahtar.sorular for k in s.ogrenme_ciktilari if k not in bilinen}, key=_dogal_sira)
        if yabanci:
            hatalar.append("Ders bilgi paketinde olmayan çıktı kodları: " + ", ".join(yabanci))
        kullanilan = {k for s in anahtar.sorular for k in s.ogrenme_ciktilari}
        olculmeyen = [k for k in ders_ciktilari if k not in kullanilan]
        if olculmeyen:
            bilgiler.append("Bu sınavda ölçülmeyen ders çıktıları: " + ", ".join(olculmeyen))
    return hatalar, bilgiler


def ogrenme_ciktisi_raporu(sonuc: SinavSonucu, esik: float = 50.0, aciklamalar: dict[str, str] | None = None) -> list[CiktiBasarisi]:
    """Her öğrenme ve program çıktısı için başarı yüzdesi.

    Öğrenme çıktısında her sorunun puanı, o sorunun çıktıya ayrılan yüzdesiyle ağırlıklandırılır:
    başarı = Σ alınan puan × yüzde / Σ tam puan × yüzde. Program çıktısında yüzde girilmez, eşlenen
    sorular tam sayılır.
    """
    rapor = []
    toplam_puan = sum(sonuc.soru_puanlari, Fraction(0))
    aciklamalar = aciklamalar or {}
    for tur, alan in (("Öğrenme çıktısı", "ogrenme_ciktilari"), ("Program çıktısı", "program_ciktilari")):
        agirlik: dict[str, dict[int, Fraction]] = {}
        for i, s in enumerate(sonuc.anahtar.sorular):
            if s.durum == SoruDurumu.BONUS:
                continue  # bonus soru çıktı başarısına girmez
            if alan == "ogrenme_ciktilari":
                for kod, y in s.cikti_dagilimi().items():
                    agirlik.setdefault(kod, {})[i] = Fraction(y, 100)
            else:
                for kod in s.program_ciktilari:
                    kod = kod.strip()
                    if kod:
                        agirlik.setdefault(kod, {})[i] = Fraction(1)
        for kod in sorted(agirlik, key=_dogal_sira):
            w = agirlik[kod]
            olasi = sum((sonuc.soru_puanlari[i] * a for i, a in w.items()), Fraction(0))
            ogrenci = {}
            for o in sonuc.ogrenciler:
                alinan = sum((o.sorular[i].puan * a for i, a in w.items()), Fraction(0))
                ogrenci[o.no] = float(alinan / olasi * 100) if olasi else 0.0
            sinif = statistics.fmean(ogrenci.values()) if ogrenci else None
            ulasan = (sum(1 for v in ogrenci.values() if v >= esik) / len(ogrenci)) if ogrenci else None
            rapor.append(CiktiBasarisi(
                kod, tur, [i + 1 for i in sorted(w)], sinif, ogrenci,
                sinav_agirligi=float(olasi / toplam_puan * 100) if toplam_puan and alan == "ogrenme_ciktilari" else 0.0,
                ulasan_orani=ulasan, aciklama=aciklamalar.get(kod, ""),
            ))
    return rapor


def _dogal_sira(s: str):
    import re

    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", s)]


__all__ = [
    "MaddeEsikleri", "MaddeSonucu", "GenelIstatistik", "Celdirici", "KisiUyumu", "BenzerCift", "CiktiBasarisi",
    "madde_analizi", "ogrenme_ciktisi_raporu", "cikti_dagilimi", "tam_sayi_dagilim", "cikti_denetimi", "esit_yuzdeler",
]
