import copy
import json
import re
from difflib import SequenceMatcher
from urllib.parse import unquote, urlparse

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
        pris = raw_produkt.get("pris")
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
    """Regner om råpris til kr/kg. Gjær returneres uendret.

    pris kan være None: scraperen skriver ikke lenger en fallback-pris
    når butikken ikke oppga noen (se modules/product_link_scraper.py).
    En ukjent pris skal forbli ukjent hele veien -- den skal ALDRI bli
    0 eller et regnestykke -- så None returneres uendret.
    """
    if pris is None:
        return None
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


# ══════════════════════════════════════════════════════════════════════
#  MATCHING PRECISION GUARD (Steg F11)
# ══════════════════════════════════════════════════════════════════════
# Bakgrunn: match_product_to_master() er ren strenglikhet (SequenceMatcher
# over master-aliaser, terskel 0,7). Et treff over terskelen ble tidligere
# skrevet DIREKTE inn i master["butikk_match"] uten noe menneskelig ledd.
# En live validering av Ølbrygging-malt viste at 14+ av 63 treff pekte på
# et helt annet produkt — f.eks. "Carafa 1 Malt" (900 EBC, brent) mot
# aliaset "Cara Malt" på caramalt_30 (30 EBC) med likhet 0,818.
#
# Prinsippet her er IKKE å fjerne fuzzy matching — den er fortsatt god
# til kandidatrangering. Prinsippet er at fuzzy score ALENE ikke skal
# være nok til en direkte skriving når det finnes sterke MOTSTRIDENDE
# identitetssignaler. Da går treffet til review i stedet, der mennesket
# allerede har et etablert verktøy (ui/review_panel.py).
#
# Alle tre signalene under er bevisst NEGATIVE: de kan bare nedgradere et
# treff fra AUTO_MATCH til REVIEW_REQUIRED. De kan aldri skape en match,
# aldri velge mellom kandidater, og aldri forkaste noe helt — butikkdata
# kan være feil og master kan være generisk, så et konfliktsignal betyr
# "et menneske må se på dette", ikke "dette er galt".
# Jf. KBH_CORE_CONTRACT § 9: ingen smart gjetting.

MATCH_AUTO = "auto_match"
MATCH_REVIEW = "review_required"
MATCH_UNMATCHED = "unmatched"

# ── Signal 1: EBC ─────────────────────────────────────────────────────
# EBC er den ene tallfestede, sammenlignbare egenskapen både butikk og
# master oppgir for malt, og den skiller produkttyper skarpt (pilsner 3,
# karamell 120, brent 1400).
#
# Ren absoluttdifferanse er ubrukelig over hele skalaen (3 mot 8 er en
# reell forskjell; 1175 mot 1300 er støy). Ren ratio er ubrukelig i
# bunnen (1 mot 4 EBC er ratio 4, men begge er lyse basismalter).
# Derfor kreves BEGGE terskler overskredet før noe regnes som konflikt:
#
#   _EBC_ABSOLUTT_SLINGRINGSMONN = 8 EBC
#       Under dette er avviket alltid innenfor normal variasjon mellom
#       produsenter og partier av samme malttype. Dekker hele
#       basismaltområdet, der ratioen er upålitelig.
#   _EBC_RATIO_GRENSE = 2.0
#       Over 8 EBC differanse kreves i tillegg at den ene er mer enn
#       DOBBELT så mørk som den andre. Bryggefaglig er en dobling av
#       farge en kategoriforskjell, ikke en variant av samme malt.
#
# Kalibrert mot ekte data (84 Ølbrygging-malter + de 119 radene i
# raw_data/malt_raw.json): fanger alle de dokumenterte fargekollisjonene
# (900/30, 320/3, 350/7, 150/10, 120/5, 90/15, 60/5, 200/70) uten å
# flagge reelle treff som Chocolate 1000/1175, Special B 300/350,
# Caraamber 80/70 eller Flaket mais 4/1.
#
# EBC = None (butikken oppga ingen — helt legitimt etter Supplier Data
# Cleanup V1) og EBC <= 0 (ingen reell måling, f.eks. den kjente
# URL-intervall-parsefeilen på "Torrified Wheat") gir ALDRI konflikt.
# Ukjent skal forbli ukjent, ikke bli til et negativt bevis.
_EBC_ABSOLUTT_SLINGRINGSMONN = 8.0
_EBC_RATIO_GRENSE = 2.0


def _ebc_konflikt(ebc_butikk, ebc_master):
    """True bare når to KJENTE, positive EBC-verdier er uforenlige."""
    if ebc_butikk is None or ebc_master is None:
        return False
    try:
        a, b = float(ebc_butikk), float(ebc_master)
    except (TypeError, ValueError):
        return False
    if a <= 0 or b <= 0:
        return False
    lav, hoy = min(a, b), max(a, b)
    if hoy - lav <= _EBC_ABSOLUTT_SLINGRINGSMONN:
        return False
    return (hoy / lav) > _EBC_RATIO_GRENSE


# ── Signal 2: produsent ───────────────────────────────────────────────
# McWeb (plattformen både vestbrygg.no og olbrygging.no kjører, se
# modules/product_link_scraper.py) bruker URL-grammatikken
# /<merke-eller-kategori>/<varenummer>/<slug>. Første segment er ofte
# produsenten — men IKKE alltid ("ekstrakt-spraymalt", "young-s",
# "tilbud" og lignende er kategorier, ikke merker).
#
# Segmentet godtas derfor bare som produsentsignal hvis det finnes i
# masterdatabasens EGET produsentvokabular (alle "produsent"-verdier i
# master, normalisert). Dette er datadrevet framfor en hardkodet liste:
# ukjente segmenter gir rett og slett INGEN signal, aldri en konflikt.
# Ingen enkeltprodukter er hardkodet noe sted.
_MCWEB_PRODUKTSTI_RE = re.compile(r"^/([^/]+)/\d{4,}/[^/]+/?$")

# Generiske produsentverdier er en eksplisitt "vi vet ikke / flere
# leverandører"-markering i master (f.eks. flaked_corn, roasted_barley)
# og skal aldri kunne stå i konflikt med noe.
_GENERISKE_PRODUSENTER = {"", "diverse", "ukjent", "unknown", "annet", "n/a"}

# Suffikser som beskriver SELSKAPSFORMEN, ikke merket: "Viking Malt",
# "viking-malt" og "Viking" er samme produsent. Lengst suffiks først, så
# "gaardsmalteri" ikke halveres av "malteri".
_PRODUSENT_SUFFIKS = (
    "gaardsmalteri", "gardsmalteri", "malteri", "maltings", "malting", "malz", "malt",
)


def _normaliser_produsentnavn(tekst):
    """Reduserer ett produsentnavn til én sammenlignbar nøkkel.

    Samme funksjon brukes på BEGGE sider (URL-segment og master sin
    "produsent"-verdi), slik at de aldri kan normaliseres ulikt:
      "simpsons-malt" / "Simpson's" / "Simpsons"   -> "simpson"
      "castle-malting" / "Castle Malting"          -> "castle"
      "bonsak-gårdsmalteri" / "Bonsak"             -> "bonsak"
      "jærmalt" / "Jærmalt"                        -> "jaer"
      "thomas-fawcetts" / "Thomas Fawcett"         -> "thomasfawcett"

    Rekkefølgen er viktig: selskapsform-suffikset fjernes FØR en
    avsluttende genitiv-/flertalls-s, ellers ender "simpsons-malt" på
    "simpsons" mens "Simpson's" ender på "simpson".
    """
    t = tekst.lower()
    for fra, til in (("æ", "ae"), ("ø", "o"), ("å", "aa"), ("ä", "a"),
                     ("ö", "o"), ("ü", "u"), ("é", "e"), ("è", "e")):
        t = t.replace(fra, til)
    t = re.sub(r"[^a-z0-9]+", "", t)
    for suffiks in _PRODUSENT_SUFFIKS:
        if t.endswith(suffiks) and len(t) > len(suffiks) + 2:
            t = t[: -len(suffiks)]
            break
    if t.endswith("s") and len(t) > 4:
        t = t[:-1]
    return t


def _produsenttokens(produsent_tekst):
    """Master lagrer noen ganger FLERE produsenter i ett felt ("Viking /
    Weyermann", "Brewferm / Castle Malting") — da er alle gyldige, og et
    treff mot én av dem er nok. Returnerer derfor et sett."""
    if not produsent_tekst:
        return frozenset()
    tokens = set()
    for bit in re.split(r"[/,+&]| og ", str(produsent_tekst)):
        bit = bit.strip()
        if not bit or bit.lower() in _GENERISKE_PRODUSENTER:
            continue
        normalisert = _normaliser_produsentnavn(bit)
        if normalisert:
            tokens.add(normalisert)
    return frozenset(tokens)


def _produsentvokabular(master):
    """Alle produsenter masterdatabasen faktisk kjenner til. Brukes som
    filter på URL-segmenter — se _produsentsignal()."""
    vokabular = set()
    for entry in master.values():
        vokabular |= _produsenttokens(entry.get("produsent"))
    return frozenset(vokabular)


def _produsentsignal(raw, vokabular):
    """Produsenten butikkraden faktisk gir uttrykk for, eller et tomt
    sett når vi ikke vet. URL-segmentet er primærkilden (mest pålitelig
    — butikken plasserer selv produktet under merket); rå-radens
    "produsent"-felt (utledet fra navn/beskrivelse i
    product_link_scraper) er sekundært. Begge må ligge i master sitt eget
    vokabular for å telle."""
    sti = urlparse(raw.get("url") or "").path
    treff = _MCWEB_PRODUKTSTI_RE.match(sti)
    if treff:
        token = _normaliser_produsentnavn(unquote(treff.group(1)))
        if token in vokabular:
            return frozenset([token])
    fra_felt = _produsenttokens(raw.get("produsent"))
    return frozenset(t for t in fra_felt if t in vokabular)


def _produsentkonflikt(raw, master_entry, vokabular):
    """True bare når BEGGE sider oppgir en kjent, ikke-generisk produsent
    og settene er disjunkte. Ukjent produsent på én av sidene er aldri en
    konflikt — fravær av bevis er ikke motbevis."""
    butikk = _produsentsignal(raw, vokabular)
    master = _produsenttokens(master_entry.get("produsent"))
    if not butikk or not master:
        return False
    return not (butikk & master)


# ── Signal 3: råvare/korntype ─────────────────────────────────────────
# Fuzzy matching er blind for at "Flaket ris" og "Flaket mais" er to
# ulike råvarer — likhet 0,857, og begge har lav EBC og generisk
# produsent, så verken signal 1 eller 2 fanger dem.
#
# Bevisst holdt til ÉN liten, lukket gruppe: hvilket korn/råstoff
# produktet er laget av. Dette er en objektiv, gjensidig utelukkende
# egenskap, ikke en smakstolkning. Det er IKKE starten på en generell
# regelmotor — adjektivpar som light/dark, pilsner/special og cara/carafa
# dekkes allerede av EBC-signalet, og er derfor bevisst utelatt framfor å
# bygge stadig flere navnespesifikke regler.
_KORNORD = {
    "ris": "ris", "rice": "ris",
    "mais": "mais", "maize": "mais", "corn": "mais",
    "hvete": "hvete", "hvetemalt": "hvete", "wheat": "hvete", "weizen": "hvete",
    "rug": "rug", "rugmalt": "rug", "rye": "rug", "roggen": "rug",
    "havre": "havre", "havremalt": "havre", "oat": "havre", "oats": "havre",
    "bygg": "bygg", "barley": "bygg",
    "spelt": "spelt", "speltmalt": "spelt",
}
_KORN_TOKEN_RE = re.compile(r"[a-zæøåA-ZÆØÅ]+")


def _kornsignal(tekst):
    """Tokenbasert (aldri substreng): "Crisp" inneholder bokstavrekken
    "ris", men er et annet ord og skal ikke telle som råvaren ris."""
    return frozenset(
        _KORNORD[t.lower()] for t in _KORN_TOKEN_RE.findall(tekst or "")
        if t.lower() in _KORNORD
    )


def _master_korntekst(master_entry):
    """Master-siden leses fra display_name + ALLE aliaser, ikke bare det
    ene aliaset som tilfeldigvis ga treffet — korntypen står ofte bare i
    ett av dem ("Flaked Corn", "Flaket Mais", "Maize")."""
    return " ".join(
        [master_entry.get("display_name") or ""]
        + list(master_entry.get("aliases") or [])
    )


def _kornkonflikt(raw, master_entry):
    butikk = _kornsignal(raw.get("navn"))
    if not butikk:
        return False
    master = _kornsignal(_master_korntekst(master_entry))
    if not master:
        return False
    return not (butikk & master)


def vurder_maltmatch(raw, master_entry, produsent_vokabular):
    """Vurderer ETT fuzzy-treff og returnerer listen over motstridende
    identitetssignaler. Tom liste => AUTO_MATCH, ellers REVIEW_REQUIRED.

    Ren funksjon: leser bare, muterer ingenting, og kaller aldri
    matcheren selv — den får treffet inn og sier bare om det er trygt nok
    til å skrives uten menneskelig godkjenning."""
    konflikter = []
    if _ebc_konflikt(raw.get("ebc"), master_entry.get("ebc")):
        konflikter.append({
            "signal": "ebc",
            "butikk": raw.get("ebc"),
            "master": master_entry.get("ebc"),
            "forklaring": (
                "EBC {} (butikk) mot {} (master) — mer enn {:g}x forskjell "
                "og over {:g} EBC i absolutt avvik.".format(
                    raw.get("ebc"), master_entry.get("ebc"),
                    _EBC_RATIO_GRENSE, _EBC_ABSOLUTT_SLINGRINGSMONN,
                )
            ),
        })
    if _produsentkonflikt(raw, master_entry, produsent_vokabular):
        konflikter.append({
            "signal": "produsent",
            "butikk": sorted(_produsentsignal(raw, produsent_vokabular)),
            "master": sorted(_produsenttokens(master_entry.get("produsent"))),
            "forklaring": (
                "Butikken fører produktet under en annen produsent enn "
                "master oppgir ({}).".format(master_entry.get("produsent"))
            ),
        })
    if _kornkonflikt(raw, master_entry):
        konflikter.append({
            "signal": "korn",
            "butikk": sorted(_kornsignal(raw.get("navn"))),
            "master": sorted(_kornsignal(_master_korntekst(master_entry))),
            "forklaring": "Produktene er laget av ulikt korn/råstoff.",
        })
    return konflikter


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

    Steg F11 (matching precision guard): et fuzzy-treff skrives bare inn
    i master_forslag når vurder_maltmatch() ikke finner noe motstridende
    identitetssignal (EBC, produsent, korntype). Treff MED konflikt blir
    ikke forkastet -- de legges i den samme `unmatched`-lista med
    status=MATCH_REVIEW og feltene "foreslatt_master_id"/"foreslatt_navn"/
    "konflikter", slik at den eksisterende review-flyten
    (raw_data/unmatched_*.json -> ui/review_panel.py) plukker dem opp uten
    noe nytt UI. Ingenting skrives til butikk_match for slike rader.

    Returnerer {"master_forslag", "unmatched", "statistikk"}."""
    master_forslag = copy.deepcopy(master_malt)
    produsent_vokabular = _produsentvokabular(master_forslag)

    unmatched = []
    kandidater_per_slot = {}
    raw_per_butikk = {}
    matchet_per_butikk = {}
    unmatched_per_butikk = {}
    review_per_butikk = {}

    for raw in malt_raw:
        navn = raw.get("navn", "")
        butikk_key = _normaliser_butikk(raw.get("butikk", ""))
        pris_raw = raw.get("pris")
        pakke_gram = raw.get("pakke_gram")
        url = raw.get("url", "")

        pris_kg = _pris_per_kg(pris_raw, pakke_gram, "malt")
        raw_per_butikk[butikk_key] = raw_per_butikk.get(butikk_key, 0) + 1

        master_id, _ = match_product_to_master(_strip_size(navn), master_forslag)
        logg_match_resultat(navn, master_id, butikk_key)

        # Et fuzzy-treff er en KANDIDAT, ikke et vedtak. Precision guard
        # (Steg F11) ser etter motstridende identitetssignaler før noe
        # får lov til å bli skrevet inn i butikk_match — se
        # vurder_maltmatch(). Treff med konflikt går til review i stedet
        # for å bli forkastet: butikkdata kan være feil, master kan være
        # generisk, og bare et menneske kan avgjøre hvilken det er.
        konflikter = (
            vurder_maltmatch(raw, master_forslag[master_id], produsent_vokabular)
            if master_id else []
        )

        if master_id and not konflikter:
            valider_url_match(master_id, master_forslag[master_id].get("display_name", master_id), url)
            kandidater_per_slot.setdefault((master_id, butikk_key), []).append({
                "navn": navn, "pris_kg": pris_kg, "pris_raw": pris_raw, "url": url,
                "pakke_gram": pakke_gram, "er_knust": raw.get("er_knust", False),
                "lagerstatus": raw.get("lagerstatus"),
            })
            matchet_per_butikk[butikk_key] = matchet_per_butikk.get(butikk_key, 0) + 1
        elif master_id:
            print(f"[REVIEW] {butikk_key}: '{navn}' -> '{master_id}' holdt tilbake "
                  f"({', '.join(k['signal'] for k in konflikter)})")
            unmatched.append({
                "navn": navn, "butikk": butikk_key,
                "pris": pris_kg, "url": url,
                "kategori": raw.get("kategori", "malt"),
                "ebc": raw.get("ebc"), "status": MATCH_REVIEW,
                # Kandidaten kastes IKKE — den følger med som forslag, så
                # review-panelet kan forhåndsvelge den og vise hvorfor den
                # ikke ble skrevet automatisk.
                "foreslatt_master_id": master_id,
                "foreslatt_navn": master_forslag[master_id].get("display_name", master_id),
                "konflikter": konflikter,
            })
            review_per_butikk[butikk_key] = review_per_butikk.get(butikk_key, 0) + 1
            unmatched_per_butikk[butikk_key] = unmatched_per_butikk.get(butikk_key, 0) + 1
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
        # Steg F11: "matchet" over betyr fortsatt NØYAKTIG det samme som
        # før -- rader som faktisk får skrive et butikk_match-forslag,
        # dvs. AUTO_MATCH. Review-tallene kommer i tillegg, additivt, og
        # er allerede talt med i unmatched_per_butikk (review-elementene
        # havner i den samme unmatched-lista, se _bygg_malt_matchresultat).
        "review_required_per_butikk": review_per_butikk,
        "review_required_totalt": sum(review_per_butikk.values()),
        "auto_match_totalt": sum(matchet_per_butikk.values()),
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

    Steg F11: en match må i tillegg passere precision guarden
    (vurder_maltmatch()) for å bli skrevet. Kandidater med motstridende
    identitetssignal går til review_required i unmatched-fila i stedet.
    Returverdien (matchet_totalt, len(unmatched)) beholder sin
    opprinnelige betydning: antall rader som FAKTISK ble skrevet, og
    antall rader som venter på et menneske.

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
        pris = raw.get("pris")
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
