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
