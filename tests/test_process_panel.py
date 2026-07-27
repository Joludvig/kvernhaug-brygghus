"""
Regresjonstester for ui/process_panel.py — spesifikt bug'en der bytte av
prosessprofil (og innlasting av en lagret oppskrift) kunne gi en
meskeplan som var en blanding av gammel og ny profil, fordi panelets
EGET utvalg (valgt_prosess_id/prosess_mash_steps) ikke ble resynket mot
den faktisk aktive oppskriftens aktiv_prosessprofil.

Bruker streamlit.testing.v1.AppTest for å simulere ekte
selectbox/number_input-interaksjon og reruns (ikke mulig å teste dette
presist med ren st.session_state-manipulering, siden selve bug'en ligger
i panelets egen change-detection-logikk).

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import logging
import os
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from modules.process_profiles import hent_standardprofil

_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_process_panel_app.py")


def _steg(at):
    return [(s["temperatur"], s["varighet"]) for s in at.session_state["prosess_mash_steps"]]


def _widget_steg(at):
    """Leser meskestegene DIREKTE fra de rendrede number_input-widgetene
    (ikke fra session_state["prosess_mash_steps"]) — dette er det brukeren
    faktisk SER i nettleseren, og er nøyaktig det som feilet: session_state
    kunne være korrekt mens widgetene fortsatt viste gamle verdier."""
    revisjon = at.session_state["_process_widget_revision"]
    i = 0
    steg = []
    while True:
        try:
            temp = at.number_input(key=f"mash_temp_{revisjon}_{i}").value
            tid = at.number_input(key=f"mash_time_{revisjon}_{i}").value
        except KeyError:
            break
        steg.append((temp, tid))
        i += 1
    return steg


def _mash_key(at, felt, indeks):
    revisjon = at.session_state["_process_widget_revision"]
    return f"mash_{felt}_{revisjon}_{indeks}"


def _ny_at():
    at = AppTest.from_file(_APP)
    at.run()
    return at


class TestByttMellomProfilerIPanelet(unittest.TestCase):
    """Krav 1-3 og 6-7: bytte av standardprofil via selectboxen skal
    erstatte HELE steglisten, uansett hvor mange ganger det byttes."""

    def test_enkel_infusjon_til_hochkurz_erstatter_hele_steglisten(self):
        at = _ny_at()
        at.selectbox(key="valgt_prosess_id").select("enkel_infusjon").run()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        self.assertEqual(_steg(at), [(63.0, 40), (70.0, 30), (77.0, 10)])
        self.assertNotIn((66.0, 60), _steg(at))
        self.assertNotIn((78.0, 5), _steg(at))

    def test_hochkurz_til_enkel_infusjon_erstatter_hele_steglisten(self):
        at = _ny_at()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        at.selectbox(key="valgt_prosess_id").select("enkel_infusjon").run()
        self.assertEqual(_steg(at), [(66.0, 60), (78.0, 5)])

    def test_ingen_steg_dupliseres_ved_gjentatte_bytter(self):
        at = _ny_at()
        for pid in ("hochkurz", "enkel_infusjon", "hochkurz", "enkel_dekoksjon", "hochkurz"):
            at.selectbox(key="valgt_prosess_id").select(pid).run()
        self.assertEqual(len(_steg(at)), 3)
        self.assertEqual(_steg(at), [(63.0, 40), (70.0, 30), (77.0, 10)])

    def test_bytte_etter_redigering_gir_fortsatt_rent_hochkurz(self):
        # Brukeren redigerer et steg på enkel infusjon FØR bytte til
        # Hochkurz — de redigerte verdiene skal ikke lekke inn i Hochkurz.
        at = _ny_at()
        at.number_input(key=_mash_key(at, "temp", 0)).set_value(68.0).run()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        self.assertEqual(_steg(at), [(63.0, 40), (70.0, 30), (77.0, 10)])
        self.assertEqual(_widget_steg(at), [(63.0, 40), (70.0, 30), (77.0, 10)])


class TestStandardprofilerMuteresAldriAvUI(unittest.TestCase):
    """Krav 4: standardprofilene i modules/process_profiles.py skal aldri
    kunne muteres via UI-redigering av den AKTIVE profilen."""

    def test_redigering_i_panelet_paavirker_ikke_standardmalen(self):
        at = _ny_at()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        at.number_input(key=_mash_key(at, "temp", 0)).set_value(61.0).run()
        original = hent_standardprofil("hochkurz")
        self.assertEqual(original["mash_steps"][0]["temperatur"], 63.0)
        self.assertEqual(original["mash_steps"][1]["temperatur"], 70.0)
        self.assertEqual(original["mash_steps"][2]["temperatur"], 77.0)


class TestNavnOgMashStepsSamsvarer(unittest.TestCase):
    """Krav 5: eksportert profilnavn og eksporterte mash_steps skal alltid
    komme fra samme aktive profil — aldri en blanding."""

    def test_navn_og_steg_samsvarer_for_alle_standardprofiler(self):
        at = _ny_at()
        for pid in ("hochkurz", "enkel_dekoksjon", "enkel_infusjon", "reiterated_mash", "hochkurz"):
            at.selectbox(key="valgt_prosess_id").select(pid).run()
            aktiv = at.session_state["aktiv_prosessprofil"]
            forventet = hent_standardprofil(pid)
            self.assertEqual(aktiv["navn"], forventet["navn"])
            self.assertEqual(
                [(s["temperatur"], s["varighet"]) for s in aktiv["mash_steps"]],
                [(s["temperatur"], s["varighet"]) for s in forventet["mash_steps"]],
                f"mash_steps samsvarte ikke med navnet for process_id={pid}",
            )

    def test_aktiv_profil_mash_steps_er_uavhengig_kopi(self):
        # aktiv_prosessprofil["mash_steps"] skal IKKE være samme listeobjekt
        # som panelets egen prosess_mash_steps (ellers kan senere UI-
        # redigering stille mutere en allerede "lagret" profil).
        at = _ny_at()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        aktiv_mash_steps = at.session_state["aktiv_prosessprofil"]["mash_steps"]
        self.assertIsNot(aktiv_mash_steps, at.session_state["prosess_mash_steps"])


class TestLagreOgGjenaapneBeholderKorrektProfilPanel(unittest.TestCase):
    """Krav 8: å laste en annen (lagret) oppskrift skal gi panelet den
    lastede oppskriftens FAKTISKE prosessprofil — ikke la panelets eget,
    gamle utvalg overskrive den nylig lastede profilen.

    Dette simulerer nøyaktig hva ui/sidebar.py gjør ved lasting: setter
    st.session_state["aktiv_prosessprofil"] direkte (uten å gå via
    selectboxen) og trigger en rerun."""

    def test_lasting_av_annen_oppskrift_synker_panelet_til_riktig_profil(self):
        at = _ny_at()
        # Brukeren har fra før stått på "Enkel infusjon" for en annen/ny oppskrift.
        at.selectbox(key="valgt_prosess_id").select("enkel_infusjon").run()
        self.assertEqual(_steg(at), [(66.0, 60), (78.0, 5)])

        # En lagret oppskrift med Hochkurz-profil blir aktiv (som ved lasting
        # via sidebaren) — UTEN å bruke selectboxen.
        lagret_hochkurz = hent_standardprofil("hochkurz")
        at.session_state["aktiv_prosessprofil"] = lagret_hochkurz
        at.session_state["_last_loaded_recipe"] = "En annen lagret oppskrift"
        at.run()

        self.assertEqual(at.session_state["valgt_prosess_id"], "hochkurz")
        aktiv = at.session_state["aktiv_prosessprofil"]
        self.assertEqual(aktiv["navn"], "Hochkurz (stegmesk)")
        self.assertEqual(
            [(s["temperatur"], s["varighet"]) for s in aktiv["mash_steps"]],
            [(63.0, 40), (70.0, 30), (77.0, 10)],
        )
        # Ingen rester av den forrige Enkel infusjon-profilen.
        self.assertNotIn((66.0, 60), _steg(at))
        self.assertNotIn((78.0, 5), _steg(at))

    def test_lasting_av_egendefinert_lagret_profil_beholder_brukerens_egne_steg(self):
        # Krav: egendefinerte steg (process_id == "egendefinert") ER selve
        # poenget med Egendefinert-profilen, og skal beholdes uendret ved
        # lasting.
        at = _ny_at()
        egendefinert_lagret = {
            "process_id": "egendefinert",
            "navn": "Egendefinert prosess",
            "beskrivelse": "", "vanskelighetsgrad": "Middels",
            "mash_steps": [
                {"temperatur": 62.0, "varighet": 45, "stegtype": "infusjon", "kommentar": "Justert"},
                {"temperatur": 71.0, "varighet": 25, "stegtype": "infusjon", "kommentar": ""},
                {"temperatur": 77.0, "varighet": 10, "stegtype": "mashout", "kommentar": ""},
            ],
            "sparge_method": "batch_sparge", "boil_minutes": 60,
            "decoction_steps": None, "reiterated_mash": None,
            "anbefalte_stiler": [], "utstyrsbegrensninger": "", "forventet_paavirkning": "",
            "ekstra_tid_min": 0, "brukernotater": "Mine egne justeringer",
        }
        at.session_state["aktiv_prosessprofil"] = egendefinert_lagret
        at.session_state["_last_loaded_recipe"] = "Oppskrift med egendefinert prosess"
        at.run()

        self.assertEqual(_steg(at), [(62.0, 45), (71.0, 25), (77.0, 10)])
        self.assertEqual(at.session_state["prosess_brukernotater"], "Mine egne justeringer")

    def test_korrupt_lagret_standardprofil_helbredes_ved_lasting(self):
        # Krav 6+7 (hardnet mot restart/hot-reload-persistens): en lagret
        # ELLER allerede aktiv profil som PÅSTÅR å være en standardprofil
        # (process_id="hochkurz") men bærer en avvikende/korrupt
        # meskeplan — f.eks. rester fra en eldre, nå rettet bug, eller en
        # hånd-redigert/korrupt oppskriftsfil — skal ALDRI vises som-is.
        # Kun en EKTE Egendefinert-profil får lov til å avvike fra malen.
        at = _ny_at()
        korrupt_hochkurz = {
            "process_id": "hochkurz", "navn": "Hochkurz (stegmesk)",
            "beskrivelse": "", "vanskelighetsgrad": "Middels",
            "mash_steps": [
                {"temperatur": 66.0, "varighet": 60, "stegtype": "infusjon", "kommentar": "Hovedmesk"},
                {"temperatur": 78.0, "varighet": 5,  "stegtype": "mashout",  "kommentar": "Mashout"},
                {"temperatur": 77.0, "varighet": 10, "stegtype": "mashout",  "kommentar": "Mashout"},
            ],
            "sparge_method": "batch_sparge", "boil_minutes": 60,
            "decoction_steps": None, "reiterated_mash": None,
            "anbefalte_stiler": [], "utstyrsbegrensninger": "", "forventet_paavirkning": "",
            "ekstra_tid_min": 20, "brukernotater": "Mine notater overlever",
        }
        at.session_state["aktiv_prosessprofil"] = korrupt_hochkurz
        at.session_state["_last_loaded_recipe"] = "Oppskrift med korrupt lagret Hochkurz"
        at.run()

        self.assertEqual(_steg(at), [(63.0, 40), (70.0, 30), (77.0, 10)])
        self.assertNotIn((66.0, 60), _steg(at))
        self.assertNotIn((78.0, 5), _steg(at))
        aktiv = at.session_state["aktiv_prosessprofil"]
        self.assertEqual(aktiv["navn"], "Hochkurz (stegmesk)")
        self.assertEqual(
            [(s["temperatur"], s["varighet"]) for s in aktiv["mash_steps"]],
            [(63.0, 40), (70.0, 30), (77.0, 10)],
        )
        # Fritekst-notatet er ufarlig og overlever likevel.
        self.assertEqual(at.session_state["prosess_brukernotater"], "Mine notater overlever")

    def test_poisonet_session_state_helbredes_etter_simulert_hot_reload(self):
        # Simulerer nøyaktig det brukeren rapporterte: en KJØRENDE
        # Streamlit-sesjon (session_state overlever et hot-reload/en
        # kodeendring, siden det er bundet til nettleser-sesjonen, ikke
        # til den kjørende koden) som fra FØR har en korrupt/hybrid
        # aktiv_prosessprofil liggende — bygget av EN TIDLIGERE, allerede
        # rettet bug. Det neste reruns (som med den rettede koden) skal
        # ALDRI videreføre denne hybriden.
        at = _ny_at()
        at.session_state["_last_loaded_recipe"] = "Poisonet oppskrift"
        at.session_state["aktiv_prosessprofil"] = {
            "process_id": "hochkurz", "navn": "Hochkurz (stegmesk)",
            "beskrivelse": "", "vanskelighetsgrad": "Middels",
            "mash_steps": [
                {"temperatur": 66.0, "varighet": 60, "stegtype": "infusjon", "kommentar": "Hovedmesk"},
                {"temperatur": 78.0, "varighet": 5,  "stegtype": "mashout",  "kommentar": "Mashout"},
                {"temperatur": 77.0, "varighet": 10, "stegtype": "mashout",  "kommentar": "Mashout"},
            ],
            "sparge_method": "batch_sparge", "boil_minutes": 60,
            "decoction_steps": None, "reiterated_mash": None,
            "anbefalte_stiler": [], "utstyrsbegrensninger": "", "forventet_paavirkning": "",
            "ekstra_tid_min": 20, "brukernotater": "",
        }
        at.run()

        self.assertEqual(_steg(at), [(63.0, 40), (70.0, 30), (77.0, 10)])
        self.assertNotIn((66.0, 60), _steg(at))
        self.assertNotIn((78.0, 5), _steg(at))


class TestWidgetVisningSamsvarerMedData(unittest.TestCase):
    """Regresjon for den ferskeste, rapporterte bug'en: prosessdataene
    (session_state["aktiv_prosessprofil"], ctx, eksport) var bevist
    korrekte, men de REDIGERBARE MESKESTEG-WIDGETENE viste fortsatt gamle
    verdier — fordi widget-nøklene (prosess_steg_{i}_...) var faste og
    Streamlit prioriterer en widgets EGEN lagrede verdi over `value=` så
    lenge nøkkelen ikke er fysisk forskjellig. Løst med revisjonsnøkler
    (mash_temp_{revisjon}_{i} osv., se _ny_widget_revisjon() i
    ui/process_panel.py) — disse testene leser widgetverdiene DIREKTE
    (via _widget_steg()), ikke bare session_state."""

    def test_gammel_oppskrift_uten_profil_velg_hochkurz_viser_kanonisk_i_widgetene(self):
        at = _ny_at()
        # Ingen aktiv_prosessprofil i det hele tatt (som en gammel
        # oppskrift lagret før feltet eksisterte).
        at.selectbox(key="valgt_prosess_id").select("enkel_infusjon").run()
        self.assertEqual(_widget_steg(at), [(66.0, 60), (78.0, 5)])

        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        self.assertEqual(_widget_steg(at), [(63.0, 40), (70.0, 30), (77.0, 10)])
        self.assertEqual(_widget_steg(at), _steg(at))

    def test_korrupt_hochkurz_i_session_state_uten_nytt_oppskriftsbytte_reparerer_widgetene(self):
        # Nøyaktig gapet som ble avdekket: aktiv_prosessprofil er korrupt,
        # MEN _last_loaded_recipe er UENDRET (ingen "ny oppskrift lastet"
        # detekteres) — kandidaten må likevel sammenlignes mot sin egen
        # normaliserte form og repareres.
        at = _ny_at()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        # Simulerer at NOE ANNET (f.eks. ui/brewday_panel.py) korrigerte
        # aktiv_prosessprofil-INNHOLDET uten å gå via denne selectboxen —
        # eller at en poisonet verdi fra FØR denne rettelsen henger igjen.
        at.session_state["aktiv_prosessprofil"] = {
            "process_id": "hochkurz", "navn": "Hochkurz (stegmesk)",
            "beskrivelse": "", "vanskelighetsgrad": "Middels",
            "mash_steps": [
                {"temperatur": 66.0, "varighet": 60, "stegtype": "infusjon", "kommentar": "Hovedmesk"},
                {"temperatur": 78.0, "varighet": 5,  "stegtype": "mashout",  "kommentar": "Mashout"},
                {"temperatur": 77.0, "varighet": 10, "stegtype": "mashout",  "kommentar": "Mashout"},
            ],
            "sparge_method": "batch_sparge", "boil_minutes": 60,
            "decoction_steps": None, "reiterated_mash": None,
            "anbefalte_stiler": [], "utstyrsbegrensninger": "", "forventet_paavirkning": "",
            "ekstra_tid_min": 20, "brukernotater": "",
        }
        at.run()  # ingen selectbox-endring, ingen _last_loaded_recipe-endring

        self.assertEqual(_widget_steg(at), [(63.0, 40), (70.0, 30), (77.0, 10)])
        self.assertNotIn((66.0, 60), _widget_steg(at))
        self.assertNotIn((78.0, 5), _widget_steg(at))

    def test_enkel_infusjon_til_hochkurz_fjerner_gamle_steg_fra_widgetene(self):
        at = _ny_at()
        at.selectbox(key="valgt_prosess_id").select("enkel_infusjon").run()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        widget_steg = _widget_steg(at)
        self.assertNotIn((66.0, 60), widget_steg)
        self.assertNotIn((78.0, 5), widget_steg)
        self.assertEqual(widget_steg, [(63.0, 40), (70.0, 30), (77.0, 10)])

    def test_hochkurz_til_enkel_infusjon_fjerner_gamle_steg_fra_widgetene(self):
        at = _ny_at()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        at.selectbox(key="valgt_prosess_id").select("enkel_infusjon").run()
        widget_steg = _widget_steg(at)
        self.assertNotIn((63.0, 40), widget_steg)
        self.assertNotIn((70.0, 30), widget_steg)
        self.assertEqual(widget_steg, [(66.0, 60), (78.0, 5)])

    def test_gjentatte_bytter_gir_aldri_duplikater_i_widgetene(self):
        at = _ny_at()
        for pid in ("hochkurz", "enkel_infusjon", "hochkurz", "enkel_dekoksjon", "reiterated_mash", "hochkurz"):
            at.selectbox(key="valgt_prosess_id").select(pid).run()
        widget_steg = _widget_steg(at)
        self.assertEqual(len(widget_steg), 3)
        self.assertEqual(widget_steg, [(63.0, 40), (70.0, 30), (77.0, 10)])

    def test_widgetverdier_aktiv_profil_og_session_state_er_identiske(self):
        at = _ny_at()
        at.selectbox(key="valgt_prosess_id").select("enkel_infusjon").run()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()

        widget_steg = _widget_steg(at)
        session_steg = _steg(at)
        aktiv_steg = [
            (s["temperatur"], s["varighet"])
            for s in at.session_state["aktiv_prosessprofil"]["mash_steps"]
        ]
        self.assertEqual(widget_steg, session_steg)
        self.assertEqual(session_steg, aktiv_steg)

    def test_egendefinerte_steg_beholdes_i_widgetene(self):
        at = _ny_at()
        egendefinert_lagret = {
            "process_id": "egendefinert", "navn": "Min egen prosess",
            "beskrivelse": "", "vanskelighetsgrad": "Middels",
            "mash_steps": [
                {"temperatur": 62.0, "varighet": 45, "stegtype": "infusjon", "kommentar": "Justert"},
                {"temperatur": 71.0, "varighet": 25, "stegtype": "infusjon", "kommentar": ""},
            ],
            "sparge_method": "batch_sparge", "boil_minutes": 60,
            "decoction_steps": None, "reiterated_mash": None,
            "anbefalte_stiler": [], "utstyrsbegrensninger": "", "forventet_paavirkning": "",
            "ekstra_tid_min": 0, "brukernotater": "",
        }
        at.session_state["aktiv_prosessprofil"] = egendefinert_lagret
        at.session_state["_last_loaded_recipe"] = "Oppskrift med egendefinert prosess"
        at.run()

        self.assertEqual(_widget_steg(at), [(62.0, 45), (71.0, 25)])


class TestAutomatiskForfremmelseTilEgendefinert(unittest.TestCase):
    """Krav 8: redigerer brukeren et meskesteg i en STANDARDPROFIL (uten
    å eksplisitt velge Egendefinert), skal profilen automatisk forfremmes
    til en Egendefinert-variant, slik at redigeringen ikke senere
    overskrives av den (bevisst alltid kanoniske) standardprofilen."""

    def test_redigering_av_hochkurz_steg_forfremmer_til_egendefinert(self):
        at = _ny_at()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        at.number_input(key=_mash_key(at, "temp", 0)).set_value(61.0).run()

        self.assertEqual(at.session_state["valgt_prosess_id"], "egendefinert")
        aktiv = at.session_state["aktiv_prosessprofil"]
        self.assertEqual(aktiv["navn"], "Egendefinert – basert på Hochkurz (stegmesk)")
        self.assertEqual(_steg(at), [(61.0, 40), (70.0, 30), (77.0, 10)])
        self.assertEqual(_widget_steg(at), [(61.0, 40), (70.0, 30), (77.0, 10)])

    def test_forfremmet_profil_overskrives_ikke_ved_senere_reparasjonssjekk(self):
        at = _ny_at()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        at.number_input(key=_mash_key(at, "temp", 0)).set_value(61.0).run()
        # En senere, ubeslektet rerun (f.eks. en annen widget-interaksjon)
        # skal IKKE tilbakestille den forfremmede, redigerte profilen.
        at.checkbox(key="prosess_historisk_autentisitet").set_value(True).run()
        self.assertEqual(_steg(at), [(61.0, 40), (70.0, 30), (77.0, 10)])


if __name__ == "__main__":
    unittest.main()
