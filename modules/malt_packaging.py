# modules/malt_packaging.py
"""
Maltvariant-/pakningsmodell for Smart Handleliste.

Svarer på ETT konkret spørsmål: «Gitt en reell mangel i gram og butikkens
registrerte malt-pakningsvarianter, hvilke praktiske kjøpskombinasjoner
finnes, og hvilken bør fremheves som anbefalt?»

Nytt, valgfritt datafelt under butikk_match.<butikk> i data/master_malt.json:

    "butikk_match": {
      "vestbrygg": {
        "varianter": [
          {"pakningsstorrelse_gram": 100,   "malttype": "knust", "pris": 15.0, "url": "..."},
          {"pakningsstorrelse_gram": 1000,  "malttype": "knust", "pris": 45.0},
          {"pakningsstorrelse_gram": 1000,  "malttype": "hel",   "pris": 42.0},
          {"pakningsstorrelse_gram": 25000, "malttype": "hel",   "pris": 750.0}
        ]
      }
    }

Uten et "varianter"-felt faller malt tilbake til den eldre, enklere
"pakke_kg"-modellen i modules/smart_shopping_list.py (eksakt mengde, eller
avrunding til ÉN kjent pakningsstørrelse) — denne modulen endrer ikke
oppførselen for malt som ikke har registrerte varianter ennå.

Valgfritt felt per variant (lagt til i Steg F2, kun brukt av Vestbrygg):
"lagerstatus" — "pa_lager"/"utsolgt"/"ukjent". En variant merket "utsolgt"
ekskluderes fra ALLE kjøpskombinasjoner (både anbefalt og alternativer),
se _varianter_for_form(). Mangler feltet helt (Ølbrygging, eller eldre
Vestbrygg-data), eller er det "ukjent", behandles varianten som om den var
på lager — fravær av signal er aldri det samme som kjent utsolgt.

Grunnprinsipp: en enkelt foreslått kjøpskombinasjon blander ALDRI hel og
knust malt. Kombinasjoner bygges separat per malttype; når flere typer
finnes å velge mellom, avgjør maltform-innstillingen (se MALTFORM_*) hvilke
som vurderes for selve ANBEFALINGEN — resten vises som alternativer.

Valgfritt flagg (lagt til i Steg F3): eksakt_mal=True til
bygg_pakningsforslag(). Gjelder KUN sammen med maltform=MALTFORM_KNUST
(Vestbrygg opplyser at knust malt kan bestilles til eksakte mål via
melding til salgsavdelingen — se Steg E-rapporten; ikke bekreftet for hel
malt). Endrer BARE kjøpsresultatets mottatt_mengde (settes til det eksakte
behovet i stedet for SKU-summen) og bestilling (uttrykker i tillegg den
eksakte ønskede mengden, se _kjopsresultat_eksakt_mal()) — selve
kombinasjonsvalget og prisen er identisk med normalmodus.

Ren Python, ingen streamlit, ingen mutasjon av input.
"""
import math

MALTFORM_KNUST = "knust"
MALTFORM_HEL = "hel"
MALTFORM_BILLIGST = "billigst_tilgjengelig"
MALTFORM_INGEN_PREFERANSE = "ingen_preferanse"

PRIORITET_BILLIGST = "billigst"
PRIORITET_MINST_OVERKJOP = "minst_overkjop"
PRIORITET_BALANSERT = "balansert"

# Ikke la balansert/minst-overkjøp anbefale et kjøp som dekker det reelle
# behovet mer enn dette mange ganger (krav 5: en 25 kg-sekk skal ikke bli
# standardforslag bare fordi den finnes/har lavest kilopris). Gjelder KUN
# hvilken kombinasjon som fremheves som "anbefalt" — grovt oversized
# kombinasjoner fjernes aldri fra alternativ-listen.
_MAKS_RIMELIG_DEKNINGSGRAD = 2.0

# Øvre grense på antall enheter av samme pakningsstørrelse som vurderes i
# søket. Realistisk for hjemmebrygging (ingen oppskrift her trenger over
# noen titalls kilo av én malt) — holder kombinatorikken liten uten å miste
# reelle, praktiske forslag.
_MAKS_ENHETER_PER_STORRELSE = 60


def hent_tilgjengelige_malttyper(varianter):
    """Sorterte, unike malttype-verdier ("hel"/"knust") som faktisk finnes
    blant de gitte variantene."""
    return sorted({v.get("malttype") for v in varianter if v.get("malttype")})


def _varianter_for_form(varianter, malttype):
    """Kun varianter av gitt malttype som faktisk kan inngå i en
    kjøpskombinasjon: eksplisitt utsolgte varianter ("lagerstatus":
    "utsolgt", se Steg F2) ekskluderes her, FØR selve kombinasjons-søket,
    slik at ingen anbefaling — eller alternativ — noensinne kan foreslå et
    kjøp av noe som er kjent utsolgt. Varianter uten "lagerstatus"-felt i
    det hele tatt (Ølbrygging, eller Vestbrygg-data eldre enn Steg F2) og
    varianter markert "ukjent" behandles likt — IKKE som utsolgt, siden
    fravær av signal aldri skal tolkes som en kjent, negativ status."""
    return [
        v for v in varianter
        if v.get("malttype") == malttype and v.get("lagerstatus") != "utsolgt"
    ]


def _generer_kombinasjoner_for_form(missing_gram, varianter_i_form):
    """Alle 'fornuftige' kombinasjoner av pakningsstørrelser i ÉN maltform
    som dekker (>=) missing_gram, med tilhørende total mengde og pris.

    Størrelsene rangeres størst -> minst. Alle unntatt den minste varieres i
    en begrenset løkke; den minste fylles ANALYTISK opp til akkurat nok for
    hver kombinasjon av de større — dette holder søket lite (produkt av
    grovt begrensede tellere for de store størrelsene) uten å miste noen
    reell, praktisk kombinasjon, siden et for stort antall av kun den
    minste pakningen aldri er den mest praktiske løsningen når større
    pakninger finnes."""
    if not varianter_i_form or missing_gram <= 0:
        return []

    pris_for_storrelse = {}
    for v in varianter_i_form:
        storrelse = float(v["pakningsstorrelse_gram"])
        pris = float(v["pris"])
        if storrelse not in pris_for_storrelse or pris < pris_for_storrelse[storrelse]:
            pris_for_storrelse[storrelse] = pris

    storrelser = sorted(pris_for_storrelse, reverse=True)
    minste = storrelser[-1]
    store_storrelser = storrelser[:-1]

    def maks_antall(storrelse):
        return min(_MAKS_ENHETER_PER_STORRELSE, math.ceil(missing_gram / storrelse) + 1)

    funnet = {}

    def rekursiv(gjenstaende, antall_per_storrelse, akkumulert_gram, akkumulert_pris):
        if not gjenstaende:
            rest_behov = missing_gram - akkumulert_gram
            antall_minste = max(0, math.ceil(rest_behov / minste))
            total_gram = akkumulert_gram + antall_minste * minste
            total_pris = akkumulert_pris + antall_minste * pris_for_storrelse[minste]
            if total_gram < missing_gram:
                return
            endelig_antall = dict(antall_per_storrelse)
            if antall_minste:
                endelig_antall[minste] = endelig_antall.get(minste, 0) + antall_minste
            nokkel = tuple(sorted(endelig_antall.items()))
            if nokkel not in funnet or total_pris < funnet[nokkel][1]:
                funnet[nokkel] = (total_gram, total_pris, endelig_antall)
            return
        storrelse = gjenstaende[0]
        rest = gjenstaende[1:]
        for n in range(0, maks_antall(storrelse) + 1):
            nytt_antall = dict(antall_per_storrelse)
            if n:
                nytt_antall[storrelse] = n
            rekursiv(rest, nytt_antall, akkumulert_gram + n * storrelse, akkumulert_pris + n * pris_for_storrelse[storrelse])

    rekursiv(store_storrelser, {}, 0.0, 0.0)

    resultat = []
    for total_gram, total_pris, antall_per_storrelse in funnet.values():
        resultat.append({
            "antall_pakninger": [
                {"pakningsstorrelse_gram": s, "antall": n}
                for s, n in sorted(antall_per_storrelse.items(), reverse=True) if n
            ],
            "total_gram": total_gram,
            "total_pris": round(total_pris, 2),
            "overkjop_gram": round(total_gram - missing_gram, 2),
            "dekningsgrad": (total_gram / missing_gram) if missing_gram else None,
        })
    return resultat


def _fjern_dominerte(kombinasjoner):
    """Beholder kun Pareto-optimale kombinasjoner: en kombinasjon fjernes
    hvis en ANNEN har både lavere-eller-lik pris OG lavere-eller-lik
    overkjøp, med minst én strengt bedre. Holder forslagslisten kort og
    meningsfull i UI-et uten å skjule reelle avveininger (krav 8: både et
    billigere-men-mer-overkjøp-alternativ og et dyrere-men-mindre-overkjøp-
    alternativ skal kunne vises samtidig — det er nettopp det Pareto-
    settet er)."""
    beholdt = []
    for a in kombinasjoner:
        dominert = False
        for b in kombinasjoner:
            if a is b:
                continue
            ikke_verre = b["total_pris"] <= a["total_pris"] and b["overkjop_gram"] <= a["overkjop_gram"]
            strengt_bedre = b["total_pris"] < a["total_pris"] or b["overkjop_gram"] < a["overkjop_gram"]
            if ikke_verre and strengt_bedre:
                dominert = True
                break
        if not dominert:
            beholdt.append(a)
    return beholdt


def _kjopsresultat_fra_kombinasjon(kombinasjon):
    """Kjøpsresultat-kontrakten — pris, mottatt_mengde, bestilling — for ÉN
    valgt pakkekombinasjon. Alle tre fasettene hentes fra NØYAKTIG samme
    kombinasjon (aldri regnet ut separat), slik at de garantert beskriver
    samme fysiske kjøp.

    "bestilling" er strukturert domenedata (samme form som
    antall_pakninger: en liste av {pakningsstorrelse_gram, antall}) — IKKE
    ferdig formattert tekst. Menneskelesbar formatering ("2 × 1 kg + 3 ×
    100 g") er UI-ansvar, se ui/smart_shopping_list_panel.py::_fmt_pakninger().
    """
    return {
        "pris": kombinasjon["total_pris"],
        "mottatt_mengde": kombinasjon["total_gram"],
        "bestilling": kombinasjon["antall_pakninger"],
    }


def _kjopsresultat_eksakt_mal(kombinasjon, eksakt_behov_gram):
    """Kjøpsresultat-kontrakten for «bestill til eksakt mål»-modus (Steg F3,
    kun Vestbrygg + knust — se bygg_pakningsforslag(..., eksakt_mal=True)).

    Samme tre topplinjefelt som normalt — pris, mottatt_mengde, bestilling —
    ALDRI et nytt fakturert_mengde-felt på toppnivå:

    - "pris" er FORTSATT summen av de faktisk valgte SKU-ene (samme
      kombinasjon som ellers) — det er hva kunden faktisk betaler for.
    - "mottatt_mengde" settes til det EKSAKTE behovet, ikke SKU-summen —
      Vestbrygg opplyser (produktsidetekst, se Steg E-rapporten) at knust
      malt kan bestilles til eksakte mål via melding til salgsavdelingen.
      Dette er IKKE en systemgarantert leveranse, kun en opplyst mulighet —
      se ui/smart_shopping_list_panel.py for hvordan dette formidles videre.
    - "bestilling" uttrykker her BEGGE deler kunden trenger for å faktisk
      gjennomføre bestillingen: den strukturerte SKU-listen som skal i
      handlekurven ("pakninger", samme form som før) OG den eksakte
      mengden som skal oppgis i meldingsfeltet ("eksakt_onsket_mengde_gram").
      Fortsatt strukturert domenedata, ikke ferdig tekst.
    """
    return {
        "pris": kombinasjon["total_pris"],
        "mottatt_mengde": eksakt_behov_gram,
        "bestilling": {
            "pakninger": kombinasjon["antall_pakninger"],
            "eksakt_onsket_mengde_gram": eksakt_behov_gram,
        },
    }


def _velg_etter_prioritet(kombinasjoner, prioritet):
    """Returnerer den anbefalte kombinasjonen for en gitt prioritet, eller
    None hvis listen er tom.

    - billigst:        ren pris-rangering (brukerens eksplisitte valg —
                        ingen dekningsgrad-begrensning; hvis en stor
                        pakning faktisk er billigst totalt, er det nettopp
                        det brukeren ba om å få vist).
    - minst_overkjop:   ren overkjøp-rangering, men ekskluderer (kun fra å
                        bli ANBEFALT, ikke fra alternativ-listen) grovt
                        oversized kombinasjoner (krav 5), med mindre det er
                        den eneste som finnes.
    - balansert (std.): kombinert pris-/overkjøp-rangering med samme
                        dekningsgrad-begrensning som minst_overkjop."""
    if not kombinasjoner:
        return None

    if prioritet == PRIORITET_BILLIGST:
        rangert = sorted(kombinasjoner, key=lambda k: (k["total_pris"], k["overkjop_gram"]))
        return rangert[0]

    rimelige = [k for k in kombinasjoner if (k["dekningsgrad"] or 0) <= _MAKS_RIMELIG_DEKNINGSGRAD]
    kandidater = rimelige or kombinasjoner

    if prioritet == PRIORITET_MINST_OVERKJOP:
        rangert = sorted(kandidater, key=lambda k: (k["overkjop_gram"], k["total_pris"]))
        return rangert[0]

    # balansert
    priser = sorted(k["total_pris"] for k in kandidater)
    overkjop = sorted(k["overkjop_gram"] for k in kandidater)
    rangert = sorted(
        kandidater,
        key=lambda k: (
            priser.index(k["total_pris"]) + overkjop.index(k["overkjop_gram"]),
            len(k["antall_pakninger"]),
            k["total_pris"],
        ),
    )
    return rangert[0]


def bygg_pakningsforslag(missing_gram, butikk_match, maltform=MALTFORM_INGEN_PREFERANSE,
                          prioritet=PRIORITET_BALANSERT, eksakt_mal=False):
    """Hovedinngang: bygger alle kandidat-kjøpskombinasjoner for én malt,
    gruppert per maltform (hel/knust), og peker ut én anbefalt kombinasjon
    per gitt prioritet.

    Returnerer None hvis ingen "varianter" er registrert i butikk_match
    (kalleren faller da tilbake til den eldre pakke_kg-modellen i
    modules/smart_shopping_list.py) eller hvis det ikke finnes noe reelt
    mangelbeløp å dekke.

    eksakt_mal (Steg F3, standard False): når True OG maltform==MALTFORM_KNUST
    (Vestbryggs opplyste eksakt-mål-tjeneste gjelder kun knust malt, se
    Steg E-rapporten), settes kjøpsresultatets mottatt_mengde til det
    EKSAKTE behovet (missing_gram) i stedet for den valgte SKU-kombinasjonens
    totalsum — se _kjopsresultat_eksakt_mal(). Prisen, kombinasjonsvalget,
    alternativene og advarselen er 100 % UENDRET av dette flagget; kun selve
    kjøpsresultat-beregningen for den allerede valgte kombinasjonen endres.
    Med eksakt_mal=False (default) eller enhver annen maltform er
    oppførselen nøyaktig som før dette flagget fantes."""
    varianter = (butikk_match or {}).get("varianter") or []
    if not varianter or not missing_gram or missing_gram <= 0:
        return None

    tilgjengelige_former = hent_tilgjengelige_malttyper(varianter)
    if not tilgjengelige_former:
        return None

    per_form = {}
    for form in tilgjengelige_former:
        kombos = _fjern_dominerte(_generer_kombinasjoner_for_form(missing_gram, _varianter_for_form(varianter, form)))
        for k in kombos:
            k["malttype"] = form
        per_form[form] = kombos

    if maltform == MALTFORM_KNUST:
        aktuelle_former = [MALTFORM_KNUST] if MALTFORM_KNUST in per_form else []
    elif maltform == MALTFORM_HEL:
        aktuelle_former = [MALTFORM_HEL] if MALTFORM_HEL in per_form else []
    else:
        # "billigste tilgjengelige" og "ingen preferanse" vurderer begge
        # ALLE tilgjengelige former for selve rangeringen -- forskjellen er
        # bare om et advarsel-notat vises (se under), ikke hvilke
        # kombinasjoner som er kandidater.
        aktuelle_former = tilgjengelige_former

    if not aktuelle_former:
        return None

    alle_aktuelle_kombinasjoner = [k for form in aktuelle_former for k in per_form.get(form, [])]
    anbefalt = _velg_etter_prioritet(alle_aktuelle_kombinasjoner, prioritet)
    if anbefalt is None:
        return None

    alternativer = []
    for form in tilgjengelige_former:
        for k in per_form.get(form, []):
            if k is not anbefalt:
                alternativer.append(k)
    alternativer.sort(key=lambda k: (k["total_pris"], k["overkjop_gram"]))

    advarsel = None
    if maltform == MALTFORM_INGEN_PREFERANSE and len(tilgjengelige_former) > 1:
        advarsel = (
            "Flere maltformer tilgjengelig (hel og knust). Forslag holdes atskilt per form -- "
            "ingen kombinasjon blander hel og knust malt uten at du eksplisitt velger maltform "
            "\"billigste tilgjengelige\"."
        )

    if eksakt_mal and maltform == MALTFORM_KNUST:
        kjopsresultat = _kjopsresultat_eksakt_mal(anbefalt, missing_gram)
    else:
        kjopsresultat = _kjopsresultat_fra_kombinasjon(anbefalt)

    return {
        "maltformer_tilgjengelig": tilgjengelige_former,
        "maltform_brukt": maltform,
        "prioritet_brukt": prioritet,
        "anbefalt_kombinasjon": anbefalt,
        "kjopsresultat": kjopsresultat,
        "alternative_kombinasjoner": alternativer,
        "advarsel": advarsel,
    }
