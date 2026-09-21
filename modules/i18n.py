"""Sentralt, App-eid NO/EN i18n-lag for brukervendt tekst i Streamlit-appen
(app.py, ui/**).

Dette er KUN et presentasjonslag for statisk UI-tekst — det er bevisst
holdt fullstendig adskilt fra domenedata: oppskrift-/malt-/humle-/
gjær-identiteter, session_state-nøkler for beregninger, og alt som
lagres på disk (recipes/, .kbhrecipe osv.) forblir språknøytrale
(norske domenenavn, jf. .claude/rules/desktop.md) uansett hvilket
visningsspråk brukeren har valgt. Denne modulen importerer aldri
Streamlit — selve språkvalget (st.session_state) eies av ui/i18n.py,
ikke her — slik at `t()` kan testes og brukes helt uten en
Streamlit-kontekst.

Konvensjoner (se docs/development/PROJECT_MAP.md for videre kontekst
ved behov):

- Nøkler er punktum-separerte, seksjon-prefikset strenger, f.eks.
  "sidebar.tittel" eller "tabs.oppskrift" — samme mønster som den
  eksisterende web-varianten (web/js/i18n.js sin TEKSTER/`t()`), for
  gjenkjennbarhet på tvers av App og Web, UTEN at noe innhold faktisk
  deles mellom dem (se web.md: web/js/i18n.js er en helt separat,
  statisk fil — denne modulen dupliserer bevisst mønsteret, ikke data).
- Interpolasjon: `{navn}`-plassholdere i teksten, fylt fra
  nøkkelord-argumenter til `t()`, f.eks. `t("sidebar.lastet_ok",
  navn="Kvernhaug Spesial")`. Ingen pluralregler, ingen betinget
  templating — nøyaktig samme bevisste avgrensning som web-varianten.
  En plassholder uten tilsvarende argument la stå urørt (aldri en
  KeyError) — trygt fordi det uansett er tydelig synlig i UI-et.
- Fallback: en nøkkel som mangler i det aktive språket, men finnes i
  SPRAK_DEFAULT ("no"), faller tilbake til norsk teksten. En nøkkel som
  mangler i BEGGE (skrivefeil, eller en nøkkel som aldri ble lagt til)
  returneres ALDRI som tom streng eller en annen nøkkels tekst — det
  ville vært en stille semantikk-endring. Den returneres i stedet
  synlig markert (se _MANGLENDE_NOKKEL_MAL under) slik at en
  glemt/feilstavet nøkkel er umulig å overse i UI-et, samtidig som
  appen aldri krasjer bare fordi en tekststreng mangler.
"""

SPRAK_LISTE = ("no", "en")
SPRAK_DEFAULT = "no"

# Synlig, umiskjennelig markør for en manglende/ugyldig nøkkel — bevisst
# ikke bare nøkkelen selv (kan forveksles med ekte, kort UI-tekst) og
# bevisst ikke en tom streng (ville vært usynlig og se ut som en bevisst
# tom label). "??"-innrammingen er ikke brukt noe annet sted i appens
# UI-tekst.
_MANGLENDE_NOKKEL_MAL = "??{nokkel}??"

TEKSTER = {
    "no": {
        "tabs.oppskrift": "🍺 Oppskrift",
        "tabs.innkjop": "🛒 Innkjøp & Lager",
        "tabs.bryggdag": "🧪 Bryggdag",
        "tabs.verktoy": "🔧 Verktøy",
        "tabs.bryggeskole": "🎓 Bryggeskole",
        "bryggeskole.heading": "🎓 Kvernhaug Bryggeskole",
        "bryggeskole.tagline": "Én Bryggeskole, to miljøer — samme verifiserte kunnskap, samme fremgang.",
        "bryggeskole.bytt_miljo": "🔁 Velg annet miljø",
        "bryggeskole.velg_miljo_heading": "Velg ditt miljø",
        "bryggeskole.miljo.hjemmebrygger": "🏠 Hjemmebrygger",
        "bryggeskole.miljo.hjemmebrygger_beskrivelse": "Kjele/BIAB, bøtte/FermZilla, keg eller flaske.",
        "bryggeskole.miljo.bryggeri": "🏭 Bryggeri",
        "bryggeskole.miljo.bryggeri_beskrivelse": "Mølle, mesk/lauter, kokekar, konisk gjæringstank.",
        "bryggeskole.miljo.velg_knapp": "Velg dette miljøet",
        "bryggeskole.prosess.aktiv_badge": "✅ Leksjon tilgjengelig",
        "bryggeskole.prosess.kommer_badge": "🔒 Kommer senere",
        "bryggeskole.anbefalt_neste": "💡 Anbefalt neste: {modul}",
        "bryggeskole.modul.mesking.tittel": "Mesking",
        "bryggeskole.modul.gjaring.tittel": "Gjæring",
        "bryggeskole.modul.start": "▶️ Start",
        "bryggeskole.modul.fortsett": "↪️ Fortsett",
        "bryggeskole.modul.se_resultat": "📊 Se resultat",
        "bryggeskole.status.ovd_tidligere": "📚 Øvd på tidligere",
        "bryggeskole.status.pabegynt": "🕒 Påbegynt",
        "bryggeskole.status.fullfort_okt": "✅ Gjennomført denne økten",
        "bryggeskole.tilbake_til_oversikt": "🔙 Tilbake til skoleoversikten",
        "bryggeskole.steg.leksjon": "Steg 1 av 3 — Leksjon",
        "bryggeskole.steg.sporsmal": "Steg 2 av 3 — Spørsmål {n} av {totalt}",
        "bryggeskole.steg.oppsummering": "Steg 3 av 3 — Oppsummering",
        "bryggeskole.leksjon.bolk_teller": "Læringsbolk {n} av {totalt}",
        "bryggeskole.leksjon.forrige": "← Forrige",
        "bryggeskole.leksjon.neste": "Neste →",
        "bryggeskole.leksjon.start_sporsmal": "▶️ Start spørsmål",
        "bryggeskole.sporsmal.velg_svar": "Velg svar",
        "bryggeskole.sporsmal.svar_knapp": "✅ Sjekk svar",
        "bryggeskole.sporsmal.fortsett": "➡️ Fortsett",
        "bryggeskole.svar.ditt_svar": "Ditt svar",
        "bryggeskole.svar.riktig_svar": "Riktig svar",
        "bryggeskole.oppsummering.heading": "🌱 Slik ligger du an",
        "bryggeskole.oppsummering.heading_forklaring": "«Denne runden» er resultatet ditt nå. «Over tid» bygger seg opp over flere runder, og endres ikke nødvendigvis av denne ene runden alene.",
        "bryggeskole.oppsummering.denne_runden_label": "Denne runden",
        "bryggeskole.oppsummering.over_tid_label": "Over tid",
        "bryggeskole.oppsummering.runde_ok": "✅ Riktig denne runden",
        "bryggeskole.oppsummering.runde_reprise": "🔁 Bør øves på igjen",
        "bryggeskole.oppsummering.prov_igjen": "🔁 Prøv igjen",
        "bryggeskole.feil.innhold_ugyldig": "❌ Kunne ikke laste leksjonsinnholdet akkurat nå.",
        "sprak.valger.label": "Språk",
        "sprak.valger.no": "🇳🇴 Norsk",
        "sprak.valger.en": "🇬🇧 English",
        "sidebar.demo_advarsel": "🍺 Demo-modus — oppskrifter lagres ikke",
        "sidebar.tittel": "📁 Lagrede oppskrifter",
        "sidebar.velg_brygg_label": "Velg et brygg fra harddisken:",
        "sidebar.velg_placeholder": "-- Velg oppskrift --",
        "sidebar.ingen_lagret": "Ingen oppskrifter lagret i mappen ennå.",
        "sidebar.lastet_ok": "Laddet: {navn}",
        "abv_calc.tittel": "🧮 ABV-kalkulator (uten oppskrift)",
        "abv_calc.beskrivelse": "Beregn alkoholprosent direkte fra målt startgravitet (OG) og sluttgravitet (FG) — helt uavhengig av en oppskrift eller et brygg. Nyttig for ekstraktsett, delvis mesking eller gamle bryggenotater.",
        "abv_calc.og_label": "Målt OG",
        "abv_calc.fg_label": "Målt FG",
        "abv_calc.resultat_label": "ABV",
        "abv_calc.standard_label": "Standardestimat",
        "abv_calc.high_gravity_label": "High-gravity-estimat",
        "abv_calc.high_gravity_forklaring": "Ved høy alkoholstyrke kan de to etablerte ABV-formlene gi merkbart forskjellig resultat — begge vises derfor her.",
        "abv_calc.ugyldig_input": "Ugyldige verdier: OG må være høyere enn 1.000, FG må være positiv, og FG kan ikke være høyere enn OG.",
        "brew_history.tittel": "📜 Brygghistorikk",
        "brew_history.demo_deaktivert": "Brygghistorikk er deaktivert i demo-modus (ingen vedvarende lagring).",
        "brew_history.tom": "Ingen lagrede brygg ennå. Bruk «▶️ Start nytt brygg» over for å starte det første.",
        "brew_history.velg_label": "Velg brygg",
        "brew_history.planlagt_tittel": "📋 Planlagt (frosset ved opprettelse)",
        "brew_history.planlagt_og": "Planlagt OG",
        "brew_history.planlagt_fg": "Planlagt FG",
        "brew_history.planlagt_abv": "Planlagt ABV",
        "brew_history.planlagt_volum": "Planlagt volum",
        "brew_history.opprettet": "Opprettet",
        "brew_history.brygget": "Brygget",
        "brew_history.status_label": "Status",
        "brew_history.status.active": "Aktiv",
        "brew_history.status.done": "Ferdig",
        "brew_history.status.discarded": "Forkastet",
        "kbhbrew.skriver_til": "🎯 Bryggdag skriver til: {oppskriftsnavn} · opprettet {opprettet}",
        "kbhbrew.advarsel_ikke_aktiv_status": "⚠️ Dette bryggets lagrede status er **{status}** — lagring her oppdaterer et brygg som ikke lenger er aktivt, ikke et nytt.",
        "kbhbrew.bekreft_standardutstyr_btn": "✅ Bruk og bekreft standardutstyr",
        "kbhbrew.bekreft_standardutstyr_hjelp": "Lagrer nåværende (eventuelt standard BrewZilla 35L) utstyrsprofil som din BEKREFTEDE utstyrsprofil, slik at «▶️ Start nytt brygg» kan brukes. Kan endres senere under «🔧 Verktøy» → «⚙️ Utstyrsprofil».",
        "kbhbrew.standardutstyr_bekreftet_ok": "Utstyrsprofil bekreftet og lagret. Trykk «▶️ Start nytt brygg» på nytt for å opprette brygget.",
        # App A4-4 (issue #248) -- fjerner internt implementasjonsspråk
        # ("snapshot", "Core V1", rå brewId) fra den brukervendte
        # create/import/eksport-flaten i ui/kbhbrew_panel.py, uten å endre
        # opprettelses-/import-/eksportoppførsel eller skjema. Legitim
        # bryggeterminologi (OG/FG/ABV/IBU/EBC, effektivitet, mash ratio,
        # boil-off, dead space, kettle capacity, selve ".kbhbrew"/
        # ".kbhrecipe"-filendelsene) er UENDRET -- se preflight-dokumentets
        # Section 6.
        "kbhbrew.start_ny_brew_tittel": "🍺 Start nytt brygg (fryser dagens oppskrift og utstyr)",
        "kbhbrew.start_ny_brew_beskrivelse": (
            "Fryser gjeldende oppskrift, utstyrsprofil og spådde verdier som ET NYTT, "
            "historisk brygg (.kbhbrew). Senere endringer i oppskrift/utstyr/masterdata "
            "påvirker ALDRI dette brygget igjen. Hvert klikk oppretter et NYTT batch — "
            "flere reelle brygg fra samme oppskrift er normalt."
        ),
        "kbhbrew.manglende_ingrediens_feil": (
            "❌ Kunne ikke starte nytt brygg — følgende ingrediens-ID-er finnes ikke i "
            "gjeldende masterdata og ville blitt hoppet stille over i det lagrede "
            "brygget: {ider}. Oppdater masterdata eller oppskriften og prøv igjen."
        ),
        "kbhbrew.nytt_brygg_toast": "Nytt brygg startet: {oppskriftsnavn}",
        "kbhbrew.import_beskrivelse": (
            "Åpne en .kbhbrew-fil (et historisk brygg, IKKE en oppskrift). Importeres "
            "alltid som et HELT NYTT, lokalt brygg med sin egen, ferskt mintede "
            "identitet — ingenting skrives før du selv trykker «Importer brygg»."
        ),
        "kbhbrew.import_bekreftet": "✅ Importert som nytt lokalt brygg: {oppskriftsnavn}",
        "kbhbrew.export_tomt": (
            "Ingen brygg lagret lokalt ennå. Bruk «▶️ Start nytt brygg» i "
            "Bryggdag-fanen, eller importer en .kbhbrew-fil over."
        ),
        "kbhbrew.oppskrift_ukjent_fallback": "Ukjent oppskrift",
        "brew_history.actuals_tittel": "🧪 Målte verdier (faktisk)",
        "brew_history.actual_og_label": "Faktisk OG",
        "brew_history.actual_fg_label": "Faktisk FG",
        "brew_history.actual_volum_label": "Faktisk volum (L)",
        "brew_history.notes_label": "Notater",
        "brew_history.brygget_dato_label": "Brygget dato (ÅÅÅÅ-MM-DD)",
        "brew_history.lagre_btn": "💾 Lagre målte verdier",
        "brew_history.lagret_ok": "✅ Lagret.",
        "brew_history.ugyldig_tall_feil": "❌ Ugyldig tall i: {felt}. Ingenting ble lagret — rett opp og prøv igjen.",
        "brew_history.sammenligning_tittel": "⚖️ Planlagt vs. faktisk",
        "brew_history.rad_og": "OG",
        "brew_history.rad_fg": "FG",
        "brew_history.rad_volum": "Volum",
        "brew_history.rad_abv": "ABV",
        "brew_history.ikke_malt": "—",
        "brew_history.sensing_tittel": "👃 Sensorikk/smaksinntrykk",
        "brew_history.sensing_judgment_label": "Helhetsvurdering",
        "brew_history.sensing_judgment.unset": "Ikke satt",
        "brew_history.sensing_judgment.yes": "Ja",
        "brew_history.sensing_judgment.maybe": "Kanskje",
        "brew_history.sensing_judgment.no": "Nei",
        "brew_history.sensing_notes_label": "Smaksnotater",
        "brew_history.learning_tittel": "📚 Læring/refleksjon",
        "brew_history.learning_what_worked_label": "Hva fungerte",
        "brew_history.learning_what_changed_label": "Hva ble endret",
        "brew_history.learning_next_time_label": "Neste gang",
        "brew_history.sensing_learning_lagre_btn": "💾 Lagre sensorikk og læring",
        "brew_history.sensing_learning_lagret_ok": "✅ Lagret.",
        "prosess.laer_bro.tittel": "🎓 Hvorfor påvirker mesketemperatur ølet?",
        "prosess.laer_bro.footer": "Vil du øve mer? Åpne Bryggeskole → Mesking.",
    },
    "en": {
        "tabs.oppskrift": "🍺 Recipe",
        "tabs.innkjop": "🛒 Shopping & Pantry",
        "tabs.bryggdag": "🧪 Brew day",
        "tabs.verktoy": "🔧 Tools",
        "tabs.bryggeskole": "🎓 Brew School",
        "bryggeskole.heading": "🎓 Kvernhaug Brew School",
        "bryggeskole.tagline": "One Brew School, two environments — the same verified knowledge, the same progress.",
        "bryggeskole.bytt_miljo": "🔁 Choose another environment",
        "bryggeskole.velg_miljo_heading": "Choose your environment",
        "bryggeskole.miljo.hjemmebrygger": "🏠 Homebrewer",
        "bryggeskole.miljo.hjemmebrygger_beskrivelse": "Kettle/BIAB, bucket/FermZilla, keg or bottle.",
        "bryggeskole.miljo.bryggeri": "🏭 Brewery",
        "bryggeskole.miljo.bryggeri_beskrivelse": "Mill, mash/lauter, kettle, conical fermenter.",
        "bryggeskole.miljo.velg_knapp": "Choose this environment",
        "bryggeskole.prosess.aktiv_badge": "✅ Lesson available",
        "bryggeskole.prosess.kommer_badge": "🔒 Coming later",
        "bryggeskole.anbefalt_neste": "💡 Recommended next: {modul}",
        "bryggeskole.modul.mesking.tittel": "Mashing",
        "bryggeskole.modul.gjaring.tittel": "Fermentation",
        "bryggeskole.modul.start": "▶️ Start",
        "bryggeskole.modul.fortsett": "↪️ Continue",
        "bryggeskole.modul.se_resultat": "📊 View result",
        "bryggeskole.status.ovd_tidligere": "📚 Practiced before",
        "bryggeskole.status.pabegynt": "🕒 In progress",
        "bryggeskole.status.fullfort_okt": "✅ Completed this session",
        "bryggeskole.tilbake_til_oversikt": "🔙 Back to the school overview",
        "bryggeskole.steg.leksjon": "Step 1 of 3 — Lesson",
        "bryggeskole.steg.sporsmal": "Step 2 of 3 — Question {n} of {totalt}",
        "bryggeskole.steg.oppsummering": "Step 3 of 3 — Summary",
        "bryggeskole.leksjon.bolk_teller": "Learning block {n} of {totalt}",
        "bryggeskole.leksjon.forrige": "← Previous",
        "bryggeskole.leksjon.neste": "Next →",
        "bryggeskole.leksjon.start_sporsmal": "▶️ Start questions",
        "bryggeskole.sporsmal.velg_svar": "Choose an answer",
        "bryggeskole.sporsmal.svar_knapp": "✅ Check answer",
        "bryggeskole.sporsmal.fortsett": "➡️ Continue",
        "bryggeskole.svar.ditt_svar": "Your answer",
        "bryggeskole.svar.riktig_svar": "Correct answer",
        "bryggeskole.oppsummering.heading": "🌱 Where you stand",
        "bryggeskole.oppsummering.heading_forklaring": "“This round” is how you did just now. “Over time” builds up across rounds, and does not necessarily change from this one round alone.",
        "bryggeskole.oppsummering.denne_runden_label": "This round",
        "bryggeskole.oppsummering.over_tid_label": "Over time",
        "bryggeskole.oppsummering.runde_ok": "✅ Correct this round",
        "bryggeskole.oppsummering.runde_reprise": "🔁 Should be practiced again",
        "bryggeskole.oppsummering.prov_igjen": "🔁 Try again",
        "bryggeskole.feil.innhold_ugyldig": "❌ Could not load the lesson content right now.",
        "sprak.valger.label": "Language",
        "sprak.valger.no": "🇳🇴 Norsk",
        "sprak.valger.en": "🇬🇧 English",
        "sidebar.demo_advarsel": "🍺 Demo mode — recipes are not saved",
        "sidebar.tittel": "📁 Saved recipes",
        "sidebar.velg_brygg_label": "Choose a brew from disk:",
        "sidebar.velg_placeholder": "-- Select recipe --",
        "sidebar.ingen_lagret": "No recipes saved in the folder yet.",
        "sidebar.lastet_ok": "Loaded: {navn}",
        "abv_calc.tittel": "🧮 ABV calculator (no recipe needed)",
        "abv_calc.beskrivelse": "Calculate alcohol by volume directly from a measured Original Gravity (OG) and Final Gravity (FG) — completely independent of any recipe or brew. Useful for extract kits, partial-mash brews, or old brewing notes.",
        "abv_calc.og_label": "Measured OG",
        "abv_calc.fg_label": "Measured FG",
        "abv_calc.resultat_label": "ABV",
        "abv_calc.standard_label": "Standard estimate",
        "abv_calc.high_gravity_label": "High-gravity estimate",
        "abv_calc.high_gravity_forklaring": "At high alcohol strength, the two established ABV formulas can diverge noticeably — both are shown here.",
        "abv_calc.ugyldig_input": "Invalid values: OG must be higher than 1.000, FG must be positive, and FG cannot be higher than OG.",
        "brew_history.tittel": "📜 Brew History",
        "brew_history.demo_deaktivert": "Brew History is disabled in demo mode (no persistent storage).",
        "brew_history.tom": "No saved brews yet. Use «▶️ Start new brew» above to start the first one.",
        "brew_history.velg_label": "Select brew",
        "brew_history.planlagt_tittel": "📋 Planned (frozen at creation)",
        "brew_history.planlagt_og": "Planned OG",
        "brew_history.planlagt_fg": "Planned FG",
        "brew_history.planlagt_abv": "Planned ABV",
        "brew_history.planlagt_volum": "Planned volume",
        "brew_history.opprettet": "Created",
        "brew_history.brygget": "Brewed",
        "brew_history.status_label": "Status",
        "brew_history.status.active": "Active",
        "brew_history.status.done": "Done",
        "brew_history.status.discarded": "Discarded",
        "kbhbrew.skriver_til": "🎯 Brewday writes to: {oppskriftsnavn} · created {opprettet}",
        "kbhbrew.advarsel_ikke_aktiv_status": "⚠️ This brew's stored status is **{status}** — saving here updates a brew that is no longer active, not a new one.",
        "kbhbrew.bekreft_standardutstyr_btn": "✅ Use and confirm default equipment",
        "kbhbrew.bekreft_standardutstyr_hjelp": "Saves the current (or default BrewZilla 35L) equipment profile as your CONFIRMED equipment profile, so «▶️ Start new brew» can be used. Can be changed later under «🔧 Tools» → «⚙️ Equipment profile».",
        "kbhbrew.standardutstyr_bekreftet_ok": "Equipment profile confirmed and saved. Click «▶️ Start new brew» again to create the brew.",
        "kbhbrew.start_ny_brew_tittel": "🍺 Start new brew (freezes today's recipe and equipment)",
        "kbhbrew.start_ny_brew_beskrivelse": (
            "Freezes the current recipe, equipment profile and predicted values as a "
            "NEW, historical brew (.kbhbrew). Later changes to the recipe/equipment/"
            "masterdata NEVER affect this brew again. Each click creates a NEW batch — "
            "multiple real brews from the same recipe are normal."
        ),
        "kbhbrew.manglende_ingrediens_feil": (
            "❌ Could not start new brew — the following ingredient IDs do not exist "
            "in current masterdata and would have been silently skipped in the stored "
            "brew: {ider}. Update masterdata or the recipe and try again."
        ),
        "kbhbrew.nytt_brygg_toast": "New brew started: {oppskriftsnavn}",
        "kbhbrew.import_beskrivelse": (
            "Open a .kbhbrew file (a historical brew, NOT a recipe). Always imported "
            "as a BRAND NEW, local brew with its own freshly minted identity — "
            "nothing is written until you click «Importer brygg» yourself."
        ),
        "kbhbrew.import_bekreftet": "✅ Imported as new local brew: {oppskriftsnavn}",
        "kbhbrew.export_tomt": (
            "No brews are stored locally yet. Use «▶️ Start new brew» in the Brewday "
            "tab, or import a .kbhbrew file above."
        ),
        "kbhbrew.oppskrift_ukjent_fallback": "Unknown recipe",
        "brew_history.actuals_tittel": "🧪 Measured values (actual)",
        "brew_history.actual_og_label": "Actual OG",
        "brew_history.actual_fg_label": "Actual FG",
        "brew_history.actual_volum_label": "Actual volume (L)",
        "brew_history.notes_label": "Notes",
        "brew_history.brygget_dato_label": "Brew date (YYYY-MM-DD)",
        "brew_history.lagre_btn": "💾 Save measured values",
        "brew_history.lagret_ok": "✅ Saved.",
        "brew_history.ugyldig_tall_feil": "❌ Invalid number in: {felt}. Nothing was saved — fix and try again.",
        "brew_history.sammenligning_tittel": "⚖️ Planned vs. actual",
        "brew_history.rad_og": "OG",
        "brew_history.rad_fg": "FG",
        "brew_history.rad_volum": "Volume",
        "brew_history.rad_abv": "ABV",
        "brew_history.ikke_malt": "—",
        "brew_history.sensing_tittel": "👃 Sensory/tasting impression",
        "brew_history.sensing_judgment_label": "Overall judgment",
        "brew_history.sensing_judgment.unset": "Not set",
        "brew_history.sensing_judgment.yes": "Yes",
        "brew_history.sensing_judgment.maybe": "Maybe",
        "brew_history.sensing_judgment.no": "No",
        "brew_history.sensing_notes_label": "Tasting notes",
        "brew_history.learning_tittel": "📚 Learning/reflection",
        "brew_history.learning_what_worked_label": "What worked",
        "brew_history.learning_what_changed_label": "What changed",
        "brew_history.learning_next_time_label": "Next time",
        "brew_history.sensing_learning_lagre_btn": "💾 Save sensory and learning",
        "brew_history.sensing_learning_lagret_ok": "✅ Saved.",
        "prosess.laer_bro.tittel": "🎓 Why does mash temperature affect the beer?",
        "prosess.laer_bro.footer": "Want to practice more? Open Brew School → Mashing.",
    },
}


def t(nokkel: str, sprak: str = SPRAK_DEFAULT, **params) -> str:
    """Slår opp `nokkel` for `sprak`, med fallback til SPRAK_DEFAULT, og
    substituerer ``{param}``-plassholdere fra `params`.

    Feiler ALDRI med en exception uansett `nokkel`/`sprak`/`params` — en
    ukjent `sprak` faller tilbake til SPRAK_DEFAULT nøyaktig som en
    manglende nøkkel gjør, og en manglende/ugyldig nøkkel returneres
    synlig markert i stedet for å endre semantikk stille (se modulens
    docstring).
    """
    spraak_tabell = TEKSTER.get(sprak) or {}
    tekst = spraak_tabell.get(nokkel)
    if tekst is None:
        tekst = TEKSTER[SPRAK_DEFAULT].get(nokkel)
    if tekst is None:
        return _MANGLENDE_NOKKEL_MAL.format(nokkel=nokkel)
    for navn, verdi in params.items():
        tekst = tekst.replace("{" + navn + "}", str(verdi))
    return tekst
