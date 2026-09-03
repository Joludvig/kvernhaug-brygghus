#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- PR Draft-handoff ved changes-requested (issue #44).

BAKGRUNN: issue #44 erstatter den upålitelige kommentar-baserte
retry-vekkingen (chief_retry_signal.py, issue #40 -- FJERNET av denne
issuen; se AGENT_WORKFLOW.md "Deterministic Chief-ready retry signal
(V1, issue #40)" for den bevarte hendelses-/bevis-historikken) med en
tilstandsovergang på selve PR-en. Draft -> Ready for review er en EGEN
GitHub-hendelsesfamilie (`ready_for_review`), atskilt fra
PR-kommentar-aktivitet, som den native ChatGPT Work-oppgaven allerede er
konfigurert til å motta (AGENT_WORKFLOW.md "Work-side Chief task (V1,
issue #31)").

DENNE MODULEN dekker første halvdel av syklusen: når en
`status:changes-requested`-runde starter (etter at eieren/Work-oppgaven
har lagt på den etiketten som svar på en reell Chief
CHANGES_REQUESTED-review), settes den samme, deterministiske PR-en
(agent/issue-N) i Draft -- FØR Claude begynner å fikse noe. Se
pr_ready_handoff.py for den andre halvdelen (Draft -> Ready ETTER at
Claude har levert og den vanlige leveranse-/markør-porten er passert).

Bruker BEVISST kun data "Capture pre-run PR state"-steget allerede har
hentet (samme (nummer, head-SHA, isDraft)-fangst deliverable_guard.py
bruker) -- ingen ekstra GitHub-kall.

Kun `status:changes-requested`-runder konverterer til Draft. En fersk
`status:ready`-PR opprettes alltid Ready (gh pr create sin default) og
skal ALDRI settes i Draft av denne modulen -- det ville brutt runde 1s
eksisterende oppvåkning via GitHubs `opened`-PR-hendelse (AGENT_WORKFLOW.md).

`vurder_draft` (den opprinnelige beslutningen om å FORSØKE
Draft-konverteringen) er IKKE-ALARMERENDE (samme filosofi som
chief_retry_signal.py, som denne erstatter): en avvisning der er et
STILLE no-op, ALDRI en feil som stopper kjøringen på egen hånd -- den
skal aldri i seg selv blokkere Claudes jobb.

Chief-review-fiks (PR #45, blokkerende funn): det ALENE var derimot
utilstrekkelig -- hvis pre-run PR-oppslaget var tomt, tvetydig,
foreldet, eller ikke kunne bevise `isDraft`, kunne kjøringen likevel
fortsette, Claude kunne produsere en ny hode, og runden kunne fullføre
med PR-en fortsatt Ready -- nøyaktig den uteblitte re-reviewen issue #44
skal forhindre, fordi `pr_ready_handoff.py` da bare ser en PR som
"allerede Ready" (`already_ready`) og aldri sender noe
`ready_for_review`-vekkesignal. DERFOR finnes `verifiser_draft` under:
en ANDRE, FAIL-CLOSED funksjon som kjøres ETTER selve
Draft-konverteringsforsøket, på et FERSKT refetch, og som gjør
Draft-tilstanden til en VERIFISERT FORUTSETNING for at "Run Claude
Code" i det hele tatt får kjøre -- men KUN for
`status:changes-requested`-runder. For `status:ready` (som aldri går
via Draft i det hele tatt) og for en runde der Draft allerede var
bekreftet FØR forsøket, er utfallet fortsatt et rent, ikke-alarmerende
"forutsetning oppfylt"-resultat -- ikke en ny alarm for tilstander som
alltid har vært trygge.

Ren, avhengighetsfri stdlib-Python, kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_pr_draft_handoff.py.

CLI-bruk (det workflowen gjør):
    TRIGGER_LABEL=status:changes-requested \
    BEFORE_PR_NUMBER="45" BEFORE_HEAD_SHA="..." BEFORE_PR_IS_DRAFT="false" \
      python3 .github/scripts/pr_draft_handoff.py decide
Skriver GITHUB_OUTPUT-linjer (`set_draft`, `pr_number` hvis kjent,
`reason`) til stdout og begrunnelsen til stderr. Alltid exit 0.
Modusen `decide` er default og kan utelates (bakoverkompatibelt med
eksisterende kall).

    echo '{"trigger_label": "status:changes-requested", "before_pr_number": "45",
           "branch": "agent/issue-45",
           "prs": [{"number": 45, "state": "OPEN", "baseRefName": "master",
                     "headRefName": "agent/issue-45", "isDraft": true}]}' \
      | python3 .github/scripts/pr_draft_handoff.py verify
Skriver GITHUB_OUTPUT-linjer (`draft_verified`, `pr_number` hvis kjent,
`reason`) til stdout og begrunnelsen til stderr. Exit 0 hvis
forutsetningen er oppfylt (eller ikke påkrevd), exit 1 ved en REELL
fail-closed avvisning -- samme kontrakt som chief_ready_signal.py/
pr_ready_handoff.py, slik at det tilhørende workflow-steget selv feiler
og en dedikert feil-rapport-oppfølger kjører, som FORHINDRER "Run
Claude Code" fra å kjøre i det hele tatt (standard GitHub Actions-
oppførsel: et feilende steg stopper resten av jobben, se
claude-agent-bridge.yml).
"""
import json
import os
import sys


def vurder_draft(*, trigger_label, before_pr_number, before_head_sha, before_pr_is_draft):
    """
    Returnerer (set_draft: bool, pr_nummer: str|None, begrunnelse: str).

    Default er ALLTID `set_draft=False` på enhver uklarhet -- se
    moduldocstring "IKKE-ALARMERENDE". `before_pr_number`/
    `before_head_sha`/`before_pr_is_draft` er nøyaktig det "Capture
    pre-run PR state"-steget allerede fanget, FØR Claude-steget kjører.
    """
    if trigger_label != "status:changes-requested":
        return False, None, (
            f"Trigger-etikett er {trigger_label!r}, ikke status:changes-requested -- "
            "Draft-handoff gjelder kun changes-requested-runder (status:ready oppretter "
            "alltid en fersk, Ready PR)."
        )

    if not before_pr_number or not before_head_sha:
        return False, None, (
            "Ingen eksisterende PR funnet på issuens deterministiske branch FØR "
            "denne kjøringen startet -- ingenting å sette i Draft."
        )

    if str(before_pr_is_draft).strip().lower() == "true":
        return False, before_pr_number, (
            f"PR #{before_pr_number} er allerede Draft -- idempotent no-op."
        )

    return True, before_pr_number, (
        f"PR #{before_pr_number} (head {before_head_sha}) settes i Draft som del "
        "av changes-requested-handoffen (issue #44)."
    )


def _apen_pr_pa_branch(prs, branch_navn):
    kandidater = [
        pr for pr in (prs or [])
        if pr.get("state") == "OPEN"
        and pr.get("baseRefName") == "master"
        and pr.get("headRefName") == branch_navn
    ]
    if len(kandidater) != 1:
        return None
    return kandidater[0]


def verifiser_draft(*, trigger_label, before_pr_number, prs, branch_navn):
    """
    Returnerer (draft_verified: bool, pr_nummer: int|str|None, begrunnelse: str).

    Chief-review-fiks (PR #45): FAIL-CLOSED motstykke til `vurder_draft`
    over -- kjøres ETTER selve Draft-konverteringsforsøket, på et FERSKT
    refetch av `prs` (ikke gjenbruk av pre-run-fangsten). Draft er kun en
    verifisert forutsetning for `status:changes-requested`; for
    `status:ready` (som aldri går via Draft) er resultatet alltid et
    ikke-alarmerende "ikke påkrevd". `draft_verified=False` betyr en REELL
    avvisning -- se CLI-kontrakten i main() (exit 1, blokkerer "Run Claude
    Code" strukturelt, se moduldocstring).
    """
    if trigger_label != "status:changes-requested":
        return True, None, (
            f"Trigger-etikett er {trigger_label!r}, ikke status:changes-requested -- "
            "Draft er ikke en forutsetning for denne runden."
        )

    if not before_pr_number:
        return False, None, (
            "Ingen PR-nummer fanget FØR denne kjøringen startet -- kan ikke "
            "verifisere Draft-forutsetningen for changes-requested-runden "
            "(fail-closed)."
        )

    pr = _apen_pr_pa_branch(prs, branch_navn)
    if pr is None:
        return False, before_pr_number, (
            f"Fant ikke nøyaktig én åpen PR mot master på branch {branch_navn!r} "
            "ved fersk refetch -- kan ikke verifisere Draft-forutsetningen "
            "(fail-closed)."
        )

    pr_nummer = pr.get("number")
    if str(pr_nummer) != str(before_pr_number):
        return False, pr_nummer, (
            f"PR-identiteten endret seg (var #{before_pr_number}, er nå "
            f"#{pr_nummer}) ved fersk refetch -- kan ikke bekrefte at dette "
            "er samme PR som ble forsøkt satt i Draft (fail-closed)."
        )

    if not pr.get("isDraft"):
        return False, pr_nummer, (
            f"PR #{pr_nummer} er IKKE Draft ved fersk refetch -- "
            "Draft-forutsetningen for changes-requested-handoffen (issue #44) "
            "er ikke etablert (fail-closed); Claude kjører ikke denne runden."
        )

    return True, pr_nummer, (
        f"PR #{pr_nummer} bekreftet Draft ved fersk refetch -- "
        "forutsetningen er etablert, Claude kan kjøre."
    )


def _kjor_decide():
    set_draft, pr_nummer, begrunnelse = vurder_draft(
        trigger_label=os.environ.get("TRIGGER_LABEL", ""),
        before_pr_number=os.environ.get("BEFORE_PR_NUMBER") or None,
        before_head_sha=os.environ.get("BEFORE_HEAD_SHA") or None,
        before_pr_is_draft=os.environ.get("BEFORE_PR_IS_DRAFT") or "",
    )

    print(begrunnelse, file=sys.stderr)
    print(f"set_draft={'true' if set_draft else 'false'}")
    if pr_nummer is not None:
        print(f"pr_number={pr_nummer}")
    print(f"reason={begrunnelse}")
    # Bevisst ALLTID exit 0 -- se moduldocstring "IKKE-ALARMERENDE": et
    # missed/skipped Draft-FORSØK skal aldri i seg selv blokkere Claude --
    # det er `_kjor_verify` under som håndhever forutsetningen.
    return 0


def _kjor_verify():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    draft_verified, pr_nummer, begrunnelse = verifiser_draft(
        trigger_label=data.get("trigger_label") or "",
        before_pr_number=data.get("before_pr_number") or None,
        prs=data.get("prs"),
        branch_navn=data.get("branch"),
    )

    print(begrunnelse, file=sys.stderr)
    print(f"draft_verified={'true' if draft_verified else 'false'}")
    if pr_nummer is not None:
        print(f"pr_number={pr_nummer}")
    print(f"reason={begrunnelse}")
    # Fail-closed: exit 1 på en REELL avvisning, slik at det tilhørende
    # workflow-steget selv feiler og "Run Claude Code" ikke kjøres (standard
    # GitHub Actions-oppførsel stopper resten av jobben på et feilende steg).
    return 0 if draft_verified else 1


def main():
    modus = sys.argv[1] if len(sys.argv) > 1 else "decide"
    if modus == "verify":
        return _kjor_verify()
    return _kjor_decide()


if __name__ == "__main__":
    sys.exit(main())
