"""
Sóti -- AI/agent-domenet i Kvernhaug Brygghus (se
docs/development/KBH_CORE_CONTRACT.md §1: Sóti er et eget domene, ikke en
del av Core/App-Web/Bryggeskole/Brew Lab). Dette er den lokale Sóti
Runtime MVP-en: en modell-/provider-abstraksjon, en identitet atskilt fra
Core sin sannhet, ett skrivebeskyttet Core-verktøy, én bryggeskill, og
lokal, testbar sesjonstilstand.

Se docs/development/SOTI_MVP.md for akseptansekriterier, eksakte
testkommandoer og videreført MVP-arbeid.
"""
from soti.providers import ModelProvider, MockProvider, ProviderSvar, ToolKall
from soti.runtime import SotiRuntime
from soti.session import SotiSession

__all__ = [
    "ModelProvider",
    "MockProvider",
    "ProviderSvar",
    "ToolKall",
    "SotiRuntime",
    "SotiSession",
]
