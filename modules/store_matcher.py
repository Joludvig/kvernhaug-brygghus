import copy
import json
import re
from difflib import SequenceMatcher

from modules.master_data_io import skriv_master_json_atomisk

_SIZE_RE = re.compile(
    r"\s*\d+[\.,]?\d*\s*(?:kg|g|gr|gram)\b"
    r"|\s*\b(?:knust|crushed|hel|whole)\b",
    re.IGNORECASE,
)

# Pakningstype (Steg F10C) er semantisk noe annet enn størrelse/maltform
# over — det beskriver EMBALLASJEN produktet selges i ("Sekk"/"Sack"),
# ikke selve maltens fysiske form. Egen, separat regel fremfor å late
# som det er samme kategori som hel/knust/whole/crushed.
_PAKNINGSTYPE_RE = re.compile(r"\s*\b(?:sekk|sack)\b", re.IGNORECASE)

def _strip_size(navn: str) -> str:
    """Fjerner størrelses-, maltform- og pakningstype-info (f.eks.
    "25 kg knust", "Sekk", "Sack") fra produktnavn før matching."""
    uten_storrelse_form = _SIZE_RE.sub("", navn)
    uten_pakningstype = _PAKNINGSTYPE_RE.sub("", uten_storrelse_form)
    return re.sub(r"\s+", " ", uten_pakningstype).strip()

_HUMLE_KERN_STOP = re.compile(
    r"(?=\s*\b\d{4}\b|\s+humle\b|\s+pellets?\b|\s+-\s|\s+\d+\s*(?:g|kg)\b|\s+\d+[\.,]\d+\s*%)",
    re.IGNORECASE,
)

def _humle_kern(navn: str) -> str:
    """Trekker ut humlsortnavnet uten år/størrelse/format for mer presis matching."""
    m = re.match(r"^([\w\-\s()]+?)" + _HUMLE_KERN_STOP.pattern, navn.strip(), re.IGNORECASE)
    return m.group(1).strip() if m else navn.strip()

def _match_humle_kern(scraped_navn: str, master_humle: dict):
    """
    Matcher humle ved å sammenligne bare sortnavnet (kern) på begge sider.
    Unngår kryssmatching mellom 'Fuggles 2023' og 'Herkules 2023' o.l.

    To-pass:
    Pass 1 — eksakt kern+år: hvis scraped har årstall, finn alias med identisk
             kern OG identisk årstall. Brukes for å skille Eclipse 2021/2024.
    Pass 2 — ren kern-likhet som fallback (håndterer kryss-årsgang og vestbrygg-
             format som 'Saaz 2025 Humle Pellets - 100g Tsjekkia' mot 'Saaz 2024').
    """
    kern_scraped = _humle_kern(scraped_navn).lower()
    year_scraped = re.search(r"\b(20\d{2})\b", scraped_navn)

    if year_scraped:
        year_str = year_scraped.group(1)
        for master_id, master_info in master_humle.items():
            for alias in master_info.get("aliases", []):
                kern_alias = _humle_kern(alias).lower()
                if kern_alias != kern_scraped:
                    continue
                year_alias = re.search(r"\b(20\d{2})\b", alias)
                if year_alias and year_alias.group(1) == year_str:
                    return (master_id, alias)

    best_match = None
    best_score = 0.7
    for master_id, master_info in master_humle.items():
        for alias in master_info.get("aliases", []):
            kern_alias = _humle_kern(alias).lower()
            score = similarity(kern_scraped, kern_alias)
            if score > best_score:
                best_score = score
                best_match = (master_id, alias)
    return best_match if best_match else (None, None)

from modules.validation import (
    valider_raw_liste, valider_duplikat_aliaser,
    valider_url_match, logg_match_resultat,
)

def similarity(a, b):
    """Enkel string-likhet (0.0 til 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

_KVALIFIKATOR_TOKEN_RE = re.compile(r"[a-zæøåA-ZÆØÅ]+")

# Ord-til-kvalifikator-tabell. Kun EXTRA er registrert (Steg F8F) — se
# _produktkvalifikatorer() sin dokstreng for hvorfor øvrige adjektiver
# (special/premium/dark/pale/super/classic/floor malted, ...) bevisst
# ikke er tatt med uten egne, konkrete funn.
_KVALIFIKATOR_ALIASER = {
    "extra": "extra",
    "ekstra": "extra",
}

def _produktkvalifikatorer(navn):
    """
    Finner diskriminerende produktkvalifikatorer i et produktnavn — ord
    som skiller to ellers like produkter fra hverandre, f.eks. "Light"
    vs. "Extra Light" (Steg F8F rotårsaksrapport: disse ble tidligere
    feilmatchet med likhetsscore 0,821, godt over 0,7-terskelen).

    Ord-/tokenbasert (\\b-avgrenset), ALDRI substreng-basert: "extract"/
    "ekstrakt" inneholder bokstavrekken "extra"/"ekstra" som prefiks,
    men er et annet ord og skal ikke telle som kvalifikatoren EXTRA.

    Returnerer et frozenset av normaliserte kvalifikatorer (tomt hvis
    ingen funnet), slik at to navn kan sammenlignes med enkel
    mengdelikhet uavhengig av hvilket av de to synonyme ordene
    ("extra"/"ekstra") som faktisk ble brukt.
    """
    tokens = (t.lower() for t in _KVALIFIKATOR_TOKEN_RE.findall(navn))
    return frozenset(_KVALIFIKATOR_ALIASER[t] for t in tokens if t in _KVALIFIKATOR_ALIASER)

def match_product_to_master(scaped_navn, master_humle):
    """
    Prøver å matche et scrapet produktnavn mot master_humle aliases.
    Returnerer (master_id, matched_alias) eller (None, None) hvis ikke match.

    Et alias vurderes kun dersom det har nøyaktig samme sett med
    diskriminerende kvalifikatorer (se _produktkvalifikatorer()) som det
    skrapede navnet — symmetrisk i begge retninger. Dette hindrer at
    f.eks. "Spraymalt Extra Light" matches mot master-aliaset "Spraymalt
    Light" (og omvendt) selv om ren streng-likhet ligger over terskelen.
    Sjekken er per alias, ikke per master-ID, så en master-ID med flere
    aliases fortsatt kan matches via et hvilket som helst alias som har
    riktig kvalifikator-signatur.
    """
    scaped_navn_lower = scaped_navn.lower().strip()
    scaped_kvalifikatorer = _produktkvalifikatorer(scaped_navn)
    best_match = None
    best_score = 0.7  # Terskel for match

    for master_id, master_info in master_humle.items():
        aliases = master_info.get("aliases", [])
        for alias in aliases:
            if _produktkvalifikatorer(alias) != scaped_kvalifikatorer:
                continue
            alias_lower = alias.lower().strip()
            score = similarity(scaped_navn_lower, alias_lower)
            if score > best_score:
                best_score = score
                best_match = (master_id, alias)

    return best_match if best_match else (None, None)

def match_store_data_to_master(humle_raw_path, master_humle_path, output_matched, output_unmatched):
    """
    Matcher alle scrapede humler mot master, oppdaterer BARE pris/URL.
    Lager ALDRI nye ingredienser automatisk.
    Master DB er sannheten – syncing er enveis.
    """
    with open(humle_raw_path, "r", encoding="utf-8") as f:
        humle_raw = json.load(f)

    with open(master_humle_path, "r", encoding="utf-8") as f:
        master_humle = json.load(f)

    humle_raw = valider_raw_liste(humle_raw, "humle")
    valider_duplikat_aliaser(master_humle)

    unmatched = []
    matched_count = 0

    for raw_produkt in humle_raw:
        navn = raw_produkt.get("navn", "")
        butikk_key = _normaliser_butikk(raw_produkt.get("butikk", ""))
        pris = raw_produkt.get("pris", 0)
        url = raw_produkt.get("url", "")
        pakke_gram = raw_produkt.get("pakke_gram") or float("inf")

        master_id, _ = _match_humle_kern(navn, master_humle)
        logg_match_resultat(navn, master_id, butikk_key)

        if master_id:
            valider_url_match(master_id, master_humle[master_id].get("display_name", master_id), url)
            if "butikk_match" not in master_humle[master_id]:
                master_humle[master_id]["butikk_match"] = {}
            if butikk_key not in master_humle[master_id]["butikk_match"]:
                master_humle[master_id]["butikk_match"][butikk_key] = {
                    "search_terms": [], "pris": None, "url": None, "pakke_gram": None,
                }
            eksisterende_gram = master_humle[master_id]["butikk_match"][butikk_key].get("pakke_gram") or float("inf")
            if master_humle[master_id]["butikk_match"][butikk_key]["pris"] is None or pakke_gram <= eksisterende_gram:
                master_humle[master_id]["butikk_match"][butikk_key]["pris"] = pris
                master_humle[master_id]["butikk_match"][butikk_key]["url"] = url
                master_humle[master_id]["butikk_match"][butikk_key]["pakke_gram"] = pakke_gram if pakke_gram != float("inf") else None
            matched_count += 1
        else:
            unmatched.append({
                "navn": navn, "butikk": butikk_key,
                "pris": pris, "url": url, "status": "pending_review",
            })

    skriv_master_json_atomisk(master_humle_path, master_humle)
    with open(output_unmatched, "w", encoding="utf-8") as f:
        json.dump(unmatched, f, ensure_ascii=False, indent=2)

    return matched_count, len(unmatched)

def _normaliser_butikk(butikk_str):
    b = butikk_str.lower()
    if "vestbrygg" in b:
        return "vestbrygg"
    if "olbrygging" in b or "ølbrygging" in b:
        return "olbrygging"
    if "litebrygg" in b:
        return "litebrygg"
    return b

def _pris_per_kg(pris, pakke_gram, kategori):
    """Regner om råpris til kr/kg. Gjær returneres uendret."""
    if kategori == "gjaer":
        return pris
    if pakke_gram and pakke_gram > 0:
        return round(pris * (1000 / pakke_gram), 2)
    if kategori == "malt" and 0 < pris < 15:
        return round(pris * 10, 2)
    return pris

_MALT_1KG_GRAM = 1000.0


def _maltkandidat_rangeringsnokkel(kandidat):
    """
    Rangeringsregel for å velge én representativ rad når flere rå
    maltprodukter (ulike pakningsstørrelser/format) matcher samme
    (master_id, butikk). Sortert stigende — laveste nøkkel vinner:

    1. En identifiserbar 1 kg-variant foretrekkes fremfor alt annet —
       den mest kjente, sammenlignbare referanseenheten for hjemme-
       bryggere, verken rabattert storkjøp eller en minimums-
       fragmentpris (jf. "Fra 7,-"-funnet i rotårsaksrapporten).
    2. Deretter minste kjente pakningsstørrelse. Ukjent størrelse
       (pakke_gram=None) rangeres sist av de kjente, men håndteres
       likevel stabilt — den blokkerer aldri et valg.
    3. Hel foretrekkes fremfor knust når størrelsen er lik. Ingen
       eksisterende prosjektlogikk bruker knust som standard (se
       modules/malt_packaging.py sin MALTFORM_INGEN_PREFERANSE).
    4. Normalisert URL som siste, stabile tie-break — alltid til
       stede og unik per skrapet rad, så dette trinnet garanterer at
       det aldri finnes en reell uavgjort situasjon.

    Bruker bevisst ALDRI pris i rangeringen.
    """
    pakke_gram = kandidat.get("pakke_gram")
    er_1kg = 0 if pakke_gram == _MALT_1KG_GRAM else 1
    storrelse = pakke_gram if pakke_gram is not None else float("inf")
    knust = 1 if kandidat.get("er_knust") else 0
    tiebreak = (kandidat.get("url") or kandidat.get("navn") or "").lower()
    return (er_1kg, storrelse, knust, tiebreak)


def _velg_representativ_maltkandidat(kandidater):
    """Velger den ene raden som skal representere (master_id, butikk) i
    butikk_match — samme resultat uansett hvilken rekkefølge
    `kandidater` kom i (se _maltkandidat_rangeringsnokkel)."""
    return min(kandidater, key=_maltkandidat_rangeringsnokkel)


def _malttype_for_kandidat(kandidat):
    return "knust" if kandidat.get("er_knust") else "hel"


def _bygg_ol_variantliste(kandidater):
    """Bygger den fullstendige variantlisten for Ølbrygging — modules.malt_packaging
    sitt eksisterende butikk_match.<butikk>.varianter-format
    ({pakningsstorrelse_gram, malttype, pris, url}), se dens moduldokstreng.

    I motsetning til _velg_representativ_maltkandidat (som velger ÉN rad)
    bevarer denne ALLE reelle pakningsalternativer — f.eks. bevares 1 kg
    hel, 1 kg knust, 25 kg hel og 25 kg knust som fire atskilte varianter
    for samme (master_id, butikk) i stedet for at bare én overlever.

    Kandidater uten kjent pakningsstørrelse kan ikke inngå i en
    kjøpskombinasjon (modules.malt_packaging krever numerisk
    pakningsstorrelse_gram) og utelates derfor — de påvirker likevel
    fortsatt det flate representative valget som før.

    "pris" her er raten PER FAKTISK PAKKE (samme tall som rå-radens
    "pris"-felt), IKKE kr/kg som det flate butikk_match-feltet bruker —
    modules.malt_packaging summerer pris×antall direkte for å bygge
    totalpris per kombinasjon.

    Determinisme: kandidatene sorteres på (pakningsstorrelse_gram,
    malttype, url, pris) FØR duplikater fjernes, så resultatet er
    identisk uansett hvilken rekkefølge kandidatene kom i, og selve
    sorteringen blir samtidig den endelige, stabile variant-rekkefølgen.
    Duplikater (identisk størrelse+type+url) telles kun én gang."""
    kjente = [k for k in kandidater if k.get("pakke_gram") is not None]
    unike = {}
    for k in sorted(
        kjente,
        key=lambda k: (k["pakke_gram"], _malttype_for_kandidat(k), k.get("url") or "", k.get("pris_raw") or 0),
    ):
        nokkel = (k["pakke_gram"], _malttype_for_kandidat(k), k.get("url") or "")
        if nokkel not in unike:
            unike[nokkel] = {
                "pakningsstorrelse_gram": k["pakke_gram"],
                "malttype": _malttype_for_kandidat(k),
                "pris": k.get("pris_raw"),
                "url": k.get("url") or "",
            }
    return list(unike.values())


def _bygg_vestbrygg_variantliste(kandidater):
    """Speiler _bygg_ol_variantliste() for Vestbryggs faktiske barn-
    /variantprodukter (se Steg F1/F2) — med ETT tillegg: "lagerstatus"
    ("pa_lager"/"utsolgt"/"ukjent"), lest ved skrapetidspunktet fra
    barn-sidens <body class="in-stock"|"not-in-stock">-signal, se
    modules/product_link_scraper.py::_lagerstatus_fra_html().

    Gruppering, deduplisering og rekkefølge er identisk med
    _bygg_ol_variantliste(). _bygg_ol_variantliste() selv er IKKE endret
    og får ikke noe lagerstatus-felt i denne runden — Ølbryggings egen
    lagerstatus-konvensjon er ikke undersøkt/bekreftet."""
    kjente = [k for k in kandidater if k.get("pakke_gram") is not None]
    unike = {}
    for k in sorted(
        kjente,
        key=lambda k: (k["pakke_gram"], _malttype_for_kandidat(k), k.get("url") or "", k.get("pris_raw") or 0),
    ):
        nokkel = (k["pakke_gram"], _malttype_for_kandidat(k), k.get("url") or "")
        if nokkel not in unike:
            unike[nokkel] = {
                "pakningsstorrelse_gram": k["pakke_gram"],
                "malttype": _malttype_for_kandidat(k),
                "pris": k.get("pris_raw"),
                "url": k.get("url") or "",
                "lagerstatus": k.get("lagerstatus") or "ukjent",
            }
    return list(unike.values())


_GYLDIGE_MALT_BUTIKKER = {"vestbrygg", "olbrygging"}


def _bygg_malt_matchresultat(malt_raw, master_malt, butikker):
    """Kjører selve matcher-hovedløkken (Steg F10D) — brukt IDENTISK av
    både den filskrivende og den lesende (dry-run) veien i
    match_store_data_to_master_malt(), slik at de aldri kan avvike.

    `master_malt` muteres ALDRI — en dyp kopi ("master_forslag") bygges
    og returneres i stedet, slik at kallerens innlastede master forblir
    urørt uansett om resultatet faktisk skrives til fil etterpå.

    `butikker` (set[str] | None) styrer KUN hvilke butikker som får lov
    til å skrive et forslag inn i master_forslag.butikk_match — matching,
    kandidatinnsamling, variantbygging og statistikk kjøres uendret for
    ALLE butikker uansett filter, slik at unmatched-lista og
    statistikk-tallene alltid reflekterer hele rådatasettet (se Fase 4/6
    i F10D-oppdraget). Filteret er allerede validert av kalleren.

    Returnerer {"master_forslag", "unmatched", "statistikk"}."""
    master_forslag = copy.deepcopy(master_malt)

    unmatched = []
    kandidater_per_slot = {}
    raw_per_butikk = {}
    matchet_per_butikk = {}
    unmatched_per_butikk = {}

    for raw in malt_raw:
        navn = raw.get("navn", "")
        butikk_key = _normaliser_butikk(raw.get("butikk", ""))
        pris_raw = raw.get("pris", 0)
        pakke_gram = raw.get("pakke_gram")
        url = raw.get("url", "")

        pris_kg = _pris_per_kg(pris_raw, pakke_gram, "malt")
        raw_per_butikk[butikk_key] = raw_per_butikk.get(butikk_key, 0) + 1

        master_id, _ = match_product_to_master(_strip_size(navn), master_forslag)
        logg_match_resultat(navn, master_id, butikk_key)

        if master_id:
            valider_url_match(master_id, master_forslag[master_id].get("display_name", master_id), url)
            kandidater_per_slot.setdefault((master_id, butikk_key), []).append({
                "navn": navn, "pris_kg": pris_kg, "pris_raw": pris_raw, "url": url,
                "pakke_gram": pakke_gram, "er_knust": raw.get("er_knust", False),
                "lagerstatus": raw.get("lagerstatus"),
            })
            matchet_per_butikk[butikk_key] = matchet_per_butikk.get(butikk_key, 0) + 1
        else:
            unmatched.append({
                "navn": navn, "butikk": butikk_key,
                "pris": pris_kg, "url": url,
                "kategori": raw.get("kategori", "malt"),
                "ebc": raw.get("ebc"), "status": "pending_review",
            })
            unmatched_per_butikk[butikk_key] = unmatched_per_butikk.get(butikk_key, 0) + 1

    slots_per_butikk = {}
    varianter_per_butikk = {}
    slots_oppdatert_per_butikk = {}
    berorte_master_ider = set()

    for (master_id, butikk_key), kandidater in kandidater_per_slot.items():
        slots_per_butikk[butikk_key] = slots_per_butikk.get(butikk_key, 0) + 1

        # Variantlisten analyseres for ALLE butikker uansett filter (ren
        # lesing, ingen skriving) — se Fase 4/10: Ølbrygging skal fortsatt
        # telles i statistikken selv når kun Vestbrygg aktiveres.
        if butikk_key == "olbrygging":
            varianter = _bygg_ol_variantliste(kandidater)
        elif butikk_key == "vestbrygg":
            varianter = _bygg_vestbrygg_variantliste(kandidater)
        else:
            varianter = []
        varianter_per_butikk[butikk_key] = varianter_per_butikk.get(butikk_key, 0) + len(varianter)

        if butikker is not None and butikk_key not in butikker:
            continue

        valgt = _velg_representativ_maltkandidat(kandidater)
        if len(kandidater) > 1:
            print(f"[VALGT] {butikk_key}: '{valgt['navn']}' foretrukket blant "
                  f"{len(kandidater)} pakningskandidater for '{master_id}'")
        if "butikk_match" not in master_forslag[master_id]:
            master_forslag[master_id]["butikk_match"] = {}
        if butikk_key not in master_forslag[master_id]["butikk_match"]:
            master_forslag[master_id]["butikk_match"][butikk_key] = {"pris": None, "url": None}
        master_forslag[master_id]["butikk_match"][butikk_key]["pris"] = valgt["pris_kg"]
        master_forslag[master_id]["butikk_match"][butikk_key]["url"] = valgt["url"]

        # Kun Ølbrygging får den fullstendige variantlisten i denne
        # runden (Steg D) — Vestbryggs løsvekt+sekk-modell er bevisst
        # ikke rørt, se modules/malt_packaging.py sin moduldokstreng.
        # Flate pris/url over forblir uendret og fungerer fortsatt som
        # fallback for enhver butikk uten "varianter".
        if varianter:
            master_forslag[master_id]["butikk_match"][butikk_key]["varianter"] = varianter

        slots_oppdatert_per_butikk[butikk_key] = slots_oppdatert_per_butikk.get(butikk_key, 0) + 1
        berorte_master_ider.add(master_id)

    statistikk = {
        "raw_totalt": len(malt_raw),
        "raw_per_butikk": raw_per_butikk,
        "matchet_per_butikk": matchet_per_butikk,
        "unmatched_per_butikk": unmatched_per_butikk,
        "slots_per_butikk": slots_per_butikk,
        "varianter_per_butikk": varianter_per_butikk,
        "slots_oppdatert_per_butikk": slots_oppdatert_per_butikk,
        "berorte_master_ider": sorted(berorte_master_ider),
        "matchet_totalt": sum(matchet_per_butikk.values()),
    }

    return {
        "master_forslag": master_forslag,
        "unmatched": unmatched,
        "statistikk": statistikk,
    }


def match_store_data_to_master_malt(malt_raw_path, master_malt_path, output_unmatched,
                                     butikker=None, dry_run=False):
    """
    Matcher scrapede malter mot master_malt aliases.
    Oppdaterer BARE pris/URL i master. Umatched → pending_review.

    Flere rå rader (ulike pakningsstørrelser/format hos samme butikk)
    kan matche samme (master_id, butikk) — se
    _maltkandidat_rangeringsnokkel(). Alle kandidater samles først i
    kandidater_per_slot og ÉN representativ rad velges deterministisk
    per (master_id, butikk) FØR noe skrives — i stedet for at siste
    behandlede rad ubetinget overskriver forrige (tidligere oppførsel,
    som gjorde butikk_match avhengig av rå-listens rekkefølge, som
    igjen er ustabil pga. Pythons hash-randomiserte set()-iterasjon i
    modules/product_link_scraper.py::finn_produktsider()).

    For Ølbrygging (Steg D) og Vestbrygg (Steg F1/F2) skrives i tillegg en
    fullstendig "varianter"-liste additivt ved siden av de flate
    pris/url-feltene — ALLE reelle pakningsalternativer (f.eks. 1/5/25 kg,
    hel/knust) bevares samlet slik at modules.malt_packaging kan bygge
    kjøpskombinasjoner, i stedet for at bare den ene representative raden
    overlever. Vestbryggs variantliste har i tillegg et "lagerstatus"-felt
    ("pa_lager"/"utsolgt"/"ukjent") — se _bygg_vestbrygg_variantliste() og
    modules/product_link_scraper.py::_lagerstatus_fra_html(). Ølbryggings
    variantliste (_bygg_ol_variantliste()) er urørt og har IKKE dette
    feltet.

    butikker (Steg F10D, valgfri): set[str] med "vestbrygg" og/eller
    "olbrygging", eller None (standard) for begge. Begrenser KUN hvilke
    butikker som får lov til å skrive et oppdatert butikk_match-forslag
    — matching og statistikk kjøres uansett for hele rådatasettet, og
    unmatched inneholder alltid alle butikker. Butikker utenfor filteret
    beholdes byte-for-byte uendret i master_forslag/masterfilen. Tomt
    sett eller ukjent butikknavn gir ValueError (sannsynlig kallerfeil).

    dry_run (Steg F10D, valgfri, standard False): når True skrives
    verken masterfil eller unmatched-fil — funksjonen returnerer i
    stedet et strukturert resultat i minnet:
    {"master_forslag", "unmatched", "statistikk", "butikker", "dry_run"}.
    Bruker NØYAKTIG samme matcher-/kandidat-/variant-/prislogikk som den
    filskrivende veien (se _bygg_malt_matchresultat()) — kun om
    resultatet skrives til fil og hva funksjonen returnerer skiller de
    to modiene.

    Når verken butikker eller dry_run oppgis er oppførselen og
    returverdien (matched_count, len(unmatched)) UENDRET fra før
    Steg F10D — eksisterende kallere (ui/import_panel.py og flere
    tester) er avhengige av nettopp denne tuppel-kontrakten.
    """
    if butikker is not None:
        if not butikker:
            raise ValueError(
                "butikker kan ikke være et tomt sett — bruk butikker=None for å behandle alle butikker."
            )
        ukjente = butikker - _GYLDIGE_MALT_BUTIKKER
        if ukjente:
            raise ValueError(
                f"Ukjent(e) butikk(er) i butikker-filter: {sorted(ukjente)}. "
                f"Gyldige verdier: {sorted(_GYLDIGE_MALT_BUTIKKER)}"
            )

    with open(malt_raw_path, "r", encoding="utf-8") as f:
        malt_raw = json.load(f)
    with open(master_malt_path, "r", encoding="utf-8") as f:
        master_malt = json.load(f)

    malt_raw = valider_raw_liste(malt_raw, "malt")
    valider_duplikat_aliaser(master_malt)

    resultat = _bygg_malt_matchresultat(malt_raw, master_malt, butikker)

    if dry_run:
        resultat["butikker"] = sorted(butikker) if butikker is not None else sorted(_GYLDIGE_MALT_BUTIKKER)
        resultat["dry_run"] = True
        return resultat

    skriv_master_json_atomisk(master_malt_path, resultat["master_forslag"])
    with open(output_unmatched, "w", encoding="utf-8") as f:
        json.dump(resultat["unmatched"], f, ensure_ascii=False, indent=2)

    return resultat["statistikk"]["matchet_totalt"], len(resultat["unmatched"])


def match_store_data_to_master_gjaer(gjaer_raw_path, master_gjaer_path, output_unmatched):
    """
    Matcher scrapede gjærsorter mot master_gjaer aliases.
    Oppdaterer BARE pris/URL i master. Umatched → pending_review.
    """
    with open(gjaer_raw_path, "r", encoding="utf-8") as f:
        gjaer_raw = json.load(f)
    with open(master_gjaer_path, "r", encoding="utf-8") as f:
        master_gjaer = json.load(f)

    gjaer_raw = valider_raw_liste(gjaer_raw, "gjaer")
    valider_duplikat_aliaser(master_gjaer)

    unmatched = []
    matched_count = 0

    for raw in gjaer_raw:
        navn = raw.get("navn", "")
        butikk_key = _normaliser_butikk(raw.get("butikk", ""))
        pris = raw.get("pris", 0)
        url = raw.get("url", "")

        master_id, _ = match_product_to_master(navn, master_gjaer)
        logg_match_resultat(navn, master_id, butikk_key)

        if master_id:
            valider_url_match(master_id, master_gjaer[master_id].get("display_name", master_id), url)
            if "butikk_match" not in master_gjaer[master_id]:
                master_gjaer[master_id]["butikk_match"] = {}
            if butikk_key not in master_gjaer[master_id]["butikk_match"]:
                master_gjaer[master_id]["butikk_match"][butikk_key] = {"pris": None, "url": None}
            master_gjaer[master_id]["butikk_match"][butikk_key]["pris"] = pris
            master_gjaer[master_id]["butikk_match"][butikk_key]["url"] = url
            matched_count += 1
        else:
            unmatched.append({
                "navn": navn, "butikk": butikk_key,
                "pris": pris, "url": url,
                "status": "pending_review",
            })

    skriv_master_json_atomisk(master_gjaer_path, master_gjaer)
    with open(output_unmatched, "w", encoding="utf-8") as f:
        json.dump(unmatched, f, ensure_ascii=False, indent=2)

    return matched_count, len(unmatched)


if __name__ == "__main__":
    matched, unmatched = match_store_data_to_master(
        "raw_data/humle_raw.json",
        "data/master_humle_v2.json",
        "raw_data/matched_hops.json",
        "raw_data/unmatched_hops.json",
    )
    print(f"Humle — Matched: {matched}, Unmatched: {unmatched}")

    matched, unmatched = match_store_data_to_master_malt(
        "raw_data/malt_raw.json",
        "data/master_malt.json",
        "raw_data/unmatched_malt.json",
    )
    print(f"Malt  — Matched: {matched}, Unmatched: {unmatched}")

    matched, unmatched = match_store_data_to_master_gjaer(
        "raw_data/gjaer_raw.json",
        "data/master_gjaer_v2.json",
        "raw_data/unmatched_gjaer.json",
    )
    print(f"Gjær  — Matched: {matched}, Unmatched: {unmatched}")
