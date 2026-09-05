"""
Sóti -- lokal sesjonstilstand. Ingen skytjeneste, ingen kontosystem: en
SotiSession er et rent in-memory objekt eid av kallende kode (f.eks. en
kommende Streamlit-side, eller en test) -- konsistent med det lokale
tillitsgrensen denne MVP-runden krever. To sesjoner deler aldri tilstand;
en SotiSession vet ikke noe om noen annen.
"""
from dataclasses import dataclass, field


@dataclass
class SotiSession:
    session_id: str
    historikk: list = field(default_factory=list)

    def legg_til(self, rolle, innhold):
        self.historikk.append({"role": rolle, "content": innhold})

    def meldinger(self):
        return list(self.historikk)
