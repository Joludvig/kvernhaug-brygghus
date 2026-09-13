#!/usr/bin/env python3
"""
Kvernhaug HO router -- foreldreløst sjekkpunkt-diagnose (issue #252).

BAKGRUNN: #152 er den ene kanoniske HO-ruteren (se AGENT_WORKFLOW.md
"HO policy -- local and GitHub jobs"). Ruten er en kommentarlinje på
#152:
    KBH_COS_CHECKPOINT_PTR_V1 issue=<N> comment=<M>
som peker på et sjekkpunkt markert `KBH_COS_LIVE_CHECKPOINT_V1` på
issue #N, kommentar #M. Observert 2026-09-13 (issue #252): et nyere
sjekkpunkt ble publisert på mål-issuen uten at en matchende, nyere
pointer-linje ble lagt til #152 -- ruteren pekte dermed på et utdatert
sjekkpunkt selv om et ferskere fantes rett ved siden av det, på samme
issue. Denne modulen er et lite, rent diagnoseverktøy en Claude-økt
(lokal eller Bridge) kan kjøre manuelt for å oppdage NØYAKTIG den
klassen avvik, gitt data den allerede har hentet via `gh issue view`.

DETTE ER IKKE en workflow-hook. Den er IKKE koblet til
claude-agent-bridge.yml, har ingen `on:`-trigger, og kalles ikke
automatisk av noe CI-steg -- den bevæpner ingenting (issue #252s eget
"do not arm automatically"-krav). Den er et frittstående, manuelt
kjørbart hjelpemiddel, akkurat som resten av HO-policyen selv utføres
manuelt av den kjørende Claude-økten, ikke av workflow-kode.

Ingen `gh`/GitHub-avhengighet i selve modulen -- ren stdlib-Python som
tar allerede hentede kommentar-bodyer som input, nøyaktig samme mønster
som de andre `.github/scripts`-modulene (f.eks. `chief_ready_signal.py`)
bruker for sine rene beslutningsfunksjoner.

CLI-bruk (manuelt, ikke fra en workflow):
    jq -n '{pointer_comments: ["...", ...],
            target_issue: 196,
            target_issue_comments: [{"id": 123, "body": "..."}, ...]}' \\
      | python3 .github/scripts/ho_router_orphan_check.py
Skriver `orphan=true|false` og en begrunnelse. Exit 1 kun når et
foreldreløst sjekkpunkt faktisk oppdages (eller pointeren/sjekkpunktet
mangler helt) -- se `finn_foreldrelos_sjekkpunkt` under for de eksakte
betingelsene. En rein feil i selve invocasjonen (ugyldig JSON) gir
exit 2.
"""
import json
import re
import sys

POINTER_MARKER_RE = re.compile(
    r"(?m)^KBH_COS_CHECKPOINT_PTR_V1 issue=(?P<issue>\d+) comment=(?P<comment>\d+)$"
)
CHECKPOINT_MARKER_RE = re.compile(r"(?m)^KBH_COS_LIVE_CHECKPOINT_V1\b")


def finn_nyeste_pointer(pointer_kommentarer):
    """`pointer_kommentarer`: kronologisk liste av #152-kommentar-bodyer.
    Returnerer (issue, comment) for den SISTE gyldige pointer-linjen
    funnet (nyeste vinner, samme regel som HO ROUTER CONTRACT V1 selv
    bruker), eller None hvis ingen gyldig linje finnes i det hele
    tatt."""
    nyeste = None
    for body in pointer_kommentarer or []:
        for m in POINTER_MARKER_RE.finditer(body or ""):
            nyeste = (int(m.group("issue")), int(m.group("comment")))
    return nyeste


def er_sjekkpunkt_kommentar(body):
    """True kun for en kommentar som faktisk inneholder den reserverte
    `KBH_COS_LIVE_CHECKPOINT_V1`-markøren -- sitater/omtaler av markøren
    uten selve linjen teller ikke (samme filosofi som de andre
    markør-parserne i denne pakken: linje-ankret, ikke fritekst-søk)."""
    return bool(CHECKPOINT_MARKER_RE.search(body or ""))


def finn_foreldrelos_sjekkpunkt(*, pointer_kommentarer, mal_issue_nummer, mal_issue_kommentarer):
    """
    `pointer_kommentarer`: kronologisk liste av #152-kommentar-bodyer.
    `mal_issue_nummer`: issue-nummeret den nyeste pointeren PÅSTÅR å
        peke på (caller sitt ansvar å hente riktig issue -- se
        AGENT_WORKFLOW.md "Canonical structure and compatibility").
    `mal_issue_kommentarer`: kronologisk liste av
        {"id": <positivt heltall>, "body": <str>} for kommentarer på
        `mal_issue_nummer`.

    Returnerer (foreldrelos: bool, begrunnelse: str, nyeste_pointer,
    nyeste_sjekkpunkt_id). `foreldrelos=True` dekker BÅDE "et nyere
    sjekkpunkt uten matchende pointer finnes" (selve issue #252-
    hendelsen) OG "pointeren/sjekkpunktet mangler eller er tvetydig" --
    begge er samme fail-closed utfall for HO-policyen: "defer the
    write and report the problem" (AGENT_WORKFLOW.md).
    """
    nyeste_pointer = finn_nyeste_pointer(pointer_kommentarer)
    if nyeste_pointer is None:
        return (
            True,
            "Ingen gyldig KBH_COS_CHECKPOINT_PTR_V1-linje funnet på #152 -- "
            "routen kan ikke bekreftes.",
            None,
            None,
        )
    pointer_issue, pointer_comment = nyeste_pointer

    nyeste_sjekkpunkt_id = None
    for rad in mal_issue_kommentarer or []:
        if er_sjekkpunkt_kommentar(rad.get("body")):
            kandidat_id = int(rad["id"])
            if nyeste_sjekkpunkt_id is None or kandidat_id > nyeste_sjekkpunkt_id:
                nyeste_sjekkpunkt_id = kandidat_id

    if nyeste_sjekkpunkt_id is None:
        return (
            True,
            f"Fant ingen KBH_COS_LIVE_CHECKPOINT_V1-markør blant de oppgitte "
            f"kommentarene på issue #{mal_issue_nummer}.",
            nyeste_pointer,
            None,
        )

    if pointer_issue != mal_issue_nummer:
        return (
            True,
            f"Nyeste pointer på #152 peker på issue #{pointer_issue}, ikke det "
            f"oppgitte mål-issuet #{mal_issue_nummer} -- avklar riktig mål før "
            "videre sjekk.",
            nyeste_pointer,
            nyeste_sjekkpunkt_id,
        )

    if nyeste_sjekkpunkt_id != pointer_comment:
        return (
            True,
            f"Foreldreløst sjekkpunkt: nyeste KBH_COS_LIVE_CHECKPOINT_V1 på "
            f"issue #{mal_issue_nummer} er comment={nyeste_sjekkpunkt_id}, men "
            f"nyeste pointer på #152 peker fortsatt på comment={pointer_comment}. "
            "Legg til en ny pointer-linje på #152 før dette sjekkpunktet "
            "behandles som rutet/current.",
            nyeste_pointer,
            nyeste_sjekkpunkt_id,
        )

    return (
        False,
        f"Nyeste pointer (issue={pointer_issue} comment={pointer_comment}) "
        "matcher nyeste sjekkpunkt-kommentar på mål-issuet -- ingen "
        "foreldreløshet oppdaget.",
        nyeste_pointer,
        nyeste_sjekkpunkt_id,
    )


def main(argv):
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        print("ugyldig JSON på stdin", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("forventet et JSON-objekt på stdin", file=sys.stderr)
        return 2

    foreldrelos, begrunnelse, nyeste_pointer, nyeste_sjekkpunkt_id = finn_foreldrelos_sjekkpunkt(
        pointer_kommentarer=data.get("pointer_comments"),
        mal_issue_nummer=data.get("target_issue"),
        mal_issue_kommentarer=data.get("target_issue_comments"),
    )

    print(begrunnelse, file=sys.stderr)
    print(f"orphan={'true' if foreldrelos else 'false'}")
    if nyeste_pointer is not None:
        print(f"pointer_issue={nyeste_pointer[0]}")
        print(f"pointer_comment={nyeste_pointer[1]}")
    if nyeste_sjekkpunkt_id is not None:
        print(f"newest_checkpoint_comment={nyeste_sjekkpunkt_id}")
    print(f"reason={begrunnelse}")

    return 1 if foreldrelos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
