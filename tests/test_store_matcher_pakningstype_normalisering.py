"""
Regresjonstester for Steg F10C: modules/store_matcher.py::_strip_size()
fjerner nå også pakningstype-ordene "sekk"/"sack" (i tillegg til
eksisterende størrelse/maltform-fjerning).

Bakgrunn (Steg F10B rotårsaksrapport): "CaraMalt – 25 kg Sekk Hel"
normaliserte tidligere til "CaraMalt – Sekk" — ordet "Sekk" ble stående
igjen, og likhetsscoren mot masteraliaset "CaraMalt" landet på 0,696,
rett under 0,7-terskelen. 17 andre Vestbrygg-produkter med samme
"25 kg Sekk Hel"-mønster matchet allerede korrekt fra før (lengre
produktnavn fortynnet det samme restfragmentet nok til å holde seg over
terskelen) — kun CaraMalt (korteste navnet i gruppen) falt under.

Steg F10C forsøkte først også å trimme foreldreløse bindestreker
(en-dash/em-dash/vanlig) i hver ende av resultatet. Den mandaterte
119-rads regresjonen (Fase 5) avdekket at dette ga en uønsket
bivirkning: fem Ølbrygging "Caramel NNN - 250 g Knust"-produkter
(Viking Malt) fikk sin avsluttende bindestrek trimmet bort og krysset
da 0,7-terskelen mot aliaset "Caramalt 30" — et falskt treff som ikke
har noe med CaraMalt-sekk-problemet å gjøre. Beslutning (godkjent):
bindestrek-trimmingen fjernes helt. Det kosmetiske restfragmentet
("CaraMalt –" i stedet for rent "CaraMalt") er akseptert som prisen
for en ellers ren, avgrenset fiks — scoren (0,889) er uansett godt over
terskelen.

Disse testene bruker utelukkende syntetiske streng-/fixture-verdier og
den ekte, committede maltkatalogen lest read-only — ingen scraper,
ingen filskrivende matcher, ingen masterdata skrives.
"""
import json
import unittest

from modules.store_matcher import _strip_size, match_product_to_master, similarity


class Test1Normalisering(unittest.TestCase):
    """_strip_size() skal fjerne størrelse, maltform OG pakningstype,
    uansett bindestrek-variant. En eventuell foreldreløs bindestrek som
    blir stående igjen etter fjerningen beholdes bevisst (Løsning A —
    generell bindestrek-trimming ble forkastet, se moduldokstring)."""

    def test_en_dash_sekk_hel(self):
        self.assertEqual(_strip_size("CaraMalt – 25 kg Sekk Hel"), "CaraMalt –")

    def test_vanlig_bindestrek_smaa_bokstaver(self):
        self.assertEqual(_strip_size("CaraMalt - 25 kg sekk hel"), "CaraMalt -")

    def test_em_dash_store_bokstaver(self):
        self.assertEqual(_strip_size("CaraMalt — 25 KG SEKK HEL"), "CaraMalt —")

    def test_sack_whole_uten_bindestrek(self):
        self.assertEqual(_strip_size("CaraMalt 25 kg Sack Whole"), "CaraMalt")

    def test_sack_crushed_smaa_bokstaver(self):
        self.assertEqual(_strip_size("CaraMalt 25 kg sack crushed"), "CaraMalt")

    def test_eksisterende_1kg_hel_uendret(self):
        self.assertEqual(_strip_size("CaraMalt 1 kg Hel"), "CaraMalt")

    def test_eksisterende_100g_knust_uendret(self):
        self.assertEqual(_strip_size("CaraMalt 100 g Knust"), "CaraMalt")


class Test2Ordgrense(unittest.TestCase):
    """sekk/sack skal aldri fjernes som del av et lengre ord — kun som
    selvstendig token. Syntetiske testverdier, ikke koblet til noe
    faktisk butikkprodukt."""

    def test_sekk_som_del_av_lengre_ord_fjernes_ikke(self):
        # "Sekkepose" inneholder bokstavrekken "sekk" som prefiks, men
        # er et annet ord og skal IKKE trigge fjerning.
        self.assertEqual(_strip_size("Sekkepose Malt 1 kg Hel"), "Sekkepose Malt")

    def test_sack_som_del_av_lengre_ord_fjernes_ikke(self):
        # "Backsack" inneholder bokstavrekken "sack" som suffiks, men
        # er et annet (syntetisk) ord og skal IKKE trigge fjerning.
        self.assertEqual(_strip_size("Backsack Malt 1 kg hel"), "Backsack Malt")


class Test3EkteMatching(unittest.TestCase):
    """Kjører mot den ekte, committede maltkatalogen (lesende), ikke en
    fixture — beviser at fiksen faktisk løser det dokumenterte
    CaraMalt-problemet i praksis."""

    @classmethod
    def setUpClass(cls):
        with open("data/master_malt.json", encoding="utf-8") as f:
            cls.master_malt = json.load(f)

    def test_caramalt_25kg_matcher_caramalt_30(self):
        stripped = _strip_size("CaraMalt – 25 kg Sekk Hel")
        master_id, alias = match_product_to_master(stripped, self.master_malt)
        self.assertEqual(master_id, "caramalt_30")

    def test_caramalt_25kg_score_over_terskel(self):
        stripped = _strip_size("CaraMalt – 25 kg Sekk Hel")
        master_id, alias = match_product_to_master(stripped, self.master_malt)
        score = similarity(stripped.lower(), alias.lower())
        self.assertGreater(score, 0.7)

    def test_caramalt_25kg_alias_er_caramalt(self):
        stripped = _strip_size("CaraMalt – 25 kg Sekk Hel")
        master_id, alias = match_product_to_master(stripped, self.master_malt)
        self.assertEqual(alias, "CaraMalt")

    def test_ovrige_tre_caramalt_varianter_matcher_fortsatt_samme_master(self):
        for navn in ("CaraMalt - 1 kg Hel", "CaraMalt – 1 KG Knust", "CaraMalt – 100 g Knust"):
            stripped = _strip_size(navn)
            master_id, _ = match_product_to_master(stripped, self.master_malt)
            self.assertEqual(master_id, "caramalt_30", msg=f"{navn!r} matchet ikke caramalt_30")

    def test_alle_fire_caramalt_varianter_samles_i_samme_slot(self):
        navn_liste = [
            "CaraMalt - 1 kg Hel", "CaraMalt – 1 KG Knust",
            "CaraMalt – 100 g Knust", "CaraMalt – 25 kg Sekk Hel",
        ]
        master_ider = {match_product_to_master(_strip_size(n), self.master_malt)[0] for n in navn_liste}
        self.assertEqual(master_ider, {"caramalt_30"})


class Test4SikkerhetsregresjonerFraTidligereSteg(unittest.TestCase):
    """Bekrefter at Steg F10C ikke svekker noe tidligere steg —
    Extra/Ekstra-sperren (F8F) og Light/Extra Light-skillet spesielt."""

    @classmethod
    def setUpClass(cls):
        with open("data/master_malt.json", encoding="utf-8") as f:
            cls.master_malt = json.load(f)

    def test_spraymalt_extra_light_forblir_unmatched(self):
        stripped = _strip_size("1 Kg Spraymalt EXTRA Light (4-5 ebc)")
        master_id, _ = match_product_to_master(stripped, self.master_malt)
        self.assertIsNone(master_id)

    def test_vanlig_spraymalt_light_matcher_fortsatt(self):
        stripped = _strip_size("Spraymalt Light (6-8 ebc)")
        master_id, _ = match_product_to_master(stripped, self.master_malt)
        self.assertEqual(master_id, "spray_light_68_ebc")

    def test_caramel_pale_malt_resultat_uendret(self):
        # Steg F10B: skal fortsatt (feilaktig, kjent og bevisst utsatt)
        # matche "crystal" via det brede "Caramel Malt"-aliaset — F10C
        # rører ikke dette, kun pakningstype-normalisering.
        stripped = _strip_size("Caramel Pale Malt 250 g Knust")
        master_id, alias = match_product_to_master(stripped, self.master_malt)
        self.assertEqual(master_id, "crystal")
        self.assertEqual(alias, "Caramel Malt")

    def test_caramel_nnn_serien_beholder_sluttbindestrek_og_forblir_unmatched(self):
        # Steg F10C, Fase 5-funn: den først implementerte generelle
        # bindestrek-trimmingen fikk disse fem Ølbrygging-produktene
        # (Viking Malt) til å krysse 0,7-terskelen mot masteraliaset
        # "Caramalt 30" ved et uhell — de har ingenting med
        # CaraMalt-sekk-problemet å gjøre. Løsning A (denne fiksen)
        # fjerner ikke bindestreker generelt, så disse skal forbli
        # utrimmet og unmatched.
        navn_og_forventet_stripped = {
            "Caramel 400- 250 g Knust": "Caramel 400-",
            "Caramel 100 - 250 g Knust": "Caramel 100 -",
            "Caramel 200 - 250 g Knust": "Caramel 200 -",
            "Caramel 150 - 250 g Knust": "Caramel 150 -",
            "Caramel 50 - 250 g Knust": "Caramel 50 -",
        }
        for navn, forventet in navn_og_forventet_stripped.items():
            stripped = _strip_size(navn)
            self.assertEqual(stripped, forventet, msg=f"{navn!r} normaliserte uventet")
            master_id, _ = match_product_to_master(stripped, self.master_malt)
            self.assertIsNone(master_id, msg=f"{navn!r} matchet uventet mot {master_id!r}")


if __name__ == "__main__":
    unittest.main()
