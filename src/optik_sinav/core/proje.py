"""Sınav proje dosyası (`.osd`, JSON): cevap anahtarı, ayarlar, düzeltmeler ve kaynak dosya yolları."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .modeller import (
    CevapAnahtari,
    Duzeltme,
    ListeEslemesi,
    OkuyucuSablonu,
    PuanlamaAyarlari,
    SinavBilgisi,
)

SURUM = 1


@dataclass
class SinavProjesi:
    sinav: SinavBilgisi = field(default_factory=SinavBilgisi)
    anahtar: CevapAnahtari = field(default_factory=CevapAnahtari)
    ayarlar: PuanlamaAyarlari = field(default_factory=PuanlamaAyarlari)
    okuyucu: OkuyucuSablonu = field(default_factory=OkuyucuSablonu)
    dat_yolu: str = ""
    liste_yolu: str = ""
    liste_esleme: ListeEslemesi = field(default_factory=ListeEslemesi)
    duzeltmeler: list[Duzeltme] = field(default_factory=list)
    profil_akreditasyon: str = "akreditasyon_soru_bazli_varsayilan"
    profil_not_giris: str = "not_giris_varsayilan"
    sistem_sablonu_yolu: str = ""
    bicim: str = "optik"  # "optik" (test, optik okuyucu) ya da "klasik" (yazılı, puanlar elle ya da Excel'den)
    klasik_soru_sayisi: int = 5
    klasik_puanlar: dict[str, list[str | None]] = field(default_factory=dict)  # öğrenci no -> soru puanları
    klasik_toplamlar: dict[str, str | None] = field(default_factory=dict)  # kâğıdın üstüne yazılan toplam (kontrol için)
    klasik_girmedi: list[str] = field(default_factory=list)  # "sınava girmedi" diye işaretlenen öğrenciler
    klasik_giris_sirasi: list[str] = field(default_factory=list)  # öğrencilerin ilk puanının girildiği sıra (okuma sırası etkisi)
    final_puanlar: dict[str, str | None] = field(default_factory=dict)  # dönem sonu notu için: öğrenci no -> final puanı
    harf_ayarlari: dict = field(default_factory=dict)  # core.donem_sonu.HarfAyarlari.to_dict()

    @property
    def klasik(self) -> bool:
        return self.bicim == "klasik"

    def to_dict(self) -> dict:
        return {
            "surum": SURUM,
            "uygulama": "optik-sinav",
            "sinav": self.sinav.to_dict(),
            "anahtar": self.anahtar.to_dict(),
            "ayarlar": self.ayarlar.to_dict(),
            "okuyucu": self.okuyucu.to_dict(),
            "dat_yolu": self.dat_yolu,
            "liste_yolu": self.liste_yolu,
            "liste_esleme": self.liste_esleme.to_dict(),
            "duzeltmeler": [d.to_dict() for d in self.duzeltmeler],
            "profil_akreditasyon": self.profil_akreditasyon,
            "profil_not_giris": self.profil_not_giris,
            "sistem_sablonu_yolu": self.sistem_sablonu_yolu,
            "bicim": self.bicim,
            "klasik_soru_sayisi": self.klasik_soru_sayisi,
            "klasik_puanlar": self.klasik_puanlar,
            "klasik_toplamlar": self.klasik_toplamlar,
            "klasik_girmedi": self.klasik_girmedi,
            "klasik_giris_sirasi": self.klasik_giris_sirasi,
            "final_puanlar": self.final_puanlar,
            "harf_ayarlari": self.harf_ayarlari,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SinavProjesi":
        return cls(
            sinav=SinavBilgisi.from_dict(d.get("sinav")),
            anahtar=CevapAnahtari.from_dict(d.get("anahtar", {})),
            ayarlar=PuanlamaAyarlari.from_dict(d.get("ayarlar")),
            okuyucu=OkuyucuSablonu.from_dict(d.get("okuyucu", {})),
            dat_yolu=d.get("dat_yolu", ""),
            liste_yolu=d.get("liste_yolu", ""),
            liste_esleme=ListeEslemesi.from_dict(d.get("liste_esleme")),
            duzeltmeler=[Duzeltme.from_dict(x) for x in d.get("duzeltmeler", [])],
            profil_akreditasyon=d.get("profil_akreditasyon", "akreditasyon_soru_bazli_varsayilan"),
            profil_not_giris=d.get("profil_not_giris", "not_giris_varsayilan"),
            sistem_sablonu_yolu=d.get("sistem_sablonu_yolu", ""),
            bicim=d.get("bicim", "optik"),
            klasik_soru_sayisi=int(d.get("klasik_soru_sayisi", 5)),
            klasik_puanlar={str(k): list(v) for k, v in d.get("klasik_puanlar", {}).items()},
            klasik_toplamlar={str(k): (None if v in (None, "") else str(v)) for k, v in d.get("klasik_toplamlar", {}).items()},
            klasik_girmedi=[str(x) for x in d.get("klasik_girmedi", [])],
            klasik_giris_sirasi=[str(x) for x in d.get("klasik_giris_sirasi", [])],
            final_puanlar={str(k): (None if v in (None, "") else str(v)) for k, v in d.get("final_puanlar", {}).items()},
            harf_ayarlari=dict(d.get("harf_ayarlari", {})),
        )

    def kaydet(self, yol: str | Path) -> None:
        Path(yol).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def ac(cls, yol: str | Path) -> "SinavProjesi":
        return cls.from_dict(json.loads(Path(yol).read_text(encoding="utf-8")))


def ders_eslemesi_kaydet(yol: str | Path, anahtar: CevapAnahtari) -> None:
    """Soru ile öğrenme ve program çıktısı eşlemesini ders bazında saklar (sonraki sınavlarda kullanmak için)."""
    veri = {str(s.no): {"ogrenme_ciktilari": s.ogrenme_ciktilari, "program_ciktilari": s.program_ciktilari,
                        "cikti_yuzdeleri": s.cikti_yuzdeleri} for s in anahtar.sorular}
    Path(yol).parent.mkdir(parents=True, exist_ok=True)
    Path(yol).write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")


def ders_eslemesi_uygula(yol: str | Path, anahtar: CevapAnahtari) -> bool:
    p = Path(yol)
    if not p.exists():
        return False
    veri = json.loads(p.read_text(encoding="utf-8"))
    for s in anahtar.sorular:
        e = veri.get(str(s.no))
        if e:
            s.ogrenme_ciktilari = list(e.get("ogrenme_ciktilari", []))
            s.program_ciktilari = list(e.get("program_ciktilari", []))
            s.cikti_yuzdeleri = {k: int(v) for k, v in e.get("cikti_yuzdeleri", {}).items()}
    return True
