import datetime
import math
from urllib.parse import urlparse
from modules.calculations import beregn_total_ibu
from modules.equipment import last_equipment
from modules.i18n import SPRAK_DEFAULT, t
from modules.recipe import resolve_fermentation_temp_target_c
from modules.process_profiles import (
    NO_SPARGE, beregn_dekoksjon_uttak, beregn_reiterated_mash,
    sjekk_utstyrsbegrensninger,
)

# ── Brewing additions ─────────────────────────────────────────────────────────
# fase: "koking" = kettle addition; "gjæring" = fermentation addition
TILSETNINGER = {
    "whirlfloc": {
        "navn":       "Whirlfloc",
        "dose":       "½ tablett per 20 L",
        "timing":     "15 min til kok slutt",
        "timing_min": 15,
        "fase":       "koking",
        "note":       "Klaringsmiddel. Fremmer proteinagglutinasjon og klart øl.",
    },
    "irish_moss": {
        "navn":       "Irish Moss",
        "dose":       "1 ts per 20 L",
        "timing":     "15 min til kok slutt",
        "timing_min": 15,
        "fase":       "koking",
        "note":       "Naturlig klaringsmiddel. Rehydrer i kaldt vann i 20 min.",
    },
    "fermaid_o": {
        "navn":       "Fermaid-O",
        "dose":       "0.25 g / L",
        "timing":     "Gjæringsstart (0–24 t)",
        "timing_min": None,
        "fase":       "gjæring",
        "note":       "Organisk gjærnæring. Tilsett ved pitching eller tidlig gjæring.",
    },
    "yeast_nutrient": {
        "navn":       "Gjærnæring",
        "dose":       "0.5 g / L",
        "timing":     "15 min til kok slutt",
        "timing_min": 15,
        "fase":       "koking",
        "note":       "Gir gjæren nitrogen og mikronæringsstoffer for frisk gjæring.",
    },
}

# Fermentation temperature ranges by gjaertype (Norwegian labels)
_TEMP = {
    "ale":                  (18, 22),
    "belgisk ale":          (20, 26),
    "hvetegjær":            (18, 22),
    "lager":                (8,  12),
    "kveik":                (30, 40),
    "saison":               (22, 26),
    "kondisjoneringsgjær":  (18, 22),
    "spesialgjær":          (18, 22),
    "wild/brett-lignende":  (18, 24),
}



_FERMTEMP_BETYDNING = "ideal_fermentation_range"
_FERMTEMP_CLAIM_TYPE = "documented_fact"
_FERMTEMP_PRODUSENT_KILDETYPER = ("manufacturer_product_page", "manufacturer_datasheet")


def _kilde_vert(ref):
    """Vertsnavn fra en http(s)-kildehenvisning, ellers "". Ren parsing — ingen
    nettverkskall — og fanger parserfeil (f.eks. «https://[»)."""
    if not isinstance(ref, str):
        return ""
    try:
        deler = urlparse(ref)
        if deler.scheme not in ("http", "https"):
            return ""
        return deler.hostname or ""
    except ValueError:
        return ""


def _verifisert_tidspunkt(verdi):
    """Hele verified_at-verdien må være et ISO 8601-tidspunkt MED tidssone
    (CORE_STATUS_PROVENANCE: verified_at er et timestamp). Returnerer
    datetime eller None."""
    if not isinstance(verdi, str):
        return None
    try:
        tidspunkt = datetime.datetime.fromisoformat(verdi)
    except ValueError:
        return None
    return tidspunkt if tidspunkt.tzinfo is not None else None


def _gyldig_produsent_fermenteringstemp(ft):
    """True bare når `fermenteringstemp` oppfyller HELE beviskravet (se
    docs/MASTER_DATA_FLOW.md): endelige tall med min_c < max_c, betydning
    «ideal_fermentation_range», claim_type «documented_fact», produsentkildetype,
    http(s)-kildehenvisning med brukbart vertsnavn og et fullt ISO 8601-
    tidspunkt med tidssone i verified_at. Mangler eller
    avviker noe, påstås ikke «produsentens ideelle område»."""
    if not isinstance(ft, dict):
        return False
    lo = resolve_fermentation_temp_target_c(ft.get("min_c"))
    hi = resolve_fermentation_temp_target_c(ft.get("max_c"))
    if lo is None or hi is None or not lo < hi:
        return False
    if ft.get("betydning") != _FERMTEMP_BETYDNING or ft.get("claim_type") != _FERMTEMP_CLAIM_TYPE:
        return False
    if ft.get("source_type") not in _FERMTEMP_PRODUSENT_KILDETYPER:
        return False
    if not _kilde_vert(ft.get("source_ref")):
        return False
    return _verifisert_tidspunkt(ft.get("verified_at")) is not None


def _gjaer_fermenteringstemp(gjaer_info, gjaer_key):
    """Fermenteringstemperaturområde med eksplisitt opphav.

    Dokumentert produsentdata (masterdata-feltet `fermenteringstemp` på selve
    gjærstammen) går foran, men bare når beviskravet i
    _gyldig_produsent_fermenteringstemp() er oppfylt. Ellers brukes den
    generelle kategoriveiledningen i _TEMP, merket som det — den gjelder ikke
    den valgte stammen. Bryggerens egen planlagte temperatur
    (recipe["fermentation_temp_target_c"]) er et helt separat tall og
    berøres aldri her."""
    ft = (gjaer_info or {}).get("fermenteringstemp")
    if _gyldig_produsent_fermenteringstemp(ft):
        return {
            "temp_min": ft["min_c"],
            "temp_maks": ft["max_c"],
            "temp_kilde": "produsent",
            "temp_kilde_ref": ft["source_ref"],
            "temp_kilde_dato": _verifisert_tidspunkt(ft["verified_at"]).date().isoformat(),
        }
    temp_min, temp_maks = _TEMP.get(gjaer_key, (18, 22))
    return {
        "temp_min": temp_min,
        "temp_maks": temp_maks,
        "temp_kilde": "generell_kategori",
        "temp_kilde_ref": None,
        "temp_kilde_dato": None,
    }


def fermenteringstemp_linjer(plan, planlagt_c=None, sprak=SPRAK_DEFAULT):
    """Tekstlinjer for gjæringstemperatur, felles for appens bryggedagspanel
    og det eksporterte bryggedagsarket, slik at de ikke kan komme i utakt.
    Skiller dokumentert produsentdata, generell kategoriveiledning og
    bryggerens egen planlagte temperatur. Teksten slås opp i modules/i18n.py
    for `sprak` (NO er standard)."""
    def _tall(v):
        return f"{v:g}"
    omraade = f"{_tall(plan['temp_min'])}–{_tall(plan['temp_maks'])}°C"
    if plan.get("temp_kilde") == "produsent":
        kilde = _kilde_vert(plan.get("temp_kilde_ref")).removeprefix("www.")
        detaljer = ", ".join(x for x in (
            t("bryggedag.gjaer_temp.kilde", sprak, kilde=kilde) if kilde else "",
            t("bryggedag.gjaer_temp.kontrollert", sprak, dato=plan["temp_kilde_dato"])
            if plan.get("temp_kilde_dato") else "",
        ) if x)
        linjer = [t("bryggedag.gjaer_temp.produsent", sprak, omraade=omraade)
                  + (f" ({detaljer})" if detaljer else "")]
    else:
        linjer = [t("bryggedag.gjaer_temp.generell", sprak, omraade=omraade)]
    planlagt = resolve_fermentation_temp_target_c(planlagt_c)
    if planlagt is not None:
        linjer.append(t("bryggedag.gjaer_temp.planlagt", sprak, temp=_tall(planlagt)))
    return linjer


def bryggedag_noter(plan, sprak=SPRAK_DEFAULT):
    """Gjærnotene i valgt språk for panel og ark. Bare notene som har en
    i18n-nøkkel i plan["noter_nokler"] (så langt lagernoten, #546) oversettes;
    øvrige noter returneres uendret (eldre språkgjeld, se #548)."""
    nokler = plan.get("noter_nokler") or []
    return [
        t(nokler[i], sprak) if i < len(nokler) and nokler[i] else note
        for i, note in enumerate(plan["noter"])
    ]


# Pitching rate in million cells / mL / °P
_PITCH_RATE = {
    "lager": 1.5,
    "kveik": 0.25,
}
_PITCH_RATE_DEFAULT = 0.75

_DRY_YEAST_BILLION_CELLS = 200  # per 11g pack


def _plato(og):
    return (og - 1.0) * 250


def beregn_vann(total_korn_kg, batch_volum_l, koketid_min, eq, sparge_method=None):
    """
    `sparge_method` (fra en prosessprofil, se modules/process_profiles.py) kan
    påvirke FORDELINGEN mellom meske- og skyllevann uten å endre totalt
    vannbehov (pre-boil-volumet, som følger av mål-batchvolum og koketid,
    er uavhengig av skyllemetode). Ved "no_sparge" meskes alt vannet inn i
    ett steg og det skylles ikke — meskevannet dekker da hele pre-boil-
    behovet direkte (så lenge det er praktisk mulig i karet; se
    sjekk_utstyrsbegrensninger for kapasitetsvarsel).
    """
    absorpsjon    = total_korn_kg * eq["grain_absorption_l_per_kg"]
    pre_boil      = batch_volum_l + eq["dead_space_l"] + eq["boil_off_l_per_hour"] * (koketid_min / 60)

    if sparge_method == NO_SPARGE:
        mash_vann = round(pre_boil + absorpsjon, 1)
        sparge    = 0.0
    else:
        mash_vann     = round(total_korn_kg * eq["mash_ratio_l_per_kg"], 1)
        wort_fra_mask = mash_vann - absorpsjon
        sparge        = max(0.0, pre_boil - wort_fra_mask)

    return {
        "mash_vann_l":   mash_vann,
        "sparge_vann_l": round(sparge, 1),
        "pre_boil_l":    round(pre_boil, 1),
    }


def _koketid(malt_ider, default_min):
    """90 min if any pilsner base malt present (drives off DMS precursor)."""
    return 90 if any("pilsner" in m.lower() or m in ("best_pils", "belgian_pils") for m in malt_ider) else default_min


def _gjær_type_key(gjaer_info):
    return gjaer_info.get("gjaertype", "Ale").lower()


def _bygg_humle_entry(h, humle_database, og, volum, total_koketid_min):
    h_info = humle_database.get(h["id"]) or {}
    navn   = h_info.get("display_name", h["id"])
    tid, gram = h["tid"], h["gram"]

    # Delegerer selve Tinseth-/alfa-aritmetikken til den autoritative
    # modules.calculations.beregn_total_ibu() (samme funksjon recipe-/
    # planleggingsstien bruker for ctx["ibu"]) i stedet for å regne den ut
    # på nytt lokalt her -- én tilsetning om gangen, med prosess-justert
    # tid, slik at bl.a. None-basert alfa-fallback (eksplisitt alfa=0.0
    # respekteres) alltid er identisk med recipe-stien.
    def _ibu_for_tid(effektiv_tid):
        return round(beregn_total_ibu(
            [{"navn": h["id"], "gram": gram, "tid": effektiv_tid}],
            {h["id"]: h_info},
            volum, og,
        ), 1)

    # En humle kan IKKE fysisk ha lengre egen koketid enn selve kokens
    # totale lengde -- ei heller "tilsettes ved kokestart" (0 min etter
    # start) OG samtidig få full IBU-utnyttelse for sin fulle, stipulerte
    # tid. `tid_over_koketid` fanger nettopp dette umulige tilfellet (en
    # 90 min-humle valgt inn i en 60 min total kok, f.eks. etter at
    # brukeren har byttet prosessprofil eller redusert koketiden uten å
    # revidere humlelisten). `ibu_bidrag` beholder brukerens OPPGITTE tid
    # uendret (dette er "oppskriftens planlagte" bidrag -- samme tall som
    # modules/calculations.py::beregn_total_ibu() uten koketid-grense);
    # `ibu_bidrag_faktisk` bruker i stedet tiden humlen FAKTISK kan få i
    # DENNE prosessens kok (aldri mer enn total_koketid_min).
    tid_over_koketid   = tid > total_koketid_min
    tid_faktisk         = min(tid, total_koketid_min)
    ibu_bidrag          = _ibu_for_tid(tid)
    ibu_bidrag_faktisk  = _ibu_for_tid(tid_faktisk) if tid_over_koketid else ibu_bidrag
    # `tid` er humlens EGEN koketid (min igjen av koken når den tilsettes),
    # ikke nødvendigvis lik total koketid — skiller mellom de to slik at en
    # 60 min-humle i en 90 min total kok korrekt vises som tilsatt 30 min
    # etter kokestart, ikke ved kokestart.
    tilsatt_etter_min = max(0, total_koketid_min - tid)
    return {
        "navn": navn, "gram": gram, "tid": tid, "ibu_bidrag": ibu_bidrag,
        "tilsatt_etter_min": tilsatt_etter_min,
        "tid_over_koketid": tid_over_koketid,
        "ibu_bidrag_faktisk": ibu_bidrag_faktisk,
    }


def beregn_pakker(og, batch_volum_l, gjaer_type_key):
    plato      = _plato(og)
    pitch_rate = _PITCH_RATE.get(gjaer_type_key, _PITCH_RATE_DEFAULT)
    celler_mrd = pitch_rate * batch_volum_l * plato
    return max(1, math.ceil(celler_mrd / _DRY_YEAST_BILLION_CELLS))


def _beregn_maks_gravitetspoeng(malt_valg, malt_database):
    """Total theoretical gravity points — same formula basis as beregn_og()."""
    return sum(
        m.get("mengde", 0.0) * ((malt_database.get(m["id"]) or {}).get("potensiale", 1.036) - 1.0) * 1000
        for m in malt_valg
    )


def beregn_effektivitet(malt_valg, malt_database, pre_boil_sg, pre_boil_vol, og, batch_vol):
    """
    Mash efficiency and brewhouse efficiency as fractions (0–1).
    Uses the same 8.3454 unit factor as beregn_og() so the numbers are consistent:
    if the brewer hits the planned OG at the planned volume, BH efficiency == designed efficiency.
    """
    poeng = _beregn_maks_gravitetspoeng(malt_valg, malt_database or {})
    if poeng <= 0:
        return {"mash_eff": 0.0, "brewhouse_eff": 0.0}
    divisor = poeng * 8.3454
    mash_eff = (
        (pre_boil_sg - 1.0) * pre_boil_vol * 1000 / divisor
        if pre_boil_vol > 0 and pre_boil_sg > 1.001 else 0.0
    )
    bh_eff = (
        (og - 1.0) * batch_vol * 1000 / divisor
        if batch_vol > 0 and og > 1.001 else 0.0
    )
    return {"mash_eff": mash_eff, "brewhouse_eff": bh_eff}


def beregn_post_boil_og(pre_boil_sg, pre_boil_vol, post_boil_vol):
    """Estimate post-boil OG by concentrating the pre-boil gravity."""
    if post_boil_vol <= 0 or pre_boil_sg <= 1.000:
        return 1.000
    return round(1.0 + (pre_boil_sg - 1.0) * pre_boil_vol / post_boil_vol, 4)


def _maskeplan_fra_profil(process_profile):
    """Konverterer en prosessprofils mash_steps (temperatur/varighet/stegtype/
    kommentar) til den interne maskeplan-formen (temp_c/varighet_min/label)
    som bryggedagsark-malene allerede vet hvordan de skal vise fram."""
    return [
        {
            "temp_c": steg["temperatur"],
            "varighet_min": steg["varighet"],
            "label": steg.get("kommentar") or steg.get("stegtype", "").replace("_", " ").capitalize(),
        }
        for steg in process_profile["mash_steps"]
    ]


def _dekoksjonsplan(process_profile, mash_vann_l):
    """Løser ut dekoksjons-uttaket: bruker brukerens eget tall hvis satt,
    ellers foreslår appen et volum ut fra beregn_dekoksjon_uttak()."""
    steg_liste = process_profile.get("decoction_steps") or []
    if not steg_liste:
        return None
    steg = steg_liste[0]
    uttak = steg.get("uttak_liter")
    if uttak is None:
        uttak = beregn_dekoksjon_uttak(mash_vann_l, steg["fra_temp_c"], steg["til_temp_c"])
    return {
        "uttak_liter": uttak,
        "fra_temp_c": steg["fra_temp_c"],
        "til_temp_c": steg["til_temp_c"],
        "koketid_min": steg["koketid_min"],
        "kommentar": steg.get("kommentar", ""),
    }


def lag_brewday_plan(malt_valg, humle_valg, gjaer_id, gjaer_info, og, batch_volum_l, humle_database,
                      malt_database=None, tilsetninger_valgt=None, process_profile=None):
    eq            = last_equipment()
    total_korn_kg = sum(m["mengde"] for m in malt_valg)
    malt_ider     = {m["id"] for m in malt_valg}
    gjaer_key     = _gjær_type_key(gjaer_info)

    # Uten valgt prosessprofil beholdes den opprinnelige oppførselen
    # uendret (60/90 min ut fra maltbase, enkel infusjon 66/78°C) — dette
    # er kun en UTVIDELSE av standardoppførselen, ikke en erstatning.
    if process_profile:
        koketid   = process_profile.get("boil_minutes") or _koketid(malt_ider, eq["default_boil_time_min"])
        maskeplan = _maskeplan_fra_profil(process_profile)
    else:
        koketid   = _koketid(malt_ider, eq["default_boil_time_min"])
        maskeplan = [
            {"temp_c": 66, "varighet_min": 60, "label": "Mashing"},
            {"temp_c": 78, "varighet_min": 5,  "label": "Mashout"},
        ]

    sparge_method        = (process_profile or {}).get("sparge_method")
    vann                 = beregn_vann(total_korn_kg, batch_volum_l, koketid, eq, sparge_method=sparge_method)
    estimert_koketap_l   = round(eq["boil_off_l_per_hour"] * (koketid / 60), 1)
    estimert_post_boil_l = round(vann["pre_boil_l"] - estimert_koketap_l, 1)
    brewzilla_varsel     = vann["pre_boil_l"] > 30.0

    dekoksjon = _dekoksjonsplan(process_profile, vann["mash_vann_l"]) if process_profile else None

    reiterated_flyt = None
    if process_profile and process_profile.get("reiterated_mash"):
        andel = process_profile["reiterated_mash"].get("mesk_1_andel", 0.5)
        reiterated_flyt = beregn_reiterated_mash(total_korn_kg, andel, eq)

    utstyrsvarsler = (
        sjekk_utstyrsbegrensninger(process_profile, total_korn_kg, eq)
        if process_profile else []
    )

    malt_liste = [
        {
            "navn":   ((malt_database or {}).get(m["id"]) or {}).get("display_name", m["id"]),
            "mengde": m["mengde"],
        }
        for m in sorted(malt_valg, key=lambda x: x["mengde"], reverse=True)
    ]

    humleplan = sorted(
        [_bygg_humle_entry(h, humle_database, og, batch_volum_l, koketid) for h in humle_valg],
        key=lambda x: x["tid"],
        reverse=True,
    )
    # Humle med lengre EGEN koketid enn selve kokens totale lengde er
    # fysisk umulig (den kan ikke få mer utnyttelse enn koken faktisk
    # varer) -- se _bygg_humle_entry sin "tid_over_koketid"/
    # "ibu_bidrag_faktisk". Samlet opp her slik at UI-laget
    # (ui/process_panel.py og ui/brewday_panel.py) kan varsle uten selv å
    # regne ut noe.
    humle_over_koketid  = [h for h in humleplan if h["tid_over_koketid"]]
    # Summeres via beregn_total_ibu() på RÅ (u-avrundede) bidrag for hele
    # humlelisten samtidig, i stedet for å summere de allerede avrundede
    # per-tilsetning-verdiene i humleplan over -- samme rekkefølge
    # (summer først, avrund til slutt) som den autoritative recipe-/
    # planleggingsstien (modules/recipe_context.py), slik at planlagt
    # Brewday-IBU er tallidentisk med oppskriftens ctx["ibu"] når det ikke
    # foreligger noen prosessbegrensning.
    _humle_data_by_id = {h["id"]: (humle_database.get(h["id"]) or {}) for h in humle_valg}
    _humle_calc_planlagt = [{"navn": h["id"], "gram": h["gram"], "tid": h["tid"]} for h in humle_valg]
    _humle_calc_faktisk  = [{"navn": h["id"], "gram": h["gram"], "tid": min(h["tid"], koketid)} for h in humle_valg]
    ibu_planlagt         = round(beregn_total_ibu(_humle_calc_planlagt, _humle_data_by_id, batch_volum_l, og), 1)
    ibu_faktisk_prosess  = round(beregn_total_ibu(_humle_calc_faktisk, _humle_data_by_id, batch_volum_l, og), 1)

    pakker         = beregn_pakker(og, batch_volum_l, gjaer_key)
    ferm_temp      = _gjaer_fermenteringstemp(gjaer_info, gjaer_key)

    noter = []
    noter_nokler = []
    if gjaer_key == "lager":
        noter.append("Lagergjær — fermenterer kaldere enn ale. Bruk dobbel pitching rate.")
        noter_nokler.append("bryggedag.gjaer_note.lager")
    elif gjaer_key == "kveik":
        noter.append("Kveik — tåler høy temperatur (30–40°C). Underpitching er OK.")
    elif gjaer_key == "saison":
        noter.append("Saison — start lavt (20°C), la temperaturen stige gradvis til 26°C.")
    elif gjaer_key == "belgisk ale":
        noter.append("Belgisk gjær — temperatur påvirker esterkarakter sterkt. Start lavt for ryddigere profil.")

    valgte_tilsetninger = [
        TILSETNINGER[k] for k in (tilsetninger_valgt or [])
        if k in TILSETNINGER
    ]

    return {
        "total_korn_kg":        round(total_korn_kg, 2),
        "malt_liste":           malt_liste,
        "koketid_min":          koketid,
        "vann":                 vann,
        "estimert_koketap_l":   estimert_koketap_l,
        "estimert_post_boil_l": estimert_post_boil_l,
        "brewzilla_varsel":     brewzilla_varsel,
        "maskeplan":            maskeplan,
        "humleplan":            humleplan,
        "humle_over_koketid":   humle_over_koketid,
        "ibu_planlagt":         ibu_planlagt,
        "ibu_faktisk_prosess":  ibu_faktisk_prosess,
        "gjaer_navn":           gjaer_info.get("display_name", gjaer_id),
        "pakker":               pakker,
        "temp_min":             ferm_temp["temp_min"],
        "temp_maks":            ferm_temp["temp_maks"],
        "temp_kilde":           ferm_temp["temp_kilde"],
        "temp_kilde_ref":       ferm_temp["temp_kilde_ref"],
        "temp_kilde_dato":      ferm_temp["temp_kilde_dato"],
        "noter":                noter,
        "noter_nokler":         noter_nokler,
        "er_lager":             gjaer_key == "lager",
        "tilsetninger":         valgte_tilsetninger,
        "prosess_profil":       process_profile,
        "dekoksjon":            dekoksjon,
        "reiterated_mash_flyt": reiterated_flyt,
        "utstyrsvarsler":       utstyrsvarsler,
    }
