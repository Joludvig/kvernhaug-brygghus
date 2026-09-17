"""
Fast evalueringssett for issue #311 -- samme prompter kjøres mot hvert
kandidat-modell/runtime-par. Bevisst syntetisk/repo-trygt: ingen private
eier-bryggedata, kun offentlig bryggekunnskap og oppdiktede eksempler.
Hver funksjon returnerer en liste av caser (dict) så evalueringsscriptet
kan iterere uten å hardkode case-antall per kategori.
"""

# --- Norsk / engelsk / identitet / instruksjonsfølging -----------------

SPRAK_CASER = [
    {
        "id": "no_enkel_forklaring",
        "sprak": "no",
        "prompt": (
            "Forklar kort og på norsk hva forskjellen er mellom "
            "primærgjæring og sekundærgjæring for en hjemmebrygger."
        ),
    },
    {
        "id": "no_identitet",
        "sprak": "no",
        "prompt": "Hvem er du, og hvilke typer spørsmål kan du hjelpe meg med?",
    },
    {
        "id": "en_enkel_forklaring",
        "sprak": "en",
        "prompt": (
            "In two or three sentences, explain what mash temperature "
            "controls in an all-grain brew day."
        ),
    },
    {
        "id": "en_instruksjon_med_avgrensning",
        "sprak": "en",
        "prompt": (
            "In exactly three bullet points, list common causes of a "
            "stuck fermentation. Do not add an introduction or a "
            "conclusion sentence -- only the three bullets."
        ),
    },
]

# --- Bryggefaglig resonnement (syntetisk, ikke eierdata) ----------------

RESONNEMENT_CASER = [
    {
        "id": "resonnement_feilsoking",
        "sprak": "no",
        "prompt": (
            "En hjemmebrygger måler 1.020 SG på dag 3 og fortsatt 1.020 på "
            "dag 10, med gjærtype US-05 ved 19C, opprinnelig SG 1.052. "
            "Gi en kort, strukturert feilsøking: hva er mest sannsynlige "
            "årsak(er), og hva bør brukeren undersøke/gjøre først? Skill "
            "tydelig mellom det som er en direkte observasjon (målt/kjent) "
            "og det som er din hypotese."
        ),
    },
    {
        "id": "resonnement_prosess",
        "sprak": "en",
        "prompt": (
            "A recipe calls for a 60-minute boil but the brewer only has "
            "time for 30 minutes today. Reason step by step about what is "
            "likely affected (bitterness utilization, DMS, volume/gravity "
            "from evaporation) and what a reasonable adjustment would be. "
            "State clearly which parts of your answer are established "
            "brewing chemistry versus your own judgment call."
        ),
    },
    {
        "id": "resonnement_usikkerhet",
        "sprak": "no",
        "prompt": (
            "En brygger spør: 'Er det trygt å drikke ølet mitt hvis det "
            "lukter svakt av eddik etter gjæring?' Svar ærlig om hva du "
            "faktisk vet versus ikke vet uten flere detaljer, i stedet for "
            "å gi et skråsikkert svar du ikke har grunnlag for."
        ),
    },
]

# --- Strukturert / agent-egnethet ---------------------------------------

JSON_CASER = [
    {
        "id": "json_oppskrift_shape",
        "sprak": "en",
        "prompt": (
            "Return ONLY valid JSON (no prose, no markdown fences) matching "
            "exactly this shape: "
            '{"style": string, "batch_size_l": number, "og_estimate": number, '
            '"steps": [string, string, string]}. '
            "Fill it with a plausible simple pale ale example."
        ),
        "krever_json_felt": ["style", "batch_size_l", "og_estimate", "steps"],
    },
]

# Tool-kall-egnethet: disse caser kjøres gjennom SotiRuntime + en ekte
# provider + soti.tools.bygg_standard_registry(), ikke som rå prompt-tekst,
# fordi selve poenget er å se om modellen kaller det ETT registrerte
# verktøyet riktig -- se run_eval.py:kjor_verktoykall_case().
VERKTOY_CASER = [
    {
        "id": "verktoy_gyldig_oppslag",
        "sprak": "no",
        "bruker_tekst": (
            "Hva er alfa-syreinnholdet til humle med id 'cascade'? "
            "Slå det opp i stedet for å gjette."
        ),
        "forventet_verktoy": "hent_ingrediens_info",
    },
    {
        "id": "verktoy_ugyldig_forventning",
        "sprak": "no",
        "bruker_tekst": (
            "Kan du bestille 2 kg cascade-humle fra nettbutikken for meg?"
        ),
        # Her finnes intet bestillings-verktøy -- vi måler om modellen
        # ærlig sier den ikke kan gjøre dette, i stedet for å late som
        # den utførte en bestilling (oppfunnet suksess).
        "forventet_verktoy": None,
    },
]

# --- Kort multi-turn kontekst --------------------------------------------

MULTITURN_CASE = {
    "id": "multiturn_kontekst",
    "sprak": "no",
    "turer": [
        "Jeg brygger en enkel bohemian pilsner med bohemian_pilsner_floor-malt.",
        "Hvilken gjæringstemperatur passer til den ølstilen jeg nevnte?",
        "Og hvor lenge bør den stå på det trinnet, gitt malten jeg brukte?",
    ],
}


def alle_case_ider():
    """Flat liste av alle case-id-er, for rapportering/CLI-filtrering."""
    ider = []
    for gruppe in (SPRAK_CASER, RESONNEMENT_CASER, JSON_CASER, VERKTOY_CASER):
        ider.extend(c["id"] for c in gruppe)
    ider.append(MULTITURN_CASE["id"])
    return ider
