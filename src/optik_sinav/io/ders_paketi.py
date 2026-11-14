"""Ders bilgi paketi: dersin öğrenme çıktıları, program çıktıları ve katkı düzeyleri.

Kaynaklar:
- Akademik Bilgi Sistemi'nin ders bilgi paketi PDF'i (pypdf ile metni okunur; ağ erişimi yok).
- Daha önce kaydedilmiş JSON (`dersler/<KOD>.json`, kullanıcı klasöründe ya da paketle gelen).
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..kaynaklar import kullanici_klasoru, paket_klasoru


@dataclass
class Cikti:
    kod: str  # "Ö01", "P07"
    aciklama: str


@dataclass
class DersPaketi:
    kod: str
    ad: str = ""
    program: str = ""
    ogrenme_ciktilari: list[Cikti] = field(default_factory=list)
    program_ciktilari: list[Cikti] = field(default_factory=list)
    katki: dict[str, int] = field(default_factory=dict)  # program çıktısı -> katkı düzeyi (1-5)
    degerlendirme: dict[str, int] = field(default_factory=dict)  # "Ara Sınav" -> 40

    def ogrenme_kodlari(self) -> list[str]:
        return [c.kod for c in self.ogrenme_ciktilari]

    def aciklamalar(self) -> dict[str, str]:
        return {c.kod: c.aciklama for c in self.ogrenme_ciktilari + self.program_ciktilari}

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DersPaketi":
        return cls(
            kod=d["kod"], ad=d.get("ad", ""), program=d.get("program", ""),
            ogrenme_ciktilari=[Cikti(**c) for c in d.get("ogrenme_ciktilari", [])],
            program_ciktilari=[Cikti(**c) for c in d.get("program_ciktilari", [])],
            katki={k: int(v) for k, v in d.get("katki", {}).items()},
            degerlendirme={k: int(v) for k, v in d.get("degerlendirme", {}).items()},
        )


def _kod_sirala(kod: str):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", kod)]


def metinden_coz(metin: str) -> DersPaketi:
    """Ders bilgi paketinin düz metninden alanları çıkarır."""
    satirlar = [s.strip() for s in metin.replace("\r", "").split("\n")]
    kod, ad = "", ""
    for s in satirlar[:8]:
        m = re.match(r"^([A-ZÇĞİÖŞÜ]{2,5}\d{3,5})\s+(.+)$", s)
        if m:
            kod, ad = m.group(1), m.group(2).strip()
            break
    program = ""
    for i, s in enumerate(satirlar):
        if re.match(r"^Bölümü\s*/\s*Programı", s) and i + 1 < len(satirlar):
            program = satirlar[i + 1]
            break

    def bolum(baslik: str, onek: str) -> list[Cikti]:
        try:
            bas = next(i for i, s in enumerate(satirlar) if s == baslik)
        except StopIteration:
            return []
        sonuc: list[Cikti] = []
        desen = re.compile(rf"^({onek}\d{{1,2}})\s+(.*)$")
        for s in satirlar[bas + 1:]:
            m = desen.match(s)
            if m:
                sonuc.append(Cikti(m.group(1), m.group(2).strip()))
            elif s.startswith("Sıra No") or not s:
                continue
            elif sonuc and not re.match(r"^(Dersin|Programın|Değerlendirme|Katkı|Yarıyıl|P\d|Ö\d|Tüm)\b", s):
                sonuc[-1].aciklama += " " + s
            else:
                break
        return sorted(sonuc, key=lambda c: _kod_sirala(c.kod))

    ogrenme = bolum("Dersin Öğrenme Çıktıları", "Ö")
    program_c = bolum("Programın Öğrenme Çıktıları", "P")
    katki: dict[str, int] = {}
    for i, s in enumerate(satirlar):
        if re.fullmatch(r"(P\d{1,2}\s*)+", s) and i + 1 < len(satirlar):
            kodlar = s.split()
            m = re.match(r"^Tüm\s+([\d\s]+)$", satirlar[i + 1])
            if m:
                degerler = [int(x) for x in m.group(1).split()]
                katki = dict(zip(kodlar, degerler))
    degerlendirme: dict[str, int] = {}
    for s in satirlar:
        m = re.match(r"^(Ara Sınav|Kısa Sınav|Ödev|Devam|Uygulama|Proje|Yarıyıl Sonu Sınavı)\s+\d+\s+%(\d+)(?:\s|$)", s)
        if m and int(m.group(2)) > 0:
            degerlendirme[m.group(1)] = int(m.group(2))
    return DersPaketi(kod=kod, ad=ad, program=program, ogrenme_ciktilari=ogrenme, program_ciktilari=program_c,
                      katki=katki, degerlendirme=degerlendirme)


def pdf_oku(yol: str | Path) -> DersPaketi:
    from pypdf import PdfReader

    metin = "\n".join((p.extract_text() or "") for p in PdfReader(str(yol)).pages)
    paket = metinden_coz(metin)
    if not paket.kod or not paket.ogrenme_ciktilari:
        raise ValueError("Bu PDF'te ders kodu ya da 'Dersin Öğrenme Çıktıları' bölümü bulunamadı. "
                         "Akademik Bilgi Sistemi'nden indirilen ders bilgi paketini seçin.")
    return paket


def _klasorler() -> list[Path]:
    return [kullanici_klasoru() / "dersler", paket_klasoru("dersler")]


def ders_bul(kod: str) -> DersPaketi | None:
    kod = "".join(c for c in kod.upper() if c.isalnum())
    if not kod:
        return None
    for k in _klasorler():
        p = k / f"{kod}.json"
        if p.exists():
            return DersPaketi.from_dict(json.loads(p.read_text(encoding="utf-8")))
    return None


def ders_kaydet(paket: DersPaketi) -> Path:
    k = kullanici_klasoru() / "dersler"
    k.mkdir(parents=True, exist_ok=True)
    p = k / f"{paket.kod}.json"
    p.write_text(json.dumps(paket.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def kayitli_dersler() -> list[str]:
    kodlar = set()
    for k in _klasorler():
        if k.exists():
            kodlar.update(p.stem for p in k.glob("*.json"))
    return sorted(kodlar)
