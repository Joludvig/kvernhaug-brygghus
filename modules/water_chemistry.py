# modules/water_chemistry.py
"""
Vannkjemi — HVILKET VANN ølet brygges med og hvordan det justeres med salter/
syrer, helt adskilt fra ingrediensoppskriften (malt/humle/gjær),
prosessprofilen (modules/process_profiles.py) og utstyrsprofilen
(modules/equipment.py). Å endre vannbehandlingen skal ALDRI endre disse.

Ren Python, ingen Streamlit-avhengighet — samme mønster som
modules/process_profiles.py og modules/style_engine.py.

Alle ionverdier (Ca, Mg, Na, Cl, SO4, HCO3) er i mg/L (= ppm for vann).
Alkalitet finnes i TRE ulike, ofte forvekslede former — bland dem ALDRI
uten å gå via konverteringsfunksjonene under:
  - HCO3 i mg/L (selve bikarbonat-ionet)
  - Alkalitet som CaCO3 i mg/L ("as CaCO3" — vanlig i norske vannrapporter)
  - Alkalitet i mmol/L (molar/ekvivalent alkalitet)
"""
import copy
import json
import os

from config import DEMO_MODE

# ══════════════════════════════════════════════════════════════════════════
# KILDE- OG MÅLPROFILER PÅ DISK
# ══════════════════════════════════════════════════════════════════════════
# Filstiene leses FRISKT ved hvert kall (aldri frosset i en modulnivå-
# konstant) — samme begrunnelse og samme mønster som _mappe() i
# modules/recipe_storage.py: KVERNHAUG_WATER_SOURCES_FILE/
# KVERNHAUG_WATER_TARGETS_FILE finnes KUN for testisolasjon, og en frosset
# konstant kunne la en tidlig import (av en HELT ANNEN testmodul) permanent
# låse stien til den EKTE data-filen før en senere tests setUp() rakk å
# sette miljøvariabelen.

def _vannkilder_fil():
    return os.getenv("KVERNHAUG_WATER_SOURCES_FILE", os.path.join("data", "water_sources.json"))


def _vannmaal_fil():
    return os.getenv("KVERNHAUG_WATER_TARGETS_FILE", os.path.join("data", "water_targets.json"))


def _last_json(filsti):
    try:
        with open(filsti, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _lagre_json(filsti, data):
    mappe = os.path.dirname(filsti)
    if mappe:
        os.makedirs(mappe, exist_ok=True)
    with open(filsti, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def last_vannkilder():
    """Alle lagrede kildevannsprofiler — kart water_id -> profil-dict."""
    return _last_json(_vannkilder_fil())


def lagre_vannkilder(kilder):
    """Persisterer HELE kart av kildevannsprofiler (bruker legger til/endrer
    én profil i kartet før kall — se ui/water_panel.py). No-op i DEMO_MODE
    -- samme mønster som modules/recipe_storage.py, modules/pantry.py,
    modules/humle_lager.py og modules/equipment.py."""
    if DEMO_MODE:
        return
    _lagre_json(_vannkilder_fil(), kilder)


def last_vannmaal():
    """Alle lagrede målprofiler — kart target_id -> profil-dict."""
    return _last_json(_vannmaal_fil())


def lagre_vannmaal(maalprofiler):
    """Persisterer HELE kart av målprofiler. No-op i DEMO_MODE -- se
    lagre_vannkilder()."""
    if DEMO_MODE:
        return
    _lagre_json(_vannmaal_fil(), maalprofiler)


# ══════════════════════════════════════════════════════════════════════════
# ALKALITET — konvertering mellom HCO3 (mg/L), CaCO3 (mg/L) og mmol/L
# ══════════════════════════════════════════════════════════════════════════
# Molmasse HCO3- = 61.017 g/mol (H 1.008 + C 12.011 + O3 47.997).
# CaCO3 har 2 ekvivalenter per mol (nøytraliserer 2 H+), så ekvivalentvekten
# (brukt til å regne om til/fra mmol/L alkalitet) er halve molmassen.
_HCO3_MOLMASSE = 61.017
_CACO3_MOLMASSE = 100.086
_CACO3_EKVIVALENTVEKT = _CACO3_MOLMASSE / 2  # 50.043 mg per mmol alkalitet


def hco3_mg_l_til_alkalitet_mmol_l(hco3_mg_l):
    """HCO3 (mg/L) -> alkalitet (mmol/L)."""
    if hco3_mg_l is None:
        return None
    return hco3_mg_l / _HCO3_MOLMASSE


def alkalitet_mmol_l_til_hco3_mg_l(mmol_l):
    """Alkalitet (mmol/L) -> HCO3 (mg/L)."""
    if mmol_l is None:
        return None
    return mmol_l * _HCO3_MOLMASSE


def alkalitet_mmol_l_til_caco3_mg_l(mmol_l):
    """Alkalitet (mmol/L) -> alkalitet som CaCO3 (mg/L)."""
    if mmol_l is None:
        return None
    return mmol_l * _CACO3_EKVIVALENTVEKT


def caco3_mg_l_til_alkalitet_mmol_l(caco3_mg_l):
    """Alkalitet som CaCO3 (mg/L) -> alkalitet (mmol/L)."""
    if caco3_mg_l is None:
        return None
    return caco3_mg_l / _CACO3_EKVIVALENTVEKT


def hco3_mg_l_til_caco3_mg_l(hco3_mg_l):
    """HCO3 (mg/L) -> alkalitet som CaCO3 (mg/L)."""
    return alkalitet_mmol_l_til_caco3_mg_l(hco3_mg_l_til_alkalitet_mmol_l(hco3_mg_l))


def caco3_mg_l_til_hco3_mg_l(caco3_mg_l):
    """Alkalitet som CaCO3 (mg/L) -> HCO3 (mg/L)."""
    return alkalitet_mmol_l_til_hco3_mg_l(caco3_mg_l_til_alkalitet_mmol_l(caco3_mg_l))


def normaliser_alkalitet(verdi, grunnlag):
    """
    Tar én oppgitt alkalitetsverdi PLUSS hvilket grunnlag den er oppgitt i
    ("hco3_mg_l", "caco3_mg_l" eller "mmol_l") og returnerer alle tre formene
    — slik at UI/eksport ALDRI kan vise feil form ved en forglemmelse. Merker
    alltid hvilket grunnlag den opprinnelige verdien faktisk hadde.
    """
    if verdi is None:
        return {"hco3_mg_l": None, "caco3_mg_l": None, "mmol_l": None, "opprinnelig_grunnlag": grunnlag}
    if grunnlag == "hco3_mg_l":
        return {
            "hco3_mg_l": verdi,
            "caco3_mg_l": hco3_mg_l_til_caco3_mg_l(verdi),
            "mmol_l": hco3_mg_l_til_alkalitet_mmol_l(verdi),
            "opprinnelig_grunnlag": grunnlag,
        }
    if grunnlag == "caco3_mg_l":
        return {
            "hco3_mg_l": caco3_mg_l_til_hco3_mg_l(verdi),
            "caco3_mg_l": verdi,
            "mmol_l": caco3_mg_l_til_alkalitet_mmol_l(verdi),
            "opprinnelig_grunnlag": grunnlag,
        }
    if grunnlag == "mmol_l":
        return {
            "hco3_mg_l": alkalitet_mmol_l_til_hco3_mg_l(verdi),
            "caco3_mg_l": alkalitet_mmol_l_til_caco3_mg_l(verdi),
            "mmol_l": verdi,
            "opprinnelig_grunnlag": grunnlag,
        }
    raise ValueError(f"Ukjent alkalitetsgrunnlag: {grunnlag!r}")


# ══════════════════════════════════════════════════════════════════════════
# IONER — de seks ionene appen sporer for enhver vannprofil
# ══════════════════════════════════════════════════════════════════════════
IONER = ["ca", "mg", "na", "cl", "so4", "hco3"]


def tomt_kildevann():
    """En 'ukjent kilde' — ALLE ioner None, ALDRI diktet opp av appen."""
    return {ion: None for ion in IONER}


# ══════════════════════════════════════════════════════════════════════════
# SALTDATABASE
# ══════════════════════════════════════════════════════════════════════════
# Ionfraksjoner er massefraksjoner (gram ion per gram salt), utledet fra
# atommasser (Ca 40.078, Mg 24.305, Na 22.990, Cl 35.453, S 32.06, O 15.999,
# H 1.008, C 12.011). Vannfritt CaCl2 og CaCl2·2H2O behandles BEVISST som to
# separate produkter — krystallvannet endrer molmassen og dermed hvor mye
# reelt ion man får per gram innveid salt.
SALTER = {
    "cacl2_2h2o": {
        "salt_id": "cacl2_2h2o",
        "navn": "Kalsiumklorid-dihydrat",
        "formel": "CaCl2·2H2O",
        "molmasse_g_mol": 147.016,
        "hydreringsform": "dihydrat",
        "ionfraksjoner": {"ca": 0.27261, "cl": 0.48226},
        "standard_renhet": 1.0,
        "advarsler": [],
    },
    "cacl2_vannfri": {
        "salt_id": "cacl2_vannfri",
        "navn": "Kalsiumklorid (vannfri)",
        "formel": "CaCl2",
        "molmasse_g_mol": 110.984,
        "hydreringsform": "vannfri",
        "ionfraksjoner": {"ca": 0.36112, "cl": 0.63888},
        "standard_renhet": 1.0,
        "advarsler": [
            "Vannfri CaCl2 er sterkt hygroskopisk og gir MER ion per gram enn "
            "dihydratformen — bland aldri sammen doseringer for de to.",
        ],
    },
    "gips": {
        "salt_id": "gips",
        "navn": "Gips",
        "formel": "CaSO4·2H2O",
        "molmasse_g_mol": 172.171,
        "hydreringsform": "dihydrat",
        "ionfraksjoner": {"ca": 0.23279, "so4": 0.55795},
        "standard_renhet": 1.0,
        "advarsler": [],
    },
    "epsomsalt": {
        "salt_id": "epsomsalt",
        "navn": "Epsomsalt",
        "formel": "MgSO4·7H2O",
        "molmasse_g_mol": 246.475,
        "hydreringsform": "heptahydrat",
        "ionfraksjoner": {"mg": 0.09861, "so4": 0.38975},
        "standard_renhet": 1.0,
        "advarsler": [],
    },
    "vanlig_salt": {
        "salt_id": "vanlig_salt",
        "navn": "Vanlig salt",
        "formel": "NaCl",
        "molmasse_g_mol": 58.443,
        "hydreringsform": "vannfri",
        "ionfraksjoner": {"na": 0.39337, "cl": 0.60663},
        "standard_renhet": 1.0,
        "advarsler": [],
    },
    "natron": {
        "salt_id": "natron",
        "navn": "Natron",
        "formel": "NaHCO3",
        "molmasse_g_mol": 84.007,
        "hydreringsform": "vannfri",
        "ionfraksjoner": {"na": 0.27366, "hco3": 0.72634},
        "standard_renhet": 1.0,
        "advarsler": [],
    },
    "kalsiumkarbonat": {
        "salt_id": "kalsiumkarbonat",
        "navn": "Kalsiumkarbonat",
        "formel": "CaCO3",
        "molmasse_g_mol": 100.086,
        "hydreringsform": "vannfri",
        # HCO3-fraksjonen antar at karbonatet løses som bikarbonat ved hjelp
        # av CO2 i mesken (CaCO3 + CO2 + H2O -> Ca2+ + 2 HCO3-) — derfor > 1.0
        # gram HCO3 per gram innveid CaCO3. Se advarsel under.
        "ionfraksjoner": {"ca": 0.40044, "hco3": 1.21935},
        "standard_renhet": 1.0,
        "advarsler": [
            "Svært lav løselighet i vann uten CO2 — i praksis løses ofte "
            "mindre enn beregnet, og effekten er langsom og vanskelig å "
            "forutsi presist. Foretrekk normalt natron for HCO3-justering.",
        ],
    },
}

_SALT_REKKEFOLGE = [
    "cacl2_2h2o", "cacl2_vannfri", "gips", "epsomsalt",
    "vanlig_salt", "natron", "kalsiumkarbonat",
]


def hent_salt(salt_id):
    """Henter en DYP KOPI av salt-definisjonen (samme mønster som
    process_profiles.hent_standardprofil — kallere skal aldri kunne mutere
    selve databasen)."""
    if salt_id not in SALTER:
        raise KeyError(f"Ukjent salt_id: {salt_id!r}")
    return copy.deepcopy(SALTER[salt_id])


def alle_salter():
    """Saltdatabasen i visningsrekkefølge (liste av dicts)."""
    return [hent_salt(sid) for sid in _SALT_REKKEFOLGE]


# ══════════════════════════════════════════════════════════════════════════
# IONBEREGNING
# ══════════════════════════════════════════════════════════════════════════

def beregn_ion_bidrag_ppm(gram_salt, ionfraksjon, renhet, vannvolum_liter):
    """tilført_ppm = gram_salt × ionfraksjon × renhet × 1000 / vannvolum_liter.

    Full presisjon internt — avrunding skjer kun i UI/eksport."""
    if not vannvolum_liter or vannvolum_liter <= 0:
        return 0.0
    return gram_salt * ionfraksjon * renhet * 1000.0 / vannvolum_liter


def gram_for_onsket_ppm(onsket_ppm, ionfraksjon, renhet, vannvolum_liter):
    """Inverst av beregn_ion_bidrag_ppm — hvor mange gram salt trengs for å
    løfte ett ion med `onsket_ppm` i `vannvolum_liter`. Brukt av
    foreslaa_salter(). Returnerer aldri negative mengder."""
    if not vannvolum_liter or vannvolum_liter <= 0 or not ionfraksjon or not renhet:
        return 0.0
    return max(0.0, onsket_ppm * vannvolum_liter / (ionfraksjon * renhet * 1000.0))


def beregn_saltbidrag(salt_id, gram, renhet, vannvolum_liter):
    """Ionbidrag (ppm) fra ÉN salttilsetning, ett ion per nøkkel."""
    salt = hent_salt(salt_id)
    renhet = renhet if renhet is not None else salt["standard_renhet"]
    return {
        ion: beregn_ion_bidrag_ppm(gram, fraksjon, renhet, vannvolum_liter)
        for ion, fraksjon in salt["ionfraksjoner"].items()
    }


def summer_ionbidrag(bidrag_liste):
    """Summerer flere salters ionbidrag uten dobbelttelling — hvert salts
    bidrag telles nøyaktig én gang inn i summen per ion."""
    total = {ion: 0.0 for ion in IONER}
    for bidrag in bidrag_liste:
        for ion, ppm in bidrag.items():
            total[ion] = total.get(ion, 0.0) + ppm
    return total


def beregn_sluttprofil(kildevann, salttilsetninger, vannvolum_liter):
    """
    slutt_ppm = start_ppm + sum(tilført_ppm).

    `salttilsetninger`: liste av {"salt_id", "gram", "renhet"} — `gram` er
    TOTAL mengde tilsatt i nettopp `vannvolum_liter`.

    Er kildevannets ion None ("ukjent"), forblir sluttverdien None — appen
    dikter aldri opp et tall den ikke har grunnlag for.

    Returnerer {"start": {...}, "tilfort": {...}, "slutt": {...}}.
    """
    bidrag_per_salt = [
        beregn_saltbidrag(s["salt_id"], s["gram"], s.get("renhet"), vannvolum_liter)
        for s in salttilsetninger
    ]
    tilfort = summer_ionbidrag(bidrag_per_salt)
    slutt = {}
    for ion in IONER:
        start_v = kildevann.get(ion)
        slutt[ion] = None if start_v is None else start_v + tilfort.get(ion, 0.0)
    return {
        "start": {ion: kildevann.get(ion) for ion in IONER},
        "tilfort": tilfort,
        "slutt": slutt,
    }


def cl_so4_forhold(cl_ppm, so4_ppm):
    """Klorid/sulfat-forhold — kun en enkel referanse, ALDRI det eneste
    kvalitetsmålet (se advarsel i UI: absolutte ionnivåer vises tydeligere)."""
    if not cl_ppm or not so4_ppm:
        return None
    return round(cl_ppm / so4_ppm, 2)


# ══════════════════════════════════════════════════════════════════════════
# FORDELING MESK / SKYLLING
# ══════════════════════════════════════════════════════════════════════════
PROPORSJONAL = "proporsjonal"
ALT_I_MESK = "alt_i_mesk"
EGENDEFINERT_FORDELING = "egendefinert"


def fordel_salttilsetning(total_gram, meskevann_l, skyllevann_l, metode=PROPORSJONAL, egendefinert_meskeandel=None):
    """Fordeler ÉN salttilsetnings totalmengde mellom meske- og skyllevann.
    `gram_mesk + gram_skyll` er ALLTID nøyaktig lik `total_gram` (skylle-
    andelen regnes som resten, ikke som en egen multiplikasjon) — garanterer
    at saltet aldri dobbelttelles eller "forsvinner" i avrunding."""
    if metode == ALT_I_MESK:
        return {"gram_mesk": total_gram, "gram_skyll": 0.0}

    if metode == EGENDEFINERT_FORDELING:
        andel = 0.5 if egendefinert_meskeandel is None else max(0.0, min(egendefinert_meskeandel, 1.0))
    else:  # proporsjonal (standard)
        total_vann = meskevann_l + skyllevann_l
        andel = (meskevann_l / total_vann) if total_vann > 0 else 1.0

    gram_mesk = total_gram * andel
    return {"gram_mesk": gram_mesk, "gram_skyll": total_gram - gram_mesk}


def fordel_alle_salter(saltliste, meskevann_l, skyllevann_l, metode=PROPORSJONAL, egendefinert_meskeandel=None):
    """Samme som fordel_salttilsetning(), men for en hel liste med salter.
    Returnerer hvert salt sitt eget dict utvidet med gram_mesk/gram_skyll."""
    return [
        {**s, **fordel_salttilsetning(s["gram"], meskevann_l, skyllevann_l, metode, egendefinert_meskeandel)}
        for s in saltliste
    ]


# ══════════════════════════════════════════════════════════════════════════
# MÅLPROFIL-EVALUERING
# ══════════════════════════════════════════════════════════════════════════

def status_for_ion(verdi, min_v, max_v):
    """"innenfor" / "under" / "over" / "ukjent" (verdi eller målgrense mangler)."""
    if verdi is None or min_v is None or max_v is None:
        return "ukjent"
    if verdi < min_v:
        return "under"
    if verdi > max_v:
        return "over"
    return "innenfor"


def bygg_ionrapport(sluttprofil, maalprofil):
    """Rader til UI-tabellen: Ion | Start | Tilført | Ferdig | Mål | Status."""
    maalprofil = maalprofil or {}
    rows = []
    for ion in IONER:
        min_v = maalprofil.get(f"{ion}_min")
        max_v = maalprofil.get(f"{ion}_max")
        slutt_v = sluttprofil["slutt"].get(ion)
        rows.append({
            "ion": ion,
            "start": sluttprofil["start"].get(ion),
            "tilfort": sluttprofil["tilfort"].get(ion),
            "slutt": slutt_v,
            "maal_min": min_v,
            "maal_maks": max_v,
            "status": status_for_ion(slutt_v, min_v, max_v),
        })
    return rows


# ══════════════════════════════════════════════════════════════════════════
# VARSLER
# ══════════════════════════════════════════════════════════════════════════
# Moderate, dokumenterte tommelfingerregler for BRYGGING — IKKE offisielle
# drikkevannsgrenser for helse. Fritt konfigurerbare via `grenser=`-
# parameteren til generer_varsler().
STANDARD_VARSELGRENSER = {
    "na_hoy_ppm": 30.0,
    "mg_hoy_ppm": 15.0,
    "cl_svaert_hoy_ppm": 150.0,
    "so4_svaert_hoy_ppm": 150.0,
    "ca_lav_ppm": 40.0,
    # Na/Mg/Cl/SO4 har alle en "høy"-terskel over — Ca hadde tidligere KUN
    # en lav-terskel (Water Recommendation Quality Audit V1, Steg F12).
    # 150 ppm er ingen kjemisk faregrense (se moduldokstrengen over: dette
    # er husregler, ikke helsegrenser) -- det er nøyaktig toppen av det
    # høyeste ca_max blant KBHs egne målprofiler i dag
    # (data/water_targets.json::humledrevet_ol), så varselet utløses ALDRI
    # av en Ca-verdi noen eksisterende husprofil selv regner som normal —
    # kun når kalsium går tydelig UTOVER det enhver husprofil ber om.
    "ca_hoy_ppm": 150.0,
    "vekt_opplosning_g": 0.1,
}


def generer_varsler(kildevann, maalprofil, sluttprofil, salt_fordeling, syrer=None, grenser=None):
    """Bygger tekstvarsler for UI-panelet. Se STANDARD_VARSELGRENSER for
    hvilke terskler som brukes og at de er husregler, ikke helsegrenser."""
    grenser = {**STANDARD_VARSELGRENSER, **(grenser or {})}
    salt_fordeling = salt_fordeling or []
    syrer = syrer or []
    varsler = []

    if all(kildevann.get(ion) is None for ion in IONER):
        varsler.append("Kildevann er ukjent — ingen ionverdier er registrert. Appen dikter ikke opp tall.")
    elif kildevann.get("hco3") is None:
        varsler.append("Alkalitet/HCO3 mangler for kildevannet — meske-pH-vurderingen blir mindre pålitelig.")

    for s in salt_fordeling:
        if 0 < s.get("gram", 0.0) < grenser["vekt_opplosning_g"]:
            navn = hent_salt(s["salt_id"])["navn"]
            varsler.append(
                f"{navn}: total mengde ({s['gram']:.3f} g) er under vektens "
                f"praktiske oppløsning ({grenser['vekt_opplosning_g']:.2f} g) — "
                "vurder å lage en fortynnet stamløsning."
            )

    slutt = sluttprofil["slutt"]
    if slutt.get("na") is not None and slutt["na"] > grenser["na_hoy_ppm"]:
        varsler.append(f"Høyt natrium: {slutt['na']:.1f} ppm (grense {grenser['na_hoy_ppm']:.0f} ppm) — kan gi salt/skarp smak.")
    if slutt.get("mg") is not None and slutt["mg"] > grenser["mg_hoy_ppm"]:
        varsler.append(f"Høyt magnesium: {slutt['mg']:.1f} ppm (grense {grenser['mg_hoy_ppm']:.0f} ppm) — kan gi bitter/skarp bismak.")
    if slutt.get("cl") is not None and slutt["cl"] > grenser["cl_svaert_hoy_ppm"]:
        varsler.append(f"Svært høyt klorid: {slutt['cl']:.1f} ppm (grense {grenser['cl_svaert_hoy_ppm']:.0f} ppm).")
    if slutt.get("so4") is not None and slutt["so4"] > grenser["so4_svaert_hoy_ppm"]:
        varsler.append(f"Svært høyt sulfat: {slutt['so4']:.1f} ppm (grense {grenser['so4_svaert_hoy_ppm']:.0f} ppm) — kan gi skarp/tørr bitterhet.")
    if slutt.get("ca") is not None and slutt["ca"] < grenser["ca_lav_ppm"]:
        varsler.append(f"Lavt kalsium: {slutt['ca']:.1f} ppm (grense {grenser['ca_lav_ppm']:.0f} ppm) — kan gi svakere enzym-/gjæraktivitet og dårligere klaring.")
    if slutt.get("ca") is not None and slutt["ca"] > grenser["ca_hoy_ppm"]:
        varsler.append(f"Høyt kalsium: {slutt['ca']:.1f} ppm (grense {grenser['ca_hoy_ppm']:.0f} ppm) — trolig unødvendig høy mineralbelastning, vurder å redusere saltmengden.")

    if maalprofil:
        for row in bygg_ionrapport(sluttprofil, maalprofil):
            if row["status"] in ("under", "over") and row["slutt"] is not None:
                varsler.append(
                    f"{row['ion'].upper()} ({row['slutt']:.1f} ppm) er {row['status']} målområdet "
                    f"({row['maal_min']:.0f}–{row['maal_maks']:.0f} ppm)."
                )
        for ion in IONER:
            start_v = kildevann.get(ion)
            max_v = maalprofil.get(f"{ion}_max")
            if start_v is not None and max_v is not None and start_v > max_v:
                varsler.append(
                    f"Kildevannets {ion.upper()} ({start_v:.1f} ppm) er allerede over målprofilens "
                    f"maks ({max_v:.0f} ppm) — salter kan bare tilsette ioner, aldri fjerne dem. "
                    "Målprofilen kan ikke nås med de valgte saltene alene."
                )

    for syre in syrer:
        if not syre.get("prosent"):
            varsler.append(f"{syre.get('navn', 'Syre')}: konsentrasjon (%) er ikke angitt — kan ikke beregne syrestyrke presist.")

    if salt_fordeling:
        total_fordelt = sum(s["gram_mesk"] + s["gram_skyll"] for s in salt_fordeling)
        total_input = sum(s["gram"] for s in salt_fordeling)
        if abs(total_fordelt - total_input) > 0.01:
            varsler.append("Summen av meske- og skylletilsetning stemmer ikke med totalmengden — mulig avrundingsfeil i fordelingen.")

    return varsler


# ══════════════════════════════════════════════════════════════════════════
# ANBEFALINGSMOTOR — MÅLPROFIL
# ══════════════════════════════════════════════════════════════════════════

def anbefal_vannmaal(stil_navn, maalprofiler=None):
    """
    Anbefaler en målprofil (target_id) basert på ølstil — samme filosofi
    som modules/process_profiles.py sin anbefal_prosess(): appen ANBEFALER,
    men velger ALDRI en målprofil automatisk. Selve valget skjer alltid via
    et eksplisitt brukervalg i UI-et (se ui/water_panel.py) — denne
    funksjonen returnerer kun et FORSLAG + begrunnelse, og har ingen
    sideeffekter (muterer aldri `maalprofiler`).

    Slår opp `stil_navn` i hver profils `anbefalte_stiler`-liste. Finnes
    ingen match, faller den tilbake til "balansert_ale" (nøytralt
    utgangspunkt for de fleste ølstiler) dersom den finnes, ellers første
    tilgjengelige profil.

    Returnerer (target_id, begrunnelse) der begrunnelse er en liste med
    forklarende tekstlinjer. (None, [...]) hvis ingen målprofiler finnes.
    """
    maalprofiler = last_vannmaal() if maalprofiler is None else maalprofiler
    stil_navn = (stil_navn or "").strip()

    if not maalprofiler:
        return None, ["Ingen målprofiler er lagret."]

    if stil_navn:
        for target_id, profil in maalprofiler.items():
            if stil_navn in (profil.get("anbefalte_stiler") or []):
                return target_id, [
                    f"{stil_navn} står oppført under anbefalte stiler for "
                    f"«{profil.get('name', target_id)}»."
                ]

    if "balansert_ale" in maalprofiler:
        return "balansert_ale", [
            "Ingen målprofil er spesifikt knyttet til denne stilen — "
            "«Balansert ale» er et nøytralt utgangspunkt for de fleste ølstiler."
        ]

    forste_id = next(iter(maalprofiler))
    return forste_id, ["Ingen spesifikk anbefaling funnet — viser første tilgjengelige målprofil."]


# ══════════════════════════════════════════════════════════════════════════
# MÅLOPPNÅELSE — full / delvis / uoppnåelig med valgte salter
# ══════════════════════════════════════════════════════════════════════════

def vurder_maaloppnaelse(sluttprofil, maalprofil, salter_i_bruk=None):
    """
    Klassifiserer hvor godt en beregnet sluttprofil treffer målprofilen —
    en eksplisitt, tre-delt vurdering som solveren (foreslaa_salter()) og
    UI-et (ui/water_panel.py, seksjon 6) ALDRI får lov til å blande sammen
    eller stilltiende hoppe over:

      - "full_match": alle ioner med et definert målområde er innenfor.
      - "delvis_match": minst ett ion er utenfor målet, MEN det finnes et
        salt blant de VALGTE (`salter_i_bruk`) som kan påvirke akkurat det
        ionet — altså et avvik som i prinsippet kan løses ved å justere
        mengden av det saltet.
      - "uoppnaelig_med_valgte_salter": minst ett ion er utenfor OG INGEN
        av de valgte saltene kan påvirke akkurat det ionet i det hele tatt
        (f.eks. HCO3 når kun CaCl2·2H2O og gips er i bruk — ingen av dem
        inneholder HCO3), ELLER kildevannet ALENE allerede ligger utenfor
        målområdet i en retning salter ikke kan rette opp (salter kan bare
        TILSETTE ioner, aldri fjerne dem). Betyr IKKE at målet er umulig
        med ANDRE salter (f.eks. natron for HCO3) — kun med akkurat dette
        utvalget.
      - "ukjent": ingen målprofil å vurdere mot.

    Returnerer {"status": ..., "avvik": [{"ion", "status", "kan_justeres_med_valgte_salter"}, ...]}.
    """
    if not maalprofil:
        return {"status": "ukjent", "avvik": []}

    ioner_i_bruk = set()
    for s in (salter_i_bruk or []):
        try:
            ioner_i_bruk |= set(hent_salt(s["salt_id"])["ionfraksjoner"].keys())
        except KeyError:
            continue

    avvik = []
    for row in bygg_ionrapport(sluttprofil, maalprofil):
        if row["status"] not in ("under", "over"):
            continue
        ion = row["ion"]
        start_v = sluttprofil["start"].get(ion)
        max_v = row["maal_maks"]
        allerede_umulig = (
            row["status"] == "over" and start_v is not None and max_v is not None and start_v > max_v
        )
        kan_justeres = (ion in ioner_i_bruk) and not allerede_umulig
        avvik.append({"ion": ion, "status": row["status"], "kan_justeres_med_valgte_salter": kan_justeres})

    if not avvik:
        status = "full_match"
    elif any(not a["kan_justeres_med_valgte_salter"] for a in avvik):
        status = "uoppnaelig_med_valgte_salter"
    else:
        status = "delvis_match"

    return {"status": status, "avvik": avvik}


# ══════════════════════════════════════════════════════════════════════════
# AUTOMATISK SALTFORSLAG
# ══════════════════════════════════════════════════════════════════════════

def foreslaa_salter(kildevann, maalprofil, vannvolum_liter):
    """
    Enkel, gjennomsiktig heuristisk solver (V1 — ikke en fullstendig
    optimaliserer): bruker Cl/SO4-midtpunktet i målprofilen og løser direkte
    for hvor mye CaCl2·2H2O og CaSO4·2H2O (gips) som trengs — nøyaktig de to
    saltene brukeren nesten alltid trenger for en maltpreget/balansert profil
    (se kontrollscenario Wiesn-Märzen). Unngår natrium og magnesium med mindre
    HCO3/Cl/SO4-mangelen ikke kan dekkes av kalsiumsaltene alene.

    Returnerer (forslag, forklaring) der forslag er en liste med
    {"salt_id", "gram", "renhet"} (redigerbar i UI), og forklaring er en kort
    tekst om HVORFOR — presenteres ALDRI som "den eneste korrekte" løsningen.
    """
    if vannvolum_liter is None or vannvolum_liter <= 0:
        return [], "Ugyldig vannvolum — kan ikke beregne saltforslag."

    ca0 = kildevann.get("ca") or 0.0
    cl0 = kildevann.get("cl") or 0.0
    so4_0 = kildevann.get("so4") or 0.0

    cl_min, cl_max = maalprofil.get("cl_min"), maalprofil.get("cl_max")
    so4_min, so4_max = maalprofil.get("so4_min"), maalprofil.get("so4_max")

    delta_cl = max(0.0, ((cl_min + cl_max) / 2) - cl0) if cl_min is not None and cl_max is not None else 0.0
    delta_so4 = max(0.0, ((so4_min + so4_max) / 2) - so4_0) if so4_min is not None and so4_max is not None else 0.0

    cacl2 = SALTER["cacl2_2h2o"]
    gips = SALTER["gips"]

    gram_cacl2 = gram_for_onsket_ppm(delta_cl, cacl2["ionfraksjoner"]["cl"], 1.0, vannvolum_liter)
    gram_gips = gram_for_onsket_ppm(delta_so4, gips["ionfraksjoner"]["so4"], 1.0, vannvolum_liter)

    forslag = []
    _TERSKEL_G = 0.05  # under dette er tilsetningen praktisk talt null
    if gram_cacl2 > _TERSKEL_G:
        forslag.append({"salt_id": "cacl2_2h2o", "gram": round(gram_cacl2, 2), "renhet": 1.0})
    if gram_gips > _TERSKEL_G:
        forslag.append({"salt_id": "gips", "gram": round(gram_gips, 2), "renhet": 1.0})

    if not forslag:
        forklaring = "Kildevannet ligger allerede nær målområdet for klorid/sulfat — ingen salter foreslått."
    else:
        deler = []
        if gram_cacl2 > _TERSKEL_G:
            deler.append("Kalsiumklorid løfter Ca og Cl")
        if gram_gips > _TERSKEL_G:
            deler.append("gips løfter Ca og SO4")
        forklaring = ". ".join(deler) + "."

    # Solveren skal ALDRI stilltiende late som om målprofilen er fullt
    # oppnådd hvis den ikke er det — se vurder_maaloppnaelse(). Spesielt
    # HCO3/Mg/Na, som verken CaCl2·2H2O eller gips påvirker i det hele
    # tatt, må navngis eksplisitt når de er utenfor målområdet.
    sluttprofil_test = beregn_sluttprofil(kildevann, forslag, vannvolum_liter)
    vurdering = vurder_maaloppnaelse(sluttprofil_test, maalprofil, forslag)
    if vurdering["status"] == "uoppnaelig_med_valgte_salter":
        uoppnaelige = sorted(
            a["ion"].upper() for a in vurdering["avvik"] if not a["kan_justeres_med_valgte_salter"]
        )
        forklaring += (
            f" Merk: {', '.join(uoppnaelige)} kan IKKE nås med kun kalsiumklorid "
            "og gips — dette krever andre salter (f.eks. natron for HCO3) eller "
            "ligger allerede utenfor målområdet i kildevannet, som salter aldri "
            "kan rette opp (de tilsetter, aldri fjerner, ioner). Målprofilen er "
            "IKKE fullt oppnådd med dette forslaget alene."
        )
    elif vurdering["status"] == "delvis_match":
        justerbare = sorted(a["ion"].upper() for a in vurdering["avvik"])
        forklaring += (
            f" {', '.join(justerbare)} er fortsatt utenfor målområdet med denne "
            "mengden — juster gram-tallene fritt for å nærme deg midten av intervallet."
        )

    return forslag, forklaring


# ══════════════════════════════════════════════════════════════════════════
# SYRER
# ══════════════════════════════════════════════════════════════════════════
SYRER = {
    "melkesyre": {"syre_id": "melkesyre", "navn": "Melkesyre", "formel": "C3H6O3"},
    "fosforsyre": {"syre_id": "fosforsyre", "navn": "Fosforsyre", "formel": "H3PO4"},
}


def bygg_syretilsetning(syre_id, prosent=None, mengde_ml=0.0, kommentar=""):
    """
    Datamodell for én syretilsetning. `prosent` (konsentrasjon) må angis
    eksplisitt av brukeren — appen antar ALDRI en konsentrasjon ut fra bare
    navnet (f.eks. melkesyre finnes vanligvis som 80 %, fosforsyre som 10 %,
    75 % eller 85 %, og disse gir svært ulik reell syremengde per mL).
    """
    syre = SYRER.get(syre_id, {"syre_id": syre_id, "navn": syre_id, "formel": ""})
    return {
        "syre_id": syre_id,
        "navn": syre["navn"],
        "formel": syre["formel"],
        "prosent": prosent,
        "mengde_ml": mengde_ml,
        "kommentar": kommentar,
    }
