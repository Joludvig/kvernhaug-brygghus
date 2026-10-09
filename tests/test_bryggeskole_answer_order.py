"""
Dekning for bryggeskole/answer_order.py (issue #338, "Answer-option order").

Kjernen er RNG-injisert og deterministisk: hvert testtilfelle injiserer en
kontrollert/fake RNG og verifiserer et eksakt utfall. I tillegg finnes noen
få regresjonstester med en SEEDET random.Random som sjekker en invariant
(ikke en fordeling): forrige spørsmåls korrekte posisjon begrenser aldri
neste trekning.

Bevisst reversering av gammel #338-oppførsel: modulen utelukket tidligere
forrige korrekte posisjon, som lekket informasjon på tvers av spørsmål.
Visningsrekkefølgen skal ikke bære informasjon om hva som er riktig;
samme korrekte posisjon på flere spørsmål på rad er derfor tillatt.

Kjøres med:
    python3 -m unittest tests.test_bryggeskole_answer_order -v
"""
import inspect
import random
import unittest

from bryggeskole.answer_order import (
    AnswerOrderError,
    finn_korrekt_indeks,
    velg_alternativ_rekkefolge,
)


def _alternativ(id_, correct):
    return {"id": id_, "text": {"no": id_, "en": id_}, "correct": correct}


class _FakeRng:
    """Deterministisk fake -- ALDRI ekte tilfeldighet -- som lar hver test
    kontrollere og observere nøyaktig hvilke kandidater/lister modulen ba
    om å velge blant."""

    def __init__(self, choice_resultat=None, shuffle_reversert=False):
        self.choice_resultat = choice_resultat
        self.shuffle_reversert = shuffle_reversert
        self.siste_choice_kandidater = None
        self.shuffle_kall = []

    def choice(self, kandidater):
        self.siste_choice_kandidater = list(kandidater)
        if self.choice_resultat is not None:
            return self.choice_resultat
        return kandidater[0]

    def shuffle(self, liste):
        self.shuffle_kall.append(list(liste))
        if self.shuffle_reversert:
            liste.reverse()


class TestVelgAlternativRekkefolgeGrunnleggende(unittest.TestCase):
    def test_tre_alternativer_ingen_forrige_kandidater_er_alle_posisjoner(self):
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=0)
        velg_alternativ_rekkefolge(options, rng)
        self.assertEqual(rng.siste_choice_kandidater, [0, 1, 2])

    def test_korrekt_alternativ_havner_pa_indeksen_choice_returnerer(self):
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=2)
        rekkefolge = velg_alternativ_rekkefolge(options, rng)
        self.assertEqual(rekkefolge[2]["id"], "a")
        self.assertTrue(rekkefolge[2]["correct"])

    def test_samme_id_er_bevart_kun_rekkefolgen_endres(self):
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=1)
        rekkefolge = velg_alternativ_rekkefolge(options, rng)
        self.assertEqual({o["id"] for o in rekkefolge}, {"a", "b", "c"})
        self.assertEqual(len(rekkefolge), 3)

    def test_distraktorer_shuffles_med_injisert_rng(self):
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=0, shuffle_reversert=True)
        rekkefolge = velg_alternativ_rekkefolge(options, rng)
        # Distraktorene ["b", "c"] reverseres av fake-shufflen til ["c", "b"];
        # korrekt ("a") settes inn på indeks 0.
        self.assertEqual([o["id"] for o in rekkefolge], ["a", "c", "b"])
        self.assertEqual(len(rng.shuffle_kall), 1)
        self.assertEqual([o["id"] for o in rng.shuffle_kall[0]], ["b", "c"])


class TestKorrektPosisjonErUavhengigAvForrigeSporsmal(unittest.TestCase):
    def _tre(self):
        return [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]

    def test_funksjonen_tar_ingen_forrige_posisjon(self):
        # Ingen tilstand fra tidligere spørsmål kan sendes inn.
        self.assertEqual(list(inspect.signature(velg_alternativ_rekkefolge).parameters), ["options", "rng"])

    def test_alle_posisjoner_er_alltid_kandidater(self):
        rng = _FakeRng(choice_resultat=1)
        velg_alternativ_rekkefolge(self._tre(), rng)
        self.assertEqual(rng.siste_choice_kandidater, [0, 1, 2])

    def test_samme_korrekte_posisjon_kan_komme_to_ganger_pa_rad(self):
        forste = velg_alternativ_rekkefolge(self._tre(), _FakeRng(choice_resultat=2))
        andre = velg_alternativ_rekkefolge(self._tre(), _FakeRng(choice_resultat=2))
        self.assertEqual(finn_korrekt_indeks(forste), 2)
        self.assertEqual(finn_korrekt_indeks(andre), 2)

    def test_med_ett_alternativ_er_den_eneste_posisjonen_kandidat(self):
        rng = _FakeRng(choice_resultat=0)
        rekkefolge = velg_alternativ_rekkefolge([_alternativ("a", True)], rng)
        self.assertEqual(rng.siste_choice_kandidater, [0])
        self.assertEqual(rekkefolge[0]["id"], "a")

    def test_seedet_trekning_gir_samme_posisjon_pa_rad_for_hver_posisjon(self):
        # Invariant, ikke fordeling: uansett hvilken korrekt posisjon som
        # kom sist, kan den komme igjen. Seedet slik at testen er
        # deterministisk; ingen prosentandeler asserteres.
        rng = random.Random(20261009)
        posisjoner = [finn_korrekt_indeks(velg_alternativ_rekkefolge(self._tre(), rng)) for _ in range(3000)]
        gjentatt = {p for forrige, p in zip(posisjoner, posisjoner[1:]) if p == forrige}
        self.assertEqual(gjentatt, {0, 1, 2})

    def test_seedet_trekning_gir_alle_overganger_mellom_posisjoner(self):
        rng = random.Random(20261009)
        posisjoner = [finn_korrekt_indeks(velg_alternativ_rekkefolge(self._tre(), rng)) for _ in range(3000)]
        overganger = set(zip(posisjoner, posisjoner[1:]))
        self.assertEqual(overganger, {(a, b) for a in range(3) for b in range(3)})

    def test_samme_seed_gir_samme_rekkefolger(self):
        def kjor():
            rng = random.Random(7)
            return [[o["id"] for o in velg_alternativ_rekkefolge(self._tre(), rng)] for _ in range(20)]
        self.assertEqual(kjor(), kjor())


class TestEvalueringAlltidPaIdAldriIndeks(unittest.TestCase):
    def test_alternativ_objektene_er_uendret_kun_rekkefolgen_er_ny(self):
        a = _alternativ("a", True)
        b = _alternativ("b", False)
        c = _alternativ("c", False)
        options = [a, b, c]
        rng = _FakeRng(choice_resultat=1)
        rekkefolge = velg_alternativ_rekkefolge(options, rng)
        for original in (a, b, c):
            self.assertIn(original, rekkefolge)


class TestFeilFormPaAlternativer(unittest.TestCase):
    def test_ingen_korrekt_alternativ_gir_feil(self):
        options = [_alternativ("a", False), _alternativ("b", False)]
        with self.assertRaises(AnswerOrderError):
            velg_alternativ_rekkefolge(options, _FakeRng())

    def test_flere_korrekte_alternativer_gir_feil(self):
        options = [_alternativ("a", True), _alternativ("b", True)]
        with self.assertRaises(AnswerOrderError):
            velg_alternativ_rekkefolge(options, _FakeRng())

    def test_tom_liste_gir_feil(self):
        with self.assertRaises(AnswerOrderError):
            velg_alternativ_rekkefolge([], _FakeRng())

    def test_finn_korrekt_indeks_uten_korrekt_alternativ_gir_feil(self):
        with self.assertRaises(AnswerOrderError):
            finn_korrekt_indeks([_alternativ("a", False), _alternativ("b", False)])


class TestFinnKorrektIndeks(unittest.TestCase):
    def test_finner_riktig_posisjon(self):
        rekkefolge = [_alternativ("b", False), _alternativ("a", True), _alternativ("c", False)]
        self.assertEqual(finn_korrekt_indeks(rekkefolge), 1)


if __name__ == "__main__":
    unittest.main()
