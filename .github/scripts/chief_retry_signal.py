#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- deterministic Chief-ready retry signal
(issue #40).

BAKGRUNN: PR #39 (issue #38) viste at en gyldig, korrekt konstruert
`KBH_CHIEF_REVIEW_READY_V1`-markor (chief_ready_signal.py, issue #32)
likevel ikke alltid vekker den native ChatGPT Work event-oppgaven --
konkret bevis fra PR #39s egne kommentar-tidsstempler:

  16:41:56Z  runde 1-markor (head c6b9954a...) -- vekket Work korrekt,
             Chief svarte CHANGES_REQUESTED 16:45:05Z.
  16:51:47Z  Claudes egen PR-rapport-kommentar (retterunde 2).
  16:52:07Z  runde 2-markor (head 0bcfc583...) -- KUN 20 sekunder etter
             forrige PR-aktivitet, og ~10.5 minutter etter forrige
             Work-oppgavekjoring startet -- ingen automatisk
             re-review observert.

Presist rotarsak (event-coalescing i Work sin leveranse, eller en
per-PR nedkjolingsperiode etter forrige oppgavekjoring) er IKKE
verifiserbart herfra -- Work sin interne event-/debounce-logikk er en
ekstern SaaS-konfigurasjon uten inspiserbart API fra dette repoet.
Denne modulen antar derfor IKKE hvilken av de to det er, og loser
begge med samme mekanisme: et enkelt, avgrenset (ett-gangs) forsokt
pa nytt, tidsmessig godt isolert fra all annen PR-aktivitet rundt
runde 2-markoren, se "Wait for Chief reaction window" og "Retry
Chief-ready signal"-stegene i workflowen.

HVA DEN GJOR: workflowen venter et fast, dokumentert tidsrom (se
workflow-kommentaren for det eksakte tallet og begrunnelsen) etter at
den ORIGINALE markoren ble postet, refetch'er FERSK live tilstand, og
kaller `vurder_retry` her. Kun hvis ALT av folgende fortsatt stemmer,
postes EN ny kommentar med DEN SAMME markor-linjen (identisk format,
se chief_ready_signal.py) som en isolert, senere PR-aktivitets-hendelse:

  1. Issuen er FORTSATT eksklusivt `status:review` (ingen owner-/
     Work-handling har skjedd i mellomtiden).
  2. Det finnes fortsatt noyaktig EN apen PR mot master pa issuens
     deterministiske branch.
  3. Den PR-ens LIVE head-SHA er UENDRET siden den opprinnelige
     markoren ble postet (ingen nyere runde har allerede overtatt).
  4. Den opprinnelige markoren finnes NOYAKTIG EN gang blant PR-ens
     topplinje-kommentarer (0 = uventet tilstand, avvis; >=2 = et
     forsok er allerede gjort, avvis -- maks ETT retry-forsok per
     hode).
  5. Ingen formell GitHub-review (APPROVED/CHANGES_REQUESTED) finnes
     for nettopp denne head-SHA-en -- hvis en review allerede finnes,
     har Chief faktisk reagert, og et retry-forsok ville vaert bortkastet
     (og i verste fall forvirrende) stoy.

IDEMPOTENS: betingelse 4 over garanterer at denne modulen aldri poster
mer enn EN ekstra markor-kommentar per (issue, head) -- selv om
retry-steget skulle kjore mer enn en gang (f.eks. en manuell re-kjoring
av samme workflow-run), vil andre forsok alltid finne >=2 eksisterende
markorer og avvise. Betingelse 5 garanterer at et retry-forsok aldri
kan trigge en DUPLISERT review -- Work sin egen idempotens (se
AGENT_WORKFLOW.md: "en review-foresporsel for en head-SHA oppgaven
allerede har reviewet, er en no-op") daekker resten uansett.

IKKE-ALARMERENDE VED "NEI": i motsetning til chief_ready_signal.py
(der en fail-closed avvisning ETTER status:review er nadd er en reell
anomali som skal rapporteres) er "post=False" her i all hovedsak det
SUNNE, forventede utfallet -- det betyr som oftest at Chief faktisk
reagerte i tide. CLI-en returnerer derfor ALLTID exit 0; begrunnelsen
er observerbar i workflow-loggen (stderr + `reason=`), men trigger
ingen egen feil-kommentar. Se main() for detaljer.

Duplisert BEVISST fra chief_ready_signal.py (samme begrunnelse som der
for LIVSSYKLUS_ETIKETTER): denne modulen skal kunne lastes helt
uavhengig, ingen .github/scripts-modul krysser-importerer en annen.
tests/test_agent_bridge_chief_retry_signal.py sjekker at de dupliserte
markor-konstantene/-funksjonene forblir identiske med
chief_ready_signal.py sine, slik at formatet aldri kan drifte
ubemerket.

Ren, avhengighetsfri stdlib-Python, kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_chief_retry_signal.py.

CLI-bruk (det workflowen gjor):
    jq -n '{issue_number: 40, issue_labels: [...], prs: [...],
            branch: "agent/issue-40", signaled_head_sha: "...",
            comments: [...], reviews: [...]}' \
      | python3 .github/scripts/chief_retry_signal.py "$RUNNER_TEMP/chief_retry_comment.txt"
Skriver GITHUB_OUTPUT-linjer (`post`, `pr_number`, `head_sha`) til
stdout og begrunnelsen til stderr. Skriver den ferdige kommentarteksten
til filstien gitt som argv[1] KUN nar `post=true`.
"""
import json
import re
import sys

# Duplisert bevisst (ikke importert) fra lifecycle_labels.LIVSSYKLUS_ETIKETTER
# og fra chief_ready_signal sin egen kopi -- se moduldocstring for hvorfor.
# tests/test_agent_bridge_chief_retry_signal.py sjekker at denne, chief_ready_
# signal.LIVSSYKLUS_ETIKETTER og lifecycle_labels.LIVSSYKLUS_ETIKETTER forblir
# identiske.
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

_REVIEW_TILSTANDER_SOM_TELLER = ("APPROVED", "CHANGES_REQUESTED")


def bygg_marker(issue_nummer, head_sha):
    """Identisk med chief_ready_signal.bygg_marker -- se moduldocstring."""
    return f"{MARKER_VERSJON} issue={int(issue_nummer)} head={head_sha}"


def bygg_retry_kommentar(issue_nummer, pr_nummer, head_sha):
    """Samme markor-linje som originalen, pluss en tydelig forklaring
    pa at dette er et automatisk, avgrenset (ett-gangs) forsokt pa nytt
    -- ikke en ny/annen hendelse, og fortsatt ikke autoritativ."""
    marker = bygg_marker(issue_nummer, head_sha)
    return (
        f"{marker}\n\n"
        f"Automatisk retry-vekking (issue #40): ingen Chief-reaksjon ble "
        f"observert for issue #{int(issue_nummer)} / PR #{pr_nummer} "
        f"(head `{head_sha}`) innen det avgrensede ventevinduet etter forrige "
        "markor. Denne kommentaren er DEN SAMME reserverte markoren, postet "
        "pa nytt som en isolert, senere PR-hendelse -- ikke en ny "
        "autoritativ kilde. Den native Work-oppgaven ma fortsatt selv "
        "refetch'e live tilstand for den reviewer noe. Dette er et "
        "engangsforsok (maks ett retry-forsok per hode); den timelige "
        "Chief-overvakingen forblir reserveveien om ogsa dette skulle "
        "utebli. Merge forblir en egen, manuell eier-handling."
    )


def _tell_markorer(kommentarer, issue_nummer, head_sha):
    antall = 0
    for body in kommentarer or []:
        if not body:
            continue
        for m in MARKER_LINJE_RE.finditer(body):
            if int(m.group("issue")) == int(issue_nummer) and m.group("head") == head_sha:
                antall += 1
    return antall


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


def _review_finnes_for_head(pr_reviews, head_sha):
    for review in pr_reviews or []:
        commit = review.get("commit") or {}
        if commit.get("oid") == head_sha and review.get("state") in _REVIEW_TILSTANDER_SOM_TELLER:
            return True
    return False


def vurder_retry(*, issue_nummer, issue_labels, prs, branch_navn, signalert_head_sha,
                  eksisterende_kommentarer, pr_reviews):
    """
    Returnerer (post: bool, pr_nummer: int|None, head_sha: str|None,
    kommentar: str|None, begrunnelse: str).

    ALT input skal vaere FERSKT refetch'et av workflowen rett for
    kallet, etter det faste ventevinduet -- se moduldocstring. Fail-
    closed pa hvert punkt: enhver uklarhet gir `post=False` uten
    unntak/krasj, og er (med unntak av "review allerede funnet")
    IKKE i seg selv en anomali -- se moduldocstring "IKKE-ALARMERENDE
    VED NEI".
    """
    if not signalert_head_sha:
        return False, None, None, None, "Mangler signalert_head_sha -- avviser retry."

    issue_labels = list(issue_labels or [])
    livssyklus_i_bruk = [e for e in issue_labels if e in LIVSSYKLUS_ETIKETTER]
    if livssyklus_i_bruk != ["status:review"]:
        return False, None, None, None, (
            f"Issue #{issue_nummer} er ikke (lenger) eksklusivt status:review "
            f"ved retry-refetch (livssyklus-etiketter funnet: {livssyklus_i_bruk}) -- "
            "trolig allerede handtert; ingen retry nodvendig."
        )

    pr = _apen_pr_pa_branch(prs, branch_navn)
    if pr is None:
        return False, None, None, None, (
            f"Fant ikke noyaktig en apen PR mot master pa branch {branch_navn!r} "
            "ved retry-refetch -- ingen retry postes."
        )

    pr_nummer = pr.get("number")
    live_head_sha = pr.get("headRefOid")
    if live_head_sha != signalert_head_sha:
        return False, pr_nummer, live_head_sha, None, (
            f"PR #{pr_nummer}s live head ({live_head_sha}) er ikke lenger "
            f"den signalerte hoden ({signalert_head_sha}) -- en nyere runde "
            "har allerede overtatt, og har fatt sin egen ferske markor; "
            "ingen retry for den utdaterte hoden."
        )

    antall_markorer = _tell_markorer(eksisterende_kommentarer, issue_nummer, signalert_head_sha)
    if antall_markorer != 1:
        return False, pr_nummer, signalert_head_sha, None, (
            f"Fant {antall_markorer} eksisterende markor(er) for issue #{issue_nummer}/"
            f"head {signalert_head_sha} (forventet noyaktig 1) -- avviser retry "
            "(0 er uventet tilstand; >=2 betyr et retry-forsok allerede er gjort)."
        )

    if _review_finnes_for_head(pr_reviews, signalert_head_sha):
        return False, pr_nummer, signalert_head_sha, None, (
            f"Fant allerede en formell review for head {signalert_head_sha} pa "
            f"PR #{pr_nummer} -- Chief har reagert, ingen retry nodvendig."
        )

    kommentar = bygg_retry_kommentar(issue_nummer, pr_nummer, signalert_head_sha)
    return True, pr_nummer, signalert_head_sha, kommentar, (
        f"Ingen Chief-reaksjon observert for issue #{issue_nummer}/PR #{pr_nummer}/"
        f"head {signalert_head_sha} innen ventevinduet -- poster ett-gangs retry-markor."
    )


def main(argv):
    if len(argv) != 2:
        print("bruk: chief_retry_signal.py <output-fil-for-retry-kommentar>", file=sys.stderr)
        return 2
    output_path = argv[1]

    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    post, pr_nummer, head_sha, kommentar, begrunnelse = vurder_retry(
        issue_nummer=data.get("issue_number"),
        issue_labels=data.get("issue_labels"),
        prs=data.get("prs"),
        branch_navn=data.get("branch"),
        signalert_head_sha=data.get("signaled_head_sha"),
        eksisterende_kommentarer=data.get("comments"),
        pr_reviews=data.get("reviews"),
    )

    print(begrunnelse, file=sys.stderr)
    print(f"post={'true' if post else 'false'}")
    if pr_nummer is not None:
        print(f"pr_number={pr_nummer}")
    if head_sha is not None:
        print(f"head_sha={head_sha}")
    print(f"reason={begrunnelse}")

    if post:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(kommentar)

    # Bevisst ALLTID exit 0 -- se moduldocstring "IKKE-ALARMERENDE VED
    # NEI". Dette avviker fra chief_ready_signal.py sin exit-kode-
    # kontrakt med hensikt: der er en fail-closed avvisning etter
    # status:review en reell anomali (ingenting postet i det hele tatt);
    # her er "ingen retry nodvendig" i all hovedsak det SUNNE utfallet
    # (Chief reagerte, eller en nyere runde har allerede overtatt), og
    # skal ikke trigge en egen feil-rapport-kommentar.
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
