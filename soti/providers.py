"""
Sóti -- modell-/runtime-provider-abstraksjon. Definerer grensesnittet
soti.runtime.SotiRuntime bruker til å snakke med en språkmodell, slik at
selve runtime-løkken aldri er bundet til ett bestemt provider- eller
modellvalg (provider velges ved injeksjon, se SotiRuntime.__init__ --
denne modulen hardkoder ingen). En ekte lokal/ekstern provider (Ollama,
llama.cpp, en API-klient, ...) implementeres som en egen ModelProvider-
underklasse senere; denne MVP-runden leverer kun grensesnittet pluss en
deterministisk test-/utviklingsprovider, slik at repoets testsuite aldri
trenger å laste ned eller kjøre en ekte modell.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolKall:
    """Ett modell-forespurt kall til et registrert verktøy (se
    soti.tools.ToolRegistry)."""
    navn: str
    argumenter: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderSvar:
    """Ett modellsvar: enten ren tekst (tool_kall er None), eller ett
    verktøykall runtime skal utføre før den spør modellen på nytt med
    resultatet lagt til meldingslisten."""
    tekst: str = ""
    tool_kall: ToolKall = None


class ModelProvider(ABC):
    """Grensesnitt enhver modell-/runtime-backend må implementere for å
    kunne brukes av SotiRuntime."""

    @abstractmethod
    def generate(self, meldinger, verktoy):
        """meldinger: liste av {"role": "system"|"user"|"assistant"|"tool", "content": str},
        i kronologisk rekkefølge. verktoy: liste av soti.tools.Tool
        tilgjengelig for denne henvendelsen (kan være tom). Returnerer ett
        ProviderSvar."""
        raise NotImplementedError


class MockProvider(ModelProvider):
    """Deterministisk test-/utviklingsprovider -- ingen nettverkskall,
    ingen modellnedlasting. Scriptbar via `svar_regler`: en liste av
    (gjenkjenner, fabrikk)-par som prøves i rekkefølge mot hele
    meldingslisten; første regel der gjenkjenner(meldinger) er sann,
    vinner, og fabrikk(meldinger) bygger ProviderSvar-et. Faller tilbake
    til et fast ekko-svar hvis ingen regel treffer, slik at et
    ukonfigurert bruksmønster feiler synlig i stedet for å henge."""

    def __init__(self, svar_regler=None, fallback_tekst="Sóti (mock): ingen svarregel traff denne henvendelsen."):
        self._svar_regler = list(svar_regler or [])
        self._fallback_tekst = fallback_tekst
        self.kall_logg = []  # for tester: full historikk av meldingslister mottatt, i rekkefølge

    def generate(self, meldinger, verktoy):
        self.kall_logg.append(list(meldinger))
        for gjenkjenner, fabrikk in self._svar_regler:
            if gjenkjenner(meldinger):
                return fabrikk(meldinger)
        return ProviderSvar(tekst=self._fallback_tekst)
