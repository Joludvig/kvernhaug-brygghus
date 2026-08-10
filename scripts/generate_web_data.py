"""Regenererer web/data/*.json fra masterdataene og BJCP-biblioteket i
modules/style_engine.py -- web/ har ingen egen, manuelt vedlikeholdt
kopi av ingrediens-/stildata; disse filene skal alltid kunne bygges på
nytt fra desktop-appens sannhetskilder.

Kjøres manuelt, ved release eller når data/master_*.json eller
modules/style_engine.py sitt bjcp_stiler-bibliotek endres:

    py -3 scripts/generate_web_data.py

Ingen eksterne avhengigheter (kun standardbiblioteket). Deterministisk:
output er sortert og feltrekkefølgen er fast, så uendret kildedata gir
byte-identisk output ved re-kjøring.

Tar BEVISST ikke med butikkpriser, butikklenker, lagerstatus,
pakningsstørrelse eller butikkspesifikke search_terms -- web-versjonen
er offentlig og skal aldri eksponere kommersielle avtaler eller
brukerens pantry-/lagerdata (som uansett ikke finnes i disse filene).
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEB_DATA = ROOT / "web" / "data"
STYLE_ENGINE_SRC = ROOT / "modules" / "style_engine.py"


def _last(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _med_felt(base: dict, kilde: dict, felter: list[str]) -> dict:
    """Kopierer over `felter` fra `kilde` til `base` -- kun der verdien
    faktisk finnes og ikke er tom, slik at web-JSON-en ikke fylles med
    unødvendige null/tom-streng-verdier for de fåtallige entriene som
    mangler et gitt felt."""
    for felt in felter:
        verdi = kilde.get(felt)
        if verdi:
            base[felt] = verdi
    return base


def bygg_malt() -> dict:
    kilde = _last(DATA / "master_malt.json")
    ut = {}
    for id_, v in sorted(kilde.items(), key=lambda kv: kv[1]["display_name"]):
        entry = {"navn": v["display_name"], "potensiale": v["potensiale"], "ebc": v["ebc"]}
        _med_felt(entry, v, ["produsent", "kategori", "display_group", "kategorier", "smakstags"])
        ut[id_] = entry
    return ut


def bygg_humle() -> dict:
    kilde = _last(DATA / "master_humle_v2.json")
    ut = {}
    for id_, v in sorted(kilde.items(), key=lambda kv: kv[1]["display_name"]):
        alfa = v.get("alfa", v.get("alfa_typisk"))
        entry = {"navn": v["display_name"], "alfa": alfa}
        _med_felt(entry, v, ["opprinnelse", "type", "kategorier", "smakstags"])
        ut[id_] = entry
    return ut


def bygg_gjaer() -> dict:
    kilde = _last(DATA / "master_gjaer_v2.json")
    ut = {}
    for id_, v in sorted(kilde.items(), key=lambda kv: kv[1]["display_name"]):
        entry = {"navn": v["display_name"], "attenuation": v["attenuation"]}
        # "beskrivelse" er bevisst utelatt: finnes kun på 1 av 103 gjærtyper
        # i masterdataene (verifisert 2026-08-10) og er dermed ikke et
        # felt som faktisk er "kort og egnet for UI" på tvers av biblioteket.
        _med_felt(entry, v, ["produsent", "kategori", "gjaertype", "kategorier", "smakstags"])
        ut[id_] = entry
    return ut


def bygg_bjcp_stiler() -> dict:
    """Leser bjcp_stiler-dictet direkte fra modules/style_engine.py sin
    kildekode (ikke en re-implementasjon) via ast.literal_eval på den
    balanserte dict-literalen -- garanterer at web-biblioteket aldri kan
    komme i utakt med det faktiske Python-biblioteket, i motsetning til
    en hånd-transkribert kopi."""
    src = STYLE_ENGINE_SRC.read_text(encoding="utf-8")
    marker = "bjcp_stiler = {"
    start = src.index(marker)
    start = src.index("{", start)
    depth = 0
    i = start
    while True:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
        i += 1
    bjcp = ast.literal_eval(src[start:end])

    ut = {}
    for navn, krav in bjcp.items():
        entry = dict(krav)
        for felt in ("og", "fg", "abv", "ibu", "ebc"):
            entry[felt] = list(entry[felt])
        entry.setdefault("bjcp_offisiell", True)
        ut[navn] = entry
    return ut


def _skriv(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    malt = bygg_malt()
    humle = bygg_humle()
    gjaer = bygg_gjaer()
    bjcp = bygg_bjcp_stiler()

    _skriv(WEB_DATA / "malt.json", malt)
    _skriv(WEB_DATA / "humle.json", humle)
    _skriv(WEB_DATA / "gjaer.json", gjaer)
    _skriv(WEB_DATA / "bjcp_styles.json", bjcp)

    print(f"malt: {len(malt)}, humle: {len(humle)}, gjaer: {len(gjaer)}, bjcp-stiler: {len(bjcp)}")
    print(f"Skrevet til {WEB_DATA}")


if __name__ == "__main__":
    main()
