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
    },
    "en": {
        "tabs.oppskrift": "🍺 Recipe",
        "tabs.innkjop": "🛒 Shopping & Pantry",
        "tabs.bryggdag": "🧪 Brew day",
        "tabs.verktoy": "🔧 Tools",
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
