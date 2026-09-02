#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge V1.2 -- leveranse-verifisering (issue #12).

BAKGRUNN (funnet på den første ekte E2E-kjøringen, issue #11):
workflow-kjøring 33646938966 fullførte med `conclusion: success` --
guard OK, secret OK, OIDC OK, Claude GitHub App-token OK, Claude Code
2.1.258 kjørte og returnerte `subtype: success` -- men repo-tilstanden
etterpå viste INGEN ny branch, INGEN åpen PR, INGEN issue/PR-kommentar,
og den etterspurte dokumentasjonsfilen ble aldri levert.
`permission_denials_count: 14` i samme kjøring er den sannsynlige
årsaken: workflowen ga (og ga fortsatt, før denne fiksen) INGEN
`--allowedTools`-liste til anthropics/claude-code-action@v1 i det hele
tatt. Ifølge Anthropics egen dokumentasjon utfører Claude ALDRI
vilkårlige Bash-kommandoer uten eksplisitt tillatelse, og åpner heller
ALDRI en PR automatisk uansett (security.md: "Claude does not
automatically create pull requests ... provides a link to the GitHub
PR creation page"). V1 tolket `conclusion: success` fra selve
Claude-prosessen som "oppgaven er fullført" -- feil for denne
tilstandsmaskinens formål: en grønn prosess uten leveranse skal ALDRI
flytte issuen til `status:review`.

RETTELSEN har to uavhengige deler:
1. Workflowen gir nå en eksplisitt, minimal `--allowedTools`-liste til
   Claude (se claude-agent-bridge.yml) -- kun git/gh/test-kommandoene
   som faktisk trengs, aldri `git merge` eller `gh pr merge`.
2. Denne modulen: en leveranse-verifiseringsport som kjører ETTER
   Claude-steget, og som workflowen bruker til å avgjøre om issuen får
   lov til å gå til `status:review` i det hele tatt -- en vellykket
   Claude-prosess er en NØDVENDIG, men ALDRI TILSTREKKELIG, betingelse
   alene.

Kriteriene (issue #12, "Goal"):
  status:ready             -- krever nøyaktig ÉN åpen PR mot `master`,
      assosiert med issuen (GitHub cross-reference -- samme
      "mentioned this issue in PR #Y"-signal prompten allerede ber
      Claude lete etter i issuens tidslinje), med et IKKE-TOMT diff.
  status:changes-requested -- krever den samme, allerede eksisterende
      assosierte PR-en, og at HEAD-SHA-en har endret seg siden FØR
      denne kjøringen startet (fanget av workflowen som
      `forrige_head_sha` rett før Claude-steget kjører).

Ren, avhengighetsfri stdlib-Python -- kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_deliverable_guard.py, slik at selve
beslutningen er testbar uten å kjøre noe mot GitHub.

CLI-bruk (det workflowen gjør):
    echo "$PRS_JSON" | TRIGGER_LABEL=status:ready \
        python3 .github/scripts/deliverable_guard.py
`PRS_JSON` er et JSON-array bygget av workflowen fra
`gh api repos/OWNER/REPO/issues/N/timeline` (kryssreferanser til
issuen) pluss ett `gh pr view --json
number,state,baseRefName,headRefOid,additions,deletions,changedFiles`
per kandidat-PR -- feltnavnene under er nøyaktig de `gh pr view`
gir, ingen ekstra oversettelse skjer i workflowen.
"""
import json
import os
import sys

GYLDIGE_TRIGGER_ETIKETTER = ("status:ready", "status:changes-requested")


def _apne_prs_mot_master(prs):
    return [
        pr for pr in prs
        if pr.get("state") == "OPEN" and pr.get("baseRefName") == "master"
    ]


def vurder_leveranse(*, trigger_label, prs, forrige_head_sha=None):
    """
    Returnerer (ok: bool, pr_number: int|None, begrunnelse: str).

    `prs`: liste av dicts for PR-er GitHub-tidslinjen viser som
    kryssrefererende til issuen. `forrige_head_sha`: PR-ens HEAD-SHA
    slik den var FØR denne kjøringen startet (kun relevant for
    status:changes-requested -- ignorert for status:ready).
    """
    if trigger_label not in GYLDIGE_TRIGGER_ETIKETTER:
        return False, None, f"Ukjent trigger-etikett {trigger_label!r} -- kan ikke verifisere leveranse."

    kandidater = _apne_prs_mot_master(prs)

    if not kandidater:
        return False, None, (
            "Ingen åpen PR mot master funnet assosiert med issuen "
            "(GitHub-tidslinjens kryssreferanser) -- ingen leveranse å vise til."
        )

    if len(kandidater) > 1:
        numre = [pr.get("number") for pr in kandidater]
        return False, None, (
            f"Flere åpne PR-er mot master er assosiert med issuen ({numre}) -- "
            "ikke entydig hvilken som er denne kjøringens leveranse."
        )

    pr = kandidater[0]
    nummer = pr.get("number")

    if trigger_label == "status:ready":
        diff_storrelse = int(pr.get("additions") or 0) + int(pr.get("deletions") or 0)
        if diff_storrelse == 0 or int(pr.get("changedFiles") or 0) == 0:
            return False, nummer, f"PR #{nummer} finnes, men har et tomt diff -- ingen faktisk leveranse."
        return True, nummer, f"PR #{nummer} mot master med ikke-tomt diff -- leveranse verifisert."

    # status:changes-requested
    if not forrige_head_sha:
        return False, nummer, (
            f"PR #{nummer} finnes, men ingen HEAD-SHA ble fanget FØR denne "
            "kjøringen startet -- kan ikke bekrefte at noe nytt ble pushet."
        )

    head_na = pr.get("headRefOid")
    if head_na == forrige_head_sha:
        return False, nummer, (
            f"PR #{nummer} sin HEAD-SHA er uendret ({head_na}) siden før kjøringen "
            "startet -- ingen nye commits ble pushet."
        )

    return True, nummer, (
        f"PR #{nummer} sin HEAD-SHA endret seg fra {forrige_head_sha} til {head_na} -- leveranse verifisert."
    )


def main():
    """
    Miljøvariabler: TRIGGER_LABEL, BEFORE_HEAD_SHA (valgfri/tom streng).
    stdin: JSON-array av PR-dicts (se moduldocstring for feltnavn).

    Skriver GITHUB_OUTPUT-linjer til stdout (`ok`, `pr_number` hvis
    kjent, `reason`) og samme begrunnelse til stderr for loggen.
    """
    raw = sys.stdin.read()
    try:
        prs = json.loads(raw) if raw.strip() else []
    except ValueError:
        prs = []
    if not isinstance(prs, list):
        prs = []

    ok, pr_number, begrunnelse = vurder_leveranse(
        trigger_label=os.environ.get("TRIGGER_LABEL", ""),
        prs=prs,
        forrige_head_sha=os.environ.get("BEFORE_HEAD_SHA") or None,
    )

    print(begrunnelse, file=sys.stderr)
    print(f"ok={'true' if ok else 'false'}")
    if pr_number is not None:
        print(f"pr_number={pr_number}")
    print(f"reason={begrunnelse}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
