"""
Bryggeskole -- ren, RNG-injisert alternativ-visningsrekkefølge for
spørsmål (issue #338, "Answer-option order").

Krav:
- tilfeldig posisjon for korrekt svar per spørsmål;
- hvert spørsmåls rekkefølge trekkes UAVHENGIG av tidligere spørsmål:
  den forrige korrekte posisjonen begrenser aldri neste trekning, den
  samme korrekte posisjonen kan komme flere ganger på rad, og serier med
  samme posisjon er tillatt;
- distraktorer randomiseres i de gjenværende posisjonene;
- evaluering skjer alltid på alternativ-id, aldri synlig indeks -- denne
  modulen endrer bare VISNINGSREKKEFØLGEN til en ny liste med de SAMME
  alternativ-dict-ene (samme id-er/tekst/correct-felt), aldri selve
  alternativenes identitet.

Bevisst reversering av gammel #338-oppførsel: modulen utelukket tidligere
forrige spørsmåls korrekte posisjon ("aldri samme korrekte posisjon som
forrige spørsmål"). Det gjorde rekkefølgen av korrekte posisjoner
avhengig av hverandre og lekket informasjon på tvers av spørsmål: en
lærer som visste hvor det korrekte svaret lå sist, kunne utelukke den
posisjonen og gjette mellom to i stedet for tre. Visningsrekkefølgen skal
ikke bære noen informasjon om hva som er riktig, og er derfor nå
uavhengig per spørsmål.

Å FRYSE den valgte rekkefølgen per modul+spørsmål+runde gjennom
reruns/submit/back-resume er UI-laget (ui/bryggeskole_panel.py) sitt
ansvar via st.session_state -- denne modulen trekker kun én ny rekkefølge
per kall, uten å vite noe om økter/runder selv.

Rent, side-effektfritt: ingen Streamlit-avhengighet, ingen tilstand, ingen
modulnivå-tilfeldighet -- `rng` er alltid injisert av kalleren (en
random.Random-instans eller kompatibel), slik at all oppførsel er
deterministisk-testbar med en kontrollert/fake RNG.
"""

_MIN_ALTERNATIVER = 1


class AnswerOrderError(ValueError):
    """Raised when the given options do not have exactly one 'correct': True
    entry -- a shape problem the pilot content validator
    (bryggeskole.pilot_fermentation / bryggeskole.pilot_mashing) already
    guarantees can't happen for real pilot content, but this module never
    assumes that guarantee silently."""


def velg_alternativ_rekkefolge(options, rng):
    """Returnerer en NY liste med de samme alternativ-dict-ene som
    `options` (samme objekter, kun ny rekkefølge) med korrekt svar plassert
    på en tilfeldig posisjon blant ALLE posisjoner, uavhengig av tidligere
    spørsmål. Resten av alternativene (distraktorene) stokkes tilfeldig i
    de gjenværende posisjonene.

    `rng` må være en random.Random-instans (eller noe med samme
    `.choice(seq)`/`.shuffle(list)`-kontrakt), alltid injisert av kalleren.
    """
    if len(options) < _MIN_ALTERNATIVER:
        raise AnswerOrderError(f"'options' må ha minst {_MIN_ALTERNATIVER} element(er), fikk {len(options)}.")

    korrekte = [o for o in options if o.get("correct") is True]
    if len(korrekte) != 1:
        raise AnswerOrderError(f"Forventet nøyaktig ett korrekt alternativ, fant {len(korrekte)}.")
    korrekt_alternativ = korrekte[0]

    ny_korrekt_indeks = rng.choice(list(range(len(options))))

    distraktorer = [o for o in options if o is not korrekt_alternativ]
    rng.shuffle(distraktorer)

    rekkefolge = list(distraktorer)
    rekkefolge.insert(ny_korrekt_indeks, korrekt_alternativ)
    return rekkefolge


def finn_korrekt_indeks(rekkefolge):
    """Returnerer indeksen til det korrekte alternativet i en allerede
    ordnet alternativ-liste (typisk output fra
    velg_alternativ_rekkefolge()). Ren hjelpefunksjon for lesing av en
    rekkefølge; verdien brukes ALDRI til å begrense neste spørsmåls
    rekkefølge."""
    for i, option in enumerate(rekkefolge):
        if option.get("correct") is True:
            return i
    raise AnswerOrderError("Fant ingen korrekt alternativ i rekkefølgen.")
