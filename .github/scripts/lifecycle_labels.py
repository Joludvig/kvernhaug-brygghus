#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge V1 -- eksklusiv livssyklus-etikett-overgang.

Chief review-fiks (PR #7, blokkerende punkt 2): `status:*`-etikettene
BESKRIVER EN TILSTAND, og en issue skal derfor aldri kunne bære to av
dem samtidig. Den opprinnelige workflowen la bare til den nye og fjernet
kun den ENE som trigget kjøringen -- så en helt normal review-runde
(`status:review` -> owner legger på `status:changes-requested` ->
workflow legger på `status:working`) endte med issuen merket BÅDE
`review` OG `working`, og etter suksess fortsatt `review` i tillegg til
den nye `review` (altså en selv-korrumperende tilstandsmaskin).

Denne modulen er DEN ENE kilden for hvordan etikettsettet ser ut etter
en overgang: ALLE livssyklus-etiketter fjernes, nøyaktig ÉN legges til,
og alt annet (agent:claude, area:*, og evt. andre etiketter repoet
bruker) beholdes uendret og i uendret rekkefølge -- livssyklusen er
eksklusiv, resten er additiv.

Ren, avhengighetsfri Python (kun stdlib) -- kalles både fra
.github/workflows/claude-agent-bridge.yml (via `python3`, som finnes
ferdig på ubuntu-latest-runnere) og fra tests/test_agent_bridge_labels.py,
slik at selve overgangslogikken er enhetstestbar uten å kjøre noe mot
GitHub i det hele tatt.

CLI-bruk (det workflowen gjør):
    gh issue view N --json labels -q '[.labels[].name]' \
      | python3 .github/scripts/lifecycle_labels.py status:working
Skriver ut en ferdig request-body for
`gh api --method PUT repos/{owner}/{repo}/issues/{n}/labels`:
    {"labels": ["agent:claude", "area:infra", "status:working"]}
"""
import json
import sys

# Alle etikettene som BESKRIVER en tilstand i tilstandsmaskinen (se
# docs/development/AGENT_WORKFLOW.md). Nøyaktig én av disse skal finnes
# på en issue om gangen.
LIVSSYKLUS_ETIKETTER = (
    "status:ready",
    "status:working",
    "status:review",
    "status:changes-requested",
    "status:approved",
)


def neste_etiketter(gjeldende, maal):
    """
    Returnerer det KOMPLETTE etikettsettet etter en overgang til `maal`.

    - Alle livssyklus-etiketter fjernes (uansett hvilke som lå der).
    - `maal` legges til én gang, sist.
    - Alle andre etiketter beholdes, i uendret rekkefølge, uten
      duplikater.

    `maal=None` betyr "fjern alle livssyklus-etiketter, ikke legg til
    noen" -- ikke brukt av workflowen i dag, men gjør funksjonen
    fullstendig og testbar for opprydding.
    """
    if maal is not None and maal not in LIVSSYKLUS_ETIKETTER:
        raise ValueError(
            f"{maal!r} er ikke en livssyklus-etikett. Gyldige: {list(LIVSSYKLUS_ETIKETTER)}"
        )

    beholdt = []
    for etikett in gjeldende:
        if etikett in LIVSSYKLUS_ETIKETTER:
            continue  # eksklusiv: enhver gammel tilstand fjernes
        if etikett in beholdt:
            continue  # ingen duplikater
        beholdt.append(etikett)

    if maal is not None:
        beholdt.append(maal)
    return beholdt


def main(argv):
    if len(argv) != 2:
        print(
            "bruk: lifecycle_labels.py <status:etikett>   (leser gjeldende etiketter som JSON-array på stdin)",
            file=sys.stderr,
        )
        return 2
    maal = argv[1]
    gjeldende = json.load(sys.stdin)
    if not isinstance(gjeldende, list):
        print("stdin må være et JSON-array med etikettnavn.", file=sys.stderr)
        return 2
    try:
        nye = neste_etiketter(gjeldende, maal)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    json.dump({"labels": nye}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
