#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- eier-varsling for GO/NO-GO (issue #66).

BAKGRUNN: AGENT_WORKFLOW.md ("Work-side Chief task") dokumenterer at den
native ChatGPT Work-oppgaven, ved PASS, allerede skal "separately
notif[y] the owner with a GO/NO-GO prompt" -- men issue #66 observerte
konkret at det livssyklus-messig korrekte tilfellet (issue #59 / PR #64
nådde eksakt-hode Chief APPROVED 2026-09-04) likevel ikke ga eieren noe
tydelig "GO?"-varsel, selv om GitHub-tilstanden var grønn. Samme klasse
problem som Chief-ready-vekkingen (issue #32/#40/#44) allerede møtte:
et varsel som kun eksisterer på en ekstern, ikke-inspiserbar SaaS-side
(Work) er ikke pålitelig nok alene.

DENNE MODULEN er repo-siden av fiksen: et eget, deterministisk,
enhetstestet varsel -- postet av selve Bridge-workflowen (dens eget
token, IKKE via Claude/--allowedTools) rett etter at issuen er
bekreftet eksklusivt `status:approved` og PR-en har en formell
APPROVED-review på eksakt sitt live hode. Varselet er UTELUKKENDE en
oppvåkning/prompt til EIEREN selv -- det er aldri autoritativt, og det
gir aldri merge-fullmakt (se AGENT_WORKFLOW.md "Owner merge gate", som
denne modulen ikke rører).

FØR VARSEL POSTES må ALT av følgende bekreftes på et FERSKT refetch
(issue #66, krav 3):
  - PR-en er åpen og ikke merget (state == OPEN i GitHubs egen PR-
    indeks -- MERGED er en egen, gjensidig utelukkende tilstand),
  - PR-ens LIVE head-SHA (headRefOid),
  - en formell GitHub-review med tilstand APPROVED finnes for NETTOPP
    dette hodet (samme `commit.oid`-mønster som pr_ready_handoff.py
    allerede bruker for CHANGES_REQUESTED/APPROVED-sjekken sin),
  - issuen har `status:approved` som sitt ENESTE livssyklus-etikett,
  - ingen ekstra manuell sperre utover disse -- dette repoet definerer
    ingen andre manuelle "gate"-etiketter enn livssyklus-etikettene selv
    (LIVSSYKLUS_ETIKETTER under), så den eksklusivitets-sjekken ER hele
    "no unresolved manual gate"-kravet; dokumentert eksplisitt her for
    å unngå et stille hull dersom en framtidig etikett skulle innføres.

IDEMPOTENS (issue #66, krav 4+5): akkurat som chief_ready_signal.py,
identifiseres et allerede-postet varsel ved en EKSAKT, linje-ankret
markør for (issue, head) blant issuens EKSISTERENDE kommentarer -- et
duplikat er et no-op, ikke en feil. En NY head-SHA (PR-en fikk en ny
runde etter en tidligere godkjenning) er bevisst IKKE et duplikat --
den forrige GO-klarheten er per definisjon foreldet, og et nytt varsel
skal postes for det nye hodet.

Ren, avhengighetsfri stdlib-Python -- kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_go_notify_signal.py, slik at selve
beslutningen er testbar uten å kjøre noe mot GitHub.

CLI-bruk (det workflowen gjør):
    jq -n '{issue_number: 66, issue_labels: [...], prs: [...],
            reviews: [...], branch: "agent/issue-66", comments: [...]}' \
      | python3 .github/scripts/go_notify_signal.py "$RUNNER_TEMP/go_notify_comment.txt"
Skriver GITHUB_OUTPUT-linjer (`post`, `duplicate`, `already_merged`,
`pr_number`, `head_sha`, `reason`) til stdout og begrunnelsen til
stderr. Skriver den ferdige kommentarteksten til filstien gitt som
argv[1] KUN når `post=true` -- selve `gh issue comment --body-file`-
kallet gjøres av workflowen, ikke her (ingen `gh`-avhengighet i denne
modulen).

EXIT-KODE (samme kontrakt som chief_ready_signal.py/pr_ready_handoff.py):
`post=true`, `duplicate=true` og (issue #264) `already_merged=true` gir
ALLE exit 0 -- et postet varsel, et idempotent no-op og en allerede
fullført eier-merge er alle suksess, ikke en feil. En fail-closed
AVVISNING (`post=false` OG `duplicate=false` OG `already_merged=false`
-- live-tilstanden tilfredsstiller ikke lenger varsel-kontrakten, eller
en eventuell MERGED PR kunne ikke verifiseres som bevis) gir exit 1,
slik at workflowens eget "Decide GO/NO-GO notification"-steg feiler og
en dedikert rapport-oppfølger kjører, i stedet for at jobben blir grønn
uten både varsel og rapport.

Ingen hemmeligheter/token/miljøverdier eller vilkårlig Claude-output
inngår noensinne i markøren eller kommentarteksten -- kun issue-nummer,
PR-nummer og PR-head-SHA, alle strukturerte tall/hex-strenger fra
`vurder_go_notify`s egne parametre.

RASE-TILFELLET (issue #264, observert i run #512): denne modulen kalles
etter et FERSKT refetch, men mellom `status:approved`-hendelsen og
akkurat dette refetch-et kan eieren allerede ha merget nøyaktig den PR-en
Chief godkjente -- da finner refetch-et 0 åpne PR-er på branchen, som før
#264 ga en fail-closed AVVISNING (exit 1) selv om utfallet i realiteten
var en suksess. `vurder_go_notify` skiller derfor nå eksplisitt mellom
TRE utfall når ingen ÅPEN PR finnes:
  1. nøyaktig én ÅPEN, uslått PR med bekreftet APPROVED-review på sitt
     eksakte hode -- uendret varslingssti (post=True);
  2. INGEN åpen PR, men nøyaktig én MERGED PR på nøyaktig samme
     deterministiske branch/base MED bekreftet APPROVED-review for
     NETTOPP sitt eget eksakte head -- benign no-op (exit 0, intet
     varsel postes; se `allerede_merget`-returverdien og
     `already_merged`-CLI-outputen);
  3. alt annet (0 PR-er, flere kandidater, MERGED uten matchende
     APPROVED-review på sitt eget hode, osv.) -- uendret fail-closed
     AVVISNING (exit 1). En vilkårlig MERGED PR teller ALDRI som bevis
     alene -- den må være den ENE kandidaten på nøyaktig denne branchen
     OG bære sin egen APPROVED-review for sitt eget eksakte head, samme
     strenghet som den ÅPNE stien allerede krevde.
"""
import json
import re
import sys

# Duplisert bevisst (ikke importert) fra lifecycle_labels.LIVSSYKLUS_ETIKETTER
# -- samme uavhengighets-begrunnelse som chief_ready_signal.py og
# pr_ready_handoff.py: denne modulen skal kunne lastes helt uavhengig.
# tests/test_agent_bridge_go_notify_signal.py sjekker at listen er
# identisk med originalen.
LIVSSYKLUS_ETIKETTER = (
    "status:ready",
    "status:working",
    "status:review",
    "status:changes-requested",
    "status:approved",
)

MARKER_VERSJON = "KBH_GO_READY_V1"
MARKER_LINJE_RE = re.compile(
    r"(?m)^" + re.escape(MARKER_VERSJON) + r" issue=(?P<issue>[1-9][0-9]*) head=(?P<head>[0-9a-f]{40})$"
)

_REVIEW_TILSTAND_GODKJENT = "APPROVED"


def bygg_marker(issue_nummer, head_sha):
    """Den ENE, kanoniske markør-linjen -- se moduldocstring for hvorfor
    formatet er akkurat dette (linje-ankret, eksakt case/mellomrom/SHA-
    lengde ved parsing)."""
    return f"{MARKER_VERSJON} issue={int(issue_nummer)} head={head_sha}"


def bygg_kommentar(issue_nummer, pr_nummer, head_sha):
    """Markøren pluss et lite, menneskelesbart GO/NO-GO-varsel til
    eieren. Inneholder bevisst KUN issue-/PR-/head-identifikatorer --
    ingen issue-body, ingen Claude-output, ingen hemmeligheter."""
    marker = bygg_marker(issue_nummer, head_sha)
    return (
        f"{marker}\n\n"
        f"PR #{pr_nummer} er Chief **APPROVED** på eksakt head `{head_sha}`.\n\n"
        "Klar for eier-beslutning: **GO / NO-GO**.\n\n"
        "Dette er kun et varsel -- ingenting merges automatisk. Merge "
        "forblir alltid en egen, manuell eier-handling (via GitHub-UI "
        "eller `gh pr merge`), helt utenfor denne automatiseringen. Et "
        "nytt varsel postes automatisk dersom PR-en får en ny head "
        "(f.eks. via en ny `status:changes-requested`-runde) -- dette "
        "varselet blir da foreldet og skal ikke gjenbrukes."
    )


def finn_eksisterende_markorer(kommentarer):
    """Returnerer settet av (issue, head)-par funnet som EKSAKTE
    markør-linjer i `kommentarer` (liste av issue-topplinje-kommentar-
    body-strenger). Se moduldocstring for hvorfor kun eksakte
    linje-matcher telles."""
    funnet = set()
    for body in kommentarer or []:
        if not body:
            continue
        for m in MARKER_LINJE_RE.finditer(body):
            funnet.add((int(m.group("issue")), m.group("head")))
    return funnet


def _apen_uslatt_pr_pa_branch(prs, branch_navn):
    """`state == "OPEN"` er tilstrekkelig for både "åpen" OG "ikke
    merget" -- GitHubs PR-tilstander (OPEN/CLOSED/MERGED) er gjensidig
    utelukkende, så en MERGED PR kan aldri også være OPEN."""
    kandidater = [
        pr for pr in (prs or [])
        if pr.get("state") == "OPEN"
        and pr.get("baseRefName") == "master"
        and pr.get("headRefName") == branch_navn
    ]
    if len(kandidater) != 1:
        return None
    return kandidater[0]


def _merget_pr_pa_branch(prs, branch_navn):
    """Issue #264: samme "eksakt én kandidat på nøyaktig denne branchen
    mot master"-strenghet som `_apen_uslatt_pr_pa_branch`, men for
    `state == "MERGED"`. Brukt UTELUKKENDE som det sekundære
    "allerede merget"-sporet i `vurder_go_notify` når ingen ÅPEN PR
    finnes -- aldri i stedet for OPEN-sjekken over, og aldri som bevis
    alene (kalleren krever i tillegg en APPROVED-review for nøyaktig
    denne PR-ens eget head via `_godkjent_review_for_head`, akkurat som
    den åpne stien)."""
    kandidater = [
        pr for pr in (prs or [])
        if pr.get("state") == "MERGED"
        and pr.get("baseRefName") == "master"
        and pr.get("headRefName") == branch_navn
    ]
    if len(kandidater) != 1:
        return None
    return kandidater[0]


def _godkjent_review_for_head(pr_reviews, head_sha):
    for review in pr_reviews or []:
        commit = review.get("commit") or {}
        if commit.get("oid") == head_sha and review.get("state") == _REVIEW_TILSTAND_GODKJENT:
            return True
    return False


def vurder_go_notify(*, issue_nummer, issue_labels, prs, branch_navn, pr_reviews, eksisterende_kommentarer):
    """
    Returnerer (post: bool, duplicate: bool, allerede_merget: bool,
    pr_nummer: int|None, head_sha: str|None, kommentar: str|None,
    begrunnelse: str).

    ALT input her skal være FERSKT refetch'et av workflowen rett før
    kallet. Fail-closed: enhver uklarhet (feil/manglende livssyklus-
    etikett, null eller flere PR-kandidater, manglende head-SHA, ingen
    APPROVED-review for nettopp dette hodet) gir `post=False` uten
    unntak/krasj.

    `allerede_merget=True` (issue #264) er en EGEN, ikke-fail-closed
    suksess-avslutning: ingen åpen PR ble funnet, men nøyaktig én MERGED
    PR på nøyaktig denne branchen bar sin egen bekreftede APPROVED-review
    for sitt eget eksakte head -- se moduldocstringens "RASE-TILFELLET".
    """
    if issue_nummer is None:
        return False, False, False, None, None, None, "Mangler issue-nummer -- avviser GO-varsling (fail-closed)."

    issue_labels = list(issue_labels or [])
    livssyklus_i_bruk = [e for e in issue_labels if e in LIVSSYKLUS_ETIKETTER]
    if livssyklus_i_bruk != ["status:approved"]:
        return False, False, False, None, None, None, (
            f"Issue #{issue_nummer} er ikke (lenger) eksklusivt status:approved "
            f"ved refetch (livssyklus-etiketter funnet: {livssyklus_i_bruk}) -- "
            "avviser GO-varsling (fail-closed)."
        )

    pr = _apen_uslatt_pr_pa_branch(prs, branch_navn)
    if pr is None:
        # Issue #264 (run #512-rasen): mellom `status:approved`-refetchet
        # som autoriserte denne jobben og DETTE refetchet kan eieren
        # allerede ha merget nøyaktig den Chief-godkjente PR-en -- det er
        # en suksess, ikke et hull. En vilkårlig MERGED PR er likevel
        # ALDRI nok alene: den må være den ENE kandidaten på nøyaktig
        # denne deterministiske branchen OG bære sin egen APPROVED-review
        # for sitt eget eksakte head, samme strenghet som OPEN-sporet
        # over. Alt annet faller uendret gjennom til fail-closed under.
        merget_pr = _merget_pr_pa_branch(prs, branch_navn)
        if merget_pr is not None:
            merget_head = merget_pr.get("headRefOid")
            if merget_head and _godkjent_review_for_head(pr_reviews, merget_head):
                return False, False, True, merget_pr.get("number"), merget_head, None, (
                    f"PR #{merget_pr.get('number')} på branch {branch_navn!r} er "
                    f"allerede MERGED, med bekreftet APPROVED-review for nettopp "
                    f"sitt eksakte head {merget_head} -- eier har allerede fullført "
                    "merge. Ingen GO-varsling nødvendig (benign no-op, ikke en feil)."
                )

        antall = len([
            p for p in (prs or [])
            if p.get("state") == "OPEN" and p.get("baseRefName") == "master"
            and p.get("headRefName") == branch_navn
        ])
        return False, False, False, None, None, None, (
            f"Fant ikke nøyaktig én åpen, uslått PR mot master på branch "
            f"{branch_navn!r} ved refetch (fant {antall}) -- avviser "
            "GO-varsling (fail-closed)."
        )

    pr_nummer = pr.get("number")
    head_sha = pr.get("headRefOid")
    if not head_sha:
        return False, False, False, pr_nummer, None, None, (
            f"PR #{pr_nummer} mangler headRefOid ved refetch -- avviser GO-varsling (fail-closed)."
        )

    if not _godkjent_review_for_head(pr_reviews, head_sha):
        return False, False, False, pr_nummer, head_sha, None, (
            f"Fant ingen formell APPROVED-review for PR #{pr_nummer}s eksakte "
            f"live head {head_sha} ved refetch -- avviser GO-varsling (fail-closed)."
        )

    eksisterende = finn_eksisterende_markorer(eksisterende_kommentarer)
    if (int(issue_nummer), head_sha) in eksisterende:
        return False, True, False, pr_nummer, head_sha, None, (
            f"GO-varslingsmarkør for issue #{issue_nummer}/head {head_sha} "
            f"finnes allerede -- behandlet som idempotent no-op, ikke en feil."
        )

    kommentar = bygg_kommentar(issue_nummer, pr_nummer, head_sha)
    return True, False, False, pr_nummer, head_sha, kommentar, (
        f"Issue #{issue_nummer} eksklusivt status:approved, PR #{pr_nummer} "
        f"(head {head_sha}) åpen/uslått med bekreftet APPROVED-review på "
        "nettopp dette hodet, ingen tidligere varslingsmarkør funnet -- postes."
    )


def main(argv):
    if len(argv) != 2:
        print("bruk: go_notify_signal.py <output-fil-for-kommentar>", file=sys.stderr)
        return 2
    output_path = argv[1]

    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    post, duplicate, allerede_merget, pr_nummer, head_sha, kommentar, begrunnelse = vurder_go_notify(
        issue_nummer=data.get("issue_number"),
        issue_labels=data.get("issue_labels"),
        prs=data.get("prs"),
        branch_navn=data.get("branch"),
        pr_reviews=data.get("reviews"),
        eksisterende_kommentarer=data.get("comments"),
    )

    print(begrunnelse, file=sys.stderr)
    print(f"post={'true' if post else 'false'}")
    print(f"duplicate={'true' if duplicate else 'false'}")
    print(f"already_merged={'true' if allerede_merget else 'false'}")
    if pr_nummer is not None:
        print(f"pr_number={pr_nummer}")
    if head_sha is not None:
        print(f"head_sha={head_sha}")
    print(f"reason={begrunnelse}")

    if post:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(kommentar)
        return 0

    if duplicate:
        # Idempotent no-op, not a failure: the exact (issue, head) marker
        # already exists, so there is nothing left to do.
        return 0

    if allerede_merget:
        # Issue #264 (run #512 race): the verified, exact-head-approved
        # PR was already merged by the owner before this job's own
        # refetch. Success, not a failure -- there is nothing left to
        # notify about, and no comment is posted since the owner already
        # completed the merge that made this notification moot.
        return 0

    # Fail-closed rejection: live state no longer satisfies the notify
    # contract. Non-zero on purpose, so the "Decide GO/NO-GO notification"
    # workflow step itself fails and its dedicated report step runs
    # instead of the job finishing green with no notification and no
    # report -- same exit-code contract as chief_ready_signal.py.
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
