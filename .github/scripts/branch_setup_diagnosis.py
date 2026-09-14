#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge V1.7 -- diagnose for manglende leveranse (issue #259).

BAKGRUNN: issue #257 feilet to ganger på nøyaktig samme, distinkte måte:
Claude-steget fullførte med `success()`, `permission_denials_count=1`, og
INGEN `agent/issue-257`-branch fantes etterpå -- den ledende hypotesen var
at `git switch -c <branch>` (moderne branch-oppretting) ble avvist fordi
`--allowedTools` kun tillot `git checkout *`. V1.7 løser selve
tillatelses-hullet med to nye eksakte `git switch`-regler (se
branch_policy.py sin `tillatte_switch_kommandoer`), men issue #259 punkt 5
krever i tillegg BEDRE DIAGNOSTIKK: når leveranse-porten (deliverable_guard.py)
avviser en kjøring, skal rapporten kunne skille "branch-oppsettet ble
sannsynligvis avvist av tillatelsesmodellen" (nettopp #257s fingeravtrykk --
ALDRI noen remote branch dukket opp) fra "Claude tok et bevisst valg om å
ikke gjøre endringer" (en annen feilklasse, som IKKE etterlater dette
fingeravtrykket), UTEN å aktivere usikker full-output-logging av selve
Claude-transkriptet (issue #259, punkt 5 sin eksplisitte begrensning).

MEKANISMEN: workflowen sjekker (med sitt eget token, IKKE gjennom Claudes
--allowedTools) om issuens deterministiske branch (agent/issue-<N>) faktisk
finnes på `origin` ETTER at Claude-steget er ferdig (`git ls-remote --heads
origin <branch>`) -- et faktum som er 100 % uavhengig av hva som står i
Claudes egen rapport/transkript. Denne modulen tar det faktumet, sammen med
data leveranse-porten allerede fanget (trigger-etikett, FØR-tilstand), og
returnerer én av et lite, fast sett med diagnoser:

- `status:ready`, INGEN remote branch i det hele tatt: nøyaktig #257s
  fingeravtrykk -- sterk indikasjon på et avvist branch-oppsett-steg, ikke
  et bevisst Claude-valg (et bevisst "jeg gjør ingenting" ville normalt
  fortsatt fått LOV til å opprette branchen selv om den aldri ble brukt).
- `status:ready`, remote branch finnes: branch-oppsettet lyktes -- den
  manglende leveransen skyldes noe SENERE i kjøringen (ingen PR åpnet,
  eller et bevisst valg om å stoppe), ikke en tillatelses-blokkering på
  selve branch-oppsettet.
- `status:changes-requested`: branchen forventes å eksistere FRA FØR
  (Draft-håndteringen krever allerede en eksisterende PR/branch før Claude
  i det hele tatt starter) -- ren tilstedeværelse beviser derfor ingenting
  om DENNE kjøringens branch-tilgang, så disse grenene rapporterer et annet,
  mer presist manglende-fremdrift-resonnement i stedet.

Ren, avhengighetsfri stdlib-Python -- kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_branch_setup_diagnosis.py, slik at selve
beslutningen er testbar uten å kjøre noe mot GitHub.
"""
import json
import os
import sys

GYLDIGE_TRIGGER_ETIKETTER = ("status:ready", "status:changes-requested")


def diagnoser_manglende_leveranse(*, trigger_label, remote_branch_finnes, forrige_pr_nummer=None, forrige_head_sha=None):
    """
    Returnerer (diagnosis: str, begrunnelse: str). Kalles KUN når
    leveranse-porten (deliverable_guard.py) allerede har avvist kjøringen
    -- denne funksjonen forklarer HVORFOR på en måte som skiller et
    sannsynlig avvist branch-oppsett fra andre feilklasser, den forklarer
    aldri om leveransen selv var ok.
    """
    if trigger_label not in GYLDIGE_TRIGGER_ETIKETTER:
        return "unknown_trigger", f"Ukjent trigger-etikett {trigger_label!r} -- kan ikke diagnostisere."

    if trigger_label == "status:ready":
        if not remote_branch_finnes:
            return "branch_never_pushed", (
                "Ingen remote branch dukket opp for denne status:ready-kjøringen i det "
                "hele tatt (git ls-remote fant ingenting) -- dette er nøyaktig "
                "fingeravtrykket fra issue #257/#259 (prosessen fullførte, men "
                "branch-oppsettet ble sannsynligvis avvist av tillatelsesmodellen), "
                "IKKE et bevisst valg fra Claude om å gjøre ingenting."
            )
        return "branch_pushed_no_pr", (
            "En remote branch finnes for denne kjøringen, så selve branch-oppsettet "
            "lyktes -- den manglende leveransen skyldes noe senere i kjøringen (ingen "
            "PR åpnet, eller et bevisst valg om å stoppe), ikke en tillatelses-"
            "blokkering på branch-oppsettet."
        )

    # status:changes-requested: branchen/PR-en forventes allerede å
    # eksistere FØR denne kjøringen (Draft-håndteringen krever det) -- ren
    # tilstedeværelse beviser derfor ingenting om DENNE kjøringens egen
    # branch-tilgang.
    if forrige_pr_nummer and forrige_head_sha:
        return "no_new_commits", (
            f"En eksisterende PR (#{forrige_pr_nummer}) og branch ble funnet FØR denne "
            "kjøringen startet, men HEAD-en endret seg ikke (eller PR-identiteten kunne "
            "ikke bekreftes uendret) -- branch-tilgangen var altså allerede tilgjengelig; "
            "Claude gjorde sannsynligvis ingen nye commits denne runden, eller "
            "PR-identitetssjekken feilet. Ikke et branch-oppsett-problem."
        )
    return "missing_prior_state", (
        "Ingen tidligere PR/branch-tilstand ble fanget for denne "
        "status:changes-requested-kjøringen -- den forventede eksisterende branchen/"
        "PR-en kunne ikke finnes i det hele tatt før kjøringen startet."
    )


def main():
    """
    Miljøvariabler: TRIGGER_LABEL, REMOTE_BRANCH_EXISTS ('true'/'false'),
    BEFORE_PR_NUMBER, BEFORE_HEAD_SHA (begge valgfrie/tomme strenger).

    Skriver GITHUB_OUTPUT-linjer til stdout (`diagnosis`, `reason`) og
    samme begrunnelse til stderr for loggen.
    """
    diagnosis, begrunnelse = diagnoser_manglende_leveranse(
        trigger_label=os.environ.get("TRIGGER_LABEL", ""),
        remote_branch_finnes=os.environ.get("REMOTE_BRANCH_EXISTS", "").strip().lower() == "true",
        forrige_pr_nummer=os.environ.get("BEFORE_PR_NUMBER") or None,
        forrige_head_sha=os.environ.get("BEFORE_HEAD_SHA") or None,
    )

    print(begrunnelse, file=sys.stderr)
    print(f"diagnosis={diagnosis}")
    print(f"reason={begrunnelse}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
