"""
TESTPLAN V2 — Steg 4: Verifisering

Sjekker alle betingelser etter full scrape+match.
Skriver ut PASS/FAIL for hvert punkt.
"""
import json
import os
import re
from collections import defaultdict

PASS = "  [PASS]"
FAIL = "  [FAIL]"
WARN = "  [WARN]"

feil = []
advarsler = []

def sjekk(betingelse, melding, detalj=""):
    if betingelse:
        print(f"{PASS} {melding}")
    else:
        print(f"{FAIL} {melding}" + (f"\n         -> {detalj}" if detalj else ""))
        feil.append(melding)

def advar(betingelse, melding, detalj=""):
    if not betingelse:
        print(f"{WARN} {melding}" + (f"\n         -> {detalj}" if detalj else ""))
        advarsler.append(melding)

def les(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

# ── 0. Filer finnes ───────────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("TESTPLAN V2 — VERIFISERING")
print("=" * 55)

print("\n[0] Master-filer finnes")
for path in ["data/master_humle_v2.json", "data/master_malt.json", "data/master_gjaer_v2.json"]:
    sjekk(os.path.exists(path), f"Finner {path}")

# ── 1. 0 unmatched ────────────────────────────────────────────────────────────
print("\n[1] Nullmatching (0 unmatched)")
for path, label in [
    ("raw_data/unmatched_hops.json",  "Humle"),
    ("raw_data/unmatched_malt.json",  "Malt"),
    ("raw_data/unmatched_gjaer.json", "Gjær"),
]:
    if not os.path.exists(path):
        sjekk(False, f"{label} unmatched-fil mangler", f"{path} ikke funnet")
    else:
        data = les(path)
        sjekk(len(data) == 0, f"{label}: 0 unmatched", f"{len(data)} umatched: {[d.get('navn','?') for d in data[:5]]}")

# ── 2. Duplikat-aliaser ───────────────────────────────────────────────────────
print("\n[2] Ingen duplikat-aliaser")
for path, label in [
    ("data/master_humle_v2.json", "Humle"),
    ("data/master_malt.json",     "Malt"),
    ("data/master_gjaer_v2.json", "Gjær"),
]:
    master = les(path)
    sett = defaultdict(list)
    for mid, info in master.items():
        for alias in info.get("aliases", []):
            sett[alias.lower().strip()].append(mid)
    duplikater = {a: ids for a, ids in sett.items() if len(ids) > 1}
    sjekk(len(duplikater) == 0, f"{label}: ingen duplikat-aliaser",
          "; ".join(f"'{a}' → {ids}" for a, ids in list(duplikater.items())[:3]))

# ── 3. Eclipse 2021/2024 separert ────────────────────────────────────────────
print("\n[3] Eclipse 2021 / 2024 separert")
humle = les("data/master_humle_v2.json")
sjekk("eclipse_2021" in humle, "eclipse_2021 finnes i master")
sjekk("eclipse_2024" in humle, "eclipse_2024 finnes i master")

if "eclipse_2021" in humle and "eclipse_2024" in humle:
    bm21 = humle["eclipse_2021"].get("butikk_match", {})
    bm24 = humle["eclipse_2024"].get("butikk_match", {})
    sjekk(bool(bm21), "eclipse_2021 har butikk_match")
    sjekk(bool(bm24), "eclipse_2024 har butikk_match")

    url21 = (bm21.get("olbrygging") or {}).get("url", "")
    url24 = (bm24.get("olbrygging") or {}).get("url", "")
    sjekk("2021" in url21, f"eclipse_2021 URL inneholder '2021'", f"URL: {url21}")
    sjekk("2024" in url24, f"eclipse_2024 URL inneholder '2024'", f"URL: {url24}")
    sjekk(url21 != url24, "eclipse_2021 og eclipse_2024 har ULIKE URLs")

    pris21 = (bm21.get("olbrygging") or {}).get("pris")
    pris24 = (bm24.get("olbrygging") or {}).get("pris")
    sjekk(pris21 != pris24, f"eclipse_2021 ({pris21}kr) og eclipse_2024 ({pris24}kr) har ULIKE priser")

# ── 4. WLP-routing ───────────────────────────────────────────────────────────
print("\n[4] WLP-routing (ingen kryssmatching)")
gjaer = les("data/master_gjaer_v2.json")

def sjekk_wlp_url(master_id, forventet_substring, label):
    if master_id not in gjaer:
        sjekk(False, f"{label}: {master_id} finnes i master")
        return
    bm = gjaer[master_id].get("butikk_match", {})
    for butikk, d in bm.items():
        url = d.get("url", "")
        sjekk(
            forventet_substring.lower() in url.lower(),
            f"{label} ({master_id}) URL matcher '{forventet_substring}'",
            f"{butikk}: {url}"
        )

# WLP 080 skal ikke peke på 077-URL
if "wlp_080" in gjaer:
    bm = gjaer["wlp_080"].get("butikk_match", {})
    for butikk, d in bm.items():
        url = d.get("url") or ""
        if not url:
            continue  # ingen URL etter scrape = produktet ikke funnet i denne butikken
        sjekk("077" not in url, f"wlp_080 ({butikk}) URL inneholder ikke '077'", f"URL: {url}")
        sjekk("080" in url, f"wlp_080 ({butikk}) URL inneholder '080'", f"URL: {url}")

# WLP 300 skal ikke peke på 380-URL
if "wlp_300" in gjaer:
    bm = gjaer["wlp_300"].get("butikk_match", {})
    for butikk, d in bm.items():
        url = d.get("url") or ""
        sjekk("380" not in url, f"wlp_300 ({butikk}) URL inneholder ikke '380'", f"URL: {url}")

# WLP 077 skal ikke peke på 080-URL
if "wlp_077" in gjaer:
    bm = gjaer["wlp_077"].get("butikk_match", {})
    for butikk, d in bm.items():
        url = d.get("url") or ""
        sjekk("080" not in url, f"wlp_077 ({butikk}) URL inneholder ikke '080'", f"URL: {url}")

# ── 5. Carafa I/II/III ────────────────────────────────────────────────────────
print("\n[5] Carafa Special I / II / III")
malt = les("data/master_malt.json")

CARAFA_FORVENTET = {
    "carafa_special_1": {"olbrygging_url_id": "101174", "vestbrygg_pris": 60},
    "carafa_special_2": {"olbrygging_url_id": "102275", "vestbrygg_pris": 60},
    "carafa_special_3": {"olbrygging_url_id": "101175", "vestbrygg_pris": 60},
}
for master_id, forv in CARAFA_FORVENTET.items():
    if master_id not in malt:
        sjekk(False, f"{master_id} finnes i master")
        continue
    bm = malt[master_id].get("butikk_match", {})
    ol = bm.get("olbrygging", {})
    vb = bm.get("vestbrygg", {})
    sjekk(
        forv["olbrygging_url_id"] in (ol.get("url") or ""),
        f"{master_id} olbrygging URL inneholder '{forv['olbrygging_url_id']}'",
        f"URL: {ol.get('url','<mangler>')}"
    )
    advar(
        vb.get("pris") == forv["vestbrygg_pris"],
        f"{master_id} vestbrygg pris = {forv['vestbrygg_pris']} kr",
        f"Faktisk: {vb.get('pris')}"
    )

# ── 6. 100g humle vinner ─────────────────────────────────────────────────────
print("\n[6] 100g humle vinner (minste pakke lagret)")
if os.path.exists("raw_data/humle_raw.json"):
    humle_raw = les("raw_data/humle_raw.json")
    humle_master = les("data/master_humle_v2.json")

    # Grupper raw etter (butikk, master_id-via-alias)
    from modules.store_matcher import _match_humle_kern, _normaliser_butikk

    multi: dict[tuple, list] = defaultdict(list)
    for prod in humle_raw:
        navn = prod.get("navn", "")
        butikk = _normaliser_butikk(prod.get("butikk", ""))
        pakke_gram = prod.get("pakke_gram")
        mid, _ = _match_humle_kern(navn, humle_master)
        if mid and pakke_gram:
            multi[(mid, butikk)].append(pakke_gram)

    feil_100g = []
    for (mid, butikk), gram_liste in multi.items():
        if len(gram_liste) < 2:
            continue
        minste = min(gram_liste)
        lagret = (humle_master[mid].get("butikk_match", {}).get(butikk) or {}).get("pakke_gram")
        if lagret != minste:
            feil_100g.append(f"{mid} @ {butikk}: rå har {sorted(gram_liste)}, lagret={lagret}")

    sjekk(len(feil_100g) == 0, "Minste pakke vinner for alle humle med flere størrelser",
          "; ".join(feil_100g[:3]))
else:
    print(f"{WARN} humle_raw.json finnes ikke — hopper over 100g-sjekk")

# ── 7. Alle master-kategorier har priser ─────────────────────────────────────
print("\n[7] Dekning (andel entries med minst én butikk)")
for path, label in [
    ("data/master_humle_v2.json", "Humle"),
    ("data/master_malt.json",     "Malt"),
    ("data/master_gjaer_v2.json", "Gjær"),
]:
    master = les(path)
    totalt = len(master)
    med_pris = sum(1 for v in master.values() if v.get("butikk_match"))
    pst = round(100 * med_pris / totalt) if totalt else 0
    advar(pst >= 70, f"{label}: {med_pris}/{totalt} ({pst}%) har butikk_match",
          f"Under 70% dekning")
    print(f"       {label}: {med_pris}/{totalt} ({pst}%) har butikk_match")

# ── Oppsummering ──────────────────────────────────────────────────────────────
print("\n" + "=" * 55)
if not feil:
    print("RESULTAT: ALT OK")
else:
    print(f"RESULTAT: {len(feil)} FEIL")
    for f in feil:
        print(f"  X {f}")
if advarsler:
    print(f"\n{len(advarsler)} ADVARSEL(ER):")
    for a in advarsler:
        print(f"  ! {a}")
print("=" * 55)
