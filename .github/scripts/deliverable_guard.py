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
  status:ready             -- krever at DENNE kjøringen faktisk startet
      fra en ren branch: INGEN åpen PR fikk lov til å ligge på den
      deterministiske branchen (agent/issue-<N>, se branch_policy.py)
      FØR kjøringen startet (`forrige_head_sha` skal være tom). Gitt
      det: nøyaktig ÉN åpen PR mot `master` på den branchen, med et
      IKKE-TOMT diff.
  status:changes-requested -- krever den samme, allerede eksisterende
      PR-en på den deterministiske branchen, og at HEAD-SHA-en har
      endret seg siden FØR denne kjøringen startet.

Begge grenene bruker altså samme `forrige_head_sha` -- fanget av
workflowen (steg "Capture pre-run PR state") rett FØR Claude-steget
kjører, uavhengig av trigger-etikett -- men på motsatte måter: for
changes-requested er en UENDRET head et avvisningsgrunnlag (ingenting
nytt ble pushet); for ready er en IKKE-TOM verdi i det hele tatt et
avvisningsgrunnlag alene (en PR fantes allerede -- se
"Chief review-fiks (PR #13, runde 3)" under).

Ren, avhengighetsfri stdlib-Python -- kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_deliverable_guard.py, slik at selve
beslutningen er testbar uten å kjøre noe mot GitHub.

CLI-bruk (det workflowen gjør):
    echo "$PRS_JSON" | TRIGGER_LABEL=status:ready BEFORE_HEAD_SHA="$before" \
        python3 .github/scripts/deliverable_guard.py
`PRS_JSON` er et JSON-array bygget av workflowen fra
`gh pr list --head agent/issue-N --base master --state open --json
number,state,baseRefName,headRefOid,additions,deletions,changedFiles`
(branch_policy.py sin `gh_pr_list_args`) -- feltnavnene under er
nøyaktig de `gh pr list --json` gir, ingen ekstra oversettelse skjer i
workflowen.

Chief review-fiks (PR #13, runde 3): `status:ready` ignorerte tidligere
`forrige_head_sha` helt. Men branch-navnet er BEVISST deterministisk og
gjenbrukbart gjennom hele issuens levetid (PR #13, runde 2-fiksen) --
så en tidligere mislykket/avbrutt/manuell kjøring kan ha etterlatt en
ÅPEN PR med et ikke-tomt diff på nøyaktig den branchen. En etterfølgende
`status:ready`-kjøring der Claude ikke gjør noe nyttig, men returnerer
process-success, ville da funnet DEN gamle PR-en via
`gh pr list --head agent/issue-N` og feilaktig godkjent den som om den
var DENNE kjøringens leveranse. `status:ready` betyr "start en FERSK
kjøring" (se AGENT_WORKFLOW.md-tabellen) -- en PR som allerede lå der
FØR kjøringen startet kan aldri være bevis for hva DENNE kjøringen
leverte, uansett innhold. Rettelsen: for status:ready skal
`forrige_head_sha` derfor være TOM -- enhver ikke-tom verdi betyr en
pre-eksisterende PR og avviser porten, uavhengig av diff-størrelse eller
om HEAD-en endret seg underveis.

Chief review-fiks (PR #13, runde 4): `status:changes-requested` beviste
fortsatt ikke PR-IDENTITET -- porten sammenlignet kun HEAD-SHA, ikke
PR-nummer. Siden branchen er den samme gjennom hele issuens levetid, og
allowlisten fortsatt gir `gh pr edit`/`gh pr create`, kunne i prinsippet
en ANNEN PR på samme branch (f.eks. hvis den opprinnelige PR-ens base
ble endret bort fra master, og en NY PR ble opprettet mot master fra
samme branch) bli funnet av post-run `gh pr list --head ... --base
master` med en HEAD-SHA som tilfeldigvis avviker fra `forrige_head_sha`
-- og bli feilaktig godkjent som "samme PR, nye commits", selv om det
faktisk var en helt annen PR. Rettelsen: workflowen fanger nå
`forrige_pr_nummer` sammen med `forrige_head_sha` (samme pre-run steg,
samme spørring), og porten krever at PR-NUMMERET er UENDRET i tillegg
til at HEAD-SHA-en har endret seg -- identiteten OG fremdriften må begge
bekreftes. Manglende PR-nummer (fanget FØR eller funnet ETTER kjøringen)
avviser porten på samme måte som manglende HEAD-SHA alltid har gjort.
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


def vurder_leveranse(*, trigger_label, prs, forrige_head_sha=None, forrige_pr_nummer=None):
    """
    Returnerer (ok: bool, pr_number: int|None, begrunnelse: str).

    `prs`: liste av dicts for PR-er funnet på issuens deterministiske
    branch (`gh pr list --head agent/issue-N`). `forrige_head_sha` og
    `forrige_pr_nummer`: PR-ens HEAD-SHA og nummer slik de var FØR denne
    kjøringen startet, fanget sammen, uavhengig av trigger-etikett --
    brukt av BEGGE grenene, på motsatte måter:
    - `status:changes-requested`: begge skal finnes, PR-NUMMERET skal
      være UENDRET (samme PR-identitet), og HEAD-SHA-en skal ha endret
      seg (bevis på nye commits til DEN SAMME PR-en -- runde 4).
    - `status:ready`: `forrige_head_sha` skal derimot være TOM (bevis
      på at ingen PR lå der FØR denne kjøringen -- runde 3);
      `forrige_pr_nummer` er ikke relevant for denne grenen.
    """
    if trigger_label not in GYLDIGE_TRIGGER_ETIKETTER:
        return False, None, f"Ukjent trigger-etikett {trigger_label!r} -- kan ikke verifisere leveranse."

    kandidater = _apne_prs_mot_master(prs)

    if not kandidater:
        return False, None, (
            "Ingen åpen PR mot master funnet på issuens deterministiske branch "
            "(eksakt head-branch-oppslag, gh pr list --head) -- ingen leveranse å vise til."
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
        if forrige_head_sha:
            return False, nummer, (
                f"PR #{nummer} fantes allerede på denne branchen FØR kjøringen startet "
                f"(HEAD var {forrige_head_sha}) -- status:ready skal starte fra en ren "
                "branch, så dette kan ikke være DENNE kjøringens leveranse. Ser ut som en "
                "gjenværende PR fra en tidligere/mislykket/manuell kjøring."
            )
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

    if not forrige_pr_nummer:
        return False, nummer, (
            f"PR #{nummer} finnes, men ingen PR-nummer ble fanget FØR denne kjøringen "
            "startet -- kan ikke bekrefte at det er samme PR som får godkjenningen."
        )

    if str(nummer) != str(forrige_pr_nummer):
        return False, nummer, (
            f"PR-identiteten endret seg underveis: FØR kjøringen var det PR "
            f"#{forrige_pr_nummer}, nå er det PR #{nummer} på samme branch -- kan ikke "
            "bekrefte at dette er samme PR som skulle fått endringene."
        )

    head_na = pr.get("headRefOid")
    if head_na == forrige_head_sha:
        return False, nummer, (
            f"PR #{nummer} sin HEAD-SHA er uendret ({head_na}) siden før kjøringen "
            "startet -- ingen nye commits ble pushet."
        )

    return True, nummer, (
        f"PR #{nummer} (samme PR-identitet bekreftet) sin HEAD-SHA endret seg fra "
        f"{forrige_head_sha} til {head_na} -- leveranse verifisert."
    )


def main():
    """
    Miljøvariabler: TRIGGER_LABEL, BEFORE_HEAD_SHA, BEFORE_PR_NUMBER
    (begge valgfrie/tomme strenger). stdin: JSON-array av PR-dicts (se
    moduldocstring for feltnavn).

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
        forrige_pr_nummer=os.environ.get("BEFORE_PR_NUMBER") or None,
    )

    print(begrunnelse, file=sys.stderr)
    print(f"ok={'true' if ok else 'false'}")
    if pr_number is not None:
        print(f"pr_number={pr_number}")
    print(f"reason={begrunnelse}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
