"""
Ren, RNG-injisert dekning for bryggeskole/answer_order.py (issue #338,
"Answer-option order"). Ingen statistisk "håp om variasjon"-testing --
hvert testtilfelle injiserer en kontrollert/fake RNG og verifiserer et
eksakt, deterministisk utfall, per issue #338 sitt eget krav
("deterministic RNG tests (patched/injected RNG, not statistical
'hope for variation' tests)").

Kjøres med:
    python3 -m unittest tests.test_bryggeskole_answer_order -v
"""
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
        velg_alternativ_rekkefolge(options, None, rng)
        self.assertEqual(rng.siste_choice_kandidater, [0, 1, 2])

    def test_korrekt_alternativ_havner_pa_indeksen_choice_returnerer(self):
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=2)
        rekkefolge = velg_alternativ_rekkefolge(options, None, rng)
        self.assertEqual(rekkefolge[2]["id"], "a")
        self.assertTrue(rekkefolge[2]["correct"])

    def test_samme_id_er_bevart_kun_rekkefolgen_endres(self):
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=1)
        rekkefolge = velg_alternativ_rekkefolge(options, None, rng)
        self.assertEqual({o["id"] for o in rekkefolge}, {"a", "b", "c"})
        self.assertEqual(len(rekkefolge), 3)

    def test_distraktorer_shuffles_med_injisert_rng(self):
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=0, shuffle_reversert=True)
        rekkefolge = velg_alternativ_rekkefolge(options, None, rng)
        # Distraktorene ["b", "c"] reverseres av fake-shufflen til ["c", "b"];
        # korrekt ("a") settes inn på indeks 0.
        self.assertEqual([o["id"] for o in rekkefolge], ["a", "c", "b"])
        self.assertEqual(len(rng.shuffle_kall), 1)
        self.assertEqual([o["id"] for o in rng.shuffle_kall[0]], ["b", "c"])


class TestUnngarSammeKorrektPosisjonSomForrigeSporsmal(unittest.TestCase):
    def test_forrige_korrekt_indeks_ekskluderes_fra_kandidatene(self):
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=1)
        velg_alternativ_rekkefolge(options, 0, rng)
        self.assertEqual(rng.siste_choice_kandidater, [1, 2])

    def test_ny_korrekt_posisjon_er_faktisk_ulik_forrige(self):
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=1)
        rekkefolge = velg_alternativ_rekkefolge(options, 0, rng)
        ny_indeks = finn_korrekt_indeks(rekkefolge)
        self.assertNotEqual(ny_indeks, 0)
        self.assertEqual(ny_indeks, 1)

    def test_ikke_tilstotende_gjenbruk_er_tillatt_kandidatene_utelater_kun_forrige(self):
        # Spørsmål 1: korrekt havnet på indeks 2. Spørsmål 2: forrige=2,
        # kandidatene skal da være [0, 1] -- ikke en lengre "aldri brukt
        # før"-historikk over hele runden.
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=0)
        velg_alternativ_rekkefolge(options, 2, rng)
        self.assertEqual(rng.siste_choice_kandidater, [0, 1])

    def test_med_kun_to_alternativer_forrige_ekskluderes_til_den_ene_gjenvaerende(self):
        options = [_alternativ("a", True), _alternativ("b", False)]
        rng = _FakeRng(choice_resultat=1)
        velg_alternativ_rekkefolge(options, 0, rng)
        self.assertEqual(rng.siste_choice_kandidater, [1])

    def test_med_ett_alternativ_forrige_kan_ikke_ekskluderes_faller_tilbake_til_alle(self):
        options = [_alternativ("a", True)]
        rng = _FakeRng(choice_resultat=0)
        rekkefolge = velg_alternativ_rekkefolge(options, 0, rng)
        self.assertEqual(rng.siste_choice_kandidater, [0])
        self.assertEqual(rekkefolge[0]["id"], "a")

    def test_forrige_korrekt_indeks_none_ekskluderer_ingenting(self):
        options = [_alternativ("a", True), _alternativ("b", False), _alternativ("c", False)]
        rng = _FakeRng(choice_resultat=0)
        velg_alternativ_rekkefolge(options, None, rng)
        self.assertEqual(rng.siste_choice_kandidater, [0, 1, 2])


class TestEvalueringAlltidPaIdAldriIndeks(unittest.TestCase):
    def test_alternativ_objektene_er_uendret_kun_rekkefolgen_er_ny(self):
        a = _alternativ("a", True)
        b = _alternativ("b", False)
        c = _alternativ("c", False)
        options = [a, b, c]
        rng = _FakeRng(choice_resultat=1)
        rekkefolge = velg_alternativ_rekkefolge(options, None, rng)
        for original in (a, b, c):
            self.assertIn(original, rekkefolge)


class TestFeilFormPaAlternativer(unittest.TestCase):
    def test_ingen_korrekt_alternativ_gir_feil(self):
        options = [_alternativ("a", False), _alternativ("b", False)]
        with self.assertRaises(AnswerOrderError):
            velg_alternativ_rekkefolge(options, None, _FakeRng())

    def test_flere_korrekte_alternativer_gir_feil(self):
        options = [_alternativ("a", True), _alternativ("b", True)]
        with self.assertRaises(AnswerOrderError):
            velg_alternativ_rekkefolge(options, None, _FakeRng())

    def test_tom_liste_gir_feil(self):
        with self.assertRaises(AnswerOrderError):
            velg_alternativ_rekkefolge([], None, _FakeRng())

    def test_finn_korrekt_indeks_uten_korrekt_alternativ_gir_feil(self):
        with self.assertRaises(AnswerOrderError):
            finn_korrekt_indeks([_alternativ("a", False), _alternativ("b", False)])


class TestFinnKorrektIndeks(unittest.TestCase):
    def test_finner_riktig_posisjon(self):
        rekkefolge = [_alternativ("b", False), _alternativ("a", True), _alternativ("c", False)]
        self.assertEqual(finn_korrekt_indeks(rekkefolge), 1)


if __name__ == "__main__":
    unittest.main()
