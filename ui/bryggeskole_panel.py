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
        / bryggeskole.pilot_raw_materials (issue #458: Råvarer, anbefalt
        først, aldri en lås)
        / bryggeskole.pilot_cleaning_safety (issue #473: Rengjøring og
        sikkerhet, anbefalt rett etter Råvarer, aldri en lås)
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
import logging
import random

import streamlit as st

from config import DEMO_MODE
from bryggeskole import course_stage as _course_stage
from bryggeskole.answer_order import finn_korrekt_indeks, velg_alternativ_rekkefolge
from bryggeskole.boil_timeline import render_boil_timeline_svg
from bryggeskole.cool_transfer_flow import render_cool_transfer_flow_svg
from bryggeskole.malt_roles_strip import render_malt_roles_strip_svg
from bryggeskole.mastery import apply_answer, mastery_label
from bryggeskole.mastery_store import (
    neutral_state_document,
    read_mastery_state,
    write_mastery_state,
)
from bryggeskole.method_context_flow import render_method_context_flow_svg
from bryggeskole.package_flow import render_package_flow_svg
from bryggeskole import pilot_boil_hop as _pilot_koking
from bryggeskole import pilot_cleaning_safety as _pilot_rengjoring
from bryggeskole import pilot_cool_transfer as _pilot_kjoling
from bryggeskole import pilot_fermentation as _pilot_gjaring
from bryggeskole import pilot_mashing as _pilot_mesking
from bryggeskole import pilot_measurement as _pilot_maaling
from bryggeskole import pilot_method_context as _pilot_metodevalg
from bryggeskole import pilot_package as _pilot_pakking
from bryggeskole import pilot_raw_materials as _pilot_raavarer
from bryggeskole import pilot_recipe as _pilot_oppskrift
from bryggeskole import pilot_sensory as _pilot_smak
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
    _pilot_raavarer.PilotContentError,
    _pilot_rengjoring.PilotContentError,
    _pilot_smak.PilotContentError,
    _pilot_maaling.PilotContentError,
    _pilot_oppskrift.PilotContentError,
)

_ENV_HJEMMEBRYGGER = "hjemmebrygger"
_ENV_BRYGGERI = "bryggeri"

# Issue #398 follow-up: two narrow, adjacent columns for a compact
# button pair, plus one wide trailing spacer column that absorbs the
# rest of the row so the pair doesn't spread across the whole width.
# Used everywhere two related Bryggeskole nav/action buttons render side
# by side (lesson Forrige/Neste, summary Prøv igjen/Tilbake). Above the
# mobile breakpoint the ratio no longer sets the button-column WIDTH --
# the scoped `.st-key-bs_nav_actions` rule in _injiser_bryggeskole_css()
# sizes those columns to their button (see there); the ratio only keeps
# the column order and the trailing spacer.
_KNAPP_GRUPPE_KOLONNER = (1, 1, 6)

_MODUL_RAAVARER = "raavarer"
_MODUL_RENGJORING = "rengjoring"
_MODUL_METODEVALG = "metodevalg"
_MODUL_MESKING = "mesking"
_MODUL_KOKING = "koking"
_MODUL_KJOLING = "kjoling"
_MODUL_GJARING = "gjaring"
_MODUL_PAKKING = "pakking"
_MODUL_MAALING = "maaling"
_MODUL_OPPSKRIFT = "oppskrift"
_MODUL_SMAK = "smak"

# Rekkefølgen speiler den faktiske brygge-prosessen (råvarer før
# forberedelse/metode før mesk før koking før kjøling/overføring før
# gjæring før pakking) -- brukt både til plasseringen i prosessgridet og
# til _anbefalt_modul()s "anbefalt neste"-signal. Kun anbefalt rekkefølge
# (issue #458), aldri en lås: alle moduler er alltid klikkbare. Issue #473
# setter Rengjøring og sikkerhet rett etter Råvarer (eierbeslutning). Issue
# #472 legger Smak og evaluering til som siste kort, etter Pakking
# (eierbeslutning D2: evaluering er slutten på bryggesløyfen). Måling og
# bryggelogg (Foundation, målingskontrakten §21.5/§22) settes inn mellom
# Pakking og Smak og evaluering -- kanonisk posisjon 9 (læreplankartet
# §6.2.8). Oppskriftsforståelse (hele modulen er Kompetent,
# oppskriftskontrakten §27/§28) settes inn mellom Måling og Smak --
# kanonisk posisjon 10, Smak og evaluering blir 11.
_MODUL_REKKEFOLGE = [
    _MODUL_RAAVARER, _MODUL_RENGJORING, _MODUL_METODEVALG, _MODUL_MESKING, _MODUL_KOKING,
    _MODUL_KJOLING, _MODUL_GJARING, _MODUL_PAKKING, _MODUL_MAALING, _MODUL_OPPSKRIFT, _MODUL_SMAK,
]

_MODULER = {
    _MODUL_RAAVARER: {
        "pilot": _pilot_raavarer,
        "tittel_nokkel": "bryggeskole.modul.raavarer.tittel",
        "ikon": "🌿",
    },
    _MODUL_RENGJORING: {
        "pilot": _pilot_rengjoring,
        "tittel_nokkel": "bryggeskole.modul.rengjoring.tittel",
        "ikon": "🧼",
    },
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
    _MODUL_MAALING: {
        "pilot": _pilot_maaling,
        "tittel_nokkel": "bryggeskole.modul.maaling.tittel",
        "ikon": "📏",
    },
    _MODUL_OPPSKRIFT: {
        "pilot": _pilot_oppskrift,
        "tittel_nokkel": "bryggeskole.modul.oppskrift.tittel",
        "ikon": "📝",
    },
    _MODUL_SMAK: {
        "pilot": _pilot_smak,
        "tittel_nokkel": "bryggeskole.modul.smak.tittel",
        "ikon": "👃",
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
# som det peker til en ekte modul. Issue #473 legger inn Rengjøring og
# sikkerhet rett etter Råvarer, med samme navn i begge miljøer (bevisst
# ikke "CIP" -- industriell rengjøring er utenfor Foundation-omfanget).
# Issue #472 legger Smak og evaluering til som siste stadium, samme navn i
# begge miljøer. Måling og bryggelogg settes inn før Smak og evaluering,
# også med samme navn i begge miljøer (én felles leksjon, ingen
# miljøspesifikt innhold). Oppskriftsforståelse settes inn mellom Måling og
# Smak, med samme navn i begge miljøer (én felles leksjon).
_PROSESS_STADIER = {
    _ENV_HJEMMEBRYGGER: [
        {"no": "Råvarer", "en": "Raw materials"},
        {"no": "Rengjøring og sikkerhet", "en": "Cleaning and safety"},
        {"no": "Forberedelse/metode", "en": "Preparation/method"},
        {"no": "Mesking (kjele/BIAB)", "en": "Mashing (kettle/BIAB)"},
        {"no": "Koking", "en": "Boil"},
        {"no": "Kjøling", "en": "Cooling"},
        {"no": "Gjæring (bøtte/FermZilla)", "en": "Fermentation (bucket/FermZilla)"},
        {"no": "Pakking", "en": "Packaging"},
        {"no": "Måling og bryggelogg", "en": "Measurement and brew log"},
        {"no": "Oppskriftsforståelse", "en": "Recipe understanding"},
        {"no": "Smak og evaluering", "en": "Tasting and evaluation"},
    ],
    _ENV_BRYGGERI: [
        {"no": "Råvarer", "en": "Raw materials"},
        {"no": "Rengjøring og sikkerhet", "en": "Cleaning and safety"},
        {"no": "Forberedelse/metode", "en": "Preparation/method"},
        {"no": "Mesk/lauter", "en": "Mash/lauter"},
        {"no": "Kokekar/whirlpool", "en": "Kettle/whirlpool"},
        {"no": "Varmeveksler", "en": "Heat exchanger"},
        {"no": "Konisk gjæringstank", "en": "Conical fermenter"},
        {"no": "Pakking/CIP", "en": "Packaging/CIP"},
        {"no": "Måling og bryggelogg", "en": "Measurement and brew log"},
        {"no": "Oppskriftsforståelse", "en": "Recipe understanding"},
        {"no": "Smak og evaluering", "en": "Tasting and evaluation"},
    ],
}

# Samme indekser i begge miljøer -- nå alle seks stadiene er
# aktive/klikkbare (issue #380 fyller den tidligere siste "Kommer
# senere"-cellen, indeks 0; issue #473 setter inn Rengjøring og sikkerhet
# som indeks 1; issue #472 legger Smak og evaluering til som indeks 8;
# Måling og bryggelogg tar indeks 8 og flytter Smak og evaluering til 9;
# Oppskriftsforståelse tar indeks 9 og flytter Smak og evaluering til 10).
_STADIUM_TIL_MODUL = {
    0: _MODUL_RAAVARER, 1: _MODUL_RENGJORING, 2: _MODUL_METODEVALG, 3: _MODUL_MESKING,
    4: _MODUL_KOKING, 5: _MODUL_KJOLING, 6: _MODUL_GJARING, 7: _MODUL_PAKKING, 8: _MODUL_MAALING,
    9: _MODUL_OPPSKRIFT, 10: _MODUL_SMAK,
}

# Menneskelesbare visningsnavn for pilotenes konsept-id-er -- aldri de
# rå id-strengene selv i oppsummeringen (læreren skal aldri se f.eks.
# "fermentation.temperature" som tekst).
_KONSEPT_LABELS = {
    "fermentation.temperature": {"no": "Gjæringstemperatur", "en": "Fermentation temperature"},
    "fermentation.yeast_activity": {"no": "Gjæraktivitet", "en": "Yeast activity"},
    "fermentation.flavor": {"no": "Smak og aroma", "en": "Flavor and aroma"},
    "fermentation.yeast_strain": {"no": "Gjærstamme-avhengighet", "en": "Yeast strain dependence"},
    # Gjæring Kompetent (gjæringskontrakten §12).
    "fermentation.yeast_metabolism": {"no": "Hva gjæren gjør", "en": "What yeast does"},
    "fermentation.phases": {"no": "Gjæringen over tid", "en": "Fermentation over time"},
    "fermentation.byproducts": {"no": "Biprodukter fra gjæringen", "en": "Fermentation by-products"},
    "fermentation.conditioning": {"no": "Modning", "en": "Maturation"},
    "fermentation.process_reasoning": {"no": "Gjæringslogg og resonnering", "en": "Fermentation log and reasoning"},
    "mashing.starch_conversion": {"no": "Stivelsesomdanning", "en": "Starch conversion"},
    "mashing.dextrins": {"no": "Dekstriner", "en": "Dextrins"},
    "mashing.temperature": {"no": "Mesketemperatur", "en": "Mash temperature"},
    "mashing.fermentability": {"no": "Gjærbarhet", "en": "Fermentability"},
    "mashing.process_variables": {"no": "Andre prosessfaktorer", "en": "Other process variables"},
    "mashing.grain_separation": {"no": "Skille vørter fra korn", "en": "Separating wort from grain"},
    "mashing.wort_collection": {"no": "Samle vørteren", "en": "Collecting the wort"},
    "mashing.preboil_check": {"no": "Sjekk før koking", "en": "Pre-boil check"},
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
    "package.priming": {"no": "Flaskekondisjonering", "en": "Bottle conditioning"},
    "package.force_carbonation": {"no": "Tvangskarbonering", "en": "Force carbonation"},
    "package.pressure_safety": {"no": "Trykksikkerhet ved pakking", "en": "Packaging pressure safety"},
    "package.path_choice": {"no": "Valg av pakkemetode", "en": "Packaging method choice"},
    # Pakking Kompetent (pakkekontrakten §5).
    "package.priming_tool": {"no": "Primemengde fra et verktøy", "en": "Priming amount from a trusted tool"},
    "malt.what_is_malt": {"no": "Hva malt er", "en": "What malt is"},
    "malt.base_vs_specialty": {"no": "Basismalt og spesialmalt", "en": "Base and specialty malt"},
    "malt.colour_flavour": {"no": "Maltens farge og smak", "en": "Malt colour and flavour"},
    "malt.grist_percentage": {"no": "Andeler i kornblandingen", "en": "Grist proportions"},
    "hop.alpha_vs_ibu": {"no": "Alfasyre og IBU", "en": "Alpha acid and IBU"},
    "hop.ageing_storage": {"no": "Humleeldring og lagring", "en": "Hop ageing and storage"},
    "yeast.organism_role": {"no": "Gjærens rolle", "en": "The role of yeast"},
    "yeast.attenuation": {"no": "Attenuering", "en": "Attenuation"},
    "yeast.ale_vs_lager": {"no": "Ale- og lagergjær", "en": "Ale and lager yeast"},
    "yeast.choice_principle": {"no": "Valg av gjær", "en": "Choosing yeast"},
    "yeast.pitch_principle": {"no": "Pitching-prinsipp", "en": "Pitching principle"},
    "water.majority_ingredient": {"no": "Vann som råvare", "en": "Water as an ingredient"},
    "water.chlorine_chloramine": {"no": "Klor og kloramin", "en": "Chlorine and chloramine"},
    "water.source_awareness": {"no": "Kjenn din vannkilde", "en": "Know your water source"},
    "method.shared_process": {"no": "Delt bryggeprosess", "en": "Shared brewing process"},
    "method.biab": {"no": "Meskepose (BIAB)", "en": "Mash bag (BIAB)"},
    "method.traditional_allgrain": {"no": "Tradisjonelt alt-korn-oppsett", "en": "Traditional all-grain setup"},
    "method.all_in_one": {"no": "Alt-i-ett bryggemaskin", "en": "All-in-one brewing machine"},
    "method.planning_variables": {"no": "Metodeavhengig planlegging", "en": "Method-dependent planning"},
    "method.no_hierarchy": {"no": "Ingen metodehierarki", "en": "No method hierarchy"},
    "hygiene.clean_vs_sanitize": {"no": "Rengjøring og sanitering", "en": "Cleaning and sanitizing"},
    "hygiene.clean_first": {"no": "Rengjør først", "en": "Clean first"},
    "safety.chem_handling": {"no": "Trygg håndtering av midler", "en": "Safe handling of products"},
    "safety.fermentation_co2": {"no": "CO₂ fra gjæring", "en": "CO₂ from fermentation"},
    "sensory.tasting_sequence": {"no": "Smak med vilje", "en": "Tasting on purpose"},
    "sensory.tasting_habits": {"no": "Smakevaner", "en": "Tasting habits"},
    "sensory.observation_vs_interpretation": {"no": "Observasjon og tolkning", "en": "Observation and interpretation"},
    "sensory.fault_vs_character": {"no": "Feil eller karakter?", "en": "Fault or character?"},
    "sensory.evaluate_against_intent": {"no": "Vurder mot hensikten", "en": "Evaluate against intent"},
    "sensory.expectation_note": {"no": "Forventning og sammenligning", "en": "Expectation and comparison"},
    "sensory.diacetyl": {"no": "Smørpreg og diacetyl", "en": "Buttery character and diacetyl"},
    "sensory.dms_recognition": {"no": "Kokt mais og DMS", "en": "Cooked corn and DMS"},
    "sensory.oxidation_recognition": {"no": "Papp og oksidasjon", "en": "Cardboard and oxidation"},
    "sensory.sourness_intent_vs_spoilage": {"no": "Syrlig med vilje eller ikke", "en": "Sour on purpose or not"},
    "measurement.gravity": {"no": "Tetthet, OG og FG", "en": "Gravity, OG and FG"},
    "measurement.fermentation_complete": {"no": "Når gjæringen er ferdig", "en": "When fermentation is finished"},
    "measurement.temperature": {"no": "Temperatur og målested", "en": "Temperature and where it was measured"},
    "measurement.hydrometer_temperature": {"no": "Prøvetemperatur og hydrometer", "en": "Sample temperature and hydrometer"},
    "log.planned_vs_actual": {"no": "Planlagt og målt", "en": "Planned and measured"},
    "measurement.instrument_choice": {"no": "Hydrometer eller refraktometer", "en": "Hydrometer or refractometer"},
    "measurement.instrument_check": {"no": "Sjekk instrumentet", "en": "Checking your instrument"},
    "measurement.volume_stages": {"no": "Volum og trinn", "en": "Volume and stages"},
    "measurement.uncertainty": {"no": "Rå avlesning og korreksjon", "en": "Raw reading and correction"},
    "measurement.mash_temperature": {"no": "Mesketemperatur som måling", "en": "Mash temperature as a measurement"},
    "log.hypothesis_next_change": {"no": "Hypotese og neste endring", "en": "Hypothesis and next change"},
    "recipe.ibu_vs_perceived_bitterness": {"no": "IBU og opplevd bitterhet", "en": "IBU and perceived bitterness"},
    "recipe.balance": {"no": "Balanse ut fra hensikten", "en": "Balance against intent"},
    "recipe.style_context": {"no": "Stil som referanseramme", "en": "Style as a reference frame"},
    "recipe.formulation_workflow": {"no": "Lag oppskriften bevisst", "en": "Building a recipe deliberately"},
}

_DEMO_TILSTAND_NOKKEL = "_demo_bryggeskole_mastery_tilstand"

_LOGGER = logging.getLogger(__name__)

# Stage UI S2 (docs/development/v22_course_stage_ui_contract.md §5, §6.1,
# §11): the lesson renderer can show ONE course stage of a module -- only
# that stage's chunks and questions, from bryggeskole/data/
# course_stage_map.json via bryggeskole.course_stage (never from
# difficulty, chunk letters or lists here). If the stage map cannot be
# loaded or validated, today's single flow is used: stages are never
# guessed.
#
# Stage UI S3 (contract §3, §4, §7.3, §8): ONE authoritative stage, the
# learner's course-stage lens, lives in the selector's own key `bs_trinn`
# ("foundation"/"kompetent" -- never the legacy environment values). The
# lesson context `bs_aktiv_trinn` is not a second model: it is only the
# stage a card action opened the current module at -- the lens, except for
# the one contract case where a card reviews Foundation content under the
# Kompetent lens -- and it is cleared when the learner leaves the module.
# `bs_trinn_valgt_eksplisitt` records an explicit learner choice (the
# selector's on_change, or a card action that switches the lens). Without
# one, the lens follows the default (Foundation, or Kompetent once
# Foundation is worked through); with one, nothing changes it again in
# this session (Chief refinement, §7.3).
_TRINN_STATE_KEY = "bs_aktiv_trinn"
_TRINN_VALG_KEY = "bs_trinn"
_TRINN_EKSPLISITT_KEY = "bs_trinn_valgt_eksplisitt"
_TRINNKART_CACHE_KEY = "_bs_trinnkart"
_TRINN_VALG_NOKKEL = {
    "foundation": "bryggeskole.trinn.foundation",
    "kompetent": "bryggeskole.trinn.kompetent",
}
_TRINN_FORKLARING_NOKKEL = {
    "foundation": "bryggeskole.trinn.foundation_forklaring",
    "kompetent": "bryggeskole.trinn.kompetent_forklaring",
}
# Widget-key infix per stage. Foundation keeps today's keys exactly; every
# other stage gets its own infix so two stages of one module can never
# share widget state. Mastery ids (question/concept ids) are not affected.
_TRINN_NOKKEL_INFIKS = {"foundation": "", "kompetent": "_k"}
_TRINN_STI_NOKKEL = {
    "foundation": "bryggeskole.trinn.sti.foundation",
    "kompetent": "bryggeskole.trinn.sti.kompetent",
}


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
    st.session_state.setdefault(_TRINN_STATE_KEY, None)
    st.session_state.setdefault(_TRINN_EKSPLISITT_KEY, False)
    if _TRINN_VALG_KEY in st.session_state:
        # Streamlit drops a widget's state in any run where the widget is
        # not drawn (inside a module, on the environment screen). Writing
        # the value back before the selector exists keeps the lens through
        # those runs -- the documented way to carry widget state.
        st.session_state[_TRINN_VALG_KEY] = st.session_state[_TRINN_VALG_KEY]
    _ovd_tidligere_baseline()


def _hent_trinnkart():
    """The validated course stage map, or None if it cannot be loaded or
    validated (stage UI contract §6.1). Read once per Streamlit session. A
    failure is logged once and never repaired; the caller then falls back
    to the single flow (no selector, no stage lines, no stage lessons)."""
    if _TRINNKART_CACHE_KEY not in st.session_state:
        try:
            kart = _course_stage.load_stage_map()
        except (ValueError, OSError) as exc:
            _LOGGER.warning(
                "Bryggeskole: course stage map unavailable (%s); using the single-flow lesson.",
                type(exc).__name__,
            )
            kart = None
        st.session_state[_TRINNKART_CACHE_KEY] = kart
    return st.session_state[_TRINNKART_CACHE_KEY]


def _valgt_trinn():
    """The learner's stage lens (the `bs_trinn` value); Foundation until the
    overview has set it."""
    trinn = st.session_state.get(_TRINN_VALG_KEY)
    return trinn if trinn in _course_stage.STAGES else "foundation"


def _svarte_sporsmal():
    """Read-only view of the stored answered_questions (never written here)."""
    return _les_tilstand().get("answered_questions") or {}


def _standard_trinn(svarte):
    """The default lens without an explicit choice (contract §3, §7.3):
    Foundation, or Kompetent once every Foundation module is worked through."""
    foundation_gjennomgatt = _course_stage.stage_worked_through(_hent_trinnkart(), "foundation", svarte)
    return "kompetent" if foundation_gjennomgatt else "foundation"


def _marker_trinn_eksplisitt():
    """on_change of the selector: only a real learner change lands here --
    the value Streamlit materialises for an untouched widget never does."""
    st.session_state[_TRINN_EKSPLISITT_KEY] = True


def _aktivt_trinn():
    """The course stage of the lesson context, or None for today's single
    flow when no valid stage map exists. The lesson context is the stage the
    module was opened at; without one (or with an unknown value) it is the
    lens."""
    if _hent_trinnkart() is None:
        return None
    trinn = st.session_state.get(_TRINN_STATE_KEY)
    return trinn if trinn in _course_stage.STAGES else _valgt_trinn()


def _sesjon_nokkel(modul_id, trinn):
    """Lesson sessions are keyed by (module, stage). The single flow keeps
    today's key (the module id), so its sessions are unchanged."""
    return modul_id if trinn is None else f"{modul_id}@{trinn}"


def _widget_base(modul_id, trinn):
    """Widget-key base: the module id for the single flow and Foundation
    (today's keys), plus the stage infix otherwise (e.g. "mesking_k")."""
    return modul_id if trinn is None else modul_id + _TRINN_NOKKEL_INFIKS[trinn]


def _trinn_visning(modul_id, pilot, trinn):
    """The pilot as the lesson context sees it: unchanged for the single
    flow, otherwise a shallow copy holding only that stage's chunks and
    questions, in the pilot's own order. The existing lesson/question/
    summary renderers run on this view unchanged."""
    if trinn is None:
        return pilot
    items = _course_stage.items_for_stage(_hent_trinnkart(), modul_id, pilot, trinn)
    return dict(pilot, chunks=items["chunks"], questions=items["questions"])


def _bytt_trinn(trinn):
    """Switches only the stage of the lesson context; the open module stays
    open and the lens is unchanged (in-lesson «Repeter Foundation-delen»)."""
    st.session_state[_TRINN_STATE_KEY] = trinn


def _bytt_til_kompetent_eksplisitt():
    """A learner action that intentionally moves to Trinn 2 (in-lesson «Gå
    til Trinn 2-delen»): lens and lesson context become Kompetent, and it
    counts as an explicit choice (contract §4, §7.3)."""
    st.session_state[_TRINN_VALG_KEY] = "kompetent"
    st.session_state[_TRINN_EKSPLISITT_KEY] = True
    st.session_state[_TRINN_STATE_KEY] = "kompetent"


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


# Leaving a module (or the environment) clears only the lesson context. The
# lens `bs_trinn` and its explicit marker are kept, so an environment switch
# (Hjemmebrygger <-> Bryggeri) or a language switch never changes the stage
# (contract §12).
def _velg_miljo(miljo):
    st.session_state["bs_miljo"] = miljo
    st.session_state["bs_aktiv_modul"] = None
    st.session_state[_TRINN_STATE_KEY] = None


def _bytt_miljo():
    st.session_state["bs_miljo"] = None
    st.session_state["bs_aktiv_modul"] = None
    st.session_state[_TRINN_STATE_KEY] = None


def _apne_modul(modul_id, trinn=None):
    """Opens a module; card actions pass the stage to open it at (S3). The
    single flow (no valid stage map) passes None."""
    st.session_state["bs_aktiv_modul"] = modul_id
    st.session_state[_TRINN_STATE_KEY] = trinn
    trinn = _aktivt_trinn()
    if trinn is not None and not _course_stage.module_has_stage(_hent_trinnkart(), modul_id, trinn):
        # Nothing to begin at this stage (stage UI S2): no session is
        # created, so nothing can later read it as «Påbegynt».
        return
    _modul_sesjon(_sesjon_nokkel(modul_id, trinn))


def _apne_modul_i_kompetent(modul_id):
    """Card action «Se Trinn 2-innholdet» on a Kompetent-only module in the
    Foundation lens: switches the lens to Kompetent -- an explicit choice
    for the rest of the session -- and opens the module there (§4)."""
    st.session_state[_TRINN_VALG_KEY] = "kompetent"
    st.session_state[_TRINN_EKSPLISITT_KEY] = True
    _apne_modul(modul_id, "kompetent")


def _tilbake_til_oversikt():
    st.session_state["bs_aktiv_modul"] = None
    st.session_state[_TRINN_STATE_KEY] = None


def _bla_bolk(sesjon_id, delta, totalt):
    """Flytter leksjonsposisjonen én bolk fram/tilbake, klemt innenfor
    modulens egne bolker. `sesjon_id` is the (module, stage) session key
    (_sesjon_nokkel()); for the single flow it is the module id."""
    sesjon = _modul_sesjon(sesjon_id)
    sesjon["bolk_idx"] = max(0, min(totalt - 1, sesjon["bolk_idx"] + delta))


def _start_sporsmal_runde(sesjon_id):
    """Starter (eller re-starter, ved «Prøv igjen») spørsmålsrunden fra
    første spørsmål. Øker ALLTID sesjon["runde"], slik at hvert
    spørsmål-widget-key blir garantert unikt for denne runden -- uten
    dette ville et gjenbrukt key ha fått Streamlit til å vise en gammel,
    lagret radioverdi fra en tidligere runde, og alternativ-rekkefølgen
    (frosset per runde, se _hent_alternativ_rekkefolge()) ville ikke blitt
    trukket på nytt. `apply_answer()`s egen `first_attempt`-logikk leser
    fortsatt den PERSISTERTE mastery-tilstanden uendret -- «Prøv igjen»
    resetter aldri selve mastery-tilstanden, kun denne UI-runden."""
    sesjon = _modul_sesjon(sesjon_id)
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


def _sjekk_svar(modul_id, sporsmal, sprak, widget_key, runde, sesjon_id=None):
    """`sesjon_id` is the (module, stage) session key; None means the
    single flow (the module id). Mastery is keyed by the question's own
    ids exactly as before -- the stage never enters apply_answer()."""
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
    sesjon = _modul_sesjon(sesjon_id or modul_id)
    sesjon["siste_feedback"] = {
        "question_id": resultat["question_id"],
        "runde": runde,
        "correct": resultat["correct"],
        "valgt_id": valgt_id,
        "feedback": resultat["feedback"],
    }


def _neste_sporsmal(sesjon_id, totalt):
    sesjon = _modul_sesjon(sesjon_id)
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
    kan aldri lekke ut av Bryggeskole-fanen.

    Issue #401: økt fra 1.08rem -- fortsatt for lite for svakere syn per
    eier-QA -- og utvidet til også å dekke selve svaralternativ-teksten
    (radio-labelene), som tidligere ikke var stylet i det hele tatt (kun
    spørsmålsteksten i sin egen container var det). `.st-key-bs_svaralternativ`
    er wrapperen rundt selve st.radio()-kallet i _render_sporsmal().

    Issue #401 (oppfølging): dette dekket kun FØR-svar-tilstanden. Etter
    «Sjekk svar» settes radioen `disabled=True` (linje ~729), og
    Streamlits/BaseWebs egen disabled-styling toner svaralternativ-teksten
    ned til `color: rgba(<tekstfarge>, 0.4)` -- verifisert i en ekte
    kjørende instans (Playwright, lys og mørk fargemodus) at attributtet
    `data-disabled="true"` på `stRadioOption`-labelen (satt av React Aria
    når `st.radio(..., disabled=True)`) er det stabile signalet å style
    mot -- ikke Streamlits auto-genererte `st-emotion-cache-*`-hash-
    klasser, som ikke er ment å refereres fra egen CSS og kan endre seg
    mellom versjoner. 0.4 gir på mørk bakgrunn (rgb(14,17,23)) en
    effektiv tekstfarge på ca. rgb(108,110,114) -- under WCAG AA-kontrast
    og i praksis nesten uleselig, per eier-QA. Låst/deaktivert interaksjon
    skal IKKE bety uleselig tekst: selve svarstatusen (riktig/feil/valgt
    alternativ) vises uansett eksplisitt som egen tekst (se
    _render_sporsmal, "Answer-state UX issue #338"), så radioens egen
    disabled-fading har ingen semantisk jobb å gjøre utover at den er
    låst -- kun kontrasten var for aggressiv.

    Chief review (theme-safety-oppfølging): en tidligere versjon av denne
    fiksen brukte hardkodede lys/mørk-RGB-verdier valgt via
    `@media (prefers-color-scheme: dark)`. Det er FEIL signal å style
    mot her -- Streamlit sitt eget tema kan settes eksplisitt (via
    `.streamlit/config.toml` eller brukerens egen temavelger i "Settings"
    -menyen) UAVHENGIG av OS/browser sin `prefers-color-scheme`, så en
    bruker med f.eks. lyst OS-tema men mørkt Streamlit-tema (eller omvendt)
    ville fått CSS-en til å velge feil gren og dermed lav kontrast igjen
    -- nøyaktig samme bug klassen som denne fiksen skulle løse (bekreftet
    med en ekte instans startet med `--theme.base dark` men lastet i en
    nettleser satt til `colorScheme: light`).

    En egen DOM-sporing (Playwright, `getComputedStyle` langs hele
    forelder-kjeden til teksten) viste PRESIST hvor `color: rgba(..., 0.4)`
    faktisk settes: IKKE på selve `<p>`-en (som ikke har noen egen
    color-regel -- den arver bare fra sin nærmeste forelder), men på DEN
    DIREKTE BARNE-DIVEN til selve `stRadioOption`-labelen (den ene diven
    som pakker inn både indikator-prikken og tekst-markdown-containeren).
    `label`-elementet selv har appens fulle, korrekte temafarge. Et første
    forsøk med `color: inherit` direkte på `p` var derfor virkningsløst
    (arver kun fra sin allerede-dempede nærmeste forelder, ikke tvers
    gjennom flere nivåer) -- selektoren treffer i stedet den DIREKTE
    barne-diven (`> div`) med `color: inherit`, som lar HELE det dempede
    delteet arve labelens fulle temafarge på nytt, `<p>` inkludert, uten
    å trenge noen egen fargeverdi. Verifisert med Playwright at dette gir
    FULL kontrast i lys, mørk OG mismatch-scenarioet over, identisk med
    FØR-svar-fargen. Fjerner samtidig hele
    `@media (prefers-color-scheme: dark)`-grenen og alle hardkodede
    rgba(...)-verdier, som ikke lenger trengs.

    Issue #401 (offline-oppfølging): regelen over treffer KUN radio-DOM-en
    til nyere Streamlit (React Aria: `stRadioOption` + `data-disabled`).
    Eldre Streamlit (verifisert på 1.57) rendrer BaseWebs
    `label[data-baseweb="radio"]` uten testid og uten `data-disabled` --
    der traff ingenting, og ekte Chromium viste fortsatt
    `rgba(49, 51, 63, 0.4)` (~2.2:1) mens kildetestene var grønne.
    Signalet begge DOM-ene deler er det native `<input type="radio"
    disabled>` inni labelen, så en andre regel bruker
    `label:has(input:disabled) > div` -- samme `color: inherit`, samme
    skop. Den dempede diven er labelens direkte barn i begge versjoner.
    To separate regler (ikke én selektorliste) så en nettleser uten
    `:has()` fortsatt beholder den første. Ekte nettleserbevis:
    tests/playwright_streamlit/quiz-answer-contrast.spec.js.

    Issue #482 (Streamlit 1.65): 1.65 legger inn en NY wrapper-div med
    `data-disabled="true"` mellom `stRadioGroup` og `stRadioOption`-
    labelene, og den dempede fargen sitter nå på DEN. Labelen og `> div`-
    regelen over arver dermed den dempede fargen (målt 2.23:1). En regel
    til, `color: inherit` på hvert `[data-disabled="true"]`-element under
    `stRadioGroup`, lar wrapperen arve radiogruppens fulle temafarge
    (radiogruppen selv er ikke dempet) -- fortsatt ingen egen fargeverdi.
    Verifisert i Chromium og Firefox, lyst og mørkt, på 1.65.0 og 1.61.1
    (tests/playwright_streamlit/quiz-answer-contrast.spec.js).

    Issue #394: skoleoversiktens modul-grid (`_render_skoleoversikt()`)
    bruker `st.columns(len(stadier))` -- alltid seks like brede kolonner,
    uansett skjermbredde. En DOM-sporing (Playwright, `getComputedStyle`)
    viste at Streamlit selv ALLEREDE setter `flex-wrap: wrap` på
    `[data-testid="stHorizontalBlock"]`-raden, men hver
    `[data-testid="stColumn"]` sin `flex-basis` er en PROSENT av
    foreldrebredden (`calc(16.6667% - 16px)` for seks kolonner) -- seks
    kolonner à 16.6667% summerer alltid til 100% uansett hvor smal
    skjermen er, så wrap utløses aldri i praksis; kolonnene bare krymper
    (`flex-shrink: 1`) til de blir for smale til å vise modulnavnet uten
    at nettleserens `overflow-wrap`-fallback bryter midt i ord (de
    observerte "Forbere / delse / metode"/"Gjæring (bøtte/ FermZill
    a)"-tilfellene). Fiksen bytter til en PIKSELBASERT minstebredde
    (`flex-basis`/`min-width: 220px`) i stedet for prosent, skopet til
    den nye `.st-key-bs_skoleoversikt_grid`-containeren (wrapperen rundt
    selve `st.columns()`-kallet, se der) -- da blir seks 220px-kort for
    brede til å dele en rad når containeren er smalere enn ca. 6*220px+
    mellomrom, og de resterende kortene wrapper naturlig til påfølgende
    rader helt ned til én kolonne på svært smale skjermer, uten en eneste
    `@media`-brytningspunkt å vedlikeholde. Ingen global
    `.stColumn`/`.stHorizontalBlock`-endring -- selektoren er skopet
    nøyaktig som resten av denne funksjonen.

    Issue #398 (responsiv oppfølging, offline eier-QA): navigasjonsraden
    (`_KNAPP_GRUPPE_KOLONNER` = (1, 1, 6)) ga hver knappekolonne
    Streamlits egen `width`/`flex: 1 1 calc(12.5% - 1rem)` -- en ÅTTENDEDEL
    av raden. Målt i ekte nettleser (Playwright, app.py med sidebar åpen):
    ved 900px er raden 440px, kolonnen 44px, og knappene (min-width 0,
    white-space normal) brytes til «← Forrige» 4 linjer, «Neste →» 3 og
    «▶️ Start spørsmål» 7 linjer, bokstav for bokstav; ved 1280px 2
    linjer. Ikke knappen, men kolonnebredden var feilen. Regelen under
    lar knappekolonnene i `.st-key-bs_nav_actions` følge sin egen knapp
    (`flex: 0 1 auto` + `width: auto` -- BEGGE trengs, siden
    `flex-basis: auto` ellers faller tilbake til Streamlits prosent-
    `width`), uten noen pikselverdi. Streamlits mobilregel
    (`@media (max-width: 640px)` → `min-width: calc(100% - 1.5rem)`) røres
    ikke, så mobilens stablede oppsett er uendret. Dekket av
    tests/playwright_streamlit/nav-buttons-responsive.spec.js."""
    st.markdown(
        """
        <style>
        .st-key-bs_leksjon_tekst p, .st-key-bs_sporsmal_tekst p {
            font-size: 1.15rem;
            line-height: 1.7;
        }
        .st-key-bs_sporsmal_tekst p {
            font-weight: 600;
        }
        .st-key-bs_svaralternativ label p {
            font-size: 1.1rem;
            line-height: 1.6;
        }
        .st-key-bs_svaralternativ [data-testid="stRadioOption"][data-disabled="true"] > div {
            color: inherit !important;
        }
        .st-key-bs_svaralternativ [role="radiogroup"] label:has(input:disabled) > div {
            color: inherit !important;
        }
        .st-key-bs_svaralternativ [data-testid="stRadioGroup"] [data-disabled="true"] {
            color: inherit !important;
        }
        .st-key-bs_skoleoversikt_grid [data-testid="stColumn"] {
            flex: 1 1 220px !important;
            min-width: 220px !important;
        }
        .st-key-bs_nav_actions [data-testid="stColumn"] {
            flex: 0 1 auto !important;
            width: auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _modul_status(modul_id, sesjon_id=None):
    """Returnerer (ovd_tidligere, sesjon) for statusmerkene på et
    modul-kort:
    - ovd_tidligere: praksis som fantes FØR denne økten -- lest fra
      øktens baseline (_ovd_tidligere_baseline()), aldri fra den levende
      tilstanden, slik at øktens egne svar ikke kan skape merket.
    - sesjon: None hvis aldri åpnet denne økten; ellers selve
      sesjondict-en, som avgjør "Påbegynt" vs. "Gjennomført denne økten".
      Stage UI S3: sesjon_id er (modul, trinn)-økten kortet viser;
      standard er enkeltflytens nøkkel (modul-id-en)."""
    return _ovd_tidligere_baseline().get(modul_id, False), _les_modul_sesjon(sesjon_id or modul_id)


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


def _anbefalt_modul_i_trinn(trinn, svarte):
    """Stage UI S3 (contract §8): the recommendation for the selected lens --
    the first module in canonical order that has content at that stage and
    is neither worked through there (answered_questions, §7.2) nor completed
    at that stage in this session. Never a lock; None when nothing is left."""
    kart = _hent_trinnkart()
    for modul_id in _MODUL_REKKEFOLGE:
        if not _course_stage.module_has_stage(kart, modul_id, trinn):
            continue
        status = _course_stage.module_stage_status(kart, modul_id, trinn, svarte)
        if status == _course_stage.STATUS_WORKED_THROUGH:
            continue
        sesjon = _les_modul_sesjon(_sesjon_nokkel(modul_id, trinn))
        if sesjon and sesjon["fullfort_denne_okten"]:
            continue
        return modul_id
    return None


def _render_trinnvalg(svarte):
    """The compact stage lens above the grid (contract §3): one horizontal
    radio, key `bs_trinn`. Without an explicit choice the default is written
    to the key before the widget exists (Foundation, or Kompetent once
    Foundation is worked through); after an explicit choice the value is
    never overridden here (only filled in if it were missing). Returns the
    selected stage."""
    if not st.session_state.get(_TRINN_EKSPLISITT_KEY):
        st.session_state[_TRINN_VALG_KEY] = _standard_trinn(svarte)
    elif st.session_state.get(_TRINN_VALG_KEY) not in _course_stage.STAGES:
        st.session_state[_TRINN_VALG_KEY] = "foundation"
    # Labels resolved now, in the current language (never a raw stage id).
    etiketter = {verdi: t(_TRINN_VALG_NOKKEL[verdi]) for verdi in _course_stage.STAGES}
    trinn = st.radio(
        t("bryggeskole.trinn.velg"),
        options=list(_course_stage.STAGES),
        format_func=etiketter.__getitem__,
        key=_TRINN_VALG_KEY,
        horizontal=True,
        help=t("bryggeskole.trinn.velg_hjelp"),
        on_change=_marker_trinn_eksplisitt,
    )
    st.caption(t(_TRINN_FORKLARING_NOKKEL[trinn]))
    return trinn


def _render_trinnveiledning(trinn, svarte):
    """Quiet guidance only -- no lock, no completion claim (contract §7.3,
    §7.4, §8). Once Foundation is worked through: «Klar for Trinn 2?» while
    the learner still looks at Foundation; when the lens moved to Kompetent
    by default (no explicit choice), a line saying Trinn 2 is now shown as
    the recommended next step (Chief S3 polish); after an explicit
    Kompetent choice, nothing. In the Kompetent lens with Foundation gaps,
    one tip line."""
    foundation_gjennomgatt = _course_stage.stage_worked_through(_hent_trinnkart(), "foundation", svarte)
    if foundation_gjennomgatt:
        if trinn == "foundation":
            st.success(t("bryggeskole.trinn.klar_for_trinn2"))
        elif not st.session_state.get(_TRINN_EKSPLISITT_KEY):
            st.success(t("bryggeskole.trinn.trinn2_anbefalt"))
    elif trinn == "kompetent":
        st.caption(t("bryggeskole.trinn.tips_foundation"))


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


def _render_trinnkort(modul_id, trinn):
    """The body of one canonical card under the stage lens (contract §4):
    one stage line, today's session badges for that (module, stage), and
    one button with the unchanged key `bs_apne_modul_{id}_btn`. A module
    without content at the selected stage is never disabled or greyed: it
    gets its own line and an action that opens the stage it does have."""
    knapp_key = f"bs_apne_modul_{modul_id}_btn"
    if not _course_stage.module_has_stage(_hent_trinnkart(), modul_id, trinn):
        if trinn == "kompetent":
            # Foundation-only module: review its Foundation content. The
            # lens stays Kompetent; only that lesson opens at Foundation.
            st.caption(t("bryggeskole.trinn.kort.bygger_pa_foundation"))
            st.button(
                t("bryggeskole.trinn.kort.repeter"), key=knapp_key,
                width="stretch", on_click=_apne_modul, args=(modul_id, "foundation"),
            )
        else:
            st.caption(t("bryggeskole.trinn.kort.horer_til_trinn2"))
            st.button(
                t("bryggeskole.trinn.kort.se_trinn2"), key=knapp_key,
                width="stretch", on_click=_apne_modul_i_kompetent, args=(modul_id,),
            )
        return

    st.caption(t("bryggeskole.trinn.kort.innhold"))
    ovd_tidligere, sesjon = _modul_status(modul_id, _sesjon_nokkel(modul_id, trinn))
    if ovd_tidligere:
        st.caption(t("bryggeskole.status.ovd_tidligere"))
    if sesjon and sesjon["fullfort_denne_okten"]:
        st.caption(t("bryggeskole.status.fullfort_okt"))
        knapp_tekst = t("bryggeskole.modul.se_resultat")
    elif sesjon:
        st.caption(t("bryggeskole.status.pabegynt"))
        knapp_tekst = t("bryggeskole.modul.fortsett")
    else:
        knapp_tekst = t("bryggeskole.modul.start")
    st.button(
        knapp_tekst, key=knapp_key,
        width="stretch", on_click=_apne_modul, args=(modul_id, trinn),
    )


def _render_skoleoversikt(miljo, sprak):
    st.subheader(t(f"bryggeskole.miljo.{miljo}"))

    # Stage UI S3: the stage lens over the same grid. With no valid stage
    # map, none of it is drawn and the overview is exactly today's.
    trinn = None
    if _hent_trinnkart() is not None:
        svarte = _svarte_sporsmal()
        trinn = _render_trinnvalg(svarte)
        _render_trinnveiledning(trinn, svarte)
        anbefalt = _anbefalt_modul_i_trinn(trinn, svarte)
    else:
        anbefalt = _anbefalt_modul()
    if anbefalt is not None:
        st.info(t("bryggeskole.anbefalt_neste", modul=t(_MODULER[anbefalt]["tittel_nokkel"])))

    stadier = _PROSESS_STADIER[miljo]
    # Issue #394: wrappes i en nøkkelbasert container KUN for at
    # _injiser_bryggeskole_css() skal kunne skope den responsive
    # grid-fiksen (se der) til nettopp dette gridet -- ingen egen
    # betydning for selve layout-logikken under.
    with st.container(key="bs_skoleoversikt_grid"):
        cols = st.columns(len(stadier))
        for i, (col, stadium) in enumerate(zip(cols, stadier)):
            modul_id = _STADIUM_TIL_MODUL.get(i)
            with col, st.container(border=True):
                st.markdown(f"**{stadium[sprak]}**")
                if modul_id is None:
                    st.caption(t("bryggeskole.prosess.kommer_badge"))
                    continue

                if trinn is not None:
                    _render_trinnkort(modul_id, trinn)
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


def _render_repeter_foundation_knapp(base):
    st.button(
        t("bryggeskole.trinn.repeter_foundation"), key=f"bs_trinn_repeter_{base}_btn",
        width="content", on_click=_bytt_trinn, args=("foundation",),
    )


def _render_leksjon_kun_sporsmal(sesjon_id, base):
    """Stage UI S2 (contract §5): a stage with questions but no chunks of
    its own (e.g. Kompetent in Råvarer and Kjøling/overføring). No chunk is
    invented: one neutral intro, a way back to the Foundation lesson, and
    the questions."""
    st.info(t("bryggeskole.trinn.kun_sporsmal"))
    with st.container(key="bs_nav_actions"):
        col1, col2, _spacer = st.columns(_KNAPP_GRUPPE_KOLONNER)
        with col1:
            _render_repeter_foundation_knapp(base)
        with col2:
            st.button(
                t("bryggeskole.leksjon.start_sporsmal"), key=f"bs_start_sporsmal_{base}_btn",
                width="content", type="primary",
                on_click=_start_sporsmal_runde, args=(sesjon_id,),
            )


def _render_leksjon(modul_id, sesjon, pilot, sprak, sesjon_id=None, base=None, trinn=None):
    """ÉN læringsbolk om gangen (issue #338 / Chief review PR #340).

    Tidligere ble alle pilotens chunks rendret i én lang skjerm og
    læreren hoppet rett til spørsmålene. Nå er leksjonen en egen liten
    reise: bolk 1 -> Neste -> bolk 2 -> ... -> Start spørsmål, med
    posisjonen lagret per modul, slik at en tur innom skoleoversikten
    gjenopptar nøyaktig samme bolk.

    Stage UI S2: `pilot` is the lesson context's view (_trinn_visning()),
    so a stage shows only its own chunks; `sesjon_id`/`base` are the
    (module, stage) session key and widget-key base (both the module id for
    the single flow)."""
    sesjon_id = sesjon_id or modul_id
    base = base or modul_id
    st.write("---")
    chunks = pilot["chunks"]
    totalt = len(chunks)
    if totalt == 0:
        _render_leksjon_kun_sporsmal(sesjon_id, base)
        return
    # Defensivt klem: innholdet kan i prinsippet ha blitt kortere siden
    # posisjonen ble lagret (kun mulig ved innholdsendring i dev).
    idx = max(0, min(sesjon["bolk_idx"], totalt - 1))
    sesjon["bolk_idx"] = idx

    st.caption(t("bryggeskole.leksjon.bolk_teller", n=idx + 1, totalt=totalt))
    with st.container(key="bs_leksjon_tekst"):
        st.markdown(_MODULER[modul_id]["pilot"].render_chunk(chunks[idx], sprak)["text"])
    if chunks[idx].get("basis") == "methodology":
        # Issue #472 (D1b): liten, sekundær merking -- metode, ikke en
        # faktapåstand. Andre piloter har ingen "basis" og påvirkes ikke.
        st.caption(t("bryggeskole.metode_etikett"))

    if modul_id == _MODUL_RAAVARER:
        # Råvarer-modulens ene Malt-visual (issue #460): kvalitativ
        # basismalt->spesialmalt-stripe, kun i bolken som dekker
        # FACT-MALT-0002 (basis vs. spesialmalt) -- se
        # bryggeskole/malt_roles_strip.py sin docstring.
        if "FACT-MALT-0002" in chunks[idx]["source_claims"]:
            st.markdown(render_malt_roles_strip_svg(sprak), unsafe_allow_html=True)
    elif modul_id == _MODUL_KOKING:
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

    # Issue #398: navigasjonsknappene brukte tidligere width="stretch",
    # som strekker hver knapp til å fylle HELE sin halv-brede kolonne --
    # på normal desktop ble det enorme, dominerende knapper. width="content"
    # (Streamlit sin egen default) gir kompakte, tekst-tilpassede knapper i
    # stedet, uten å endre knapperekkefølge, disabled-semantikk eller
    # klikkbarhet -- se ui/bryggeskole_panel.py sin bruk samme sted i
    # _render_sporsmal() og _render_oppsummering() for de to andre
    # forekomstene av dette samme mønsteret.
    #
    # Owner-QA correction (issue #398 follow-up): width="content" alone
    # fixed the SIZE, but col1/col2 = st.columns(2) still gives each
    # button its own half-width column, so the two compact buttons ended
    # up far apart with a big empty gap between them. _KNAPP_GRUPPE_KOLONNER
    # (1, 1, N) puts both buttons in two narrow, ADJACENT columns
    # followed by one wide empty spacer column that absorbs the rest of
    # the row -- a plain Streamlit-layout fix (no CSS) for "grouped
    # side-by-side buttons, not spread across the whole width". Below the
    # narrow/mobile breakpoint Streamlit stacks all three columns
    # full-width regardless of ratio, so this is a no-op there (the third
    # column just renders as empty, harmless whitespace). Above it, the
    # scoped `.st-key-bs_nav_actions` CSS sizes each button column to its
    # button, so a narrow row (sidebar open) can no longer squeeze the
    # labels into letter-stacked columns -- see _injiser_bryggeskole_css().
    with st.container(key="bs_nav_actions"):
        col1, col2, _spacer = st.columns(_KNAPP_GRUPPE_KOLONNER)
        with col1:
            st.button(
                t("bryggeskole.leksjon.forrige"), key=f"bs_bolk_forrige_{base}_btn",
                width="content", disabled=idx == 0,
                on_click=_bla_bolk, args=(sesjon_id, -1, totalt),
            )
        with col2:
            if idx + 1 < totalt:
                st.button(
                    t("bryggeskole.leksjon.neste"), key=f"bs_bolk_neste_{base}_btn",
                    width="content", type="primary",
                    on_click=_bla_bolk, args=(sesjon_id, 1, totalt),
                )
            else:
                # «Start spørsmål» finnes KUN på siste bolk -- det er det som
                # gjør leksjonen til en sekvens og ikke en scroll-skjerm.
                st.button(
                    t("bryggeskole.leksjon.start_sporsmal"), key=f"bs_start_sporsmal_{base}_btn",
                    width="content", type="primary",
                    on_click=_start_sporsmal_runde, args=(sesjon_id,),
                )
    if trinn is not None and trinn != "foundation" and _course_stage.module_has_stage(
        _hent_trinnkart(), modul_id, "foundation"
    ):
        # Stage UI S2 (contract §5): a quiet way back to this module's
        # Foundation lesson from a later stage. Never forced.
        _render_repeter_foundation_knapp(base)


def _render_sporsmal(modul_id, sesjon, pilot, sprak, sesjon_id=None, base=None):
    """Stage UI S2: `pilot` is the lesson context's view, so a stage asks
    only its own questions; `sesjon_id`/`base` as in _render_leksjon()."""
    sesjon_id = sesjon_id or modul_id
    base = base or modul_id
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
    # Stage UI S2: the base also carries the stage infix (e.g. "mesking_k"),
    # for the same reason between two stages of one module.
    widget_key = f"bs_valg_{base}_r{runde}_q{idx}"

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
    if sporsmal.get("basis") == "methodology":
        st.caption(t("bryggeskole.metode_etikett"))

    with st.container(key="bs_svaralternativ"):
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
        with st.container(key="bs_nav_actions"):
            st.button(
                t("bryggeskole.sporsmal.svar_knapp"), key=f"bs_svar_btn_{base}_r{runde}_q{idx}",
                width="content", on_click=_sjekk_svar,
                args=(modul_id, sporsmal, sprak, widget_key, runde, sesjon_id),
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
        with st.container(key="bs_nav_actions"):
            st.button(
                t("bryggeskole.sporsmal.fortsett"), key=f"bs_fortsett_btn_{base}_r{runde}_q{idx}",
                width="content", on_click=_neste_sporsmal, args=(sesjon_id, totalt),
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


def _render_oppsummering(modul_id, pilot, sprak, sesjon_id=None, base=None):
    """Stage UI S2: with a stage view as `pilot`, the summary lists only the
    concepts of that stage's questions. «Over tid» is still the one shared
    concept mastery -- no stage-specific mastery exists."""
    sesjon_id = sesjon_id or modul_id
    base = base or modul_id
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

    # Issue #398 follow-up: same compact side-by-side grouping as the
    # lesson Forrige/Neste row -- see that call site's comment.
    with st.container(key="bs_nav_actions"):
        col1, col2, _spacer = st.columns(_KNAPP_GRUPPE_KOLONNER)
        with col1:
            st.button(
                t("bryggeskole.oppsummering.prov_igjen"), key=f"bs_prov_igjen_{base}_btn",
                width="content", on_click=_start_sporsmal_runde, args=(sesjon_id,),
            )
        with col2:
            st.button(
                t("bryggeskole.tilbake_til_oversikt"), key=f"bs_oppsummering_tilbake_{base}_btn",
                width="content", on_click=_tilbake_til_oversikt,
            )


def _render_ingen_trinndel(trinn, base):
    """Stage UI S2 (contract §4, §6.2): the module has no content at the
    requested stage. Nothing is invented. Foundation-only module asked for
    Kompetent -> Foundation is the material; Kompetent-only module asked for
    Foundation -> it belongs to Trinn 2. S3 cards never open a module at a
    stage it lacks; this state stays as the safe answer if it is reached."""
    if trinn == "foundation":
        st.info(t("bryggeskole.trinn.horer_til_kompetent"))
        st.button(
            t("bryggeskole.trinn.til_kompetent"), key=f"bs_trinn_til_kompetent_{base}_btn",
            width="content", on_click=_bytt_til_kompetent_eksplisitt,
        )
    else:
        st.info(t("bryggeskole.trinn.ingen_kompetent_del"))
        _render_repeter_foundation_knapp(base)


def _render_modul(modul_id, miljo, sprak):
    modul_info = _MODULER[modul_id]
    # Stage UI S2/S3: the lesson context is (module, stage). trinn is None
    # only for today's single flow, the fallback when the stage map is
    # unavailable.
    trinn = _aktivt_trinn()
    sesjon_id = _sesjon_nokkel(modul_id, trinn)
    base = _widget_base(modul_id, trinn)

    # Two separate axes in the breadcrumb: the legacy environment and, when
    # a stage is active, the course stage (contract §5, §12).
    sti = [t("tabs.bryggeskole"), t(f"bryggeskole.miljo.{miljo}")]
    if trinn is not None:
        sti.append(t(_TRINN_STI_NOKKEL[trinn]))
    sti.append(t(modul_info["tittel_nokkel"]))
    st.caption(" ▸ ".join(sti))
    st.button(t("bryggeskole.tilbake_til_oversikt"), key=f"bs_tilbake_{base}_btn", on_click=_tilbake_til_oversikt)
    st.subheader(f"{modul_info['ikon']} {t(modul_info['tittel_nokkel'])}")

    visning = None
    if trinn is not None:
        try:
            pilot = modul_info["pilot"].read_pilot_file()
        except _PILOT_CONTENT_ERRORS:
            st.error(t("bryggeskole.feil.innhold_ugyldig"))
            return
        visning = _trinn_visning(modul_id, pilot, trinn)
        if not visning["chunks"] and not visning["questions"]:
            _render_ingen_trinndel(trinn, base)
            return

    sesjon = _modul_sesjon(sesjon_id)
    fase = sesjon["fase"]
    if fase == "leksjon":
        st.caption(t("bryggeskole.steg.leksjon"))
    elif fase == "oppsummering":
        st.caption(t("bryggeskole.steg.oppsummering"))

    if visning is None:
        try:
            visning = modul_info["pilot"].read_pilot_file()
        except _PILOT_CONTENT_ERRORS:
            st.error(t("bryggeskole.feil.innhold_ugyldig"))
            return

    if fase == "leksjon":
        _render_leksjon(modul_id, sesjon, visning, sprak, sesjon_id, base, trinn)
    elif fase == "sporsmal":
        _render_sporsmal(modul_id, sesjon, visning, sprak, sesjon_id, base)
    else:
        _render_oppsummering(modul_id, visning, sprak, sesjon_id, base)


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
