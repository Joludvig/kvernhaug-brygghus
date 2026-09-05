# modules/kbhbrew_history_ui.py
"""
V2-1A (issue #83) -- rene, testbare hjelpefunksjoner for Brew History-
UI-en (ui/kbhbrew_history_panel.py). Ingen Streamlit-avhengighet, ingen
filsystem-tilgang, ingen sideeffekter -- samme "ren modul"-prinsipp som
modules/kbhbrew_ui.py, som denne gjenbruker for selve utvalgs-/etikett-/
sorteringslogikken: historikklisten trenger NØYAKTIG samme felt (frosset
oppskriftsnavn, brygget-dato > opprettet-dato, status, kort identitet
for disambiguering) som PRI 3B2 sitt eksport-utvalg allerede bygger, se
modules/kbhbrew_ui.py::sorter_brews_for_eksport()/bygg_brew_eksport_label()
-- ingen ny, parallell sorterings-/etikett-logikk lages her.

Omfang (issue #83): KUN lesing/formatering av et allerede lagret brygg
for visning -- et read-only planlagt-sammendrag fra det frosne
snapshotet, og en planlagt-vs-faktisk-sammenligning fra actuals. Selve
lagringen (eksplisitt "Lagre"-klikk) skjer i UI-laget, som kaller
modules/kbhbrew_storage.py::oppdater_brew_lag() direkte -- ingen ny
skrivevei bygges her.
"""
import math
import re

from modules.calculations import beregn_abv_fra_og_fg

_TALLTYPER = (int, float)


def _er_reelt_tall(v):
    return isinstance(v, _TALLTYPER) and not isinstance(v, bool)


# Chief review-fiks (PR #84 runde 2, issue #83): modules/kbhbrew.py sin
# normaliser_actuals_lag() er BEVISST tolerant (Core V1 Section 5.16,
# JS parseFloat-prefiks-parity for import/kryss-app-data) -- "1,055"
# tolkes som "1" (komma stopper prefikset), "1.055abc" tolkes som
# "1.055" (etterslep forkastes stille), og ren søppel-tekst gir None,
# som ved lagring TØMMER et allerede lagret mål uten synlig varsel.
# Riktig oppførsel for Core-normaliseringen (import/legacy-toleranse) er
# FEIL for direkte manuell tasting i denne UI-en -- en skrivefeil skal
# ALDRI stille lagres som et annet tall, og ugyldig tekst skal ALDRI
# oppføre seg som en implisitt "tøm feltet"-handling (som er reservert
# for et BEVISST blankt felt). Denne funksjonen validerer derfor
# rå-teksten STRENGT her, FØR den når oppdater_brew_lag() i det hele
# tatt -- selve Core-normaliseringen i modules/kbhbrew.py endres IKKE
# (utenfor scope, se issue #83 "Do not redesign .kbhbrew V1").
_TALLFELT_KOMMA_RE = re.compile(r"^[+-]?\d+,\d+$")


def parse_actual_tallfelt(raw_tekst):
    """Strengt validerer ETT actuals-tallfelt (og/fg/volumeL) fra
    Brew History-skjemaet, FØR kalleren i det hele tatt bygger
    `actuals`-argumentet til oppdater_brew_lag().

    Returnerer (True, None) for et blankt/tomt felt -- det BEVISST
    reserverte "tøm dette feltet"-signalet, uendret oppførsel fra før
    denne fiksen.

    Returnerer (True, <float>) for eksakt gyldig tallgrammatikk (Python
    sin egen `float()`, INGEN prefiks-/etterslep-toleranse) eller for
    norsk komma-som-desimaltegn ("1,055" -> 1.055, KUN når teksten er
    ett heltall, komma, ett heltall -- aldri en gjetning på et
    tusenskille).

    Returnerer (False, None) for ALT annet (søppeltekst, flere komma,
    komma OG punktum, uendelig/NaN, tallEtterfulgtAvSøppel) -- kalleren
    MÅ da vise en synlig feil og utføre INGEN skriving i det hele
    tatt, for NOEN av de redigerte tallfeltene i samme lagre-klikk."""
    tekst = raw_tekst.strip() if isinstance(raw_tekst, str) else ""
    if not tekst:
        return True, None
    kandidat = tekst
    if _TALLFELT_KOMMA_RE.match(kandidat):
        kandidat = kandidat.replace(",", ".")
    try:
        verdi = float(kandidat)
    except ValueError:
        return False, None
    if not math.isfinite(verdi):
        return False, None
    return True, verdi


def bygg_planlagt_sammendrag(brew):
    """Read-only planlagt-sammendrag fra brew["snapshot"] (issue #83,
    "Read-only frozen plan summary") -- leser ALDRI actuals eller
    dagens masterdata/oppskrift, kun det frosne laget pluss identitets-/
    statusfeltene på selve brew-objektet. Et manglende/uventet felt gir
    None i resultatet, ALDRI en fabrikert verdi -- kalleren (UI-laget)
    avgjør selv hvordan et manglende felt vises ("—")."""
    brew = brew if isinstance(brew, dict) else {}
    snapshot = brew.get("snapshot") or {}
    recipe = snapshot.get("recipe") or {}
    predicted = snapshot.get("predicted") or {}
    return {
        "navn": recipe.get("navn") or "(uten navn)",
        "planlagt_og": predicted.get("og") if _er_reelt_tall(predicted.get("og")) else None,
        "planlagt_fg": predicted.get("fg") if _er_reelt_tall(predicted.get("fg")) else None,
        "planlagt_abv": predicted.get("abv") if _er_reelt_tall(predicted.get("abv")) else None,
        "planlagt_volum": recipe.get("volum") if _er_reelt_tall(recipe.get("volum")) else None,
        "opprettet_dato": brew.get("createdAt"),
        "brygget_dato": brew.get("brewedAt"),
        "status": brew.get("status"),
    }


def bygg_planlagt_vs_faktisk(brew):
    """Planlagt-vs-faktisk-sammenligning (issue #83, "Planned vs
    actual") -- inkluderer KUN rader der en verdi faktisk finnes,
    utelater resten helt i stedet for å vise en gjettet/fabrikert
    0-verdi.

    Returnerer et dict med opptil nøklene "og"/"fg"/"volum"/"abv", hver
    formet som {"planlagt": <tall|None>, "faktisk": <tall|dict|None>}:

      - "og"/"fg": tas med hvis MINST én av planlagt/faktisk finnes.
      - "volum": tas med KUN hvis en planlagt verdi finnes (issue #83:
        "volume: planned vs actual when a planned volume exists").
      - "abv": "faktisk" avledes UTELUKKENDE for visning her -- ALDRI
        lagret/skrevet til `.kbhbrew`-actuals (se
        modules/kbhbrew.py::FORBUDTE_ACTUALS_EKSPORTFELT) -- via den
        eksisterende Core-kontrakten fra issue #77
        (modules/calculations.py::beregn_abv_fra_og_fg()), som
        returnerer BEGGE navngitte estimater
        ({"standard", "high_gravity"}) -- ingen ny ABV-formel bygges
        her. Kun tatt med hvis BÅDE faktisk OG og faktisk FG finnes,
        ELLER en planlagt ABV finnes."""
    brew = brew if isinstance(brew, dict) else {}
    snapshot = brew.get("snapshot") or {}
    predicted = snapshot.get("predicted") or {}
    recipe = snapshot.get("recipe") or {}
    actuals = brew.get("actuals") or {}

    ut = {}

    planlagt_og = predicted.get("og") if _er_reelt_tall(predicted.get("og")) else None
    faktisk_og = actuals.get("og") if _er_reelt_tall(actuals.get("og")) else None
    if planlagt_og is not None or faktisk_og is not None:
        ut["og"] = {"planlagt": planlagt_og, "faktisk": faktisk_og}

    planlagt_fg = predicted.get("fg") if _er_reelt_tall(predicted.get("fg")) else None
    faktisk_fg = actuals.get("fg") if _er_reelt_tall(actuals.get("fg")) else None
    if planlagt_fg is not None or faktisk_fg is not None:
        ut["fg"] = {"planlagt": planlagt_fg, "faktisk": faktisk_fg}

    planlagt_volum = recipe.get("volum") if _er_reelt_tall(recipe.get("volum")) else None
    if planlagt_volum is not None:
        faktisk_volum = actuals.get("volumeL") if _er_reelt_tall(actuals.get("volumeL")) else None
        ut["volum"] = {"planlagt": planlagt_volum, "faktisk": faktisk_volum}

    planlagt_abv = predicted.get("abv") if _er_reelt_tall(predicted.get("abv")) else None
    faktisk_abv = None
    if faktisk_og is not None and faktisk_fg is not None:
        try:
            faktisk_abv = beregn_abv_fra_og_fg(faktisk_og, faktisk_fg)
        except ValueError:
            faktisk_abv = None
    if planlagt_abv is not None or faktisk_abv is not None:
        ut["abv"] = {"planlagt": planlagt_abv, "faktisk": faktisk_abv, "faktisk_og": faktisk_og}

    return ut
