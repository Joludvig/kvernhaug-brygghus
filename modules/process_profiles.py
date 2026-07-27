# modules/process_profiles.py
"""
Prosessprofiler ("bryggemåte") — HVORDAN et brygg lages, adskilt fra
oppskriften (HVA det er laget av). En prosessprofil beskriver meskesteg,
skyllemetode, koketid og ev. dekoksjons-/dobbeltmesk-detaljer, og lagres
sammen med oppskriften uten å røre malt/humle/gjær-listene.

Ingen Streamlit-avhengighet her — ren datamodell + beregninger, testbart
isolert (samme mønster som style_engine.py).
"""
import copy

# ── Vanskelighetsgrad ────────────────────────────────────────────────────────
LETT     = "Lett"
MIDDELS  = "Middels"
KREVENDE = "Krevende"

# ── Stegtyper ────────────────────────────────────────────────────────────────
INFUSJON        = "infusjon"
DEKOKSJON_UTTAK = "dekoksjon_uttak"
DEKOKSJON_RETUR = "dekoksjon_retur"
MASHOUT         = "mashout"

# ── Skyllemetoder ────────────────────────────────────────────────────────────
BATCH_SPARGE = "batch_sparge"
NO_SPARGE    = "no_sparge"
FLY_SPARGE   = "fly_sparge"

_SPARGE_NAVN = {
    BATCH_SPARGE: "Batch sparge (skyller i én/to porsjoner)",
    NO_SPARGE:    "No-sparge (alt vann i mesken, ingen skylling)",
    FLY_SPARGE:   "Fly sparge (kontinuerlig skylling)",
}


def _steg(temperatur, varighet, stegtype=INFUSJON, kommentar=""):
    return {
        "temperatur": float(temperatur),
        "varighet": int(varighet),
        "stegtype": stegtype,
        "kommentar": kommentar,
    }


# ── STANDARDPROFILER ─────────────────────────────────────────────────────────
# process_id -> statisk definisjon. `mash_steps`/`decoction_steps` her er
# STANDARDVERDIER — de kopieres inn i en oppskrifts prosessprofil og kan
# redigeres fritt av brukeren uten å endre denne malen.

STANDARDPROFILER = {
    "enkel_infusjon": {
        "process_id": "enkel_infusjon",
        "navn": "Enkel infusjon",
        "beskrivelse": (
            "Én mesketemperatur (single-infusion). Raskest og enklest — "
            "passer de aller fleste ales og de fleste moderne lagerstiler."
        ),
        "vanskelighetsgrad": LETT,
        "mash_steps": [
            _steg(66, 60, INFUSJON, "Hovedmesk — enzymatisk konvertering"),
            _steg(78, 5,  MASHOUT,  "Mashout — stopper enzymaktivitet"),
        ],
        "sparge_method": BATCH_SPARGE,
        "boil_minutes": 60,
        "decoction_steps": None,
        "reiterated_mash": None,
        "anbefalte_stiler": [],  # fallback/standard — ikke stilspesifikk
        "utstyrsbegrensninger": "Ingen spesielle krav utover vanlig meskekar.",
        "forventet_paavirkning": (
            "Nøytral referanse — verken ekstra kropp eller ekstra tørrhet "
            "utover det maltbill og gjær selv gir."
        ),
        "ekstra_tid_min": 0,
    },
    "hochkurz": {
        "process_id": "hochkurz",
        "navn": "Hochkurz (stegmesk)",
        "beskrivelse": (
            "Klassisk tysk to-trinns stegmesk: en beta-amylase-hvile "
            "(mer gjærbart sukker, tørrere øl) etterfulgt av en "
            "alfa-amylase-hvile (mer kropp/uforgjærbart sukker) og mashout. "
            "Gir en rundere, mer 'tysk' maltkarakter enn enkel infusjon."
        ),
        "vanskelighetsgrad": MIDDELS,
        "mash_steps": [
            _steg(63, 40, INFUSJON, "Beta-hvile — gjærbarhet"),
            _steg(70, 30, INFUSJON, "Alfa-hvile — kropp/dekstriner"),
            _steg(77, 10, MASHOUT,  "Mashout — stopper enzymaktivitet"),
        ],
        "sparge_method": BATCH_SPARGE,
        "boil_minutes": 60,
        "decoction_steps": None,
        "reiterated_mash": None,
        "anbefalte_stiler": [
            "Märzen", "Historisk Wiesn-Märzen", "Festbier",
            "Heller Bock (Mai-Bock)", "Dunkles Bock", "Münchener Dunkel",
            "Vienna Lager",
        ],
        "utstyrsbegrensninger": (
            "Krever presis, stabil temperaturstyring gjennom flere steg — "
            "godt egnet for elektrisk mesk-kar (f.eks. BrewZilla), "
            "vanskeligere med kun gassbrenner og manuell temperaturstyring."
        ),
        "forventet_paavirkning": (
            "To separate hviler gir brygger bedre kontroll over "
            "gjærbarhet/kropp enn én enkelt temperatur — vanligvis noe "
            "tørrere og renere enn en tilsvarende enkel infusjon ved samme "
            "gjennomsnittstemperatur."
        ),
        "ekstra_tid_min": 20,
    },
    "enkel_dekoksjon": {
        "process_id": "enkel_dekoksjon",
        "navn": "Enkel dekoksjon",
        "beskrivelse": (
            "Historisk teknikk: en del av mesken ('tykkmesken') tas ut, "
            "kokes 10-15 min for å utvikle melanoidiner (rik, bakt/toastet "
            "maltkarakter), og føres tilbake i hovedmesken for å heve "
            "temperaturen mot mashout. Uttaksvolumet beregnes av "
            "appen, men ALLE verdier kan redigeres fritt."
        ),
        "vanskelighetsgrad": KREVENDE,
        "mash_steps": [
            _steg(63, 20, INFUSJON, "Startmesk — før uttak"),
            _steg(77, 10, MASHOUT,  "Mashout etter dekoksjon er ført tilbake"),
        ],
        "sparge_method": BATCH_SPARGE,
        "boil_minutes": 60,
        "decoction_steps": [
            {
                "uttak_liter": None,  # beregnes dynamisk, se beregn_dekoksjon()
                "fra_temp_c": 63,
                "til_temp_c": 70,
                "koketid_min": 12,
                "kommentar": "Kok tykkmesken 10-15 min, rør ofte for å unngå svidd bunn.",
            },
        ],
        "reiterated_mash": None,
        "anbefalte_stiler": ["Historisk Wiesn-Märzen"],
        "utstyrsbegrensninger": (
            "Krever en egen kjele (eller nok ledig kapasitet i hovedkjelen) "
            "til å koke en del av mesken separat, samt et kar/kjele å øse "
            "tykkmesken over i. Lang bryggedag — sett av ekstra tid."
        ),
        "forventet_paavirkning": (
            "Kokingen av tykkmesken karamelliserer/melanoidinerer sukker og "
            "gir en dypere, rikere, mer 'bakt' maltkarakter og ofte noe "
            "mørkere farge enn samme oppskrift meskes med infusjon. "
            "Gjærbarhet påvirkes lite hvis hovedmeskens temperaturprofil "
            "for øvrig er lik."
        ),
        "ekstra_tid_min": 60,
    },
    "reiterated_mash": {
        "process_id": "reiterated_mash",
        "navn": "Reiterated mash (dobbel mesk)",
        "beskrivelse": (
            "Historisk 'dobbelmesk'-teknikk: maltmengden deles i to. Første "
            "mesk lages med fersk vann og lautres til en vørt. Denne vørten "
            "brukes SOM meskevann til den andre mesken, som deretter lautres "
            "til sluttvørt. Gir en svært maltrik, kompleks vørt, men er "
            "tidkrevende og kan gi redusert samlet effektivitet."
        ),
        "vanskelighetsgrad": KREVENDE,
        "mash_steps": [
            _steg(66, 60, INFUSJON, "Mesk 1 — fersk vann"),
            _steg(66, 60, INFUSJON, "Mesk 2 — meskevann er vørt fra mesk 1"),
            _steg(78, 5,  MASHOUT,  "Mashout på mesk 2"),
        ],
        "sparge_method": BATCH_SPARGE,
        "boil_minutes": 60,
        "decoction_steps": None,
        "reiterated_mash": {
            "mesk_1_andel": 0.5,  # andel av total maltmengde i første mesk
        },
        "anbefalte_stiler": [],
        "utstyrsbegrensninger": (
            "Krever lauter-kapasitet for to fulle mesker etter hverandre, "
            "og et meskekar/kjele stort nok til hver delmengde korn for "
            "seg. Svært lang bryggedag (to fulle meske- og lauteresykluser)."
        ),
        "forventet_paavirkning": (
            "Gir typisk en svært fyldig, maltrik vørt med redusert "
            "forutsigbarhet i endelig effektivitet (den andre mesken meskes "
            "ikke med rent vann, så enzymaktivitet/utbytte er vanskeligere "
            "å anslå presist enn ved vanlig infusjon)."
        ),
        "ekstra_tid_min": 120,
    },
    "egendefinert": {
        "process_id": "egendefinert",
        "navn": "Egendefinert prosess",
        "beskrivelse": "Fritt redigerbar prosess — start tom eller kopiér en standardprofil som utgangspunkt.",
        "vanskelighetsgrad": MIDDELS,
        "mash_steps": [
            _steg(66, 60, INFUSJON, ""),
        ],
        "sparge_method": BATCH_SPARGE,
        "boil_minutes": 60,
        "decoction_steps": None,
        "reiterated_mash": None,
        "anbefalte_stiler": [],
        "utstyrsbegrensninger": "",
        "forventet_paavirkning": "",
        "ekstra_tid_min": 0,
    },
}

_REKKEFOLGE = ["enkel_infusjon", "hochkurz", "enkel_dekoksjon", "reiterated_mash", "egendefinert"]


def tilgjengelige_profiler():
    """Returnerer standardprofilene i visningsrekkefølge (liste av dicts)."""
    return [hent_standardprofil(pid) for pid in _REKKEFOLGE]


def hent_standardprofil(process_id):
    """
    Henter en DYP KOPI av standardprofilen for `process_id`. Dyp kopi er
    viktig — UI-en redigerer meskesteg direkte på det returnerte objektet,
    og skal aldri kunne mutere selve malen i STANDARDPROFILER.
    """
    mal = STANDARDPROFILER.get(process_id) or STANDARDPROFILER["enkel_infusjon"]
    profil = copy.deepcopy(mal)
    profil["brukernotater"] = ""
    return profil


def normaliser_prosessprofil(profile):
    """
    DEN ENE, FELLES kilden for å gjøre en "aktiv kandidat"-prosessprofil
    trygg å bruke — kalles FØR profilen tas i bruk noe sted (UI-visning,
    lag_brewday_plan(), lagring, eksport). Løser rotårsaken til
    hybrid-meskeplan-bugs: enhver kode som stolte på en ALLEREDE lagret/
    aktiv profils egne mash_steps for en KJENT standardprofil kunne
    videreføre en profil som i utgangspunktet var korrupt (f.eks. rester
    fra en eldre, nå rettet bug, eller en oppskriftsfil lagret av en
    eldre app-versjon).

    Regler:
      - `process_id` er en KJENT standardprofil og IKKE "egendefinert":
        returnerer en fersk deepcopy av hent_standardprofil(process_id)
        — ALDRI de innsendte mash_steps (eller andre strukturelle felt:
        boil_minutes, sparge_method, decoction_steps, reiterated_mash).
        En standardprofil (Hochkurz osv.) SKAL alltid bety nøyaktig sine
        egne, kanoniske meskesteg. Kun `brukernotater` — fritekst uten
        strukturell betydning — overtas uendret fra kandidaten.
      - `process_id == "egendefinert"`: brukerens egne steg ER selve
        poenget med profilen — returnerer en uendret deepcopy.
      - Manglende/tomt/ugyldig `process_id` (None, {} eller en ukjent
        verdi): faller tilbake til en bakoverkompatibel standardprofil
        ("enkel_infusjon").

    Returnerer ALLTID en ny, uavhengig deepcopy — aldri samme objekt
    eller nestede lister/dicts som ble sendt inn, og ALDRI samme objekt
    som en tidligere/annen kilde (session_state, ctx, en lagret fil).
    """
    if not profile or not isinstance(profile, dict):
        return hent_standardprofil("enkel_infusjon")

    process_id = profile.get("process_id")

    if process_id == "egendefinert":
        return copy.deepcopy(profile)

    if process_id in STANDARDPROFILER:
        kanonisk = hent_standardprofil(process_id)
        kanonisk["brukernotater"] = profile.get("brukernotater", "")
        return kanonisk

    return hent_standardprofil("enkel_infusjon")


def bygg_egendefinert_profil(navn, mash_steps, sparge_method=BATCH_SPARGE,
                              boil_minutes=60, brukernotater=""):
    """Bygger en fullstendig egendefinert prosessprofil fra brukerens egne steg."""
    return {
        "process_id": "egendefinert",
        "navn": navn or "Egendefinert prosess",
        "beskrivelse": "Brukerdefinert prosess.",
        "vanskelighetsgrad": MIDDELS,
        "mash_steps": list(mash_steps),
        "sparge_method": sparge_method,
        "boil_minutes": int(boil_minutes),
        "decoction_steps": None,
        "reiterated_mash": None,
        "anbefalte_stiler": [],
        "utstyrsbegrensninger": "",
        "forventet_paavirkning": "",
        "ekstra_tid_min": 0,
        "brukernotater": brukernotater,
    }


# ── DEKOKSJONSBEREGNING ──────────────────────────────────────────────────────

def beregn_dekoksjon_uttak(mesk_volum_l, fra_temp_c, til_temp_c, koke_temp_c=100.0):
    """
    Anbefalt uttaksvolum (liter) av tykk mesk for å heve resten av mesken fra
    `fra_temp_c` til `til_temp_c` ved å koke uttaket og føre det tilbake.

    Standard, mye brukt tilnærming i hjemmebrygging ("decoction thickness"-
    formelen): andelen av mesken som må kokes er proporsjonal med hvor stor
    temperaturøkning som trengs, relativt til avstanden fra utgangstemperatur
    til kokepunktet:

        andel = (til_temp_c - fra_temp_c) / (koke_temp_c - fra_temp_c)
        uttak_liter = mesk_volum_l * andel

    Dette er en forenkling (den ser bort fra at malt og vann har ulik
    varmekapasitet), men samme presisjonsnivå som resten av appens
    beregninger (jf. Plato-omregningen i brewday_calc.py) — og brukeren kan
    uansett redigere det foreslåtte tallet fritt i UI-et.
    """
    if mesk_volum_l <= 0 or til_temp_c <= fra_temp_c or koke_temp_c <= fra_temp_c:
        return 0.0
    andel = (til_temp_c - fra_temp_c) / (koke_temp_c - fra_temp_c)
    andel = max(0.0, min(andel, 1.0))
    return round(mesk_volum_l * andel, 2)


# ── REITERATED MASH-BEREGNING ────────────────────────────────────────────────

def beregn_reiterated_mash(total_malt_kg, mesk_1_andel, eq):
    """
    Beregner vann-/volumflyt for en dobbelmesk-prosess:
      Mesk 1 (fersk vann) -> vørt 1 -> brukes som meskevann i mesk 2 -> vørt 2.

    Bruker samme forhold (mash_ratio_l_per_kg, grain_absorption_l_per_kg) som
    resten av vannberegningen i brewday_calc.py, hentet fra utstyrsprofilen —
    ingenting er hardkodet.

    Returnerer en dict som beskriver hvert steg i vann-/volumflyten, samt en
    liste med tekst-varsler (redusert effektivitet, lang bryggedag, evt.
    for tynt/tykt vørtvolum til mesk 2).
    """
    mesk_1_andel = max(0.05, min(mesk_1_andel, 0.95))
    malt_1_kg = round(total_malt_kg * mesk_1_andel, 3)
    malt_2_kg = round(total_malt_kg - malt_1_kg, 3)

    ratio = eq["mash_ratio_l_per_kg"]
    absorpsjon = eq["grain_absorption_l_per_kg"]

    vann_mesk_1 = round(malt_1_kg * ratio, 1)
    vort_1 = round(max(0.0, vann_mesk_1 - malt_1_kg * absorpsjon), 1)

    # Vørt 1 brukes SOM meskevann til mesk 2 — ikke friskt vann.
    vann_mesk_2_faktisk = vort_1
    vann_mesk_2_anbefalt = round(malt_2_kg * ratio, 1)
    vort_2 = round(max(0.0, vann_mesk_2_faktisk - malt_2_kg * absorpsjon), 1)

    varsler = [
        "Lang bryggedag: to fulle meske- og lauteresykluser etter hverandre.",
        "Redusert/uforutsigbar effektivitet: mesk 2 meskes med vørt (ikke "
        "ferskt vann), så utbyttet er vanskeligere å anslå presist enn ved "
        "vanlig infusjon.",
    ]
    if vann_mesk_2_faktisk < vann_mesk_2_anbefalt * 0.85:
        varsler.append(
            f"Vørt fra mesk 1 ({vann_mesk_2_faktisk:.1f} L) gir en tykkere mesk 2 enn "
            f"normalt meskeforhold skulle tilsi ({vann_mesk_2_anbefalt:.1f} L) — "
            "vurder å øke mesk 1-andelen eller tilsette noe ekstra vann."
        )

    return {
        "malt_1_kg": malt_1_kg,
        "malt_2_kg": malt_2_kg,
        "vann_mesk_1_l": vann_mesk_1,
        "vort_1_l": vort_1,
        "vann_mesk_2_l": vann_mesk_2_faktisk,
        "vann_mesk_2_anbefalt_l": vann_mesk_2_anbefalt,
        "vort_2_l": vort_2,
        "sluttvolum_l": vort_2,
        "varsler": varsler,
    }


# ── UTSTYRSSJEKK ─────────────────────────────────────────────────────────────

def sjekk_utstyrsbegrensninger(profile, total_malt_kg, eq):
    """
    Returnerer en liste med tekstvarsler dersom valgt prosessprofil ser ut
    til å overskride utstyrets kapasitet (kjelekapasitet fra
    modules/equipment.py — samme utstyrsprofil som resten av appen bruker).
    """
    varsler = []
    kjele = eq.get("kettle_capacity_l", 35.0)
    ratio = eq.get("mash_ratio_l_per_kg", 3.2)
    grain_vol_l_per_kg = 0.7  # grov, dokumentert tilnærming til kornvolum

    if profile.get("process_id") == "reiterated_mash":
        andel = (profile.get("reiterated_mash") or {}).get("mesk_1_andel", 0.5)
        r = beregn_reiterated_mash(total_malt_kg, andel, eq)
        for delnavn, malt_kg, vann_l in (
            ("Mesk 1", r["malt_1_kg"], r["vann_mesk_1_l"]),
            ("Mesk 2", r["malt_2_kg"], r["vann_mesk_2_l"]),
        ):
            volum = vann_l + malt_kg * grain_vol_l_per_kg
            if volum > kjele:
                varsler.append(
                    f"{delnavn}: estimert meskevolum {volum:.1f} L overskrider "
                    f"kjelekapasitet på {kjele:.0f} L."
                )
    else:
        mesk_vann_l = total_malt_kg * ratio
        volum = mesk_vann_l + total_malt_kg * grain_vol_l_per_kg
        if volum > kjele:
            varsler.append(
                f"Estimert meskevolum {volum:.1f} L overskrider kjelekapasitet "
                f"på {kjele:.0f} L — vurder reiterated mash (dobbel mesk) eller "
                "et mindre batch."
            )

    return varsler


# ── ANBEFALINGSMOTOR ─────────────────────────────────────────────────────────

# Terskler for "svært høy OG" / "maltmengde over kapasitet" — dokumentert her
# fordi de IKKE er offisielle tall, kun rimelige husregler for denne appen.
_SVAER_HOY_OG = 1.075


def anbefal_prosess(stil_navn, stats, total_malt_kg, eq, historisk_autentisitet=False):
    """
    Anbefaler en prosessprofil basert på (i prioritert rekkefølge):
      1. Utstyrskapasitet / svært høy OG -> reiterated mash (hardt fysisk problem,
         overstyrer stilvalg).
      2. Stil (valgt eller nærmeste) i _HOCHKURZ_STILER -> hochkurz, med
         dekoksjon tilbudt som historisk alternativ (og som primærvalg
         dersom `historisk_autentisitet=True` og stilen selv anbefaler det).
      3. Ellers -> enkel infusjon (vanlige ales/stout/de fleste lagerstiler).

    Returnerer (process_id, begrunnelse) der begrunnelse er en liste med
    forklarende tekstlinjer — anbefalingen skal ALLTID kunne begrunnes, og
    APPEN SKAL ALDRI SETTE PROSESSEN AUTOMATISK; dette er kun et forslag
    UI-laget viser fram og lar brukeren velge fra (eller overstyre helt).
    """
    begrunnelse = []
    og = (stats or {}).get("og", 0.0)

    eq = eq or {}
    kjele = eq.get("kettle_capacity_l", 35.0)
    ratio = eq.get("mash_ratio_l_per_kg", 3.2)
    estimert_meskevolum = total_malt_kg * ratio + total_malt_kg * 0.7

    if estimert_meskevolum > kjele:
        begrunnelse.append(
            f"Total maltmengde ({total_malt_kg:.1f} kg) gir et estimert "
            f"meskevolum ({estimert_meskevolum:.1f} L) som overskrider "
            f"kjelekapasiteten ({kjele:.0f} L)."
        )
        return "reiterated_mash", begrunnelse

    if og >= _SVAER_HOY_OG:
        begrunnelse.append(
            f"Mål-OG ({og:.3f}) er svært høy (>= {_SVAER_HOY_OG:.3f}) — én enkelt "
            "mesk vil normalt ikke klare å ekstrahere nok sukker/passe "
            "meskeforhold i ett kar."
        )
        return "reiterated_mash", begrunnelse

    stil_navn = stil_navn or ""
    hochkurz_stiler = set(STANDARDPROFILER["hochkurz"]["anbefalte_stiler"])
    dekoksjon_stiler = set(STANDARDPROFILER["enkel_dekoksjon"]["anbefalte_stiler"])

    if stil_navn in dekoksjon_stiler and historisk_autentisitet:
        begrunnelse.append(
            f"{stil_navn} er historisk knyttet til dekoksjonsmesking, og "
            "historisk autentisitet er etterspurt."
        )
        return "enkel_dekoksjon", begrunnelse

    if stil_navn in hochkurz_stiler:
        begrunnelse.append(
            f"{stil_navn} er en tradisjonell tysk/østerriksk lagerstil som "
            "vanligvis meskes med Hochkurz-stegmesk for rundere maltkarakter."
        )
        if stil_navn in dekoksjon_stiler:
            begrunnelse.append(
                "Dekoksjon er tilgjengelig som et mer historisk autentisk, "
                "men også mer tidkrevende alternativ."
            )
        return "hochkurz", begrunnelse

    begrunnelse.append(
        "Ingen spesielle krav funnet for valgt/nærmeste stil, maltbase eller "
        "utstyr — enkel infusjon er raskest og passer de fleste ales, stout "
        "og moderne lagerstiler."
    )
    return "enkel_infusjon", begrunnelse
