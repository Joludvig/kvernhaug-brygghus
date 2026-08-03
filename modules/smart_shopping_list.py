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

ENHETSKONTRAKT — to atskilte enhetssystemer, ALDRI bland dem:

  1. *_base-felt (required_base, available_base, missing_base,
     expected_remainder_base) er ALLTID i Pantry sin BASISENHET, akkurat
     som modules.pantry.beregn_mangler() returnerer dem:
       - malt:  gram
       - humle: gram
       - gjær:  pakker

  2. suggested_purchase_quantity er ALLTID uttrykt i purchase_unit — en
     menneskevennlig INNKJØPSENhet, IKKE nødvendigvis samme enhet som
     *_base-feltene over:
       - malt:  kg   (ingen registrert pakningsstørrelse i dagens
                 masterdata — Vestbrygg leverer eksakt oppgitt mengde, en
                 bevisst tidligere prosjektbeslutning, se
                 docs/PROJECT_STATUS_JUNI_2026.md)
       - humle: g
       - gjær:  hele pakker

  Konkret eksempel (malt, hentet fra en reell mangel på 3230 g med et
  registrert 1 kg-sekk som pakningsstørrelse):

      required_base               = 4230      # gram (Pantry-basisenhet)
      available_base              = 1000      # gram
      missing_base                = 3230      # gram — REELL mangel, uavrundet
      base_unit                   = "g"
      suggested_purchase_quantity = 4.0        # KILOGRAM (purchase_unit), ikke 4000
      purchase_unit                = "kg"
      expected_remainder_base     = 770       # gram: 1000 + 4000 - 4230

  suggested_purchase_quantity=4.0 og purchase_unit="kg" beskriver SAMME
  fysiske mengde som 4000 g — men skal ALDRI skrives som
  suggested_purchase_quantity=4000 med purchase_unit="kg" (det ville vært
  1000× for mye malt). Se
  tests/test_smart_shopping_list.py::TestEnhetskontrakt for regresjonstester
  som låser nøyaktig denne forvekslingen.

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

from modules.calculations import beregn_total_ibu
from modules.pantry import beregn_mangler
from modules.malt_packaging import bygg_pakningsforslag, MALTFORM_INGEN_PREFERANSE, MALTFORM_KNUST, PRIORITET_BALANSERT

_MALT_FALLBACK_KR_KG = 35.0
_HUMLE_FALLBACK_PAKKE_GRAM = 100.0
_HUMLE_FALLBACK_KR_PAKKE = 99.0
_GJAER_FALLBACK_KR_PAKKE = 59.0

_BUTIKKER = (("Vestbrygg", "vestbrygg"), ("Ølbrygging.no", "olbrygging"))

# Krav 9: en "svært liten" humlemangel (f.eks. 1 g av 81 g) skal ALDRI
# trigge et automatisk kjøpsforslag som eneste alternativ -- i stedet vises
# et informativt alternativ ("bruk det du har, IBU blir ca. X i stedet for
# Y") ved SIDEN AV det ordinære kjøpsforslaget. Terskelen er bevisst en
# ANDEL av det oppskriften faktisk trenger, ikke et fast gramtall, siden
# "svært liten" betyr noe helt annet for en 5 g tørrhumle-tilsetning enn
# for en 300 g bittertilsetning.
_HUMLE_LITEN_MANGEL_ANDEL = 0.05


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


def _humle_ibu_for_hopliste(hops, humle_db, volum, og):
    liste = [{"navn": h.get("id"), "gram": float(h.get("gram", 0.0)), "tid": h.get("tid", 0)} for h in hops]
    return beregn_total_ibu(liste, humle_db or {}, volum, og)


def _humle_liten_mangel_alternativ(recipe, humle_db, humle_id, missing_base, available_base, required_base):
    """Krav 9 (Tettnang-scenariet): når mangelen er svært liten i forhold
    til det oppskriften faktisk trenger, foreslå IKKE bare et ordinært
    kjøp -- vis i tillegg et informativt alternativ: bruk det du allerede
    har, med den faktiske IBU-konsekvensen regnet ut på nytt (samme Tinseth-
    formel som resten av appen, modules.calculations.beregn_total_ibu).

    Endrer ALDRI oppskriften selv -- bygger kun en midlertidig kopi av
    hop-listen for selve IBU-utregningen. Returnerer None når mangelen ikke
    er "svært liten", når ingrediensen ikke faktisk er en humle i
    oppskriftens hop-liste, eller når oppskriften mangler det som trengs
    for å beregne IBU pålitelig (batch_size, stats.og)."""
    if not missing_base or missing_base <= 0:
        return None
    if not required_base or required_base <= 0 or missing_base > required_base * _HUMLE_LITEN_MANGEL_ANDEL:
        return None

    hops = recipe.get("hops", [])
    if not any(h.get("id") == humle_id for h in hops):
        return None

    volum = recipe.get("batch_size")
    og = (recipe.get("stats") or {}).get("og")
    if not volum or volum <= 0 or not og or og <= 1.000:
        return None

    skalering = available_base / required_base
    hops_alternativ = [
        dict(h, gram=float(h.get("gram", 0.0)) * skalering) if h.get("id") == humle_id else h
        for h in hops
    ]

    ibu_original = _humle_ibu_for_hopliste(hops, humle_db, volum, og)
    ibu_alternativ = _humle_ibu_for_hopliste(hops_alternativ, humle_db, volum, og)

    return {
        "bruk_gram": available_base,
        "ibu_original": round(ibu_original, 1),
        "ibu_alternativ": round(ibu_alternativ, 1),
        "advarsel": "Svært liten mangel",
        "tekst": (
            f"Bruk {available_base:g} g – beregnet IBU ca. {round(ibu_alternativ, 1):g} "
            f"i stedet for {round(ibu_original, 1):g}"
        ),
    }


_KNAPP_ADVISORY = "Nok til oppskriften, men under anbefalt sikkerhetsmargin."


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
        "pantry_status": "ukjent_match",
        "advisory": None,
        "supplier_options": [],
        "estimated_cost": None,
        "cost_is_estimate": None,
        "malt_pakningsforslag": None,
        "malt_ingen_relevant_variant": False,
        "liten_mangel_alternativ": None,
    }


def _rad_naar_ikke_noe_mangler(mangel_rad, db):
    ingredient_type = mangel_rad["ingredient_type"]
    ingredient_id = mangel_rad["ingredient_id"]
    required_base = mangel_rad["required_base"]
    available_base = mangel_rad["available_base"]
    # mangel_rad["status"] her er Pantry sin EGEN status (jf.
    # modules.pantry.vurder_tilgjengelighet): "nok" eller "knapp" — begge
    # havner i denne grenen fordi missing_base==0 for begge. Handlelistens
    # EGEN status kollapses bevisst til "nok" for begge (ingenting er
    # PÅKREVD å kjøpe), men Pantry sitt opprinnelige signal bevares i
    # pantry_status/advisory i stedet for å kastes bort helt — se krav 2
    # i oppryddingen 2026-07-27.
    pantry_status = mangel_rad["status"]
    advisory = _KNAPP_ADVISORY if pantry_status == "knapp" else None
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
        "pantry_status": pantry_status,
        "advisory": advisory,
        "supplier_options": _supplier_options(ingredient_type, ingredient_id, db),
        "estimated_cost": 0.0,
        "cost_is_estimate": False,
        "malt_pakningsforslag": None,
        "malt_ingen_relevant_variant": False,
        "liten_mangel_alternativ": None,
    }


def _rad_naar_kjop_trengs(mangel_rad, malt_db, humle_db, gjaer_db, butikk_nokkel,
                          recipe=None, maltform=MALTFORM_INGEN_PREFERANSE, malt_prioritet=PRIORITET_BALANSERT,
                          eksakt_mal_knust=False):
    ingredient_type = mangel_rad["ingredient_type"]
    ingredient_id = mangel_rad["ingredient_id"]
    required_base = mangel_rad["required_base"]
    available_base = mangel_rad["available_base"]
    missing_base = mangel_rad["missing_base"]
    db = {"malt": malt_db, "humle": humle_db, "gjaer": gjaer_db}[ingredient_type]

    # 1) Kjøpsforslag i BASISENHET (gram/pakker), rundet til kjent
    # pakningsstørrelse. Gjær rundes alltid opp til hele pakker (V1-krav —
    # ingen levedyktighets-/starterberegning). Malt bruker den nye
    # variant-/kombinasjonsmodellen (modules.malt_packaging) DERSOM
    # butikk_match har registrerte "varianter" -- ellers samme eldre,
    # enklere pakke_kg-avrunding som før (se _malt_pakke_kg_pris_og_url).
    pakke_gram = None
    pakke_kg = None
    malt_pakningsforslag = None
    malt_ingen_relevant_variant = False
    advisory_kjop = None
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
        malt_bm = _butikk_match(ingredient_id, malt_db, butikk_nokkel)
        # Steg F3: «bestill til eksakt mål» gjelder KUN Vestbrygg + knust —
        # eksplisitt brukervalg (se ui/smart_shopping_list_panel.py), aldri
        # automatisk for hel malt, Ølbrygging eller andre butikker. Selve
        # gaten står her (ikke bare i UI-et) som et sikkerhetsnett — flagget
        # sendes videre til bygg_pakningsforslag(), som i tillegg selv
        # krever maltform==MALTFORM_KNUST før det har noen effekt.
        bruk_eksakt_mal = eksakt_mal_knust and butikk_nokkel == "vestbrygg" and maltform == MALTFORM_KNUST
        malt_pakningsforslag = bygg_pakningsforslag(
            missing_base, malt_bm, maltform=maltform, prioritet=malt_prioritet, eksakt_mal=bruk_eksakt_mal)
        if malt_pakningsforslag is not None:
            # Kjøpsresultatet (pris+mottatt_mengde+bestilling) er den
            # autoritative kilden — begge fasettene under er alltid hentet
            # fra SAMME valgte kombinasjon, se malt_packaging.py.
            suggested_purchase_base = malt_pakningsforslag["kjopsresultat"]["mottatt_mengde"]
            pakningsstorrelse_kjent = True
        elif malt_bm.get("varianter"):
            # Steg F3-sluttkontroll: registrert variantdata FINNES, men
            # bygg_pakningsforslag() kunne likevel ikke bygge noen
            # kombinasjon for ønsket maltform (enten fordi ingen variant av
            # den formen noensinne er registrert, eller — det tilfellet
            # denne sjekken faktisk finnes for — fordi ALLE relevante
            # varianter er eksplisitt "utsolgt", se
            # modules/malt_packaging.py::_varianter_for_form()).
            #
            # Dette skal ALDRI forveksles med "ingen variantdata i det hele
            # tatt" (den eldre, fortsatt gyldige pakke_kg-/eksakt-mengde-
            # fallbacken under) — her VET vi presist at ingen kjøpbar
            # kombinasjon finnes akkurat nå, og skal derfor ikke late som et
            # kjøp kan gjennomføres via det flate butikk_match-prisfeltet
            # (som uansett ikke skiller på maltform eller lagerstatus).
            suggested_purchase_base = missing_base
            pakningsstorrelse_kjent = False
            malt_ingen_relevant_variant = True
            advisory_kjop = (
                "Ingen kjøpbar variant registrert for valgt maltform akkurat nå "
                "(utsolgt, eller ingen registrert variant av denne typen). "
                "Kostnadsestimatet under er derfor ikke tilgjengelig."
            )
        else:
            pakke_kg, _, _, _ = _malt_pakke_kg_pris_og_url(ingredient_id, malt_db, butikk_nokkel)
            if pakke_kg:
                pakke_gram_malt = pakke_kg * 1000.0
                suggested_purchase_base = math.ceil(missing_base / pakke_gram_malt) * pakke_gram_malt
                pakningsstorrelse_kjent = True
            else:
                suggested_purchase_base = missing_base
                pakningsstorrelse_kjent = False

    # Resten regnes ALLTID fra suggested_purchase_base -- for pakket-malt
    # med registrert variantdata er dette allerede nøyaktig samme tall som
    # malt_pakningsforslag["kjopsresultat"]["mottatt_mengde"] (satt over),
    # for humle/gjær den tilsvarende avrundede kjøpsmengden. Pris, eller et
    # fremtidig fakturert_mengde (avrundet KUN for prisberegning ved
    # løsvekt), skal ALDRI inngå i dette regnestykket.
    expected_remainder_base = max(0.0, available_base + suggested_purchase_base - required_base)

    # 2) Pris + menneskevennlig innkjøpsenhet. estimated_cost/er_estimat_kost
    # er alltid satt sammen, ETT sted per type — ingen etterhånds-overstyring.
    if ingredient_type == "malt":
        purchase_unit = "kg"
        suggested_purchase_quantity = suggested_purchase_base / 1000.0
        if malt_pakningsforslag is not None:
            estimated_cost = malt_pakningsforslag["kjopsresultat"]["pris"]
            er_estimat_kost = False  # registrerte variantpriser er ikke gjettet
        elif malt_ingen_relevant_variant:
            # Ingen pålitelig pris finnes -- det flate butikk_match-prisfeltet
            # kan tilhøre en annen maltform eller en utsolgt variant, og skal
            # ALDRI presenteres som et konkret kostnadstall her (se
            # begrunnelse over). None (ikke et gjettet tall) + cost_is_estimate
            # =True er det samme signalet UI/oppsummer_handleliste() allerede
            # bruker for "usikkert, kan ikke beregnes" (jf. ukjent_match-raden).
            estimated_cost = None
            er_estimat_kost = True
        else:
            _, pris_kg, er_estimat, url = _malt_pakke_kg_pris_og_url(ingredient_id, malt_db, butikk_nokkel)
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

    liten_mangel_alternativ = None
    if ingredient_type == "humle" and recipe is not None:
        liten_mangel_alternativ = _humle_liten_mangel_alternativ(
            recipe, humle_db, ingredient_id, missing_base, available_base, required_base)

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
        "pantry_status": "mangler",
        "advisory": advisory_kjop,
        "supplier_options": _supplier_options(ingredient_type, ingredient_id, db),
        "estimated_cost": estimated_cost,
        "cost_is_estimate": er_estimat_kost,
        "malt_pakningsforslag": malt_pakningsforslag,
        "malt_ingen_relevant_variant": malt_ingen_relevant_variant,
        "liten_mangel_alternativ": liten_mangel_alternativ,
    }


def beregn_handleliste(recipe, pantry_data, malt_db=None, humle_db=None, gjaer_db=None,
                        butikk="Ølbrygging.no", marginer=None,
                        maltform=MALTFORM_INGEN_PREFERANSE, malt_prioritet=PRIORITET_BALANSERT,
                        eksakt_mal_knust=False):
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

    Pantry sitt opprinnelige, firedelte signal KASTES ikke bort når det
    kollapses til "nok" — hver rad har i tillegg:
      - pantry_status: Pantrys egen status ("nok"/"knapp"/"mangler"/
        "ukjent_match"), uavhengig av handlelistens forenklede status.
      - advisory: en kort, menneskelesbar tekst når pantry_status=="knapp"
        (f.eks. "Nok til oppskriften, men under anbefalt sikkerhetsmargin."),
        ellers None. UI-et bruker dette til å vise "✅ Nok – knapp margin"
        i stedet for en udifferensiert "✅ Nok" — men KUN når brukeren
        bevisst har bedt om å se varer man har nok av; raden teller aldri
        med blant "må kjøpes" og bidrar aldri til estimert kostnad.

    `maltform` (modules.malt_packaging.MALTFORM_*) og `malt_prioritet`
    (modules.malt_packaging.PRIORITET_*) styrer KUN hvordan malt-
    pakningsforslag rangeres/velges når butikk_match har registrerte
    "varianter" (se modules/malt_packaging.py) — uten registrerte varianter
    er de uten virkning (samme eldre pakke_kg-oppførsel som før).

    `eksakt_mal_knust` (Steg F3, standard False): eksplisitt brukervalg
    (se ui/smart_shopping_list_panel.py) for Vestbryggs opplyste «bestill
    til eksakt mål»-tjeneste for knust malt. Har KUN effekt når butikk er
    Vestbrygg OG maltform==MALTFORM_KNUST samtidig — automatisk aldri for
    hel malt, Ølbrygging, humle eller gjær. Når aktiv settes
    kjøpsresultatets mottatt_mengde (og dermed expected_remainder_base) til
    det eksakte behovet i stedet for SKU-summen; prisen er uendret. Se
    modules/malt_packaging.py::bygg_pakningsforslag(eksakt_mal=...).

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
            handleliste.append(_rad_naar_kjop_trengs(
                rad, malt_db, humle_db, gjaer_db, butikk_nokkel,
                recipe=recipe, maltform=maltform, malt_prioritet=malt_prioritet,
                eksakt_mal_knust=eksakt_mal_knust))

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
