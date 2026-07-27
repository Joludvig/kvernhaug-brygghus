# modules/smart_shopping_list.py
"""
Smart Handleliste V1 — ren beregningsmodul.

Svarer på: "Hva må jeg kjøpe for å brygge den aktive oppskriften, etter at
lagerbeholdningen (Pantry) er trukket fra?"

Bygger EKSPLISITT videre på modules.pantry.beregn_mangler() — dupliserer
IKKE matching-/mangelberegningen derfra. Denne modulen legger kun til det
som er spesifikt for en handleliste: kjøpsforslag rundet til kjent
pakningsstørrelse, forventet rest etter kjøp, og et pris-/leverandør-
estimat fra eksisterende master-databaser (butikk_match).

Leser ALDRI data/humle_lager.json (det gamle, humle-only lageret) — Smart
Handleliste bruker utelukkende Pantry som sannhetskilde for
lagerbeholdning. Det gamle humlelageret fortsetter uendret å styre
kostnadsberegningen i den EKSISTERENDE handlelisten (ui/shopping_list_panel.py)
inntil videre; de to er bevisst IKKE koblet sammen i V1.

Enhetskonvensjon (viktig, se rapport for begrunnelse):
  - *_base-felt (required_base/available_base/missing_base/
    expected_remainder_base) er ALLTID i samme basisenhet som
    modules.pantry.beregn_mangler() bruker: gram for malt/humle, pakker
    for gjær — akkurat som Pantry sitt eget "_base"-navnekonvensjon.
  - suggested_purchase_quantity/purchase_unit er i en menneskevennlig
    innkjøpsenhet: kg for malt (ingen registrert pakningsstørrelse for
    malt i dagens masterdata — Vestbrygg leverer eksakt oppgitt mengde,
    en bevisst tidligere prosjektbeslutning, se docs/PROJECT_STATUS_JUNI_2026.md),
    gram for humle, hele pakker for gjær.

Pris hentes fra samme butikk_match-struktur som brukes ellers i appen
(butikk_match.{vestbrygg|olbrygging}.{pris, url, pakke_gram}) — IKKE fra de
eldre, flate pris_olbrygging/pris_vestbrygg-feltene ui/shopping_list_panel.py
i dag leser for malt, som ikke lenger finnes i noen entry i
data/master_malt.json (prisdata for malt flyttet til butikk_match i en
tidligere opprydding, jf. docs/PROJECT_STATUS_JUNI_2026.md). Denne modulen
leser derfor malt-pris fra butikk_match, konsistent med humle/gjær og med
hvor dataene faktisk ligger i dag.
"""
import math

from modules.pantry import beregn_mangler

_MALT_FALLBACK_KR_KG = 35.0
_HUMLE_FALLBACK_PAKKE_GRAM = 100.0
_HUMLE_FALLBACK_KR_PAKKE = 99.0
_GJAER_FALLBACK_KR_PAKKE = 59.0

_BUTIKKER = (("Vestbrygg", "vestbrygg"), ("Ølbrygging.no", "olbrygging"))


def _butikk_nokkel(butikk_navn):
    return "olbrygging" if butikk_navn == "Ølbrygging.no" else "vestbrygg"


def _butikk_match(ingredient_id, db, butikk_nokkel):
    if not db or not ingredient_id:
        return {}
    return db.get(ingredient_id, {}).get("butikk_match", {}).get(butikk_nokkel, {})


def _malt_pakke_kg_pris_og_url(ingredient_id, malt_db, butikk_nokkel):
    """Malt har i dagens masterdata INGEN registrert pakningsstørrelse
    (Vestbrygg leverer eksakt oppgitt mengde — en bevisst, tidligere
    prosjektbeslutning, se docs/PROJECT_STATUS_JUNI_2026.md). Leser
    likevel av et valgfritt "pakke_kg"-felt på butikk_match, med samme
    mekanikk som humle sin pakke_gram — slik at avrunding til
    pakningsstørrelse fungerer uniformt DERSOM en fremtidig datakilde
    faktisk registrerer én for en spesifikk malt (f.eks. et 25 kg sekk).
    Uten et slikt felt (dagens virkelighet) foreslås eksakt mengde."""
    bm = _butikk_match(ingredient_id, malt_db, butikk_nokkel)
    pakke_kg = bm.get("pakke_kg")
    pris_kg = bm.get("pris") or _MALT_FALLBACK_KR_KG
    er_estimat = not bm.get("pris")
    return (float(pakke_kg) if pakke_kg else None), pris_kg, er_estimat, bm.get("url")


def _humle_pakke_gram_pris_og_url(ingredient_id, humle_db, butikk_nokkel):
    bm = _butikk_match(ingredient_id, humle_db, butikk_nokkel)
    pakke_gram = bm.get("pakke_gram")
    pris_pakke = bm.get("pris") or _HUMLE_FALLBACK_KR_PAKKE
    er_estimat = not bm.get("pris")
    return (float(pakke_gram) if pakke_gram else None), pris_pakke, er_estimat, bm.get("url")


def _gjaer_pris_pakke_og_url(ingredient_id, gjaer_db, butikk_nokkel):
    bm = _butikk_match(ingredient_id, gjaer_db, butikk_nokkel)
    pris_pakke = bm.get("pris") or _GJAER_FALLBACK_KR_PAKKE
    er_estimat = not bm.get("pris")
    return pris_pakke, er_estimat, bm.get("url")


def _supplier_options(ingredient_type, ingredient_id, db):
    """Enkel liste med kjente leverandøralternativer (butikk/pris/url/om
    prisen er et estimat) for INFORMASJON — ingen "billigst"-sammenligning
    eller automatisk butikkvalg gjøres her. Butikksammenligning er bevisst
    utenfor scope for V1 (se roadmap)."""
    if not db or not ingredient_id:
        return []
    resultat = []
    for butikk_navn, butikk_nokkel in _BUTIKKER:
        bm = _butikk_match(ingredient_id, db, butikk_nokkel)
        if bm.get("pris") is not None or bm.get("url"):
            resultat.append({
                "butikk": butikk_navn, "pris": bm.get("pris"), "url": bm.get("url"),
                "er_estimat": bm.get("pris") is None,
            })
    return resultat


def _tom_rad_ukjent_match(mangel_rad):
    return {
        "ingredient_type": mangel_rad["ingredient_type"],
        "ingredient_id": mangel_rad["ingredient_id"],
        "name": mangel_rad["name"],
        "required_base": mangel_rad["required_base"],
        "available_base": mangel_rad["available_base"],
        "missing_base": mangel_rad["missing_base"],
        "base_unit": mangel_rad["base_unit"],
        "suggested_purchase_quantity": None,
        "purchase_unit": None,
        "package_size_known": None,
        "expected_remainder_base": None,
        "status": "ukjent_match",
        "supplier_options": [],
        "estimated_cost": None,
        "cost_is_estimate": None,
    }


def _rad_naar_ikke_noe_mangler(mangel_rad, db):
    ingredient_type = mangel_rad["ingredient_type"]
    ingredient_id = mangel_rad["ingredient_id"]
    required_base = mangel_rad["required_base"]
    available_base = mangel_rad["available_base"]
    return {
        "ingredient_type": ingredient_type,
        "ingredient_id": ingredient_id,
        "name": mangel_rad["name"],
        "required_base": required_base,
        "available_base": available_base,
        "missing_base": 0.0,
        "base_unit": mangel_rad["base_unit"],
        "suggested_purchase_quantity": 0.0,
        "purchase_unit": {"malt": "kg", "humle": "g", "gjaer": "pakke"}[ingredient_type],
        "package_size_known": None,
        "expected_remainder_base": max(0.0, available_base - required_base) if required_base is not None else available_base,
        "status": "nok",
        "supplier_options": _supplier_options(ingredient_type, ingredient_id, db),
        "estimated_cost": 0.0,
        "cost_is_estimate": False,
    }


def _rad_naar_kjop_trengs(mangel_rad, malt_db, humle_db, gjaer_db, butikk_nokkel):
    ingredient_type = mangel_rad["ingredient_type"]
    ingredient_id = mangel_rad["ingredient_id"]
    required_base = mangel_rad["required_base"]
    available_base = mangel_rad["available_base"]
    missing_base = mangel_rad["missing_base"]
    db = {"malt": malt_db, "humle": humle_db, "gjaer": gjaer_db}[ingredient_type]

    # 1) Kjøpsforslag i BASISENHET (gram/pakker), rundet til kjent
    # pakningsstørrelse. Gjær rundes alltid opp til hele pakker (V1-krav —
    # ingen levedyktighets-/starterberegning). Malt har ingen registrert
    # pakningsstørrelse i dagens data (se _malt_pakke_kg_pris_og_url) ->
    # eksakt foreslått mengde, men bruker samme avrundingsmekanikk som
    # humle DERSOM en pakke_kg-verdi faktisk er registrert.
    pakke_gram = None
    pakke_kg = None
    if ingredient_type == "gjaer":
        suggested_purchase_base = math.ceil(missing_base)
        pakningsstorrelse_kjent = True
    elif ingredient_type == "humle":
        pakke_gram, _, _, _ = _humle_pakke_gram_pris_og_url(ingredient_id, humle_db, butikk_nokkel)
        if pakke_gram:
            suggested_purchase_base = math.ceil(missing_base / pakke_gram) * pakke_gram
            pakningsstorrelse_kjent = True
        else:
            suggested_purchase_base = missing_base
            pakningsstorrelse_kjent = False
    else:  # malt
        pakke_kg, _, _, _ = _malt_pakke_kg_pris_og_url(ingredient_id, malt_db, butikk_nokkel)
        if pakke_kg:
            pakke_gram_malt = pakke_kg * 1000.0
            suggested_purchase_base = math.ceil(missing_base / pakke_gram_malt) * pakke_gram_malt
            pakningsstorrelse_kjent = True
        else:
            suggested_purchase_base = missing_base
            pakningsstorrelse_kjent = False

    expected_remainder_base = max(0.0, available_base + suggested_purchase_base - required_base)

    # 2) Pris + menneskevennlig innkjøpsenhet. estimated_cost/er_estimat_kost
    # er alltid satt sammen, ETT sted per type — ingen etterhånds-overstyring.
    if ingredient_type == "malt":
        _, pris_kg, er_estimat, url = _malt_pakke_kg_pris_og_url(ingredient_id, malt_db, butikk_nokkel)
        purchase_unit = "kg"
        suggested_purchase_quantity = suggested_purchase_base / 1000.0
        estimated_cost = round(suggested_purchase_quantity * pris_kg, 1)
        er_estimat_kost = er_estimat
    elif ingredient_type == "humle":
        _, pris_pakke, er_estimat, url = _humle_pakke_gram_pris_og_url(ingredient_id, humle_db, butikk_nokkel)
        purchase_unit = "g"
        suggested_purchase_quantity = suggested_purchase_base
        # Kjøpsforslaget (over) bruker ALDRI en gjettet pakningsstørrelse —
        # "foreslå eksakt mengde" når den er ukjent, jf. spesifikasjonen.
        # For selve KOSTNADSESTIMATET er en falltilbake-pakningsstørrelse
        # (samme 100 g-konvensjon som ui/shopping_list_panel.py allerede
        # bruker) likevel bedre enn ingen pris i det hele tatt — så lenge
        # den tydelig merkes som et estimat (både pris og pakningsstørrelse
        # er da antatt, ikke bare prisen).
        pakke_gram_for_pris = pakke_gram or _HUMLE_FALLBACK_PAKKE_GRAM
        estimated_cost = round(pris_pakke * suggested_purchase_base / pakke_gram_for_pris, 1)
        er_estimat_kost = er_estimat or not pakke_gram
    else:  # gjaer
        pris_pakke, er_estimat, url = _gjaer_pris_pakke_og_url(ingredient_id, gjaer_db, butikk_nokkel)
        purchase_unit = "pakke"
        suggested_purchase_quantity = suggested_purchase_base
        estimated_cost = round(pris_pakke * suggested_purchase_base, 1)
        er_estimat_kost = er_estimat

    return {
        "ingredient_type": ingredient_type,
        "ingredient_id": ingredient_id,
        "name": mangel_rad["name"],
        "required_base": required_base,
        "available_base": available_base,
        "missing_base": missing_base,
        "base_unit": mangel_rad["base_unit"],
        "suggested_purchase_quantity": suggested_purchase_quantity,
        "purchase_unit": purchase_unit,
        "package_size_known": pakningsstorrelse_kjent,
        "expected_remainder_base": expected_remainder_base,
        "status": "kjop",
        "supplier_options": _supplier_options(ingredient_type, ingredient_id, db),
        "estimated_cost": estimated_cost,
        "cost_is_estimate": er_estimat_kost,
    }


def beregn_handleliste(recipe, pantry_data, malt_db=None, humle_db=None, gjaer_db=None,
                        butikk="Ølbrygging.no", marginer=None):
    """Bygger Smart Handleliste V1 for en oppskrift, gitt Pantry sin
    beregnede beholdning. Returnerer én rad per ingrediens — samme
    ingredienser som modules.pantry.beregn_mangler() ville returnert,
    beriket med kjøpsforslag/forventet rest/pris/leverandør.

    Statuskartlegging fra Pantry sin firedelte status til handlelistens
    tredelte status (per oppgavespesifikasjonen: "kjop | nok | ukjent_match"):
      - Pantry "mangler"      -> "kjop" (reell mangel, må kjøpes)
      - Pantry "nok"/"knapp"  -> "nok"  (dekker det oppskriften faktisk
        krever — "knapp" betyr man er innenfor sikkerhetsmarginen, ikke at
        noe MÅ kjøpes; å presentere en marginbasert påfylling som en
        obligatorisk "kjøp" ville brutt kravet om at avrundet/anbefalt
        kjøp aldri skal se ut som en faktisk mangel)
      - Pantry "ukjent_match" -> "ukjent_match" (uendret)

    Muterer ALDRI `recipe` eller `pantry_data` — kaller kun
    modules.pantry.beregn_mangler(), som selv er en ren funksjon."""
    butikk_nokkel = _butikk_nokkel(butikk)
    mangel_rader = beregn_mangler(recipe, pantry_data, malt_db, humle_db, gjaer_db, marginer)

    handleliste = []
    for rad in mangel_rader:
        if rad["status"] == "ukjent_match" or rad["ingredient_id"] is None:
            handleliste.append(_tom_rad_ukjent_match(rad))
            continue

        db = {"malt": malt_db, "humle": humle_db, "gjaer": gjaer_db}[rad["ingredient_type"]]
        if not rad["missing_base"]:
            handleliste.append(_rad_naar_ikke_noe_mangler(rad, db))
        else:
            handleliste.append(_rad_naar_kjop_trengs(rad, malt_db, humle_db, gjaer_db, butikk_nokkel))

    return handleliste


def oppsummer_handleliste(handleliste):
    """Bygger et kompakt totalsammendrag: antall varer som må kjøpes,
    antall usikre matcher, og en estimert totalkostnad (merket som
    estimert dersom NOEN av kostnadene i summen er et prisestimat, eller
    dersom kostnaden ikke kunne beregnes for en eller flere kjøp-rader)."""
    antall_kjop = sum(1 for r in handleliste if r["status"] == "kjop")
    antall_ukjent = sum(1 for r in handleliste if r["status"] == "ukjent_match")

    kjop_rader = [r for r in handleliste if r["status"] == "kjop"]
    kjente_kostnader = [r["estimated_cost"] for r in kjop_rader if r["estimated_cost"] is not None]
    total_kostnad = sum(kjente_kostnader) if kjente_kostnader else 0.0
    kostnad_er_ufullstendig = any(r["estimated_cost"] is None for r in kjop_rader)
    kostnad_er_estimat = kostnad_er_ufullstendig or any(r.get("cost_is_estimate") for r in kjop_rader)

    return {
        "antall_ma_kjopes": antall_kjop,
        "antall_usikre_matcher": antall_ukjent,
        "estimert_totalkostnad": round(total_kostnad, 1),
        "totalkostnad_er_estimat": kostnad_er_estimat,
        "totalkostnad_er_ufullstendig": kostnad_er_ufullstendig,
    }
