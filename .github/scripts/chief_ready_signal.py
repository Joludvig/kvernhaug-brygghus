#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge V1 -- Chief-ready PR-signal (issue #32).

BAKGRUNN: den autoritative Bridge-tilstandsmaskinen (AGENT_WORKFLOW.md)
lever på GitHub-ISSUEN og går til `status:review` kun etter at
leveranse-porten (deliverable_guard.py) har godkjent en ekte PR. Den
offisielle ChatGPT Work-integrasjonen støtter derimot kun
event-triggede/webhook-oppgaver på **PR-aktivitet** (inkl. PR-
kommentarer), ikke på issue-etiketter. Denne modulen er den minste
mulige adapteren mellom de to: EN reservert, maskinlesbar markør
postet som EN topplinje-kommentar på den assosierte PR-en, KUN etter at
Bridgen selv har bekreftet at issuen faktisk står i `status:review`.

Markøren finnes UTELUKKENDE for å vekke den native ChatGPT Work-
oppgaven -- den er ikke, og skal aldri behandles som, en autoritativ
kilde. Work-oppgaven må selv refetch'e live issue/PR/head-tilstand før
den reviewer noe; se AGENT_WORKFLOW.md.

ORDNING / RACE-SIKKERHET: denne modulen kalles fra workflowen ETTER
"Move to status:review"-steget har lyktes, og med FERSKT refetch'et
tilstand (ikke gjenbruk av data fra før Claude-steget kjørte) -- se
`vurder_signal` under. Hvis noen av betingelsene (issue fortsatt
eksklusivt status:review, PR fortsatt åpen mot master på issuens
deterministiske branch) ikke lenger holder ved refetch, avvises
signalet -- fail-closed, ingen markør postes.

IDEMPOTENS: GitHub/webhook-levering kan retry'e, og workflow-steg kan
kjøres på nytt. `finn_eksisterende_markorer` leter gjennom PR-ens
EKSISTERENDE topplinje-kommentarer etter en EKSAKT match på
(issue-nummer, head-SHA) før noe nytt postes -- et duplikat er et
no-op, ikke en feil. En NY head-SHA (en ny status:changes-requested-
runde) er bevisst IKKE et duplikat, slik at re-review vekkes korrekt.

Markørformatet er strengt (linje-ankret regex, eksakt versjonsstreng,
eksakt 40-tegns hex-SHA) slik at feilstavede/nesten-like linjer --
feil versjon, feil case, manglende mellomrom, kort SHA, ekstra tekst på
samme linje -- bevisst ALDRI telles som den reserverte markøren. Dette
hindrer både falske duplikat-treff og at noen (Chief, en review-bot,
et automatisk sitat) utilsiktet eller bevisst kan forfalske signalet.

Ren, avhengighetsfri stdlib-Python -- kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_chief_ready_signal.py, slik at selve
beslutningen er testbar uten å kjøre noe mot GitHub.

CLI-bruk (det workflowen gjør):
    jq -n '{issue_number: 32, issue_labels: [...], prs: [...],
            branch: "agent/issue-32", comments: [...]}' \
      | python3 .github/scripts/chief_ready_signal.py "$RUNNER_TEMP/chief_ready_comment.txt"
Skriver GITHUB_OUTPUT-linjer (`post`, `duplicate`, `pr_number`,
`head_sha`) til stdout og begrunnelsen til stderr. Skriver den ferdige
kommentarteksten til filstien gitt som argv[1] KUN når `post=true` --
selve `gh pr comment --body-file`-kallet gjøres av workflowen, ikke her
(ingen `gh`-avhengighet i denne modulen).

Ingen hemmeligheter/token/miljøverdier eller vilkårlig Claude-output
inngår noensinne i markøren eller kommentarteksten -- kun issue-nummer,
PR-nummer og PR-head-SHA, alle strukturerte tall/hex-strenger fra
`vurder_signal`s egne parametre.
"""
import json
import re
import sys

# Duplisert bevisst (ikke importert) fra lifecycle_labels.LIVSSYKLUS_ETIKETTER
# -- denne modulen skal kunne lastes helt uavhengig (samme mønster som de
# andre .github/scripts-modulene, som heller ikke krysser-importerer).
# tests/test_agent_bridge_chief_ready_signal.py sjekker at de to listene
# er identiske, slik at et framtidig etikett-endring i lifecycle_labels.py
# ikke kan drifte fra denne uten at testsuiten fanger det.
LIVSSYKLUS_ETIKETTER = (
    "status:ready",
    "status:working",
    "status:review",
    "status:changes-requested",
    "status:approved",
)

MARKER_VERSJON = "KBH_CHIEF_REVIEW_READY_V1"
MARKER_LINJE_RE = re.compile(
    r"(?m)^" + re.escape(MARKER_VERSJON) + r" issue=(?P<issue>\d+) head=(?P<head>[0-9a-f]{40})$"
)


def bygg_marker(issue_nummer, head_sha):
    """Den ENE, kanoniske markør-linjen -- se moduldocstring for hvorfor
    formatet er akkurat dette (linje-ankret, eksakt case/mellomrom/SHA-
    lengde ved parsing)."""
    return f"{MARKER_VERSJON} issue={int(issue_nummer)} head={head_sha}"


def bygg_kommentar(issue_nummer, pr_nummer, head_sha):
    """Markøren pluss et lite, menneskelesbart forklarings-avsnitt.
    Inneholder bevisst KUN issue-/PR-/head-identifikatorer -- ingen
    issue-body, ingen Claude-output, ingen hemmeligheter."""
    marker = bygg_marker(issue_nummer, head_sha)
    return (
        f"{marker}\n\n"
        f"Issue #{int(issue_nummer)} er nå `status:review` -- PR #{pr_nummer} "
        f"(head `{head_sha}`) er klar for Chief-review.\n\n"
        "Denne kommentaren finnes kun for å vekke den native ChatGPT Work "
        "event-oppgaven. Den oppgaven må selv refetch'e live issue-/PR-/"
        "head-tilstand før den reviewer noe -- den skal aldri stole på "
        "denne kommentaren som autoritet. Den timelige Chief-"
        "overvåkingen er fortsatt reserveveien om dette signalet skulle "
        "utebli. Merge forblir en egen, manuell eier-handling."
    )


def finn_eksisterende_markorer(kommentarer):
    """Returnerer settet av (issue, head)-par funnet som EKSAKTE
    markør-linjer i `kommentarer` (liste av PR-topplinje-kommentar-
    body-strenger). Se moduldocstring for hvorfor kun eksakte
    linje-matcher telles."""
    funnet = set()
    for body in kommentarer or []:
        if not body:
            continue
        for m in MARKER_LINJE_RE.finditer(body):
            funnet.add((int(m.group("issue")), m.group("head")))
    return funnet


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


def vurder_signal(*, issue_nummer, issue_labels, prs, branch_navn, eksisterende_kommentarer):
    """
    Returnerer (post: bool, duplicate: bool, pr_nummer: int|None,
    head_sha: str|None, kommentar: str|None, begrunnelse: str).

    ALT input her skal være FERSKT refetch'et av workflowen rett før
    kallet -- se "Ordering / race safety" i moduldocstringen og i
    issue #32. Fail-closed: enhver uklarhet (feil/manglende
    livssyklus-etikett, null eller flere PR-kandidater, manglende
    head-SHA) gir `post=False` uten unntak/krasj.
    """
    issue_labels = list(issue_labels or [])
    livssyklus_i_bruk = [e for e in issue_labels if e in LIVSSYKLUS_ETIKETTER]
    if livssyklus_i_bruk != ["status:review"]:
        return False, False, None, None, None, (
            f"Issue #{issue_nummer} er ikke (lenger) eksklusivt status:review "
            f"ved refetch (livssyklus-etiketter funnet: {livssyklus_i_bruk}) -- "
            "avviser signal (fail-closed)."
        )

    pr = _apen_pr_pa_branch(prs, branch_navn)
    if pr is None:
        antall = len([
            p for p in (prs or [])
            if p.get("state") == "OPEN" and p.get("baseRefName") == "master"
            and p.get("headRefName") == branch_navn
        ])
        return False, False, None, None, None, (
            f"Fant ikke nøyaktig én åpen PR mot master på branch {branch_navn!r} "
            f"ved refetch (fant {antall}) -- avviser signal (fail-closed)."
        )

    pr_nummer = pr.get("number")
    head_sha = pr.get("headRefOid")
    if not head_sha:
        return False, False, pr_nummer, None, None, (
            f"PR #{pr_nummer} mangler headRefOid ved refetch -- avviser signal (fail-closed)."
        )

    eksisterende = finn_eksisterende_markorer(eksisterende_kommentarer)
    if (int(issue_nummer), head_sha) in eksisterende:
        return False, True, pr_nummer, head_sha, None, (
            f"Markør for issue #{issue_nummer}/head {head_sha} finnes allerede på "
            f"PR #{pr_nummer} -- behandlet som idempotent no-op, ikke en feil."
        )

    kommentar = bygg_kommentar(issue_nummer, pr_nummer, head_sha)
    return True, False, pr_nummer, head_sha, kommentar, (
        f"Issue #{issue_nummer} eksklusivt status:review, PR #{pr_nummer} "
        f"(head {head_sha}) bekreftet ved refetch, ingen tidligere markør "
        "funnet -- postes."
    )


def main(argv):
    if len(argv) != 2:
        print("bruk: chief_ready_signal.py <output-fil-for-kommentar>", file=sys.stderr)
        return 2
    output_path = argv[1]

    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    post, duplicate, pr_nummer, head_sha, kommentar, begrunnelse = vurder_signal(
        issue_nummer=data.get("issue_number"),
        issue_labels=data.get("issue_labels"),
        prs=data.get("prs"),
        branch_navn=data.get("branch"),
        eksisterende_kommentarer=data.get("comments"),
    )

    print(begrunnelse, file=sys.stderr)
    print(f"post={'true' if post else 'false'}")
    print(f"duplicate={'true' if duplicate else 'false'}")
    if pr_nummer is not None:
        print(f"pr_number={pr_nummer}")
    if head_sha is not None:
        print(f"head_sha={head_sha}")
    print(f"reason={begrunnelse}")

    if post:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(kommentar)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
