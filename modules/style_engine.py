# modules/style_engine.py

_ENGLISH_ALE_MALTS  = {"fawcett_maris_otter", "pale_ale_malt", "golden_promise"}
_ENGLISH_ALE_HOPS   = {"east_kent_goldings", "fuggles", "goldings"}
_ENGLISH_ALE_YEASTS = {"safale_s04", "wlp002", "wlp007", "wyeast_1318", "lalbrew_london"}
_DARK_MALT_IDS = {
    "pale_chocolate", "roasted_barley", "carafa_special_1",
    "carafa_special_2", "carafa_special_3", "chocolate_wheat", "dark_wheat",
}

_HAZY_HOPS   = {"citra", "mosaic", "galaxy", "ekuanot", "sabro", "el_dorado", "azacca"}
_HAZY_MALTS  = {"oat_malt", "flaked_oats", "flaked_wheat", "wheat_malt"}

_BELGIAN_YEASTS = {
    "wlp500", "wlp510", "wlp530", "wlp545",
    "wyeast_3787", "wyeast_3522", "wyeast_3724",
    "safbrew_t58", "safale_wb06",
}

_STOUT_MALTS = {"roasted_barley", "black"}

_WEST_COAST_HOPS   = {"centennial", "chinook", "simcoe", "cascade", "amarillo", "columbus"}
_WEST_COAST_YEASTS = {"safale_us_05", "wlp001", "wyeast_1056"}

_LAGER_YEASTS = {
    "saflager_w3470", "saflager_s23", "saflager_s189", "saflager_e30",
    "lalbrew_diamond_lager", "lalbrew_nova_lager",
    "bohemian_lager_m84", "california_lager_m54", "bavarian_lager_m76",
    "wlp_800", "wlp_802", "wlp_810", "wlp_820", "wlp_830",
    "wlp_833", "wlp_838", "wlp_850", "wlp_940",
    "versa_lager_m24",
}

_ENGLISH_STYLES_BASE = {"English Bitter", "Best Bitter", "ESB / Strong Bitter"}
_ENGLISH_STYLES_DARK = {"Robust Porter"}
_LAGER_BOCK_STYLES   = {
    "Tysk Pilsner", "Tsjekkisk Pilsner", "Münchener Dunkel",
    "Heller Bock (Mai-Bock)", "Dunkles Bock", "Klassisk Røykøl (Rauchbier)",
}
_HAZY_STYLES    = {"Hazy IPA / NEIPA"}
_BELGIAN_STYLES = {"Belgisk Witbier", "Belgisk Tripel", "Belgisk Dubbel"}
_STOUT_STYLES   = {"Irsk Tørr Stout", "Oatmeal Stout", "Robust Porter"}

_ENGLISH_ALE_BOOST  = 20
_LAGER_BOCK_PENALTY = 20
_SIGNATURE_BOOST    = 20
_SIGNATURE_PENALTY  = 15


def detect_recipe_signatures(recipe):
    malts = {m["id"] for m in recipe.get("malts", [])}
    hops  = {h["id"] for h in recipe.get("hops",  [])}
    yeast = recipe.get("yeast", "")

    english_ale = (
        bool(malts & _ENGLISH_ALE_MALTS) or
        bool(hops  & _ENGLISH_ALE_HOPS)  or
        yeast in _ENGLISH_ALE_YEASTS
    )

    # Hazy: tropiske humler + myk malt (oats/wheat) begge må være til stede
    hazy = bool(hops & _HAZY_HOPS) and bool(malts & _HAZY_MALTS)

    belgian = yeast in _BELGIAN_YEASTS

    # Stout: krever minst 150 g roasted barley eller black malt
    stout = any(
        m["id"] in _STOUT_MALTS and m.get("mengde", 0) >= 0.15
        for m in recipe.get("malts", [])
    )

    west_coast = bool(hops & _WEST_COAST_HOPS) and yeast in _WEST_COAST_YEASTS

    lager = yeast in _LAGER_YEASTS

    return {
        "english_ale": english_ale,
        "dark_malt":   bool(malts & _DARK_MALT_IDS),
        "hazy":        hazy,
        "belgian":     belgian,
        "stout":       stout,
        "west_coast":  west_coast,
        "lager":       lager,
    }


def analyser_stil_og_balanse(recipe):
    """
    Komplett BJCP-stilmatching og skreddersydd kategoriranking for Kvernhaug Brygghus.
    """
    stats = recipe["stats"]
    og = stats["og"]
    fg = stats["fg"]
    ibu = stats["ibu"]
    ebc = stats["ebc"]
    abv = stats["abv"]
    flavor = recipe["flavor_profile"]

    # 1. BEREGN BITTERHETSINDEKS (BU:GU)
    gravity_points = (og - 1) * 1000
    bu_gu = ibu / gravity_points if gravity_points > 0 else 0.0

    # 2. BJCP-BIBLIOTEKET
    bjcp_stiler = {
        "Tysk Pilsner": {
            "prio": 1, "kat_navn": "🍺 Pilsner & Lys Lager",
            "og": (1.044, 1.050), "fg": (1.008, 1.013), "abv": (4.4, 5.2), "ibu": (22, 40), "ebc": (4, 8),
            "smak_krav": {"Brød": 4, "Sitrus": 1, "Bitterhet": 4},
            "beskrivelse": "Ren, sprø, tørr og elegant tysk lagerøl med en markant bitter finish."
        },
        "Tsjekkisk Pilsner": {
            "prio": 1, "kat_navn": "🍺 Pilsner & Lys Lager",
            "og": (1.044, 1.056), "fg": (1.013, 1.017), "abv": (4.2, 5.8), "ibu": (30, 45), "ebc": (6, 14),
            "smak_krav": {"Brød": 4, "Maltfylde": 4, "Bitterhet": 4},
            "beskrivelse": "Rundere pilsnerstil med dypere maltsødme og rik, edel humlebitterhet."
        },
        "Münchener Dunkel": {
            "prio": 1, "kat_navn": "🍺 Pilsner & Lys Lager",
            "og": (1.048, 1.056), "fg": (1.010, 1.016), "abv": (4.5, 5.6), "ibu": (18, 28), "ebc": (28, 56),
            "smak_krav": {"Brød": 5, "Toast": 4, "Karamell": 3, "Nøtter": 2},
            "beskrivelse": "Klassisk mørk tysk lager med fokus på rike brødskorpe-toner, uten brentsmak."
        },
        "Heller Bock (Mai-Bock)": {
            "prio": 2, "kat_navn": "🐐 Bock-øl",
            "og": (1.064, 1.072), "fg": (1.011, 1.018), "abv": (6.3, 7.4), "ibu": (23, 35), "ebc": (12, 22),
            "smak_krav": {"Maltfylde": 6, "Brød": 5, "Toast": 2, "Bitterhet": 2},
            "beskrivelse": "Et kraftig, lyst bock-øl som kombinerer solid alkoholstyrke med rik maltsmak."
        },
        "Dunkles Bock": {
            "prio": 2, "kat_navn": "🐐 Bock-øl",
            "og": (1.064, 1.072), "fg": (1.013, 1.019), "abv": (6.3, 7.2), "ibu": (20, 27), "ebc": (44, 60),
            "smak_krav": {"Karamell": 6, "Maltfylde": 7, "Toast": 4, "Nøtter": 3},
            "beskrivelse": "Et mørkt tysk tradisjonsøl med store smaker av karamell og knekk."
        },
        "Tysk Weissbier / Hefeweizen": {
            "prio": 3, "kat_navn": "🌾 Tyske Hveteøl",
            "og": (1.044, 1.052), "fg": (1.010, 1.014), "abv": (4.3, 5.6), "ibu": (8, 15), "ebc": (4, 12),
            "smak_krav": {"Fruktighet": 6, "Krydder": 3, "Brød": 4},
            "beskrivelse": "Et friskt, kremet og lyst hveteøl preget av gjærens intense noter av banan og nellik."
        },
        "Robust Porter": {
            "prio": 4, "kat_navn": "☕ Porter, Stout & Røykøl",
            "og": (1.048, 1.065), "fg": (1.012, 1.016), "abv": (4.8, 6.5), "ibu": (25, 50), "ebc": (60, 100),
            "smak_krav": {"Sjokolade": 5, "Kaffe": 3, "Toast": 4, "Maltfylde": 4},
            "beskrivelse": "Et moderat mørkt øl preget av røstet korn, kakao og rund sjokoladesmak."
        },
        "Imperial Porter / Baltic Porter": {
            "prio": 4, "kat_navn": "☕ Porter, Stout & Røykøl",
            "og": (1.060, 1.090), "fg": (1.016, 1.024), "abv": (7.0, 9.5), "ibu": (20, 40), "ebc": (60, 120),
            "smak_krav": {"Maltfylde": 8, "Karamell": 6, "Sjokolade": 7, "Nøtter": 4, "Toast": 4},
            "beskrivelse": "Et mektig, mørkt og fløyelsmykt luksusøl. Enorm maltsødme med dype smaker av lakris, mørk sjokolade og tørket frukt."
        },
        "Irsk Tørr Stout": {
            "prio": 4, "kat_navn": "☕ Porter, Stout & Røykøl",
            "og": (1.036, 1.044), "fg": (1.007, 1.011), "abv": (4.0, 4.5), "ibu": (25, 45), "ebc": (80, 120),
            "smak_krav": {"Kaffe": 7, "Sjokolade": 3, "Toast": 5, "Bitterhet": 4},
            "beskrivelse": "Helt sort, kremet øl preget av intens espresso-smak fra røstet bygg."
        },
        "Oatmeal Stout": {
            "prio": 4, "kat_navn": "☕ Porter, Stout & Røykøl",
            "og": (1.048, 1.065), "fg": (1.010, 1.018), "abv": (4.2, 5.9), "ibu": (20, 40), "ebc": (64, 100),
            "smak_krav": {"Sjokolade": 6, "Kaffe": 4, "Maltfylde": 6, "Nøtter": 3},
            "beskrivelse": "Kremet og fyldig stout med myk munnfølelse fra havre. Sjokolade og mokka i front, uten den skarpe brenttonen."
        },
        "Klassisk Røykøl (Rauchbier)": {
            "prio": 4, "kat_navn": "☕ Porter, Stout & Røykøl",
            "og": (1.050, 1.058), "fg": (1.012, 1.016), "abv": (4.8, 6.0), "ibu": (20, 30), "ebc": (24, 44),
            "smak_krav": {"Røyk": 7, "Brød": 4, "Toast": 4, "Maltfylde": 5},
            "beskrivelse": "Tysk lagerstil der malten tørkes over åpen bøkebål. Smaker av røkt kjøtt."
        },
        "Tradisjonelt Norsk Gårdsøl / Kveik": {
            "prio": 5, "kat_navn": "🇧🇻 Tradisjonelt Norsk Gårdsøl",
            "og": (1.048, 1.060), "fg": (1.010, 1.016), "abv": (4.5, 6.5), "ibu": (15, 30), "ebc": (10, 25),
            "smak_krav": {"Fruktighet": 6, "Sitrus": 5, "Maltfylde": 4},
            "beskrivelse": "Historisk norsk ølstil brygget på kveik-gjær. Preget av saftig appelsinsmak."
        },
        "Tradisjonelt Norsk Juleøl": {
            "prio": 6, "kat_navn": "🎄 Juleøl",
            "og": (1.060, 1.075), "fg": (1.014, 1.022), "abv": (6.0, 8.5), "ibu": (25, 35), "ebc": (40, 75),
            "smak_krav": {"Karamell": 7, "Maltfylde": 7, "Krydder": 2, "Toast": 4, "Nøtter": 3},
            "beskrivelse": "Klassisk mørkt høytidsøl. Proppfullt av sødmefull karamell og mørk sirup."
        },
        "Belgisk Witbier": {
            "prio": 7, "kat_navn": "🇧🇪 Belgisk Gårds- & Klosterøl",
            "og": (1.044, 1.052), "fg": (1.008, 1.012), "abv": (4.5, 5.5), "ibu": (10, 20), "ebc": (4, 8),
            "smak_krav": {"Fruktighet": 4, "Krydder": 4, "Brød": 4},
            "beskrivelse": "Forfriskende belgisk hveteøl, krydret med korianderfrø og appelsinskall."
        },
        "Belgisk Dubbel": {
            "prio": 7, "kat_navn": "🇧🇪 Belgisk Gårds- & Klosterøl",
            "og": (1.062, 1.075), "fg": (1.010, 1.018), "abv": (6.0, 7.6), "ibu": (15, 25), "ebc": (22, 44),
            "smak_krav": {"Karamell": 6, "Maltfylde": 6, "Fruktighet": 5, "Krydder": 3},
            "beskrivelse": "Rikt klosterøl med dype karamell- og tørket-frukt-toner (svisker, rosiner). Belgisk gjær gir mye liv."
        },
        "Belgisk Tripel": {
            "prio": 7, "kat_navn": "🇧🇪 Belgisk Gårds- & Klosterøl",
            "og": (1.075, 1.085), "fg": (1.008, 1.014), "abv": (7.5, 9.5), "ibu": (20, 40), "ebc": (9, 14),
            "smak_krav": {"Krydder": 5, "Fruktighet": 6, "Bitterhet": 3},
            "beskrivelse": "Et lyst, sterkt klosterøl. Varmende alkohol med toner av pepper, nellik og pære."
        },
        "Hazy IPA / NEIPA": {
            "prio": 8, "kat_navn": "🍋 Humledominert IPA",
            "og": (1.060, 1.085), "fg": (1.010, 1.016), "abv": (6.0, 8.5), "ibu": (40, 70), "ebc": (6, 18),
            "smak_krav": {"Tropisk": 7, "Fruktighet": 6, "Sitrus": 4},
            "beskrivelse": "Saftig, tropisk og tåkete IPA med myk munnfølelse fra havre/hvete. Lav opplevd bitterhet tross høye IBU."
        },
        "Amerikansk IPA": {
            "prio": 8, "kat_navn": "🍋 Humledominert IPA",
            "og": (1.056, 1.070), "fg": (1.008, 1.014), "abv": (5.5, 7.5), "ibu": (40, 70), "ebc": (12, 30),
            "smak_krav": {"Sitrus": 6, "Tropisk": 6, "Fruktighet": 4},
            "beskrivelse": "Moderne, overhumlet stil der maltkarakteren skyves helt til side."
        },
        "English Bitter": {
            "prio": 9, "kat_navn": "🇬🇧 Engelsk Ale",
            "og": (1.030, 1.039), "fg": (1.007, 1.011), "abv": (3.2, 3.8), "ibu": (25, 35), "ebc": (12, 36),
            "smak_krav": {"Brød": 4, "Maltfylde": 3, "Bitterhet": 3},
            "beskrivelse": "Lett, tørr britisk øl. Ren maltsødme balansert av fin jordlig humlebitterhet."
        },
        "Best Bitter": {
            "prio": 9, "kat_navn": "🇬🇧 Engelsk Ale",
            "og": (1.040, 1.048), "fg": (1.008, 1.012), "abv": (3.8, 4.6), "ibu": (25, 40), "ebc": (12, 32),
            "smak_krav": {"Brød": 4, "Maltfylde": 4, "Nøtter": 2, "Bitterhet": 3},
            "beskrivelse": "Klassisk britisk fatøl med god maltbalanse og jordlig EKG-karakter."
        },
        "ESB / Strong Bitter": {
            "prio": 9, "kat_navn": "🇬🇧 Engelsk Ale",
            "og": (1.048, 1.060), "fg": (1.010, 1.016), "abv": (4.6, 6.2), "ibu": (30, 50), "ebc": (12, 44),
            "smak_krav": {"Brød": 5, "Maltfylde": 5, "Nøtter": 2, "Bitterhet": 4},
            "beskrivelse": "Kraftig britisk bitter med rik maltsødme, nøtteaktige toner og markant bitterhet."
        },
        "English Dark Mild": {
            "prio": 9, "kat_navn": "🇬🇧 Engelsk Ale",
            "og": (1.030, 1.038), "fg": (1.008, 1.013), "abv": (3.0, 3.8), "ibu": (10, 25), "ebc": (24, 100),
            "smak_krav": {"Brød": 3, "Maltfylde": 3, "Karamell": 2},
            "beskrivelse": "En liten, mørk og søtlig britisk tradisjonsstil med mild malt- og karamellsmak."
        },
    }

    # 3. BJCP STYLE SCORING
    stil_matcher = []

    for stil_navn, krav in bjcp_stiler.items():
        score = 100.0
        mangler = []

        if og < krav["og"][0]:
            score -= (krav["og"][0] - og) * 400
            mangler.append(f"For lav sukkermengde (OG bør være over {krav['og'][0]:.3f})")
        elif og > krav["og"][1]:
            score -= (og - krav["og"][1]) * 400
            mangler.append(f"For høy sukkermengde (OG bør være under {krav['og'][1]:.3f})")

        if fg < krav["fg"][0]:
            score -= (krav["fg"][0] - fg) * 400
            mangler.append(f"Gjæret for langt ned (FG bør være over {krav['fg'][0]:.3f})")
        elif fg > krav["fg"][1]:
            score -= (fg - krav["fg"][1]) * 400
            mangler.append(f"For mye restsødme (FG bør være under {krav['fg'][1]:.3f})")

        if ibu < krav["ibu"][0]:
            score -= (krav["ibu"][0] - ibu) * 1.5
            mangler.append(f"Mangler bitterhet (Mangler {krav['ibu'][0] - ibu:.0f} IBU)")
        elif ibu > krav["ibu"][1]:
            score -= (ibu - krav["ibu"][1]) * 1.2
            mangler.append(f"For høy bitterhet ({ibu - krav['ibu'][1]:.0f} IBU for mye)")

        if ebc < krav["ebc"][0]:
            score -= (krav["ebc"][0] - ebc) * 0.8
            mangler.append("Ølet er for lyst for stilen")
        elif ebc > krav["ebc"][1]:
            score -= (ebc - krav["ebc"][1]) * 0.5
            mangler.append("Ølet er for mørkt for stilen")

        for smaks_navn, min_verdi in krav["smak_krav"].items():
            reell_verdi = flavor.get(smaks_navn, 0.0)
            if reell_verdi < min_verdi:
                score -= (min_verdi - reell_verdi) * 5
                mangler.append(f"Mangler sensorisk preg av *{smaks_navn.lower()}*")

        endelig_score = max(0, min(int(score), 100))

        stil_matcher.append({
            "stil": stil_navn, "score": endelig_score, "mangler": mangler,
            "beskrivelse": krav["beskrivelse"], "prio": krav["prio"], "kat_navn": krav["kat_navn"]
        })

    # 4. SIGNATURJUSTERING
    sigs = detect_recipe_signatures(recipe)

    for s in stil_matcher:
        stil = s["stil"]

        if sigs["english_ale"]:
            og_max = bjcp_stiler[stil]["og"][1]
            if og <= og_max + 0.020:
                if stil in _ENGLISH_STYLES_BASE:
                    s["score"] = min(100, s["score"] + _ENGLISH_ALE_BOOST)
                elif stil in _ENGLISH_STYLES_DARK and sigs["dark_malt"]:
                    s["score"] = min(100, s["score"] + _ENGLISH_ALE_BOOST)
            if stil in _LAGER_BOCK_STYLES:
                s["score"] = max(0, s["score"] - _LAGER_BOCK_PENALTY)

        if sigs["lager"]:
            if stil in _LAGER_BOCK_STYLES:
                s["score"] = min(100, s["score"] + _SIGNATURE_BOOST)

        if sigs["hazy"]:
            if stil in _HAZY_STYLES:
                s["score"] = min(100, s["score"] + _SIGNATURE_BOOST)
            elif stil in _LAGER_BOCK_STYLES:
                s["score"] = max(0, s["score"] - _SIGNATURE_PENALTY)

        if sigs["belgian"]:
            if stil in _BELGIAN_STYLES:
                s["score"] = min(100, s["score"] + _SIGNATURE_BOOST)
            elif stil in _ENGLISH_STYLES_BASE:
                s["score"] = max(0, s["score"] - _SIGNATURE_PENALTY)

        if sigs["stout"]:
            if stil in _STOUT_STYLES:
                s["score"] = min(100, s["score"] + _SIGNATURE_BOOST)

    stil_matcher = sorted(stil_matcher, key=lambda x: (x["prio"], -x["score"]))

    topp_match_reell = max(stil_matcher, key=lambda x: x["score"])
    dominant_stil = topp_match_reell["stil"] if topp_match_reell["score"] > 40 else "Kreativt Brygg"

    # 5. BALANSEANALYSE OG ADVARSLER
    balanse_notater, problemer = [], []

    if bu_gu > 0.85:
        balanse_notater.append("🔥 **Humledominert:** Bitterheten vil dominere kraftig over maltprofilen din.")
    elif bu_gu < 0.38:
        balanse_notater.append("🌾 **Maltdominert:** Lav bitterhet gjør at restsødmen fra kornene vil merkes godt.")
    else:
        balanse_notater.append("⚖️ **Harmonisk balansert:** Forholdet mellom sødme og bitterhet oppleves veldig balansert.")

    if fg >= 1.018 and abv < 6.0:
        problemer.append("⚠️ **Fare for tung sødme:** Høy FG betyr uforgjærbart sukker. Ølet kan bli klissete.")
    elif fg <= 1.006:
        balanse_notater.append("🍃 **Ekstremt tørt brygg:** Gjæren har spist opp nesten alt sukkeret.")

    if flavor.get("Kaffe", 0) > 6 and ebc > 80 and bu_gu > 0.8:
        problemer.append("☕ **Askeaktig finish:** Kombinasjonen av mørkt brentmalt og høy bitterhet kan skape en skarp ettersmak.")

    # Juice/sirup-fare: tropisk/frukt + høy restsødme + lav bitterhet
    if (flavor.get("Tropisk", 0) + flavor.get("Fruktighet", 0) > 8) and fg > 1.016 and ibu < 35:
        problemer.append("🧃 **Juice/sirup-fare:** Tropisk humle, høy restsødme og lav bitterhet kan gi et søtt, sirupaktig resultat.")

    # Røyk-konflikt: røykmalt og tropisk/sitrus slåss
    if flavor.get("Røyk", 0) > 4 and (flavor.get("Sitrus", 0) > 3 or flavor.get("Tropisk", 0) > 3):
        problemer.append("🔥 **Sensorisk konflikt:** Røykmalt og sitrus-/tropisk humle slåss mot hverandre — disse smaknuansene forsterker ikke hverandre.")

    # Belgisk gjær + aggressiv humle
    if sigs["belgian"] and (flavor.get("Tropisk", 0) + flavor.get("Sitrus", 0)) > 8:
        problemer.append("🇧🇪 **Stilkollisjon:** Belgisk gjær og aggressive amerikanske humler kan overvelde gjærens esterprofil — vurder nøytral gjær for humledrevne stiler.")

    # Signaturbekreftelser
    if sigs["english_ale"]:
        balanse_notater.append("🇬🇧 **Britisk ale-signatur:** Maris Otter / EKG / britisk gjær gir klassisk pub ale-karakter.")
    if sigs["hazy"]:
        balanse_notater.append("🌀 **Hazy-signatur:** Tropiske humler kombinert med myk malt (havre/hvete) peker mot NEIPA / Hazy IPA.")
    if sigs["belgian"]:
        balanse_notater.append("🇧🇪 **Belgisk signatur:** Gjæren vil dominere med krydrede fenol- og esternoter — typisk pepper, nellik og frukt.")
    if sigs["stout"]:
        balanse_notater.append("☕ **Stout-signatur:** Røstet bygg / sort malt gir brent espresso-karakter og sort farge.")
    if sigs["west_coast"]:
        balanse_notater.append("🏄 **West Coast-signatur:** Ren, tørr gjær og bittre aromatiske humler gir klassisk West Coast IPA-profil.")
    if sigs["lager"]:
        balanse_notater.append("🍺 **Lager-signatur:** Lagergjær peker mot pilsner og lagerstiler.")

    return {
        "stil": dominant_stil, "stil_liste": stil_matcher,
        "bu_gu": bu_gu, "balanse": balanse_notater, "problemer": problemer
    }
