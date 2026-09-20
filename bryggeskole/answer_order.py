"""
Bryggeskole -- ren, RNG-injisert alternativ-visningsrekkefølge for
spørsmål (issue #338, "Answer-option order").

Krav, hentet direkte fra issue #338:
- tilfeldig posisjon for korrekt svar per spørsmål;
- når mer enn én posisjon finnes, ALDRI samme korrekte posisjon som
  forrige spørsmål i samme runde (ikke-tilstøtende gjenbruk er greit --
  denne modulen husker kun ÉN forrige posisjon, aldri en lengre historikk);
- distraktorer randomiseres i de gjenværende posisjonene;
- evaluering skjer alltid på alternativ-id, aldri synlig indeks -- denne
  modulen endrer bare VISNINGSREKKEFØLGEN til en ny liste med de SAMME
  alternativ-dict-ene (samme id-er/tekst/correct-felt), aldri selve
  alternativenes identitet.

Å FRYSE den valgte rekkefølgen per modul+spørsmål+runde gjennom
reruns/submit/back-resume er UI-laget (ui/bryggeskole_panel.py) sitt
ansvar via st.session_state -- denne modulen trekker kun én ny rekkefølge
per kall, uten å vite noe om økter/runder selv.

Rent, side-effektfritt: ingen Streamlit-avhengighet, ingen tilstand, ingen
modulnivå-tilfeldighet -- `rng` er alltid injisert av kalleren (en
random.Random-instans eller kompatibel), slik at all oppførsel er
deterministisk-testbar med en kontrollert/fake RNG i stedet for
statistiske "håp om variasjon"-tester.
"""

_MIN_ALTERNATIVER = 1


class AnswerOrderError(ValueError):
    """Raised when the given options do not have exactly one 'correct': True
    entry -- a shape problem the pilot content validator
    (bryggeskole.pilot_fermentation / bryggeskole.pilot_mashing) already
    guarantees can't happen for real pilot content, but this module never
    assumes that guarantee silently."""


def velg_alternativ_rekkefolge(options, forrige_korrekt_indeks, rng):
    """Returnerer en NY liste med de samme alternativ-dict-ene som
    `options` (samme objekter, kun ny rekkefølge) med korrekt svar plassert
    på en tilfeldig posisjon.

    `forrige_korrekt_indeks` er indeksen det korrekte svaret hadde i FORRIGE
    spørsmål i samme runde (fra en tidligere finn_korrekt_indeks()-kall),
    eller None for rundens første spørsmål. Når mer enn én posisjon finnes
    å velge mellom, ekskluderes akkurat denne ene indeksen fra kandidatene
    -- resten av utvalget (og all distraktor-rekkefølge) er uniformt
    tilfeldig via `rng`.

    `rng` må være en random.Random-instans (eller noe med samme
    `.choice(seq)`/`.shuffle(list)`-kontrakt), alltid injisert av kalleren.
    """
    if len(options) < _MIN_ALTERNATIVER:
        raise AnswerOrderError(f"'options' må ha minst {_MIN_ALTERNATIVER} element(er), fikk {len(options)}.")

    korrekte = [o for o in options if o.get("correct") is True]
    if len(korrekte) != 1:
        raise AnswerOrderError(f"Forventet nøyaktig ett korrekt alternativ, fant {len(korrekte)}.")
    korrekt_alternativ = korrekte[0]

    n = len(options)
    kandidat_indekser = list(range(n))
    if forrige_korrekt_indeks is not None and n > 1 and forrige_korrekt_indeks in kandidat_indekser:
        uten_forrige = [i for i in kandidat_indekser if i != forrige_korrekt_indeks]
        if uten_forrige:
            kandidat_indekser = uten_forrige

    ny_korrekt_indeks = rng.choice(kandidat_indekser)

    distraktorer = [o for o in options if o is not korrekt_alternativ]
    rng.shuffle(distraktorer)

    rekkefolge = list(distraktorer)
    rekkefolge.insert(ny_korrekt_indeks, korrekt_alternativ)
    return rekkefolge


def finn_korrekt_indeks(rekkefolge):
    """Returnerer indeksen til det korrekte alternativet i en allerede
    ordnet alternativ-liste (typisk output fra
    velg_alternativ_rekkefolge()) -- brukes til å huske «forrige spørsmåls
    korrekte posisjon» til neste velg_alternativ_rekkefolge()-kall i samme
    runde."""
    for i, option in enumerate(rekkefolge):
        if option.get("correct") is True:
            return i
    raise AnswerOrderError("Fant ingen korrekt alternativ i rekkefølgen.")
