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

from modules.i18n import SPRAK_DEFAULT, t

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

# ── VISNINGSTEKST (NO/EN, #548) ──────────────────────────────────────────────
# Standardprofilenes tekster lagres og beregnes ALLTID på norsk (lagrede
# profiler, process_id og datakontrakter er språknøytrale/uendret). Kun
# VISNINGEN oversettes, og KUN med profilidentitet og feltkontekst: en tekst
# oversettes bare når profilen er en kjent standardprofil OG teksten er
# nøyaktig den standardprofilen selv har i akkurat det feltet. Brukerens egne
# profilnavn og kommentarer (også «Lett», «Infusjon» e.l. som tilfeldigvis
# ligner en systemtekst) matcher dermed aldri.
_STEG_KOMMENTAR_NOKLER = {
    "Hovedmesk — enzymatisk konvertering": "pp.steg.hovedmesk",
    "Mashout — stopper enzymaktivitet": "pp.steg.mashout",
    "Lavere temperaturhvile": "pp.steg.lavere",
    "Høyere temperaturhvile": "pp.steg.hoyere",
    "Startmesk — før uttak": "pp.steg.startmesk",
    "Mashout etter dekoksjon er ført tilbake": "pp.steg.mashout_dek",
    "Mesk 1 — fersk vann": "pp.steg.mesk1",
    "Mesk 2 — meskevann er vørt fra mesk 1": "pp.steg.mesk2",
    "Mashout på mesk 2": "pp.steg.mashout_m2",
    "Kok tykkmesken 10-15 min, rør ofte for å unngå svidd bunn.": "pp.steg.dek_kommentar",
}
_PROFIL_FELT_NOKKEL = {
    "navn": "pp.navn.{pid}",
    "beskrivelse": "pp.besk.{pid}",
    "utstyrsbegrensninger": "pp.utstyr.{pid}",
    "forventet_paavirkning": "pp.paavirkning.{pid}",
}
_EGENDEFINERT_PREFIKS = "Egendefinert – basert på "


def _er_standardprofil(process_id):
    return process_id in STANDARDPROFILER


def profiltekst_visning(felt, tekst, process_id, sprak=SPRAK_DEFAULT):
    """Visningstekst for et profilfelt (navn, beskrivelse, utstyrsbegrensninger,
    forventet_paavirkning) i valgt språk. Oversettes bare når `process_id` er
    en standardprofil og `tekst` er identisk med standardprofilens egen tekst
    i dette feltet; ellers uendret."""
    if sprak == SPRAK_DEFAULT or not isinstance(tekst, str) or not _er_standardprofil(process_id):
        return tekst
    mal = _PROFIL_FELT_NOKKEL.get(felt)
    if mal and tekst and tekst == STANDARDPROFILER[process_id].get(felt):
        return t(mal.format(pid=process_id), sprak)
    return tekst


def profilnavn_visning(navn, sprak=SPRAK_DEFAULT, process_id=None):
    """Visningsnavn for en prosessprofil. Det lagrede navnet er alltid norsk.
    En standardprofil med standardnavn oversettes; «Egendefinert – basert på X»
    (appens eget navn ved redigering av en standardprofil) oversettes i prefikset
    og, bare når X er en standardprofils navn, også i X. Alt annet — brukerens
    eget navn, også når det ligner en systemtekst — beholdes. Uten `process_id`
    finnes ingen kontekst, og navnet returneres uendret."""
    if sprak == SPRAK_DEFAULT or not isinstance(navn, str) or not _er_standardprofil(process_id):
        return navn
    if process_id == "egendefinert" and navn.startswith(_EGENDEFINERT_PREFIKS):
        rest = navn[len(_EGENDEFINERT_PREFIKS):]
        for pid, profil in STANDARDPROFILER.items():
            if pid != "egendefinert" and rest == profil["navn"]:
                rest = t(f"pp.navn.{pid}", sprak)
                break
        return t("pp.navn.egendefinert_prefiks", sprak) + rest
    return profiltekst_visning("navn", navn, process_id, sprak)


def mesketrinn_kommentar_visning(kommentar, process_id, sprak=SPRAK_DEFAULT):
    """Kommentar på et meskesteg/dekoksjonssteg i valgt språk. Oversettes bare
    for en standardprofil (ikke «egendefinert») og bare når teksten er en av
    den profilens egne standardkommentarer."""
    if (sprak == SPRAK_DEFAULT or not isinstance(kommentar, str) or not kommentar
            or not _er_standardprofil(process_id) or process_id == "egendefinert"):
        return kommentar
    profil = STANDARDPROFILER[process_id]
    egne = {s.get("kommentar") for s in profil["mash_steps"]}
    egne |= {s.get("kommentar") for s in (profil.get("decoction_steps") or [])}
    nokkel = _STEG_KOMMENTAR_NOKLER.get(kommentar)
    return t(nokkel, sprak) if nokkel and kommentar in egne else kommentar


def vanskelighetsgrad_visning(verdi, sprak=SPRAK_DEFAULT):
    """Lett/Middels/Krevende (lagrede koder, uendret) i valgt språk."""
    if verdi in (LETT, MIDDELS, KREVENDE):
        return t(f"pp.vansk.{verdi}", sprak)
    return verdi


def maskeplan_steg_visning(steg, process_id, sprak=SPRAK_DEFAULT):
    """Visningslabel for ett steg i brewday-planens `maskeplan`. Appens egne
    labeler (steg uten profil, eller stegtype-fallback når kommentaren er tom)
    bærer en `label_nokkel` og oversettes; en kommentar oversettes bare via
    mesketrinn_kommentar_visning() (standardprofil + standardkommentar)."""
    nokkel = steg.get("label_nokkel")
    if nokkel:
        return t(nokkel, sprak)
    return mesketrinn_kommentar_visning(steg["label"], process_id, sprak)


def sparge_navn(sparge_method, sprak=SPRAK_DEFAULT):
    """Visningsnavn for en skyllemetode (nøkkelen er uendret, f.eks. batch_sparge)."""
    if sparge_method in _SPARGE_NAVN:
        return t(f"pp.sparge.{sparge_method}", sprak)
    return "—"


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
            "Klassisk tysk to-trinns stegmesk: én hvile ved lavere "
            "temperatur etterfulgt av én hvile ved høyere temperatur "
            "(mer uforgjærbart sukker), og deretter mashout."
        ),
        "vanskelighetsgrad": MIDDELS,
        "mash_steps": [
            _steg(63, 40, INFUSJON, "Lavere temperaturhvile"),
            _steg(70, 30, INFUSJON, "Høyere temperaturhvile"),
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
            "Profilen bruker to separate temperaturhviler i sekvens, "
            "etterfulgt av mashout."
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

def reiterated_varsler(vann_mesk_2_faktisk, vann_mesk_2_anbefalt, sprak=SPRAK_DEFAULT):
    """Varslene for en dobbelmesk i valgt språk (én kilde for beregningen
    og for visningen)."""
    varsler = [t("pp.rm.v_lang", sprak), t("pp.rm.v_effektivitet", sprak)]
    if vann_mesk_2_faktisk < vann_mesk_2_anbefalt * 0.85:
        varsler.append(t(
            "pp.rm.v_tykk", sprak,
            faktisk=f"{vann_mesk_2_faktisk:.1f}", anbefalt=f"{vann_mesk_2_anbefalt:.1f}",
        ))
    return varsler


def beregn_reiterated_mash(total_malt_kg, mesk_1_andel, eq, sprak=SPRAK_DEFAULT):
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

    varsler = reiterated_varsler(vann_mesk_2_faktisk, vann_mesk_2_anbefalt, sprak)

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

def sjekk_utstyrsbegrensninger(profile, total_malt_kg, eq, sprak=SPRAK_DEFAULT):
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
        r = beregn_reiterated_mash(total_malt_kg, andel, eq, sprak)
        for delnavn, malt_kg, vann_l in (
            (t("pp.del.mesk1", sprak), r["malt_1_kg"], r["vann_mesk_1_l"]),
            (t("pp.del.mesk2", sprak), r["malt_2_kg"], r["vann_mesk_2_l"]),
        ):
            volum = vann_l + malt_kg * grain_vol_l_per_kg
            if volum > kjele:
                varsler.append(t(
                    "pp.utstyr.mesk_del", sprak,
                    **{"del": delnavn}, vol=f"{volum:.1f}", kjele=f"{kjele:.0f}",
                ))
    else:
        mesk_vann_l = total_malt_kg * ratio
        volum = mesk_vann_l + total_malt_kg * grain_vol_l_per_kg
        if volum > kjele:
            varsler.append(t(
                "pp.utstyr.mesk", sprak, vol=f"{volum:.1f}", kjele=f"{kjele:.0f}",
            ))

    return varsler


# ── ANBEFALINGSMOTOR ─────────────────────────────────────────────────────────

# Terskler for "svært høy OG" / "maltmengde over kapasitet" — dokumentert her
# fordi de IKKE er offisielle tall, kun rimelige husregler for denne appen.
_SVAER_HOY_OG = 1.075


def anbefal_prosess(stil_navn, stats, total_malt_kg, eq, historisk_autentisitet=False,
                    sprak=SPRAK_DEFAULT):
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
        begrunnelse.append(t(
            "pp.anb.kapasitet", sprak, kg=f"{total_malt_kg:.1f}",
            vol=f"{estimert_meskevolum:.1f}", kjele=f"{kjele:.0f}",
        ))
        return "reiterated_mash", begrunnelse

    if og >= _SVAER_HOY_OG:
        begrunnelse.append(t(
            "pp.anb.hoy_og", sprak, og=f"{og:.3f}", grense=f"{_SVAER_HOY_OG:.3f}",
        ))
        return "reiterated_mash", begrunnelse

    stil_navn = stil_navn or ""
    hochkurz_stiler = set(STANDARDPROFILER["hochkurz"]["anbefalte_stiler"])
    dekoksjon_stiler = set(STANDARDPROFILER["enkel_dekoksjon"]["anbefalte_stiler"])

    if stil_navn in dekoksjon_stiler and historisk_autentisitet:
        begrunnelse.append(t("pp.anb.dekoksjon_historisk", sprak, stil=stil_navn))
        return "enkel_dekoksjon", begrunnelse

    if stil_navn in hochkurz_stiler:
        begrunnelse.append(t("pp.anb.hochkurz", sprak, stil=stil_navn))
        if stil_navn in dekoksjon_stiler:
            begrunnelse.append(t("pp.anb.dekoksjon_alt", sprak))
        return "hochkurz", begrunnelse

    begrunnelse.append(t("pp.anb.standard", sprak))
    return "enkel_infusjon", begrunnelse
