# ui/bryggeskole_panel.py
"""
Kvernhaug Bryggeskole -- flermodul lærings-UI (issue #338, productionizing
the owner-accepted multi-module Bryggeskole UX direction; issue #366 adds
Koking som tredje modul; issue #370 adds Kjøling/overføring som fjerde
modul; issue #374 adds Pakking som femte fysiske prosess-modul; issue
#380 adds Forberedelse/metode som sjette og siste modul, fylt inn i
prosessgridets tidligere ubrukte første celle).
Renderes som sin egen topplinje-fane i app.py, ikke gjemt under Verktøy.

Én Bryggeskole -> to visuelle miljøer (Hjemmebrygger / Bryggeri) -> én
skoleoversikt med seks reelle, åpne moduler (Forberedelse/metode /
Mesking / Koking / Kjøling-overføring / Gjæring / Pakking) -- delt
verifisert kunnskap + delt mastery på tvers av moduler og miljøer.
Miljøvalget er bevisst uendret fra issue #327: kun navigasjon/
presentasjon, ingen nye kursfakta oppstår her.

Gjenbruker den eksisterende læringsmotoren uendret, per issue #338 sitt
eksplisitte "Reuse boundaries"-krav -- nå fra SEKS topic-scopede
pilotmoduler i stedet for én, hver med nøyaktig samme funksjonsnavn
(read_pilot_file/render_chunk/render_question/evaluate_answer, per
bryggeskole/pilot_mashing.py sin egen "topic-scoped copy, never a shared
engine"-arkitektur):
    bryggeskole.pilot_mashing / bryggeskole.pilot_fermentation
        / bryggeskole.pilot_boil_hop / bryggeskole.pilot_cool_transfer
        / bryggeskole.pilot_package / bryggeskole.pilot_method_context
    bryggeskole.mastery.{apply_answer, mastery_label}
    bryggeskole.mastery_store.{read_mastery_state, write_mastery_state,
        neutral_state_document}
Ingen av disse er endret for denne skiven. Én NY, rent tilleggsmodul,
bryggeskole/answer_order.py, dekker det NYE "answer-option order"-kravet
issue #338 selv innfører (fantes ikke i issue #327s scope) -- se dens egen
docstring. bryggeskole/boil_timeline.py (issue #366),
bryggeskole/cool_transfer_flow.py (issue #370),
bryggeskole/package_flow.py (issue #374) og
bryggeskole/method_context_flow.py (issue #380) er hver sin egen, rene
SVG-genererende tilleggsmodul for Koking-, Kjøling/overføring-, Pakking-
og Forberedelse/metode-modulenes eneste visuelle krav -- se deres egne
docstrings. Pakking-modulen gjenbruker to eksisterende verifiserte
fakta/konsept-id-er fra Kjøling/overføring (cool.sanitation_boundary,
oxygen.post_pitch), og Forberedelse/metode-modulen gjenbruker to
eksisterende verifiserte fakta fra Mesking/Koking (FACT-MASH-0001,
FACT-BOIL-0001) under sin egen module-lokale
"method.shared_process"-konsept-id (kontrakt §8: ikke en ny
Registry-konsept på de gjenbrukte fakta-postene) -- se
bryggeskole/pilot_package.py og bryggeskole/pilot_method_context.py sine
egne docstrings -- den konkrete mekanismen bak "delt mastery på tvers av
moduler" nevnt under.

Skoleoversikten gjenbruker den eksisterende seks-stadiers prosessgrid fra
issue #327 (_PROSESS_STADIER) i stedet for å bygge en egen parallell
modul-kort-grid ved siden av den: alle seks stadiene (Forberedelse/
metode, Mesking, Koking, Kjøling, Gjæring, Pakking) er nå klikkbare
moduler med statusmerker -- det første stadiet het tidligere "Maling av
malt"/"Mølle" og var ren orientering ("Kommer senere"); issue #380 fyller
denne siste ubrukte cellen med en ekte modul og gir den et
lærings-dekkende navn (Forberedelse/metode) i stedet for det tidligere
malings-spesifikke navnet. Dette er bevisst étt sammenhengende grid, ikke
to -- det tilfredsstiller "show full brewing learning journey" +
"compact module cards that scale to 3+ active modules" samtidig.

Sesjonstilstand er nå PER MODUL (st.session_state["bs_modul_sesjon"][id]),
ikke global -- "returning to overview does not discard active session
progress" og "in-session resume per module" krever at hver modul husker
sin egen fase/runde/spørsmål-indeks uavhengig av at læreren navigerer
frem og tilbake til skoleoversikten. Ingen ny PERSISTENT
fullføringskontrakt er lagt til: "Gjennomført denne økten" lever kun i
st.session_state, aldri på disk/mastery_store.

DEMO_MODE-grensen er uendret fra issue #327: en PANEL-NIVÅ vakt her (ikke
en ny modules/bryggeskole_state.py-adapter), se _les_tilstand()/
_skriv_tilstand() -- samme begrunnelse som før, ui/demo_state.py er
avgrenset til fire urelaterte domener og bryggeskole/mastery_store.py
er allerede sin egen isolerte lese/skrive-grense.
"""
import datetime
import random

import streamlit as st

from config import DEMO_MODE
from bryggeskole.answer_order import finn_korrekt_indeks, velg_alternativ_rekkefolge
from bryggeskole.boil_timeline import render_boil_timeline_svg
from bryggeskole.cool_transfer_flow import render_cool_transfer_flow_svg
from bryggeskole.mastery import apply_answer, mastery_label
from bryggeskole.mastery_store import (
    neutral_state_document,
    read_mastery_state,
    write_mastery_state,
)
from bryggeskole.method_context_flow import render_method_context_flow_svg
from bryggeskole.package_flow import render_package_flow_svg
from bryggeskole import pilot_boil_hop as _pilot_koking
from bryggeskole import pilot_cool_transfer as _pilot_kjoling
from bryggeskole import pilot_fermentation as _pilot_gjaring
from bryggeskole import pilot_mashing as _pilot_mesking
from bryggeskole import pilot_method_context as _pilot_metodevalg
from bryggeskole import pilot_package as _pilot_pakking
from ui.i18n import gjeldende_sprak, t

# Hver pilotmodul definerer sin EGEN PilotContentError-klasse (bevisst
# topic-scopet kopi, jf. pilot_mashing.py sin docstring -- "never a shared
# engine") -- de er derfor IKKE samme klasseobjekt og må fanges som et
# tuppel, aldri bare den ene modulens, ellers ville den andre modulens
# feil forbli ufanget her.
_PILOT_CONTENT_ERRORS = (
    _pilot_mesking.PilotContentError,
    _pilot_gjaring.PilotContentError,
    _pilot_koking.PilotContentError,
    _pilot_kjoling.PilotContentError,
    _pilot_pakking.PilotContentError,
    _pilot_metodevalg.PilotContentError,
)

_ENV_HJEMMEBRYGGER = "hjemmebrygger"
_ENV_BRYGGERI = "bryggeri"

_MODUL_METODEVALG = "metodevalg"
_MODUL_MESKING = "mesking"
_MODUL_KOKING = "koking"
_MODUL_KJOLING = "kjoling"
_MODUL_GJARING = "gjaring"
_MODUL_PAKKING = "pakking"

# Rekkefølgen speiler den faktiske brygge-prosessen (forberedelse/metode
# før mesk før koking før kjøling/overføring før gjæring før pakking) --
# brukt både til plasseringen i prosessgridet og til _anbefalt_modul()s
# "anbefalt neste"-signal.
_MODUL_REKKEFOLGE = [
    _MODUL_METODEVALG, _MODUL_MESKING, _MODUL_KOKING, _MODUL_KJOLING, _MODUL_GJARING, _MODUL_PAKKING,
]

_MODULER = {
    _MODUL_METODEVALG: {
        "pilot": _pilot_metodevalg,
        "tittel_nokkel": "bryggeskole.modul.metodevalg.tittel",
        "ikon": "🧭",
    },
    _MODUL_MESKING: {
        "pilot": _pilot_mesking,
        "tittel_nokkel": "bryggeskole.modul.mesking.tittel",
        "ikon": "🌾",
    },
    _MODUL_KOKING: {
        "pilot": _pilot_koking,
        "tittel_nokkel": "bryggeskole.modul.koking.tittel",
        "ikon": "🔥",
    },
    _MODUL_KJOLING: {
        "pilot": _pilot_kjoling,
        "tittel_nokkel": "bryggeskole.modul.kjoling.tittel",
        "ikon": "❄️",
    },
    _MODUL_GJARING: {
        "pilot": _pilot_gjaring,
        "tittel_nokkel": "bryggeskole.modul.gjaring.tittel",
        "ikon": "🧪",
    },
    _MODUL_PAKKING: {
        "pilot": _pilot_pakking,
        "tittel_nokkel": "bryggeskole.modul.pakking.tittel",
        "ikon": "📦",
    },
}

# Seks representative prosess-stadier (forberedelse/metode -> mesk ->
# koking -> kjøling -> gjæring -> pakking) i to miljø-varianter, per
# issue #327 sitt krav om "malt/milling → mash → boil → cooling →
# fermentation → packaging". Bevisst lokale bilingual-dicts (samme
# mønster som bryggeskole/pilot_fermentation.py sitt eget "no"/
# "en"-format) i stedet for modules/i18n.py-nøkler, for å holde
# i18n-tillegget der til et minimum -- disse er navigasjons-/
# presentasjonstekst, ikke lærings-innhold, og teksten er identisk begge
# steder uansett miljøvalg. Det første stadiet het tidligere "Maling av
# malt"/"Mølle" og var kun orientering; issue #380 gir det navnet
# Forberedelse/metode i BEGGE miljøer (Chief-avgjørelse i kontrakt §5) nå
# som det peker til en ekte modul.
_PROSESS_STADIER = {
    _ENV_HJEMMEBRYGGER: [
        {"no": "Forberedelse/metode", "en": "Preparation/method"},
        {"no": "Mesking (kjele/BIAB)", "en": "Mashing (kettle/BIAB)"},
        {"no": "Koking", "en": "Boil"},
        {"no": "Kjøling", "en": "Cooling"},
        {"no": "Gjæring (bøtte/FermZilla)", "en": "Fermentation (bucket/FermZilla)"},
        {"no": "Tapping/flasking", "en": "Kegging/bottling"},
    ],
    _ENV_BRYGGERI: [
        {"no": "Forberedelse/metode", "en": "Preparation/method"},
        {"no": "Mesk/lauter", "en": "Mash/lauter"},
        {"no": "Kokekar/whirlpool", "en": "Kettle/whirlpool"},
        {"no": "Varmeveksler", "en": "Heat exchanger"},
        {"no": "Konisk gjæringstank", "en": "Conical fermenter"},
        {"no": "Pakking/CIP", "en": "Packaging/CIP"},
    ],
}

# Samme indekser i begge miljøer -- nå alle seks stadiene er
# aktive/klikkbare (issue #380 fyller den tidligere siste "Kommer
# senere"-cellen, indeks 0).
_STADIUM_TIL_MODUL = {
    0: _MODUL_METODEVALG, 1: _MODUL_MESKING, 2: _MODUL_KOKING, 3: _MODUL_KJOLING,
    4: _MODUL_GJARING, 5: _MODUL_PAKKING,
}

# Menneskelesbare visningsnavn for pilotenes konsept-id-er -- aldri de
# rå id-strengene selv i oppsummeringen (læreren skal aldri se f.eks.
# "fermentation.temperature" som tekst).
_KONSEPT_LABELS = {
    "fermentation.temperature": {"no": "Gjæringstemperatur", "en": "Fermentation temperature"},
    "fermentation.yeast_activity": {"no": "Gjæraktivitet", "en": "Yeast activity"},
    "fermentation.flavor": {"no": "Smak og aroma", "en": "Flavor and aroma"},
    "fermentation.yeast_strain": {"no": "Gjærstamme-avhengighet", "en": "Yeast strain dependence"},
    "mashing.starch_conversion": {"no": "Stivelsesomdanning", "en": "Starch conversion"},
    "mashing.dextrins": {"no": "Dekstriner", "en": "Dextrins"},
    "mashing.temperature": {"no": "Mesketemperatur", "en": "Mash temperature"},
    "mashing.fermentability": {"no": "Gjærbarhet", "en": "Fermentability"},
    "mashing.process_variables": {"no": "Andre prosessfaktorer", "en": "Other process variables"},
    "boil.enzyme_inactivation": {"no": "Enzym-inaktivering", "en": "Enzyme inactivation"},
    "boil.volatile_removal": {"no": "Fjerning av flyktige stoffer (DMS)", "en": "Volatile removal (DMS)"},
    "boil.hot_break": {"no": "Hot break", "en": "Hot break"},
    "boil.observation": {"no": "Kokeobservasjon", "en": "Boil observation"},
    "hop.isomerization_time": {"no": "Isomerisering og koketid", "en": "Isomerization and boil time"},
    "hop.aroma_volatility": {"no": "Aroma og flyktighet", "en": "Aroma and volatility"},
    "hop.addition_strategy": {"no": "Tilsetningsstrategi", "en": "Addition strategy"},
    "hop.whirlpool_technique": {"no": "Whirlpool-teknikk", "en": "Whirlpool technique"},
    "cool.speed": {"no": "Nedkjølingshastighet", "en": "Cooling speed"},
    "cool.cold_break": {"no": "Kjøldis", "en": "Cold break"},
    "cool.sanitation_boundary": {"no": "Saniteringsgrense", "en": "Sanitation boundary"},
    "oxygen.pre_pitch": {"no": "Oksygen før pitching", "en": "Pre-pitch oxygen"},
    "oxygen.post_pitch": {"no": "Oksygen under gjæring", "en": "Oxygen during fermentation"},
    "oxygen.timing_distinction": {"no": "Oksygen-tidspunkt", "en": "Oxygen timing"},
    "transfer.method_tradeoffs": {"no": "Overføringsmetoder", "en": "Transfer methods"},
    "package.priming": {"no": "Flaskekonditionering", "en": "Bottle conditioning"},
    "package.force_carbonation": {"no": "Tvangskarbonering", "en": "Force carbonation"},
    "package.pressure_safety": {"no": "Trykksikkerhet ved pakking", "en": "Packaging pressure safety"},
    "package.path_choice": {"no": "Valg av pakkemetode", "en": "Packaging method choice"},
    "method.shared_process": {"no": "Delt bryggeprosess", "en": "Shared brewing process"},
    "method.biab": {"no": "Meskepose (BIAB)", "en": "Mash bag (BIAB)"},
    "method.traditional_allgrain": {"no": "Tradisjonelt alt-korn-oppsett", "en": "Traditional all-grain setup"},
    "method.all_in_one": {"no": "Alt-i-ett bryggemaskin", "en": "All-in-one brewing machine"},
    "method.planning_variables": {"no": "Metodeavhengig planlegging", "en": "Method-dependent planning"},
    "method.no_hierarchy": {"no": "Ingen metodehierarki", "en": "No method hierarchy"},
}

_DEMO_TILSTAND_NOKKEL = "_demo_bryggeskole_mastery_tilstand"


def _konsept_label(konsept_id, sprak):
    return _KONSEPT_LABELS.get(konsept_id, {}).get(sprak, konsept_id)


def _les_tilstand():
    if DEMO_MODE:
        if _DEMO_TILSTAND_NOKKEL not in st.session_state:
            st.session_state[_DEMO_TILSTAND_NOKKEL] = neutral_state_document()
        return st.session_state[_DEMO_TILSTAND_NOKKEL]
    return read_mastery_state()


def _skriv_tilstand(dokument):
    if DEMO_MODE:
        st.session_state[_DEMO_TILSTAND_NOKKEL] = dokument
        return
    write_mastery_state(dokument)


def _utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _konsept_rekkefolge(pilot):
    """Pedagogisk konsept-rekkefølge -- rekkefølgen konseptene FØRST nevnes
    av pilotens egne spørsmål (som igjen følger chunk-rekkefølgen
    innholdet ble undervist i), IKKE alfabetisk id-sortering. Issue #338:
    "concept presentation order follows pedagogical learning order, not
    alphabetic concept-id order"."""
    rekkefolge = []
    for sporsmal in pilot["questions"]:
        for konsept_id in sporsmal["concepts"]:
            if konsept_id not in rekkefolge:
                rekkefolge.append(konsept_id)
    return rekkefolge


def _init_state():
    st.session_state.setdefault("bs_miljo", None)
    st.session_state.setdefault("bs_aktiv_modul", None)
    st.session_state.setdefault("bs_modul_sesjon", {})
    _ovd_tidligere_baseline()


def _ny_modul_sesjon():
    return {
        "fase": "leksjon",
        # Læringsbolkene vises ÉN om gangen (issue #338: "overview ->
        # chunks -> question..."). Posisjonen ligger her, per modul, slik
        # at en tur til skoleoversikten og tilbake gjenopptar nøyaktig
        # samme bolk -- og slik at Mesking og Gjæring har helt uavhengig
        # leksjonsfremdrift i samme økt.
        "bolk_idx": 0,
        "sporsmal_idx": 0,
        "runde": 0,
        "siste_feedback": None,
        "fullfort_denne_okten": False,
        "rekkefolger": {},
        "forrige_korrekt_indeks": {},
    }


def _har_persistert_praksis(modul_id, tilstand):
    """True hvis den PERSISTERTE mastery-tilstanden har minst ett forsøk
    på et av modulens konsepter."""
    try:
        pilot = _MODULER[modul_id]["pilot"].read_pilot_file()
    except _PILOT_CONTENT_ERRORS:
        return False
    konsepter = _konsept_rekkefolge(pilot)
    return any(
        (tilstand.get("concepts", {}).get(k) or {}).get("attempts", 0) > 0 for k in konsepter
    )


def _ovd_tidligere_baseline():
    """«Øvd på tidligere» ØYEBLIKKSBILDE, tatt før denne øktens egen
    læring rekker å endre noe (Chief review, PR #340).

    Tidligere ble merket utledet direkte fra den LEVENDE persisterte
    tilstanden. Men apply_answer() skriver til disk med én gang læreren
    svarer, så det første svaret i økten skapte umiddelbart «Øvd på
    tidligere» ved siden av «Påbegynt» -- selv for en lærer som aldri
    hadde vært innom modulen før. Issue #338 skiller eksplisitt
    PERSISTENT tidligere praksis fra øktens egen status, så baselinen
    beregnes én gang per Streamlit-økt, ved første render av panelet
    (_init_state()), altså før noe svar kan ha blitt lagret.

    Ingen endring i mastery-schema eller lagring: dette er kun et
    session_state-øyeblikksbilde av tall som allerede fantes.
    """
    if "bs_ovd_baseline" not in st.session_state:
        tilstand = _les_tilstand()
        st.session_state["bs_ovd_baseline"] = {
            modul_id: _har_persistert_praksis(modul_id, tilstand)
            for modul_id in _MODUL_REKKEFOLGE
        }
    return st.session_state["bs_ovd_baseline"]


def _modul_sesjon(modul_id):
    """Henter (og oppretter ved behov) den PER-MODUL sesjonstilstanden.
    Selve opprettelsen her er signalet på at læreren har "Påbegynt" modulen
    denne økten (se _modul_status())."""
    alle = st.session_state["bs_modul_sesjon"]
    if modul_id not in alle:
        alle[modul_id] = _ny_modul_sesjon()
    return alle[modul_id]


def _les_modul_sesjon(modul_id):
    """Samme oppslag som _modul_sesjon(), men oppretter ALDRI en ny
    oppføring -- brukt av skoleoversikten, som må kunne vise «ikke
    påbegynt» uten selv å utløse en "Påbegynt"-tilstand ved bare å se på
    kortet."""
    return st.session_state["bs_modul_sesjon"].get(modul_id)


def _velg_miljo(miljo):
    st.session_state["bs_miljo"] = miljo
    st.session_state["bs_aktiv_modul"] = None


def _bytt_miljo():
    st.session_state["bs_miljo"] = None
    st.session_state["bs_aktiv_modul"] = None


def _apne_modul(modul_id):
    st.session_state["bs_aktiv_modul"] = modul_id
    _modul_sesjon(modul_id)


def _tilbake_til_oversikt():
    st.session_state["bs_aktiv_modul"] = None


def _bla_bolk(modul_id, delta, totalt):
    """Flytter leksjonsposisjonen én bolk fram/tilbake, klemt innenfor
    modulens egne bolker."""
    sesjon = _modul_sesjon(modul_id)
    sesjon["bolk_idx"] = max(0, min(totalt - 1, sesjon["bolk_idx"] + delta))


def _start_sporsmal_runde(modul_id):
    """Starter (eller re-starter, ved «Prøv igjen») spørsmålsrunden fra
    første spørsmål. Øker ALLTID sesjon["runde"], slik at hvert
    spørsmål-widget-key blir garantert unikt for denne runden -- uten
    dette ville et gjenbrukt key ha fått Streamlit til å vise en gammel,
    lagret radioverdi fra en tidligere runde, og alternativ-rekkefølgen
    (frosset per runde, se _hent_alternativ_rekkefolge()) ville ikke blitt
    trukket på nytt. `apply_answer()`s egen `first_attempt`-logikk leser
    fortsatt den PERSISTERTE mastery-tilstanden uendret -- «Prøv igjen»
    resetter aldri selve mastery-tilstanden, kun denne UI-runden."""
    sesjon = _modul_sesjon(modul_id)
    sesjon["runde"] += 1
    sesjon["fase"] = "sporsmal"
    sesjon["sporsmal_idx"] = 0
    sesjon["siste_feedback"] = None


def _hent_alternativ_rekkefolge(sesjon, sporsmal):
    """Henter den frosne visningsrekkefølgen (liste med alternativ-id-er)
    for dette spørsmålet i denne runden, eller trekker og fryser en ny
    første gang spørsmålet vises i runden -- uendret gjennom reruns/
    submit/back-resume, per issue #338s "Answer-option order"-krav.
    RNG-en er ekte tilfeldig i produksjon (random.Random()); testene
    injiserer sin egen kontrollerte RNG direkte mot
    bryggeskole.answer_order, ikke via denne funksjonen."""
    runde = sesjon["runde"]
    rekkefolger_for_runde = sesjon["rekkefolger"].setdefault(runde, {})
    qid = sporsmal["id"]
    if qid in rekkefolger_for_runde:
        return rekkefolger_for_runde[qid]

    forrige_indeks = sesjon["forrige_korrekt_indeks"].get(runde)
    rekkefolge_raw = velg_alternativ_rekkefolge(sporsmal["options"], forrige_indeks, random.Random())
    id_rekkefolge = [o["id"] for o in rekkefolge_raw]
    rekkefolger_for_runde[qid] = id_rekkefolge
    sesjon["forrige_korrekt_indeks"][runde] = finn_korrekt_indeks(rekkefolge_raw)
    return id_rekkefolge


def _sjekk_svar(modul_id, sporsmal, sprak, widget_key, runde):
    pilot_modul = _MODULER[modul_id]["pilot"]
    valgt_id = st.session_state.get(widget_key)
    if valgt_id is None:
        # Forsvarslinje mot Chief-review-blokkeren (PR #328): knappen er
        # disabled inntil et svar er valgt (se _render_sporsmal), men denne
        # vaktlinjen sikrer at et uvalgt spørsmål ALDRI kan mutere persistert
        # mastery selv om noe utenfor normal UI-flyt likevel utløser klikket.
        return
    resultat = pilot_modul.evaluate_answer(sporsmal, valgt_id, sprak)
    tilstand = _les_tilstand()
    nytt_tilstand = apply_answer(tilstand, sporsmal, resultat["correct"], now=_utc_now_iso())
    _skriv_tilstand(nytt_tilstand)
    sesjon = _modul_sesjon(modul_id)
    sesjon["siste_feedback"] = {
        "question_id": resultat["question_id"],
        "runde": runde,
        "correct": resultat["correct"],
        "valgt_id": valgt_id,
        "feedback": resultat["feedback"],
    }


def _neste_sporsmal(modul_id, totalt):
    sesjon = _modul_sesjon(modul_id)
    ny_idx = sesjon["sporsmal_idx"] + 1
    sesjon["sporsmal_idx"] = ny_idx
    sesjon["siste_feedback"] = None
    if ny_idx >= totalt:
        sesjon["fase"] = "oppsummering"
        sesjon["fullfort_denne_okten"] = True
    else:
        sesjon["fase"] = "sporsmal"


def _injiser_bryggeskole_css():
    """Scoped typografi -- KUN for Bryggeskole-panelets egne containere
    (st.container(key=...) gir Streamlit sin egen "st-key-<key>"-klasse på
    wrapper-diven), aldri en global theme-endring. "learning text visually
    dominates controls": leksjon-/spørsmålstekst får større skrift/
    linjehøyde; ingen annen fane i appen bruker disse nøklene, så CSS-en
    kan aldri lekke ut av Bryggeskole-fanen."""
    st.markdown(
        """
        <style>
        .st-key-bs_leksjon_tekst p, .st-key-bs_sporsmal_tekst p {
            font-size: 1.08rem;
            line-height: 1.7;
        }
        .st-key-bs_sporsmal_tekst p {
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _modul_status(modul_id):
    """Returnerer (ovd_tidligere, sesjon) for statusmerkene på et
    modul-kort:
    - ovd_tidligere: praksis som fantes FØR denne økten -- lest fra
      øktens baseline (_ovd_tidligere_baseline()), aldri fra den levende
      tilstanden, slik at øktens egne svar ikke kan skape merket.
    - sesjon: None hvis aldri åpnet denne økten; ellers selve
      sesjondict-en, som avgjør "Påbegynt" vs. "Gjennomført denne økten"."""
    return _ovd_tidligere_baseline().get(modul_id, False), _les_modul_sesjon(modul_id)


def _anbefalt_modul():
    """Ett ikke-blokkerende "anbefalt neste"-signal, basert på
    prosessrekkefølgen (mesk før gjæring) og gjeldende øktstatus -- den
    første modulen i _MODUL_REKKEFOLGE som IKKE er "Gjennomført denne
    økten" ennå. Returnerer None når alle er fullført denne økten (ingen
    anbefaling å gi). Anbefalingen låser aldri en annen modul -- den er
    bare en ekstra ledetekst over det samme klikkbare gridet."""
    for modul_id in _MODUL_REKKEFOLGE:
        sesjon = _les_modul_sesjon(modul_id)
        if not (sesjon and sesjon["fullfort_denne_okten"]):
            return modul_id
    return None


def _render_miljovalg():
    st.subheader(t("bryggeskole.velg_miljo_heading"))
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown(f"### {t('bryggeskole.miljo.hjemmebrygger')}")
            st.caption(t("bryggeskole.miljo.hjemmebrygger_beskrivelse"))
            st.button(
                t("bryggeskole.miljo.velg_knapp"), key="bs_velg_hjemmebrygger_btn",
                width="stretch", on_click=_velg_miljo, args=(_ENV_HJEMMEBRYGGER,),
            )
    with col2:
        with st.container(border=True):
            st.markdown(f"### {t('bryggeskole.miljo.bryggeri')}")
            st.caption(t("bryggeskole.miljo.bryggeri_beskrivelse"))
            st.button(
                t("bryggeskole.miljo.velg_knapp"), key="bs_velg_bryggeri_btn",
                width="stretch", on_click=_velg_miljo, args=(_ENV_BRYGGERI,),
            )


def _render_skoleoversikt(miljo, sprak):
    st.subheader(t(f"bryggeskole.miljo.{miljo}"))

    anbefalt = _anbefalt_modul()
    if anbefalt is not None:
        st.info(t("bryggeskole.anbefalt_neste", modul=t(_MODULER[anbefalt]["tittel_nokkel"])))

    stadier = _PROSESS_STADIER[miljo]
    cols = st.columns(len(stadier))
    for i, (col, stadium) in enumerate(zip(cols, stadier)):
        modul_id = _STADIUM_TIL_MODUL.get(i)
        with col, st.container(border=True):
            st.markdown(f"**{stadium[sprak]}**")
            if modul_id is None:
                st.caption(t("bryggeskole.prosess.kommer_badge"))
                continue

            st.caption(t("bryggeskole.prosess.aktiv_badge"))
            ovd_tidligere, sesjon = _modul_status(modul_id)
            merker = []
            if ovd_tidligere:
                merker.append(t("bryggeskole.status.ovd_tidligere"))
            if sesjon and sesjon["fullfort_denne_okten"]:
                merker.append(t("bryggeskole.status.fullfort_okt"))
            elif sesjon:
                merker.append(t("bryggeskole.status.pabegynt"))
            for merke in merker:
                st.caption(merke)

            if sesjon is None:
                knapp_tekst = t("bryggeskole.modul.start")
            elif sesjon["fullfort_denne_okten"]:
                knapp_tekst = t("bryggeskole.modul.se_resultat")
            else:
                knapp_tekst = t("bryggeskole.modul.fortsett")
            st.button(
                knapp_tekst, key=f"bs_apne_modul_{modul_id}_btn",
                width="stretch", on_click=_apne_modul, args=(modul_id,),
            )


def _render_leksjon(modul_id, sesjon, pilot, sprak):
    """ÉN læringsbolk om gangen (issue #338 / Chief review PR #340).

    Tidligere ble alle pilotens chunks rendret i én lang skjerm og
    læreren hoppet rett til spørsmålene. Nå er leksjonen en egen liten
    reise: bolk 1 -> Neste -> bolk 2 -> ... -> Start spørsmål, med
    posisjonen lagret per modul, slik at en tur innom skoleoversikten
    gjenopptar nøyaktig samme bolk."""
    st.write("---")
    chunks = pilot["chunks"]
    totalt = len(chunks)
    # Defensivt klem: innholdet kan i prinsippet ha blitt kortere siden
    # posisjonen ble lagret (kun mulig ved innholdsendring i dev).
    idx = max(0, min(sesjon["bolk_idx"], totalt - 1))
    sesjon["bolk_idx"] = idx

    st.caption(t("bryggeskole.leksjon.bolk_teller", n=idx + 1, totalt=totalt))
    with st.container(key="bs_leksjon_tekst"):
        st.markdown(_MODULER[modul_id]["pilot"].render_chunk(chunks[idx], sprak)["text"])

    if modul_id == _MODUL_KOKING:
        # Koking-modulens eneste visuelle krav (issue #366 kontrakt §4):
        # ett statisk, ikke-interaktivt tidslinjediagram, synlig gjennom
        # hele leksjonen (ikke bare første/siste bolk) -- se
        # bryggeskole/boil_timeline.py sin docstring.
        st.markdown(render_boil_timeline_svg(sprak), unsafe_allow_html=True)
    elif modul_id == _MODUL_KJOLING:
        # Kjøling/overføring-modulens eneste visuelle krav (issue #370
        # kontrakt §4): ett statisk kjele->kjøling->overføring->gjæringskar
        # flytdiagram med sanitert-sone-skyggelegging, synlig gjennom hele
        # leksjonen -- se bryggeskole/cool_transfer_flow.py sin docstring.
        st.markdown(render_cool_transfer_flow_svg(sprak), unsafe_allow_html=True)
    elif modul_id == _MODUL_PAKKING:
        # Pakking-modulens eneste visuelle krav (issue #374 kontrakt §4):
        # ett statisk gjæringskar->delt sti->flaske/fat->servering/lagring
        # flytdiagram med to likeverdige pakkestier, synlig gjennom hele
        # leksjonen -- se bryggeskole/package_flow.py sin docstring.
        st.markdown(render_package_flow_svg(sprak), unsafe_allow_html=True)
    elif modul_id == _MODUL_METODEVALG:
        # Forberedelse/metode-modulens eneste visuelle krav (issue #380
        # kontrakt §4): tre likeverdige rader (BIAB/tradisjonelt/
        # alt-i-ett) som alle munner ut i den identiske
        # kok->kjøl->gjær->pakk-prosessen, synlig gjennom hele leksjonen --
        # se bryggeskole/method_context_flow.py sin docstring.
        st.markdown(render_method_context_flow_svg(sprak), unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.button(
            t("bryggeskole.leksjon.forrige"), key=f"bs_bolk_forrige_{modul_id}_btn",
            width="stretch", disabled=idx == 0,
            on_click=_bla_bolk, args=(modul_id, -1, totalt),
        )
    with col2:
        if idx + 1 < totalt:
            st.button(
                t("bryggeskole.leksjon.neste"), key=f"bs_bolk_neste_{modul_id}_btn",
                width="stretch", type="primary",
                on_click=_bla_bolk, args=(modul_id, 1, totalt),
            )
        else:
            # «Start spørsmål» finnes KUN på siste bolk -- det er det som
            # gjør leksjonen til en sekvens og ikke en scroll-skjerm.
            st.button(
                t("bryggeskole.leksjon.start_sporsmal"), key=f"bs_start_sporsmal_{modul_id}_btn",
                width="stretch", type="primary",
                on_click=_start_sporsmal_runde, args=(modul_id,),
            )


def _render_sporsmal(modul_id, sesjon, pilot, sprak):
    st.write("---")
    pilot_modul = _MODULER[modul_id]["pilot"]
    sporsmal_liste = pilot["questions"]
    totalt = len(sporsmal_liste)
    idx = sesjon["sporsmal_idx"]
    if idx >= totalt:
        # Forsvarslinje -- normal flyt går alltid via _neste_sporsmal(),
        # som selv setter fasen til "oppsummering" når siste spørsmål er
        # besvart, så dette skal aldri inntreffe i praksis.
        sesjon["fase"] = "oppsummering"
        return

    sporsmal = sporsmal_liste[idx]
    rendret = pilot_modul.render_question(sporsmal, sprak)
    runde = sesjon["runde"]
    # Widget-nøkkelen MÅ inneholde modul_id (Chief review, PR #340):
    # begge moduler starter på samme runde-/spørsmålsindeks, så en
    # modul-agnostisk nøkkel ville latt Streamlit gjenbruke den lagrede
    # radioverdien fra den ene modulen når den andre åpnes i samme økt.
    widget_key = f"bs_valg_{modul_id}_r{runde}_q{idx}"

    id_rekkefolge = _hent_alternativ_rekkefolge(sesjon, sporsmal)
    rendret_by_id = {o["id"]: o for o in rendret["options"]}
    alternativer = [rendret_by_id[oid] for oid in id_rekkefolge]

    siste = sesjon["siste_feedback"]
    besvart = bool(
        siste
        and siste["question_id"] == sporsmal["id"]
        and siste["runde"] == runde
    )

    st.caption(t("bryggeskole.steg.sporsmal", n=idx + 1, totalt=totalt))
    with st.container(key="bs_sporsmal_tekst"):
        st.markdown(rendret["prompt"])

    st.radio(
        t("bryggeskole.sporsmal.velg_svar"),
        options=[o["id"] for o in alternativer],
        format_func=lambda oid: next(o["text"] for o in alternativer if o["id"] == oid),
        index=None,
        key=widget_key,
        label_visibility="collapsed",
        disabled=besvart,
    )

    if not besvart:
        # Chief review (PR #328): en fersk spørsmål-radio må ALDRI ha et
        # forhåndsvalgt alternativ (index=None over), og «Sjekk svar» skal
        # være disabled inntil læreren faktisk har valgt ett -- ellers kan
        # et ubesvart spørsmål stille mutere persistert mastery via
        # Streamlits standard "velg første alternativ"-oppførsel.
        st.button(
            t("bryggeskole.sporsmal.svar_knapp"), key=f"bs_svar_btn_{modul_id}_r{runde}_q{idx}",
            width="stretch", on_click=_sjekk_svar, args=(modul_id, sporsmal, sprak, widget_key, runde),
            disabled=st.session_state.get(widget_key) is None,
        )
    else:
        # Answer-state UX (issue #338): svarstatusen skal aldri hvile kun
        # på radioens grå disabled-styling -- lærerens eget svar og (ved
        # feil) det korrekte svaret vises alltid eksplisitt som tekst.
        valgt_tekst = next(o["text"] for o in alternativer if o["id"] == siste["valgt_id"])
        st.caption(f"{t('bryggeskole.svar.ditt_svar')}: {valgt_tekst}")
        if not siste["correct"]:
            riktig_raw = next(o for o in sporsmal["options"] if o["correct"] is True)
            st.caption(f"{t('bryggeskole.svar.riktig_svar')}: {riktig_raw['text'][sprak]}")
        (st.success if siste["correct"] else st.error)(siste["feedback"])
        st.button(
            t("bryggeskole.sporsmal.fortsett"), key=f"bs_fortsett_btn_{modul_id}_r{runde}_q{idx}",
            width="stretch", on_click=_neste_sporsmal, args=(modul_id, totalt),
        )


def _konsept_runde_status(tilstand, pilot, konsept_id):
    """Utleder DENNE rundens signal for et konsept -- aldri den persisterte
    cumulative masteryen -- fra korrektheten på spørsmålene i akkurat
    fullført runde som dekker konseptet (Chief-review, PR #328: cumulative
    mastery og gjeldende runde ble tidligere vist med samme label, slik at
    en lærer som svarte alt feil på en «Prøv igjen»-runde så nøyaktig samme
    «På god vei» som ved en perfekt runde).

    `tilstand["answered_questions"][qid]["last_correct"]` er alltid det
    SISTE forsøket på det spørsmålet (apply_answer() overskriver den ved
    hvert svar) -- siden oppsummeringsfasen kun nås etter at alle pilotens
    spørsmål er besvart i inneværende runde (se _neste_sporsmal()), er
    dette derfor nøyaktig denne rundens resultat, uten å måtte holde noen
    egen UI-lokal runde-logg.

    Returnerer True (alt riktig denne runden), False (minst ett feil), eller
    None (spørsmålet mangler i answered_questions -- bør ikke inntreffe i
    normal flyt, men behandles defensivt som «intet signal ennå»)."""
    sporsmal_for_konsept = [s for s in pilot["questions"] if konsept_id in s["concepts"]]
    besvarte = tilstand.get("answered_questions") or {}
    resultater = []
    for sporsmal in sporsmal_for_konsept:
        oppforing = besvarte.get(sporsmal["id"])
        if oppforing is None:
            return None
        resultater.append(oppforing["last_correct"])
    if not resultater:
        return None
    return all(resultater)


def _render_oppsummering(modul_id, pilot, sprak):
    st.write("---")
    tilstand = _les_tilstand()
    konsepter = _konsept_rekkefolge(pilot)

    # ÉTT kort per konsept, med BEGGE signalene samlet (issue #338 /
    # Chief review PR #340). Tidligere var dette to atskilte lister --
    # først cumulative mastery for alle konsepter, så denne rundens
    # status for alle konsepter -- slik at læreren måtte holde to lister
    # opp mot hverandre for å se hvordan ett enkelt konsept lå an.
    #
    # De to linjene er bevisst fortsatt SKILT fra hverandre inne i
    # kortet (Chief review, PR #328): «Denne runden» endrer seg synlig
    # ved feil svar selv når «Over tid» ikke gjør det. Rekkefølgen på
    # kortene er pedagogisk (_konsept_rekkefolge()), ikke alfabetisk.
    st.subheader(t("bryggeskole.oppsummering.heading"))
    st.caption(t("bryggeskole.oppsummering.heading_forklaring"))
    for konsept_id in konsepter:
        konsept_tilstand = tilstand["concepts"].get(konsept_id)
        runde_status = _konsept_runde_status(tilstand, pilot, konsept_id)
        if konsept_tilstand is None and runde_status is None:
            continue
        with st.container(border=True):
            st.markdown(f"**{_konsept_label(konsept_id, sprak)}**")
            if runde_status is not None:
                runde_nokkel = (
                    "bryggeskole.oppsummering.runde_ok" if runde_status
                    else "bryggeskole.oppsummering.runde_reprise"
                )
                st.markdown(
                    f"{t('bryggeskole.oppsummering.denne_runden_label')}: {t(runde_nokkel)}"
                )
            if konsept_tilstand is not None:
                st.markdown(
                    f"{t('bryggeskole.oppsummering.over_tid_label')}: "
                    f"{mastery_label(konsept_tilstand, sprak)}"
                )

    col1, col2 = st.columns(2)
    with col1:
        st.button(
            t("bryggeskole.oppsummering.prov_igjen"), key=f"bs_prov_igjen_{modul_id}_btn",
            width="stretch", on_click=_start_sporsmal_runde, args=(modul_id,),
        )
    with col2:
        st.button(
            t("bryggeskole.tilbake_til_oversikt"), key=f"bs_oppsummering_tilbake_{modul_id}_btn",
            width="stretch", on_click=_tilbake_til_oversikt,
        )


def _render_modul(modul_id, miljo, sprak):
    modul_info = _MODULER[modul_id]
    sesjon = _modul_sesjon(modul_id)

    st.caption(
        f"{t('tabs.bryggeskole')} ▸ {t(f'bryggeskole.miljo.{miljo}')} ▸ {t(modul_info['tittel_nokkel'])}"
    )
    st.button(t("bryggeskole.tilbake_til_oversikt"), key=f"bs_tilbake_{modul_id}_btn", on_click=_tilbake_til_oversikt)
    st.subheader(f"{modul_info['ikon']} {t(modul_info['tittel_nokkel'])}")

    fase = sesjon["fase"]
    if fase == "leksjon":
        st.caption(t("bryggeskole.steg.leksjon"))
    elif fase == "oppsummering":
        st.caption(t("bryggeskole.steg.oppsummering"))

    try:
        pilot = modul_info["pilot"].read_pilot_file()
    except _PILOT_CONTENT_ERRORS:
        st.error(t("bryggeskole.feil.innhold_ugyldig"))
        return

    if fase == "leksjon":
        _render_leksjon(modul_id, sesjon, pilot, sprak)
    elif fase == "sporsmal":
        _render_sporsmal(modul_id, sesjon, pilot, sprak)
    else:
        _render_oppsummering(modul_id, pilot, sprak)


def render_bryggeskole_panel():
    _init_state()
    _injiser_bryggeskole_css()
    sprak = gjeldende_sprak()

    st.header(t("bryggeskole.heading"))
    st.caption(t("bryggeskole.tagline"))

    miljo = st.session_state["bs_miljo"]
    if miljo is None:
        _render_miljovalg()
        return

    st.button(t("bryggeskole.bytt_miljo"), key="bs_bytt_miljo_btn", on_click=_bytt_miljo)

    aktiv_modul = st.session_state["bs_aktiv_modul"]
    if aktiv_modul is None:
        _render_skoleoversikt(miljo, sprak)
        return

    _render_modul(aktiv_modul, miljo, sprak)
