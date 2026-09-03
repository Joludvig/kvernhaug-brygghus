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

IKKE-ALARMERENDE (samme filosofi som chief_retry_signal.py, som denne
erstatter): enhver avvisning her er et STILLE no-op, ALDRI en feil som
stopper kjøringen -- Draft-konvertering er et vekke-signal-hjelpemiddel,
ikke en forutsetning for at Claude skal få lov til å jobbe. CLI-en
returnerer derfor alltid exit 0.

Ren, avhengighetsfri stdlib-Python, kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_pr_draft_handoff.py.

CLI-bruk (det workflowen gjør):
    TRIGGER_LABEL=status:changes-requested \
    BEFORE_PR_NUMBER="45" BEFORE_HEAD_SHA="..." BEFORE_PR_IS_DRAFT="false" \
      python3 .github/scripts/pr_draft_handoff.py
Skriver GITHUB_OUTPUT-linjer (`set_draft`, `pr_number` hvis kjent,
`reason`) til stdout og begrunnelsen til stderr.
"""
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


def main():
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
    # missed/skipped Draft-forsøk skal aldri blokkere selve Claude-kjøringen.
    return 0


if __name__ == "__main__":
    sys.exit(main())
