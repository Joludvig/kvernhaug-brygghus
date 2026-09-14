#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- PÅ JOBB sekvensiell kø (issue #260).

BAKGRUNN: eieren vil kunne forhåndsgodkjenne flere avgrensede issues for
ubevoktet Claude-arbeid mens de er borte/sover ("PÅ JOBB"), uten å
risikere at flere Bridge-kjøringer starter samtidig (parallelle
scope-kollisjoner), eller at automasjonen får lov til å merge/deploye
på egen hånd. Køen legger derfor til NØYAKTIG ETT nytt lag foran den
eksisterende, allerede portvoktede Bridge-mekanikken (trigger_guard.py
/ lifecycle_labels.py / deliverable_guard.py) -- den endrer ingenting i
den mekanikken selv, og introduserer ingen ny merge/deploy-vei.

MODELL: to nye, additive etiketter (ikke en del av den eksklusive
`status:*`-livssyklusen fra lifecycle_labels.py):
  - `queue:pa-jobb`  -- markerer en issue som et køelement. Krever
                        ALLTID `agent:claude` i tillegg (samme
                        autorisasjonsgrense som resten av broen) -- en
                        issue med `queue:pa-jobb` men UTEN
                        `agent:claude` telles ikke som et køelement.
  - `queue:priority` -- valgfritt: flytter et køelement FØRST i køen
                        (blant andre `queue:priority`-elementer,
                        fortsatt i stigende issue-nummer-rekkefølge).
                        Dette er ownerens verktøy for å OMPRIORITERE
                        rekkefølgen uten å måtte endre issue-numre.

Et køelements TILSTAND leses av dets EKSISTERENDE `status:*`-etikett
(lifecycle_labels.py sitt eksklusive sett -- aldri en egen kø-tilstand):
  - ingen status:*-etikett              -> "ikke_startet" (venter i køen)
  - status:ready ELLER status:working   -> "aktiv"
  - status:changes-requested            -> "aktiv" (samme element venter
                                            på en NY Claude-runde --
                                            issue #260s "proposed queue
                                            model" er eksplisitt: køen
                                            skal PAUSE her, ikke gå
                                            videre til neste element)
  - status:review ELLER status:approved -> "ferdig" (Chief-review-løpet
                                            overtar herfra; blokkerer
                                            ALDRI neste køelement)

status:ready telles bevisst som "aktiv", ikke "ikke_startet": det er
akkurat det dispatcheren selv setter idet den bevæpner et element (se
pa-jobb-queue.yml), rett før den kaller
`gh workflow run claude-agent-bridge.yml`. Om selve dispatch-kallet
skulle feile ETTER at etiketten er satt, skal et duplikat-event ALDRI
bevæpne et nytt element eller dispatche på nytt for samme element --
fail-closed, ikke fail-open (issue #260, akseptansetest 7).

VALG: et NYTT element velges KUN når INGEN køelement er "aktiv". Om ett
er "aktiv" stopper hele køen der, uansett hvor mange andre
"ikke_startet"-elementer som venter -- det er nettopp "maks én aktiv
Bridge-kjøring om gangen"-kravet (issue #260, akseptansetest 3/4).
Når det IKKE finnes noe "aktivt" element, kan et nytt starte -- det
dekker både "forrige nådde status:review" (akseptansetest 5) og en helt
tom/fersk kø (akseptansetest 2).

Ren, avhengighetsfri stdlib-Python (samme mønster som resten av
.github/scripts/ -- ingen skript krysser-importerer et annet) -- selve
utvelgelseslogikken er enhetstestet i
tests/test_agent_bridge_queue_dispatch.py uten å kjøre noe mot GitHub.
Selve BEVÆPNINGEN (å sette status:ready) gjenbruker det EKSISTERENDE
`lifecycle_labels.py` (`... | python3 lifecycle_labels.py status:ready |
gh api --method PUT ...`, identisk mønster som claude-agent-bridge.yml
allerede bruker for status:working/status:review) -- ingen ny
etikett-overgangslogikk er skrevet for dette; se pa-jobb-queue.yml.

CLI-bruk (det workflowen gjør):
    gh issue list --repo "$REPO" --label queue:pa-jobb --state open \
      --json number,labels,state \
      --jq '[.[] | {number:.number, state:.state, labels:[.labels[].name]}]' \
      | python3 .github/scripts/queue_dispatch.py >> "$GITHUB_OUTPUT"
Skriver `dispatch=true`/`dispatch=false`, og `issue_number=<N>` når
`dispatch=true`, som GITHUB_OUTPUT-linjer på stdout, og en
menneskelesbar begrunnelse til stderr.
"""
import json
import sys

AGENT_ETIKETT = "agent:claude"
KO_ETIKETT = "queue:pa-jobb"
PRIORITET_ETIKETT = "queue:priority"

# Samme sett som lifecycle_labels.py sin LIVSSYKLUS_ETIKETTER --
# duplisert bevisst (samme mønster som deliverable_guard.py sin
# GYLDIGE_TRIGGER_ETIKETTER): hvert skript i .github/scripts/ er
# selvstendig og avhengighetsfritt.
LIVSSYKLUS_ETIKETTER = (
    "status:ready",
    "status:working",
    "status:review",
    "status:changes-requested",
    "status:approved",
)
AKTIVE_LIVSSYKLUS_ETIKETTER = ("status:ready", "status:working", "status:changes-requested")
FERDIGE_LIVSSYKLUS_ETIKETTER = ("status:review", "status:approved")


def er_ko_element(labels):
    """Et køelement krever BEGGE agent:claude og queue:pa-jobb -- samme
    autorisasjonsgrense som resten av broen (issue #260: "only
    pre-authorized bounded issues may enter queue")."""
    labels = set(labels or [])
    return AGENT_ETIKETT in labels and KO_ETIKETT in labels


def gjeldende_livssyklus(labels):
    """Returnerer den ene status:*-etiketten issuen bærer, eller None om
    ingen gjør det. lifecycle_labels.py garanterer at det aldri er mer
    enn én samtidig."""
    labels = list(labels or [])
    for etikett in LIVSSYKLUS_ETIKETTER:
        if etikett in labels:
            return etikett
    return None


def elementets_tilstand(labels):
    """"ikke_startet" | "aktiv" | "ferdig" -- se moduldoc for tabellen."""
    livssyklus = gjeldende_livssyklus(labels)
    if livssyklus is None:
        return "ikke_startet"
    if livssyklus in AKTIVE_LIVSSYKLUS_ETIKETTER:
        return "aktiv"
    return "ferdig"


def velg_neste(issues):
    """
    `issues`: liste av {"number": int, "state": "OPEN"/"CLOSED",
    "labels": [str, ...]} -- rå `gh issue list --label queue:pa-jobb`-
    utdata, normalisert til strengnavn.

    Returnerer (issue_number: int|None, begrunnelse: str).
    `issue_number` er None når køen ikke skal starte noe nytt element nå
    (tom kø, satt på pause av et aktivt element, eller ingen gyldig
    kandidat igjen) -- aldri et gjettet fallback-nummer.
    """
    ko = [
        i for i in (issues or [])
        if str(i.get("state", "OPEN")).upper() == "OPEN" and er_ko_element(i.get("labels", []))
    ]
    if not ko:
        return None, "Tom kø: ingen åpne issues har både agent:claude og queue:pa-jobb."

    aktive = [i for i in ko if elementets_tilstand(i.get("labels", [])) == "aktiv"]
    if aktive:
        blokkerer = sorted(aktive, key=lambda i: i["number"])[0]
        tilstand_etikett = gjeldende_livssyklus(blokkerer.get("labels", []))
        return (
            None,
            f"Køen er satt på pause: issue #{blokkerer['number']} er fortsatt aktiv "
            f"({tilstand_etikett}) -- maks én aktiv Bridge-kjøring om gangen.",
        )

    kandidater = [i for i in ko if elementets_tilstand(i.get("labels", [])) == "ikke_startet"]
    if not kandidater:
        return None, "Ingen nye kandidater: alle køelementer er allerede ferdige (status:review/status:approved)."

    def sorteringsnokkel(i):
        prioritert = 0 if PRIORITET_ETIKETT in (i.get("labels", []) or []) else 1
        return (prioritert, i["number"])

    vinner = sorted(kandidater, key=sorteringsnokkel)[0]
    return vinner["number"], f"Valgte issue #{vinner['number']} (neste i PÅ JOBB-køen)."


def main():
    try:
        raatekst = sys.stdin.read()
        issues = json.loads(raatekst) if raatekst.strip() else []
    except (TypeError, ValueError) as e:
        print(f"stdin er ikke gyldig JSON: {e}", file=sys.stderr)
        print("dispatch=false")
        return 2
    if not isinstance(issues, list):
        print("stdin må være et JSON-array med issue-objekter.", file=sys.stderr)
        print("dispatch=false")
        return 2

    issue_number, begrunnelse = velg_neste(issues)
    print(begrunnelse, file=sys.stderr)
    if issue_number is None:
        print("dispatch=false")
        return 0
    print("dispatch=true")
    print(f"issue_number={issue_number}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
