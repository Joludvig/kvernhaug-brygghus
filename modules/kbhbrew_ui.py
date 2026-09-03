# modules/kbhbrew_ui.py
"""
PRI 3B2 -- rene, testbare hjelpefunksjoner for den nye Streamlit
`.kbhbrew` V1-UI-en (ui/kbhbrew_panel.py). Ingen Streamlit-avhengighet,
ingen filsystem-tilgang, ingen sideeffekter -- samme "ren modul"-prinsipp
som modules/kbhbrew.py selv (se den for selve motoren/valideringen denne
kun forbereder input til/leser output fra).

Omfang: KUN formatering/uttrekk for UI-visning (predicted-input til en
ny brew, et menneskelesbart utvalg + filsystem-trygt filnavn for
eksport, og en opprettelses-preflight for manglende masterdata-ID-er)
-- ingen ny snapshot-/valideringslogikk. `modules/kbhbrew.py::
_frys_predicted()`/`_frys_ingredienser()` validerer/filtrerer uansett
alt som faktisk fryses; funksjonene her bygger kun et best-effort
kandidat-dict fra `ctx` (se modules/recipe_context.py::
bygg_recipe_context()), eller varsler FØR fryning om noe
`_frys_ingredienser()` uansett ville hoppet stille over.
"""
import re

_TALLTYPER = (int, float)

# Chief review (PR #30 blocker 2) -- konservativ filnavn-sanering som
# dekker BÅDE Windows- og POSIX-ugyldige tegn (`\ / : * ? " < > |`) og
# kontrolltegn, ikke kun mellomrom/skråstrek.
_UGYLDIGE_FILNAVN_TEGN_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

# Windows reserverte enhets-basenavn (case-insensitive, uten filtype) --
# et filnavn som kun består av ett av disse er ugyldig på Windows selv
# om det ikke inneholder noen av tegnene over.
_RESERVERTE_WINDOWS_BASENAVN = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def _saniter_filnavnkomponent(tekst):
    """Gjør `tekst` trygg som EN komponent i et nedlastet filnavn, på
    tvers av Windows og POSIX. Erstatter aldri med noe som kan
    forveksles med et faktisk feltinnhold -- kun `_`, aldri stille
    fjerning som kunne latt to ulike navn kollidere."""
    tekst = (tekst or "").strip()
    tekst = _UGYLDIGE_FILNAVN_TEGN_RE.sub("_", tekst)
    tekst = tekst.replace(" ", "_")
    # Windows tillater ikke et filnavn som slutter på punktum/mellomrom.
    tekst = tekst.rstrip(". ")
    tekst = tekst.strip("_") or "brygg"
    if tekst.upper() in _RESERVERTE_WINDOWS_BASENAVN:
        tekst = f"_{tekst}"
    return tekst


def _er_reelt_tall(v):
    return isinstance(v, _TALLTYPER) and not isinstance(v, bool)


def bygg_predicted_fra_ctx(ctx):
    """Bygger `predicted`-kandidaten `modules/kbhbrew_storage.py::
    opprett_og_lagre_ny_brew()` forventer, fra en allerede bygget
    `ctx` (modules/recipe_context.py::bygg_recipe_context()).

    Leser KUN allerede beregnede verdier -- fabrikerer aldri et tall/felt
    som ikke faktisk finnes i `ctx`. `style`-nøkkelen utelates helt hvis
    `ctx["style_analysis"]` ikke (ennå) peker på en navngitt stil, i
    stedet for å skrive en gjettet/tom verdi."""
    ctx = ctx if isinstance(ctx, dict) else {}
    style_analysis = ctx.get("style_analysis") or {}
    recipe = ctx.get("recipe") or {}

    predicted = {}
    for felt, verdi in (
        ("og", ctx.get("og")), ("fg", ctx.get("fg")), ("abv", ctx.get("abv")),
        ("ibu", ctx.get("ibu")), ("ebc", ctx.get("ebc")), ("buGu", style_analysis.get("bu_gu")),
    ):
        if _er_reelt_tall(verdi):
            predicted[felt] = verdi

    flavor_profile = recipe.get("flavor_profile")
    if isinstance(flavor_profile, dict) and flavor_profile:
        predicted["flavorProfile"] = flavor_profile

    stil = style_analysis.get("stil")
    if stil:
        score = next(
            (s.get("score") for s in style_analysis.get("stil_liste", []) if s.get("stil") == stil),
            None,
        )
        predicted["style"] = {"stil": stil, "score": score}

    return predicted


def bygg_brew_eksport_label(brew, brew_id):
    """Menneskelesbart utvalgsnavn for én lagret brew -- ALDRI selve
    selektoren (den forblir `brewId`, se sorter_brews_for_eksport()).

    Chief review-fiks (PR #30 blocker 1): `recipe navn — dato — status`
    alene er tvetydig for legitime samme-dag repeat-batcher (PRI 3B2
    tillater eksplisitt flere reelle brygg fra samme oppskrift) -- en
    kort del av `brewId` legges derfor alltid til på slutten, slik at
    to ellers identiske etiketter fortsatt kan skilles i selectboxen.
    Endrer ALDRI selve identiteten: `brewId` er og blir kun lest fra det
    lagrede brygget (sorter_brews_for_eksport()), aldri avledet av
    etiketten."""
    brew = brew if isinstance(brew, dict) else {}
    snapshot = brew.get("snapshot") or {}
    recipe = snapshot.get("recipe") or {}
    navn = recipe.get("navn") or "(uten navn)"
    dato = (brew.get("brewedAt") or brew.get("createdAt") or "")[:10]
    status = brew.get("status") or "?"
    kjerne = f"{navn} — {dato} — {status}" if dato else f"{navn} — {status}"
    kort_id = (brew_id or "")[-8:]
    return f"{kjerne} · {kort_id}" if kort_id else kjerne


def sorter_brews_for_eksport(brews):
    """`brews`: dict brewId -> brew (modules/kbhbrew_storage.py::
    hent_alle_brews()). Returnerer en liste [(brewId, label), ...] sortert
    med nyeste `createdAt` først -- ren visningsrekkefølge, endrer
    ALDRI selve `brewId`-verdien brukt som faktisk eksportvalg."""
    brews = brews if isinstance(brews, dict) else {}
    par = sorted(
        brews.items(),
        key=lambda kv: (kv[1].get("createdAt") or "", kv[0]),
        reverse=True,
    )
    return [(brew_id, bygg_brew_eksport_label(brew, brew_id)) for brew_id, brew in par]


def bygg_brew_eksport_filnavn(brew, brew_id):
    """Filsystem-trygt, deterministisk-nok filnavn for en `.kbhbrew`-
    nedlasting -- inkluderer en kort del av `brewId` for å unngå at flere
    batcher av samme oppskrift(navn) kolliderer på filnavn. Redefinerer
    ALDRI identitet: `brewId` er fortsatt kun lest fra det lagrede
    brygget, aldri avledet av dette filnavnet.

    Chief review-fiks (PR #30 blocker 2): den forrige varianten
    erstattet kun mellomrom/skråstrek, som ikke er nok på Windows
    (`\\ : * ? " < > |`, kontrolltegn, etterslengt punktum/mellomrom,
    reserverte enhets-basenavn som CON/NUL/COM1). `_saniter_
    filnavnkomponent()` dekker begge plattformer konservativt."""
    snapshot = (brew or {}).get("snapshot") or {}
    recipe = snapshot.get("recipe") or {}
    navn = _saniter_filnavnkomponent(recipe.get("navn") or "brygg")
    kort_id = _saniter_filnavnkomponent((brew_id or "brew")[-8:])
    return f"{navn}_{kort_id}.kbhbrew"


def manglende_ingrediens_ider(recipe, malt_db, humle_db, gjaer_db):
    """Chief review-fiks (PR #30 blocker 3) -- opprettelses-preflight:
    forutsier NØYAKTIG hvilke malt-/humle-/gjær-ID-er
    `modules/kbhbrew.py::_frys_ingredienser()` uansett ville hoppet
    stille over fordi de ikke finnes i den oppgitte masterdata-
    databasen (samme "id ikke i db -> hoppes over"-sjekk, gjentatt her
    FØR fryning i stedet for etter, slik at UI-et kan nekte å opprette
    et brygg med et ufullstendig ingrediens-embed i stedet for å
    stille fryse et hull i historikken).

    `recipe` er et App Recipe Object (samme rå form som
    modules/kbh_contract.py::recipe_to_kbhrecipe_payload() selv leser
    -- `recipe["malts"]`/`["hops"]`/`["yeast"]`), IKKE den allerede
    oversatte .kbhrecipe-payloaden. App har i dag ingen custom-
    ingredienser (kbh_contract.py bygger aldri en "custom"-rad), så
    enhver id som faktisk er satt på oppskriften MÅ finnes i databasen
    den fryses mot.

    Returnerer en liste med manglende ID-er (tom liste = alt funnet),
    ALDRI en exception -- selve avgjørelsen om å nekte opprettelse tas
    av kalleren (ui/kbhbrew_panel.py)."""
    recipe = recipe if isinstance(recipe, dict) else {}
    malt_db = malt_db if isinstance(malt_db, dict) else {}
    humle_db = humle_db if isinstance(humle_db, dict) else {}
    gjaer_db = gjaer_db if isinstance(gjaer_db, dict) else {}

    manglende = []
    for rad in recipe.get("malts") or []:
        id_ = rad.get("id") if isinstance(rad, dict) else None
        if id_ and id_ not in malt_db:
            manglende.append(id_)
    for rad in recipe.get("hops") or []:
        id_ = rad.get("id") if isinstance(rad, dict) else None
        if id_ and id_ not in humle_db:
            manglende.append(id_)
    gjaer_id = recipe.get("yeast")
    if gjaer_id and gjaer_id not in gjaer_db:
        manglende.append(gjaer_id)
    return manglende
