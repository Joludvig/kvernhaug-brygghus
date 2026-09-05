"""
Sóti -- runtime. Kobler sammen en ModelProvider (soti.providers), en
identitet (soti.identity), en skills verktøytilgang (soti.skills) og
lokal sesjonstilstand (soti.session) til én løkke: ta imot en
brukermelding, returner et svar -- ev. via ett verktøykall underveis.
Provider-/modellvalg skjer utelukkende ved injeksjon i __init__; denne
modulen hardkoder aldri ett bestemt provider- eller modellnavn.
"""
from soti.identity import bygg_system_melding
from soti.skills import BRYGGE_OPPSLAG_SKILL, registry_for_skill

# Tak på antall verktøykall-runder per henvendelse -- unngår en uendelig
# løkke hvis provideren stadig ber om nye verktøykall i stedet for å
# levere et endelig tekstsvar.
MAKS_VERKTOY_RUNDER = 2


class SotiRuntime:
    def __init__(self, provider, skill=BRYGGE_OPPSLAG_SKILL):
        self._provider = provider
        self._skill = skill
        self._registry = registry_for_skill(skill)

    def handle_message(self, session, bruker_tekst):
        """Legger brukermeldingen til sesjonen, kjører provider-/verktøy-
        løkken, legger det endelige svaret til sesjonen, og returnerer det
        som en ren tekststreng."""
        if not session.historikk:
            session.legg_til("system", bygg_system_melding(self._skill.instruksjoner))
        session.legg_til("user", bruker_tekst)

        verktoy = self._registry.alle()
        svar = None
        for _ in range(MAKS_VERKTOY_RUNDER):
            svar = self._provider.generate(session.meldinger(), verktoy)
            if svar.tool_kall is None:
                session.legg_til("assistant", svar.tekst)
                return svar.tekst
            resultat = self._registry.utfoer(svar.tool_kall.navn, svar.tool_kall.argumenter)
            session.legg_til("tool", f"[{svar.tool_kall.navn}] {resultat}")

        # Tak nådd uten et endelig tekstsvar -- fail-visible i stedet for
        # en uendelig løkke eller et stille tomt svar.
        fallback = "Sóti nådde grensen for verktøykall-runder uten et endelig svar."
        session.legg_til("assistant", fallback)
        return fallback
