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
_LAGER_STYLES        = {
    "Tysk Pilsner", "Tsjekkisk Pilsner", "Münchener Dunkel",
    "Vienna Lager", "Märzen", "Historisk Wiesn-Märzen", "Festbier",
    "Heller Bock (Mai-Bock)", "Dunkles Bock", "Klassisk Røykøl (Rauchbier)",
}
_HAZY_STYLES    = {"Hazy IPA / NEIPA"}
_BELGIAN_STYLES = {"Belgisk Witbier", "Belgisk Tripel", "Belgisk Dubbel"}
_STOUT_STYLES   = {"Irsk Tørr Stout", "Oatmeal Stout", "Robust Porter"}

_ENGLISH_ALE_BOOST  = 20
_LAGER_BOCK_PENALTY = 20
_SIGNATURE_BOOST    = 20
_SIGNATURE_PENALTY  = 15

# Toleranser (epsilon) for numeriske BJCP-sammenligninger.
# Beregnede oppskrift-tall (særlig IBU/EBC) er estimater med iboende
# flyttallsstøy — uten en toleranse vil f.eks. en IBU som i visningen
# rundes til 23, men i realiteten er 22.98, feilaktig bli rapportert som
# "under grensen på 23" med en avvik-tekst som runder ned til "0 IBU".
_EPS_OG   = 0.0005
_EPS_FG   = 0.0005
_EPS_IBU  = 0.5
_EPS_EBC  = 0.5
_EPS_ABV  = 0.05
_EPS_SMAK = 0.05

# Et avvik regnes som "kritisk" for et felt når det er minst halvparten av
# stilens EGET toleransevindu utenfor grensen (f.eks. en Bock med et smalt
# 0.008-bredt OG-vindu blir kritisk ved 0.004 avvik, mens en bredere stil
# tåler mer i absolutte tall før den treffes). Dette er bevisst uavhengig av
# måleenhet, slik at OG/FG/IBU/EBC/ABV kan sammenlignes med samme terskel.
_KRITISK_NORM_TERSKEL   = 0.5
# "Flere kritiske avvik" (krav: OG, ABV, IBU eller farge) skal gi et hardt
# tak på totalscoren som verken normal poengsum eller signaturbonus kan løfte
# forbi — dette er mekanismen som hindrer at f.eks. en lagergjær-bonus kan
# gjøre en tydelig feil stil (galt OG-område, gal farge, gal ABV) om til en
# tilsynelatende god match.
_KRITISK_ANTALL_FOR_TAK = 2
_TAK_KRITISK = 80
# Selv uten et eneste "kritisk" avvik skal en stil med FLERE synlige
# numeriske avvik (mangler-listen) ikke kunne vises som en nesten-perfekt
# match — ellers kan signaturbonusen alene dekke over at f.eks. OG, farge
# OG alkoholstyrke alle er utenfor stilens vindu samtidig, bare fordi ingen
# av dem alene er stor nok til å telle som "kritisk". Terskelen er satt til
# tre for å fange nettopp dette (se kommentaren ved bruken under), og taket
# ligger mellom _TAK_KRITISK og _TAK_AVVIK slik at rangeringen "0-1 avvik >
# 2 avvik > kritisk avvik" alltid gjenspeiles i den viste prosenten.
_MANGE_AVVIK_ANTALL_FOR_TAK = 3
_TAK_FLERE_AVVIK = 85
# Selv uten kritiske avvik skal 100 % være forbeholdt et faktisk fullt treff:
# enhver gjenværende mangel eller ønsket sensorisk preg trekker taket ned til
# "svært god, men ikke perfekt" i stedet for å tillate en flat avrunding opp.
_TAK_AVVIK = 95


def _avvik_numerisk(verdi, lo, hi, eps, vekt_under, vekt_over, tekst_under, tekst_over):
    """
    Eneste stedet som sammenligner en oppskriftsverdi mot et BJCP-intervall.
    Brukes av både scoreberegningen og "Se hva som mangler"-teksten, slik at
    de to aldri kan komme i utakt med hverandre.

    Sammenligningen skjer alltid på full flyttallspresisjon (ingen avrunding
    før dette punktet). `eps` er en liten toleranse som absorberer avrundings-
    og modellstøy i beregnede verdier, slik at en verdi som reelt sett ligger
    på grensen ikke gir utslag.

    Straffen normaliseres mot bredden på stilens eget intervall (hi - lo) før
    den ganges med vekten. Uten dette straffes et gitt avvik likt uansett om
    stilen har et smalt eller bredt toleransevindu — i praksis var f.eks. et
    OG-avvik nesten gratis fordi OG måles i tusendeler, uansett hvor smalt
    stilens vindu var. Med normalisering blir "halvparten av stilens eget
    vindu utenfor grensen" like alvorlig for alle felt og alle stiler.

    Returnerer (score_endring, mangel_tekst_or_None, er_kritisk).
    """
    bredde = max(hi - lo, 1e-9)
    if verdi < lo - eps:
        diff = lo - verdi
        normalisert = diff / bredde
        return -(normalisert * vekt_under), tekst_under(diff), normalisert >= _KRITISK_NORM_TERSKEL
    if verdi > hi + eps:
        diff = verdi - hi
        normalisert = diff / bredde
        return -(normalisert * vekt_over), tekst_over(diff), normalisert >= _KRITISK_NORM_TERSKEL
    return 0.0, None, False


def _avvik_sensorisk(reell_verdi, min_verdi, eps=_EPS_SMAK, vekt=5):
    """Samme toleranseprinsipp som _avvik_numerisk, for sensoriske smak_krav."""
    if reell_verdi < min_verdi - eps:
        diff = min_verdi - reell_verdi
        return -(diff * vekt), diff
    return 0.0, None


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
        # Manglet helt i biblioteket (rangvis "Amber Malty European Lager" +
        # Vienna Lager, jf. BJCP 2021 kat. 3/6) — dette var årsaken til at
        # Munich/Vienna-dominerte lagere aldri kunne foreslås som Märzen: det
        # fantes ingen kandidat med det navnet å score.
        "Vienna Lager": {
            "prio": 1, "kat_navn": "🍂 Oktoberfest & Ravgul Lager",
            "og": (1.046, 1.052), "fg": (1.010, 1.014), "abv": (4.5, 5.5), "ibu": (18, 30), "ebc": (12, 18),
            "smak_krav": {"Brød": 4, "Toast": 3, "Maltfylde": 4, "Bitterhet": 3},
            "beskrivelse": "Ravgul østerriksk/tysk lager med ren, toastet maltkarakter og edel humlebalanse."
        },
        # Canonical BJCP 2021 (6A Märzen): OG 1.054-1.060, FG 1.010-1.014,
        # ABV 5.8-6.3 %, IBU 18-24, SRM 8-17 — verifisert mot bjcp.org.
        # FG/ABV ble tidligere bevisst utvidet (til 1.016/6.5 %) for å få en
        # spesifikk sterk oppskrift nærmere stilen. Det er nå reversert: vi
        # utvider ikke offisielle BJCP-grenser bare for å tette gapet til én
        # oppskrift. Den sterkere, historiske Wiesn-profilen finnes i stedet
        # som sin egen, tydelig merkede stil rett under.
        "Märzen": {
            "prio": 1, "kat_navn": "🍂 Oktoberfest & Ravgul Lager",
            "og": (1.054, 1.060), "fg": (1.010, 1.014), "abv": (5.8, 6.3), "ibu": (18, 24), "ebc": (14, 26),
            "smak_krav": {"Brød": 5, "Toast": 3, "Maltfylde": 5, "Bitterhet": 3},
            "beskrivelse": "Rik, ravgul Oktoberfest-lager med dominerende brødskorpe/toast fra Munich- og Vienna-malt."
        },
        # IKKE en BJCP-stil (verken 2021 eller eldre) — en egen, bevisst merket
        # kategori for de sterkere, førkrigs-/"Wiesn"-inspirerte Märzen-
        # oppskriftene. Finnes som eget valg nettopp for å unngå å måtte
        # utvide selve Märzen-canonical-vinduet ovenfor for å dekke denne
        # varianten.
        #
        # VIKTIG: da denne stilen først ble lagt til (2026-07-26) ble kun
        # FG/ABV utvidet — OG ble ved en feil stående igjen identisk med
        # canonical Märzen (1.054-1.060), som gjorde "historisk" meningsløst
        # for enhver oppskrift sterkere enn moderne Märzen selv. Rettet her
        # (2026-07-26, oppfølging): OG er nå det som faktisk gjør denne
        # stilen "historisk" — et eget vindu sentrert rundt ca. 16 °Plato.
        #
        # Antakelser vinduet bygger på (dokumentert fordi dette IKKE er en
        # offisiell guideline, kun en rimelig tolkning):
        #  - OG: 16 °Plato tilsvarer omtrent 1.064 med samme omregning som
        #    brukes ellers i appen (`_plato(og) = (og-1)*250` i
        #    brewday_calc.py, dvs. og = 1 + plato/250). Vinduet (1.060-1.068)
        #    starter der canonical Märzen slutter (1.060) og gir ca. ±0.004
        #    margin rundt 16 °P — bredt nok til normal oppskriftsvariasjon,
        #    men fortsatt tydelig atskilt fra moderne Märzen/Festbier.
        #  - FG/ABV: en fyldigere, mindre gjæret historisk tolkning enn
        #    dagens sprø 2021-stil — høyere restsødme (FG) og styrke (ABV)
        #    ved samme OG-nivå.
        #  - IBU: noe høyere enn canonical Märzen for å balansere den ekstra
        #    maltsødmen, fortsatt et "edelt", ikke aggressivt bitterhetsnivå.
        #  - EBC: eldre Wiesnbier (før pale-malt-teknologien moderniserte
        #    Oktoberfest-ølet på 1970-tallet) regnes gjerne som mørkere/mer
        #    ravgul-kobberfarget enn dagens lyse festbier-stil — vinduet er
        #    derfor forskjøvet oppover fra canonical Märzens (14-26).
        # Disse tallene er en NB: forfatterens rimelige tolkning, ikke en
        # verifisert historisk kilde — juster gjerne hvis bedre dokumentasjon
        # dukker opp, men ikke bare for å tette gapet til én enkelt oppskrift.
        "Historisk Wiesn-Märzen": {
            "prio": 1, "kat_navn": "🍂 Oktoberfest & Ravgul Lager",
            # Eneste stilen i biblioteket som IKKE er en offisiell BJCP-stil
            # (se forklaringen over) — flagget eksplisitt slik at UI-et kan
            # merke den som en Kvernhaug/historisk kategori i stedet for å la
            # den se ut som en ordinær BJCP-guideline på lik linje med de
            # andre. Alle andre stiler i biblioteket er ekte BJCP 2021-
            # kategorier og trenger ikke dette feltet (default True, se
            # `krav.get("bjcp_offisiell", True)` under).
            "bjcp_offisiell": False,
            "og": (1.060, 1.068), "fg": (1.012, 1.018), "abv": (6.3, 7.0), "ibu": (20, 27), "ebc": (16, 32),
            # Bitterhet-kravet er satt til å være oppnåelig innenfor STILENS
            # EGET IBU-vindu (ikke bare på toppen av det), gitt formelen
            # Bitterhet = IBU/8 i flavor_engine.py: ved nedre grense (IBU 20)
            # gir det nøyaktig 2.5. Uten dette ville enhver oppskrift midt i
            # (eller under toppen av) stilens eget IBU-område vist en falsk
            # "mangler bitterhet"-advarsel — se undersøkelsen i
            # 2026-07-26-oppfølgingen for detaljer.
            "smak_krav": {"Brød": 5, "Toast": 3, "Maltfylde": 5, "Bitterhet": 2.5},
            "beskrivelse": "Kraftigere, historisk Wiesn-stil Märzen (ikke offisiell BJCP-stil) — sterkere, fyldigere og mer ravgul enn moderne 2021-guideline. Sentrert rundt ca. 16 °Plato."
        },
        "Festbier": {
            "prio": 1, "kat_navn": "🍂 Oktoberfest & Ravgul Lager",
            "og": (1.050, 1.057), "fg": (1.008, 1.012), "abv": (5.8, 6.3), "ibu": (18, 25), "ebc": (6, 11),
            "smak_krav": {"Brød": 4, "Maltfylde": 4, "Bitterhet": 3},
            "beskrivelse": "Moderne, lysere og renere Oktoberfest-stil enn Märzen — samme styrke, mindre toast/farge."
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
        onsket_sensorisk = []
        kritiske_avvik = 0

        d, tekst, kritisk = _avvik_numerisk(
            og, krav["og"][0], krav["og"][1], _EPS_OG, 30, 30,
            lambda diff: f"For lav sukkermengde (OG bør være over {krav['og'][0]:.3f})",
            lambda diff: f"For høy sukkermengde (OG bør være under {krav['og'][1]:.3f})",
        )
        score += d
        if tekst: mangler.append(tekst)
        if kritisk: kritiske_avvik += 1

        d, tekst, kritisk = _avvik_numerisk(
            fg, krav["fg"][0], krav["fg"][1], _EPS_FG, 25, 25,
            lambda diff: f"Gjæret for langt ned (FG bør være over {krav['fg'][0]:.3f})",
            lambda diff: f"For mye restsødme (FG bør være under {krav['fg'][1]:.3f})",
        )
        score += d
        if tekst: mangler.append(tekst)
        if kritisk: kritiske_avvik += 1

        # IBU-avviket vises med 1 desimal (ikke 0) slik at et reelt, men lite,
        # avvik (f.eks. 0.6 IBU) ikke fremstår som "0 IBU" i teksten.
        d, tekst, kritisk = _avvik_numerisk(
            ibu, krav["ibu"][0], krav["ibu"][1], _EPS_IBU, 25, 20,
            lambda diff: f"Mangler bitterhet (Mangler {diff:.1f} IBU)",
            lambda diff: f"For høy bitterhet ({diff:.1f} IBU for mye)",
        )
        score += d
        if tekst: mangler.append(tekst)
        if kritisk: kritiske_avvik += 1

        d, tekst, kritisk = _avvik_numerisk(
            ebc, krav["ebc"][0], krav["ebc"][1], _EPS_EBC, 15, 12,
            lambda diff: "Ølet er for lyst for stilen",
            lambda diff: "Ølet er for mørkt for stilen",
        )
        score += d
        if tekst: mangler.append(tekst)
        if kritisk: kritiske_avvik += 1

        d, tekst, kritisk = _avvik_numerisk(
            abv, krav["abv"][0], krav["abv"][1], _EPS_ABV, 25, 25,
            lambda diff: f"For lav alkohol (ABV bør være over {krav['abv'][0]:.1f}%)",
            lambda diff: f"For høy alkohol (ABV bør være under {krav['abv'][1]:.1f}%)",
        )
        score += d
        if tekst: mangler.append(tekst)
        if kritisk: kritiske_avvik += 1

        # Sensoriske smak_krav er ønskede trekk, ikke harde grenser — de teller
        # med i scoren på samme måte som før, men presenteres separat som
        # "ønsket sensorisk preg" i stedet for en rød mangel (krav 7). De er
        # alle på samme faste 0–10-skala for alle stiler, så de trenger ikke
        # normaliseres mot et intervall slik OG/FG/IBU/EBC/ABV gjør, og teller
        # heller ikke som "kritisk avvik" (krav 3/5 gjelder eksplisitt de
        # numeriske feltene OG, ABV, IBU og farge/EBC).
        for smaks_navn, min_verdi in krav["smak_krav"].items():
            reell_verdi = flavor.get(smaks_navn, 0.0)
            d, diff = _avvik_sensorisk(reell_verdi, min_verdi)
            if diff is not None:
                score += d
                onsket_sensorisk.append(
                    f"Ønsket sensorisk preg av *{smaks_navn.lower()}* "
                    f"(har {reell_verdi:.1f}, stilen ber om {min_verdi:.1f}+)"
                )

        raw_score = max(0, min(int(score), 100))

        stil_matcher.append({
            "stil": stil_navn, "score": raw_score, "raw_score": raw_score,
            "mangler": mangler, "onsket_sensorisk": onsket_sensorisk,
            "kritiske_avvik": kritiske_avvik,
            "beskrivelse": krav["beskrivelse"], "prio": krav["prio"], "kat_navn": krav["kat_navn"],
            "bjcp_offisiell": krav.get("bjcp_offisiell", True),
        })

    # 4. SIGNATURJUSTERING
    #
    # `score` er (fortsatt) tallet som brukes til RANGERING mellom stiler —
    # signaturbonusen skal fritt kunne endre rekkefølgen mellom plausible
    # kandidater (krav 3). `signaturbonus` er den samme nominelle justeringen
    # lagret som eget felt, kun til internt bruk (feilsøking/tester) — den
    # vises ikke direkte til brukeren, men gjør det mulig å se hvor mye av
    # `score` som faktisk kommer fra tall/sensorikk (raw_score) og hvor mye
    # som kommer fra en gjær-/malt-/humle-signatur.
    sigs = detect_recipe_signatures(recipe)

    for s in stil_matcher:
        stil = s["stil"]
        s["signaturbonus"] = 0

        if sigs["english_ale"]:
            og_max = bjcp_stiler[stil]["og"][1]
            if og <= og_max + 0.020:
                if stil in _ENGLISH_STYLES_BASE:
                    s["score"] = min(100, s["score"] + _ENGLISH_ALE_BOOST)
                    s["signaturbonus"] += _ENGLISH_ALE_BOOST
                elif stil in _ENGLISH_STYLES_DARK and sigs["dark_malt"]:
                    s["score"] = min(100, s["score"] + _ENGLISH_ALE_BOOST)
                    s["signaturbonus"] += _ENGLISH_ALE_BOOST
            if stil in _LAGER_STYLES:
                s["score"] = max(0, s["score"] - _LAGER_BOCK_PENALTY)
                s["signaturbonus"] -= _LAGER_BOCK_PENALTY

        if sigs["lager"]:
            if stil in _LAGER_STYLES:
                s["score"] = min(100, s["score"] + _SIGNATURE_BOOST)
                s["signaturbonus"] += _SIGNATURE_BOOST

        if sigs["hazy"]:
            if stil in _HAZY_STYLES:
                s["score"] = min(100, s["score"] + _SIGNATURE_BOOST)
                s["signaturbonus"] += _SIGNATURE_BOOST
            elif stil in _LAGER_STYLES:
                s["score"] = max(0, s["score"] - _SIGNATURE_PENALTY)
                s["signaturbonus"] -= _SIGNATURE_PENALTY

        if sigs["belgian"]:
            if stil in _BELGIAN_STYLES:
                s["score"] = min(100, s["score"] + _SIGNATURE_BOOST)
                s["signaturbonus"] += _SIGNATURE_BOOST
            elif stil in _ENGLISH_STYLES_BASE:
                s["score"] = max(0, s["score"] - _SIGNATURE_PENALTY)
                s["signaturbonus"] -= _SIGNATURE_PENALTY

        if sigs["stout"]:
            if stil in _STOUT_STYLES:
                s["score"] = min(100, s["score"] + _SIGNATURE_BOOST)
                s["signaturbonus"] += _SIGNATURE_BOOST

    # Tak på totalscoren (krav: signaturbonus skal aldri kunne oppheve store
    # avvik). Disse takene appliseres ETTER signaturbonusene over, slik at en
    # bonus i beste fall løfter en stil opp til taket — den kan aldri løfte
    # en stil forbi det taket, uansett hvor stor bonusen er.
    #
    #  - To eller flere kritiske avvik (>= halve stilens toleransevindu
    #    utenfor grensen, i OG/FG/IBU/EBC/ABV) => maks _TAK_KRITISK.
    #    Dette er hva som fanger f.eks. en Munich-dominert 1.062/6.7 %-øl
    #    som blir foreslått som Tysk/Tsjekkisk Pilsner: feil OG-område, feil
    #    farge og feil ABV samtidig er ikke en "nesten"-match uansett hvilken
    #    gjær som er brukt.
    #  - Ellers, hvis stilen har _MANGE_AVVIK_ANTALL_FOR_TAK eller flere
    #    SYNLIGE numeriske avvik (mangler-listen — OG/FG/IBU/EBC/ABV utenfor
    #    stilens vindu, uavhengig av om hvert enkelt avvik er "kritisk" i seg
    #    selv) => maks _TAK_FLERE_AVVIK. Dette var kjernebugen: en stil med
    #    tre reelle numeriske avvik (f.eks. Märzen: for høy OG, for lys, for
    #    høy ABV) fikk likevel en signaturbonus stor nok til å ende på samme
    #    _TAK_AVVIK-tak (95 %) som en stil med kun ett avvik (f.eks. Heller
    #    Bock) — to synlig ulike raw_score (79 mot 92) ble dermed vist med
    #    identisk prosent, og rangeringen mellom dem forsvant i UI-en.
    #    Signaturbonusen skal kunne PÅVIRKE rangeringen (over), men skal ikke
    #    kunne dekke over at det fortsatt er flere reelle tallavvik igjen.
    #  - Ellers, dersom det fortsatt finnes mangler eller ønsket sensorisk
    #    preg, er 100 % reservert et faktisk fullt treff (krav 2/8) — taket
    #    er da _TAK_AVVIK, ikke en flat "100 -> 99"-avrunding.
    for s in stil_matcher:
        if s["kritiske_avvik"] >= _KRITISK_ANTALL_FOR_TAK:
            s["score"] = min(s["score"], _TAK_KRITISK)
        elif len(s["mangler"]) >= _MANGE_AVVIK_ANTALL_FOR_TAK:
            s["score"] = min(s["score"], _TAK_FLERE_AVVIK)
        elif s["mangler"] or s["onsket_sensorisk"]:
            s["score"] = min(s["score"], _TAK_AVVIK)

    stil_matcher = sorted(stil_matcher, key=lambda x: (x["prio"], -x["score"]))

    # "Nærmeste stil" (headline) og "prosentvis stiltreff" (listen under) er
    # bevisst to forskjellige begreper (krav 5): headline bruker raw_score —
    # den numeriske/sensoriske treffgraden FØR signaturbonus og tak — slik at
    # en gjær-signaturbonus ikke kan gjøre en dårligere-passende stil til
    # "nærmeste stil". Prosentlisten bruker derimot den justerte/tak-begrensede
    # scoren, som er det brukeren faktisk skal lese som en prosentandel.
    topp_match_reell = max(stil_matcher, key=lambda x: x["raw_score"])
    dominant_stil = topp_match_reell["stil"] if topp_match_reell["raw_score"] > 40 else "Kreativt Brygg"

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
