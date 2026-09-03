# modules/kbhbrew_ui.py
"""
PRI 3B2 -- rene, testbare hjelpefunksjoner for den nye Streamlit
`.kbhbrew` V1-UI-en (ui/kbhbrew_panel.py). Ingen Streamlit-avhengighet,
ingen filsystem-tilgang, ingen sideeffekter -- samme "ren modul"-prinsipp
som modules/kbhbrew.py selv (se den for selve motoren/valideringen denne
kun forbereder input til/leser output fra).

Omfang: KUN formatering/uttrekk for UI-visning (predicted-input til en
ny brew, og et menneskelesbart utvalg for eksport) -- ingen ny
snapshot-/valideringslogikk. `modules/kbhbrew.py::_frys_predicted()`
validerer/filtrerer uansett alt som faktisk fryses; funksjonene her
bygger kun et best-effort kandidat-dict fra `ctx` (se
modules/recipe_context.py::bygg_recipe_context()) for det.
"""

_TALLTYPER = (int, float)


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


def bygg_brew_eksport_label(brew):
    """Menneskelesbart utvalgsnavn for én lagret brew -- ALDRI selve
    selektoren (den forblir `brewId`, se sorter_brews_for_eksport())."""
    brew = brew if isinstance(brew, dict) else {}
    snapshot = brew.get("snapshot") or {}
    recipe = snapshot.get("recipe") or {}
    navn = recipe.get("navn") or "(uten navn)"
    dato = (brew.get("brewedAt") or brew.get("createdAt") or "")[:10]
    status = brew.get("status") or "?"
    return f"{navn} — {dato} — {status}" if dato else f"{navn} — {status}"


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
    return [(brew_id, bygg_brew_eksport_label(brew)) for brew_id, brew in par]


def bygg_brew_eksport_filnavn(brew, brew_id):
    """Filsystem-trygt, deterministisk-nok filnavn for en `.kbhbrew`-
    nedlasting -- inkluderer en kort del av `brewId` for å unngå at flere
    batcher av samme oppskrift(navn) kolliderer på filnavn. Redefinerer
    ALDRI identitet: `brewId` er fortsatt kun lest fra det lagrede
    brygget, aldri avledet av dette filnavnet."""
    snapshot = (brew or {}).get("snapshot") or {}
    recipe = snapshot.get("recipe") or {}
    navn = (recipe.get("navn") or "brygg").replace(" ", "_").replace("/", "-")
    kort_id = (brew_id or "brew")[-8:]
    return f"{navn}_{kort_id}.kbhbrew"
