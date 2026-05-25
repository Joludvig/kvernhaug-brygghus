# modules/validation.py
import re

# ── Forventede antall-ranger per kategori ─────────────────────────────────
EXPECTED_COUNTS = {
    "humle": (40, 120),
    "gjaer": (30, 80),
    "malt":  (80, 250),
}

# ── Produsent-whitelister ──────────────────────────────────────────────────
KJENTE_PRODUSENTER = {
    "gjaer": {
        "Fermentis", "Lallemand", "Mangrove Jack's", "Wyeast",
        "White Labs", "Omega", "Kveik Yeastery",
    },
    "malt": {
        "Weyermann", "Viking Malt", "Castle Malting", "Thomas Fawcett",
        "Crisp Malting", "BestMalz", "Bonsak", "Ireks", "Muntons", "Briess",
        "Brewferm",
    },
    "humle": {
        "USA", "Germany", "New Zealand", "England",
        "Slovenia", "Czech Republic", "Australia",
    },
}

# ── Støynøkkelord ──────────────────────────────────────────────────────────
STOYNOKKELORD = {
    "pizza", "ooni", "bbq", "grill", "tomat", "caputo",
    "peel", "wok", "utstyr", "krydder", "saus", "oven", "ovn",
    "gjærnæring", "fermaid", "go-ferm", "ispose", "nutrient",
}


def _log(nivaa: str, melding: str):
    print(f"[{nivaa}] {melding}")


# ── 1. Antall-validering ───────────────────────────────────────────────────
def valider_antall(kategori: str, antall: int):
    rng = EXPECTED_COUNTS.get(kategori)
    if not rng:
        return
    lav, høy = rng
    if antall < lav:
        _log("WARNING", f"Mistenkelig FÅ {kategori} funnet: {antall} (forventet {lav}–{høy})")
    elif antall > høy:
        _log("WARNING", f"Mistenkelig MANGE {kategori} funnet: {antall} (forventet {lav}–{høy})")
    else:
        _log("VALIDATION", f"{kategori.capitalize()}: {antall} produkter — OK")


# ── 2. Støyfilter ──────────────────────────────────────────────────────────
def is_noise_product(navn: str) -> bool:
    navn_lower = navn.lower()
    for ord in STOYNOKKELORD:
        if ord in navn_lower:
            _log("BLOCKED", f"Støyprodukt filtrert: '{navn}' (matchet '{ord}')")
            return True
    return False


# ── 3. Produsent-validering ────────────────────────────────────────────────
def valider_produsent(kategori: str, produsent: str, kontekst: str = ""):
    whitelist = KJENTE_PRODUSENTER.get(kategori, set())
    if not whitelist:
        return
    if produsent and produsent not in ("Ukjent", "") and produsent not in whitelist:
        _log("WARNING", f"Ukjent {kategori}-produsent: '{produsent}'" +
             (f" ({kontekst})" if kontekst else ""))


# ── 4. URL-heuristikk ──────────────────────────────────────────────────────
def valider_url_match(master_id: str, display_name: str, url: str):
    """Sjekker at kanonisk navn finnes et sted i URL-slugen."""
    if not url:
        return
    slug = url.lower()
    # Normaliser navn til enkle tokens
    navn_tokens = re.sub(r"[^a-z0-9]", " ", display_name.lower()).split()
    # Filtrer bort generiske ord
    stopp = {"malt", "humle", "hop", "hops", "pellets", "yeast", "gjær", "ale", "lager"}
    tokens = [t for t in navn_tokens if t not in stopp and len(t) > 2]
    if not tokens:
        return
    # Minst ett token bør finnes i slugen
    if not any(t in slug for t in tokens):
        _log("WARNING", f"URL mismatch mistanke: master='{master_id}' | "
             f"nøkkelord={tokens} | url=...{url[-60:]}")


# ── 5. Duplikat-alias sjekk ────────────────────────────────────────────────
def valider_duplikat_aliaser(master_db: dict):
    """Finner aliaser som matcher mer enn én master-ID."""
    alias_map: dict[str, list[str]] = {}
    for m_id, info in master_db.items():
        for alias in info.get("aliases", []):
            nøkkel = alias.lower().strip()
            alias_map.setdefault(nøkkel, []).append(m_id)

    konflikter = 0
    for alias, ids in alias_map.items():
        if len(ids) > 1:
            _log("WARNING", f"Duplikat-alias konflikt: '{alias}' matcher -> {ids}")
            konflikter += 1

    if konflikter == 0:
        _log("VALIDATION", "Ingen duplikat-aliaser funnet")
    else:
        _log("WARNING", f"Totalt {konflikter} alias-konflikter funnet")


# ── 6. Valider raw scraping-liste ─────────────────────────────────────────
def valider_raw_liste(produkter: list, kategori: str) -> list:
    """
    Kjører alle sjekker på en rå scraped produktliste.
    Returnerer filtrert liste (støy fjernet).
    Skriver warnings for resten.
    """
    _log("VALIDATION", f"=== Validerer {len(produkter)} {kategori}-produkter ===")
    valider_antall(kategori, len(produkter))

    rene = []
    for p in produkter:
        navn = p.get("navn", "")
        if is_noise_product(navn):
            continue
        produsent = p.get("produsent", "")
        if produsent:
            valider_produsent(kategori, produsent, navn)
        rene.append(p)

    fjernet = len(produkter) - len(rene)
    if fjernet:
        _log("VALIDATION", f"{fjernet} støyprodukter fjernet — {len(rene)} igjen")

    return rene


# ── 7. Logg matching-resultat ─────────────────────────────────────────────
def logg_match_resultat(navn: str, master_id: str | None, butikk: str):
    if master_id:
        _log("MATCHED", f"'{navn}' -> {master_id} ({butikk})")
    else:
        _log("UNMATCHED", f"'{navn}' ({butikk}) -> pending_review")
