#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- PR Ready-for-review-overgang (issue #44).

BAKGRUNN: se pr_draft_handoff.py sin moduldocstring for hele
resonnementet bak hvorfor issue #44 erstatter den upålitelige
kommentar-baserte retry-vekkingen (chief_retry_signal.py, issue #40 --
FJERNET av denne issuen) med en PR-tilstandsovergang.

DENNE MODULEN dekker andre halvdel av syklusen: som DEN SISTE handlingen
i en vellykket bridge-runde -- etter at leveranse-porten
(deliverable_guard.py) og den eksisterende Chief-ready-markøren
(chief_ready_signal.py, issue #32) begge har passert på et FERSKT
refetch av live tilstand -- konverteres den samme PR-en fra Draft til
Ready for review. Det er DENNE GitHub-hendelsen (`ready_for_review`),
ikke enda en PR-kommentar, den native ChatGPT Work-oppgaven våkner på
for runde 2+ (AGENT_WORKFLOW.md "Work-side Chief task (V1, issue #31)").

RUNDE 1 / INITIAL-RUNDE-SIKKERHET: en fersk `status:ready`-PR opprettes
alltid Ready (gh pr create sin default) -- den er ALDRI Draft når denne
porten kjører for runde 1. For `status:ready` er "PR-en er allerede
Ready" derfor UNNTAKSFRITT trygt: `already_ready=True`, ingen mutasjon,
og runde 1s eksisterende oppvåkning via GitHubs `opened`-PR-hendelse +
Chief-ready-markøren fortsetter helt uforstyrret.

Chief-review-fiks (PR #45, runde 3): for `status:changes-requested` er
"allerede Ready" derimot IKKE unntaksfritt trygt -- `pr_draft_handoff.py`
gjør Draft en VERIFISERT forutsetning FØR Claude kjører, men PR-en kan i
prinsippet bli eksternt/prematurt undraftet ETTER den verifiseringen og
FØR dette steget kjører, uten at DENNE mekanismen noensinne faktisk
utførte en Draft -> Ready-overgang for det nye hodet -- nøyaktig den
uteblitte re-review-vekkingen issue #44 skal forhindre. Derfor: for
`status:changes-requested` teller "allerede Ready" kun som et trygt,
idempotent no-op når en EGEN, reservert
`KBH_PR_READY_TRANSITION_DONE_V1`-markør for nettopp dette
(issue, head)-paret allerede finnes blant PR-ens kommentarer -- BEVIS
at DENNE mekanismen (og ikke noe eksternt) alt utførte overgangen for
akkurat dette hodet (f.eks. en re-kjøring av selve dette workflow-
steget etter at overgangen alt lyktes). Uten den markøren er "allerede
Ready" i en changes-requested-runde en REELL, fail-closed avvisning --
se `vurder_ready` og "FAIL-CLOSED" under.

FAIL-CLOSED (issue #44, akseptansekriterium 3) -- enhver av følgende gir
`set_ready=False, already_ready=False` (en REELL avvisning, se CLI-
kontrakten i main()):
  1. Manglende signalert head-SHA fra Chief-ready-signalet.
  2. Issuen er ikke (lenger) eksklusivt `status:review` ved refetch.
  3. Ingen (eller mer enn én) åpen PR mot master på issuens
     deterministiske branch (feil branch/base).
  4. PR-ens LIVE head-SHA er ikke lenger den signalerte hoden (stale
     head -- en nyere runde har allerede overtatt).
  5. Antall gyldige forekomster av DEN SAMME markøren (issue, head) blant
     PR-ens topplinje-kommentarer er ikke nøyaktig 1 (0 = manglende
     markør, >=2 = konflikt/duplikat).
  6. En formell GitHub-review (APPROVED/CHANGES_REQUESTED) finnes
     allerede for nettopp denne head-SHA-en -- en ny overgang ville
     trigget en overflødig/forvirrende re-review.
  7. (Kun `status:changes-requested`, PR #45 runde 3): PR-en er allerede
     Ready (ikke Draft), MEN ingen `KBH_PR_READY_TRANSITION_DONE_V1`-
     markør for dette (issue, head)-paret beviser at DENNE mekanismen
     utførte overgangen -- se "RUNDE 1 / INITIAL-RUNDE-SIKKERHET" over.

("failed deliverable validation" fra samme akseptansekriterium er
allerede strukturelt umulig å nå denne porten med -- workflowen gater
alle disse nye stegene på `steps.deliverable.outputs.ok == 'true'`, se
claude-agent-bridge.yml.)

IDEMPOTENS / "No duplicate review/lifecycle mutation for an exact
head" (issue #44, akseptansekriterium 4): en PR som allerede ER Ready
(fordi en tidligere kjøring av dette steget allerede lyktes, ELLER fordi
det er runde 1) faller alltid i `already_ready`-grenen over -- `gh pr
ready` kalles rett og slett ikke på nytt for samme hode.

Duplisert BEVISST (ikke importert) fra lifecycle_labels.py og
chief_ready_signal.py/chief_retry_signal.py sine kopier av
LIVSSYKLUS_ETIKETTER, MARKER_VERSJON, MARKER_LINJE_RE og hjelperne under
-- samme uavhengighets-begrunnelse som der: denne modulen skal kunne
lastes helt uavhengig av de andre .github/scripts-modulene.
tests/test_agent_bridge_pr_ready_handoff.py sjekker at kopiene forblir
identiske.

Ren, avhengighetsfri stdlib-Python, kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_pr_ready_handoff.py.

CLI-bruk (det workflowen gjør):
    jq -n '{issue_number: 44, issue_labels: [...], prs: [...],
            branch: "agent/issue-44", signaled_head_sha: "...",
            comments: [...], reviews: [...], trigger_label: "status:changes-requested"}' \
      | python3 .github/scripts/pr_ready_handoff.py "$RUNNER_TEMP/pr_ready_done_marker.txt"
Skriver GITHUB_OUTPUT-linjer (`set_ready`, `already_ready`, `pr_number`,
`head_sha`, `reason`) til stdout og begrunnelsen til stderr. Skriver
`KBH_PR_READY_TRANSITION_DONE_V1`-markørlinjen til filstien gitt som
argv[1] KUN når `set_ready=true` (argumentet er valgfritt -- utelates
det, skrives ingen fil, samme bakoverkompatible mønster som
chief_ready_signal.py); selve `gh pr comment --body-file`-postingen
gjøres av workflowen, ikke her.

EXIT-KODE: `set_ready=true` og `already_ready=true` gir begge exit 0 --
en gjennomført overgang og et idempotent no-op er begge suksess. En
REELL fail-closed avvisning (begge False) gir exit 1, slik at "Decide PR
ready-for-review transition"-workflow-steget selv feiler og en dedikert
feil-rapport-oppfølger kjører -- samme kontrakt/begrunnelse som
chief_ready_signal.py.
"""
import json
import re
import sys

LIVSSYKLUS_ETIKETTER = (
    "status:ready",
    "status:working",
    "status:review",
    "status:changes-requested",
    "status:approved",
)

MARKER_VERSJON = "KBH_CHIEF_REVIEW_READY_V1"
MARKER_LINJE_RE = re.compile(
    r"(?m)^" + re.escape(MARKER_VERSJON) + r" issue=(?P<issue>[1-9][0-9]*) head=(?P<head>[0-9a-f]{40})$"
)

# Egen, reservert markør (PR #45 runde 3) -- POSTES av DENNE modulen selv,
# rett etter at `gh pr ready` faktisk har lyktes for et gitt (issue, head)
# -- se moduldocstring "RUNDE 1 / INITIAL-RUNDE-SIKKERHET" og
# "FAIL-CLOSED" punkt 7. Formatet følger bevisst samme strenge,
# linje-ankrede mønster som MARKER_LINJE_RE over (egen versjonsstreng, så
# den aldri kan forveksles med Chief-ready-markøren).
MARKER_READY_DONE_VERSJON = "KBH_PR_READY_TRANSITION_DONE_V1"
MARKER_READY_DONE_LINJE_RE = re.compile(
    r"(?m)^" + re.escape(MARKER_READY_DONE_VERSJON) + r" issue=(?P<issue>[1-9][0-9]*) head=(?P<head>[0-9a-f]{40})$"
)

_REVIEW_TILSTANDER_SOM_TELLER = ("APPROVED", "CHANGES_REQUESTED")


def _tell_markorer(kommentarer, issue_nummer, head_sha):
    antall = 0
    for body in kommentarer or []:
        if not body:
            continue
        for m in MARKER_LINJE_RE.finditer(body):
            if int(m.group("issue")) == int(issue_nummer) and m.group("head") == head_sha:
                antall += 1
    return antall


def bygg_ready_done_marker(issue_nummer, head_sha):
    """Den ENE, kanoniske ready-transition-done-markør-linjen -- postes
    KUN etter at `gh pr ready` faktisk har lyktes, som bevis for at DENNE
    mekanismen (og ikke noe eksternt) utførte Draft -> Ready-overgangen
    for nettopp dette (issue, head)-paret."""
    return f"{MARKER_READY_DONE_VERSJON} issue={int(issue_nummer)} head={head_sha}"


def _tell_ready_done_markorer(kommentarer, issue_nummer, head_sha):
    antall = 0
    for body in kommentarer or []:
        if not body:
            continue
        for m in MARKER_READY_DONE_LINJE_RE.finditer(body):
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


def vurder_ready(*, issue_nummer, issue_labels, prs, branch_navn, signalert_head_sha,
                  eksisterende_kommentarer, pr_reviews, trigger_label=None):
    """
    Returnerer (set_ready: bool, already_ready: bool, pr_nummer: int|None,
    head_sha: str|None, begrunnelse: str).

    ALT input skal være FERSKT refetch'et av workflowen rett før kallet,
    ETTER at Chief-ready-markøren allerede er postet/bekreftet duplikat
    -- se moduldocstring "Ordering". `already_ready=True` er et
    IKKE-alarmerende no-op; enhver annen `set_ready=False` er en
    fail-closed AVVISNING (se moduldocstring, akseptansekriterium 3).

    `trigger_label` avgjør HVOR trygt "PR-en er allerede Ready" er (PR #45
    runde 3, se moduldocstring "RUNDE 1 / INITIAL-RUNDE-SIKKERHET"): kun
    for eksakt `status:changes-requested` kreves et bevist
    `KBH_PR_READY_TRANSITION_DONE_V1`-funn for nettopp dette hodet --
    samme "`!= status:changes-requested` er den trygge grenen"-konvensjon
    som `pr_draft_handoff.py` allerede bruker. Enhver annen verdi
    (`status:ready`, eller ikke oppgitt -- workflowen sender alltid en av
    de to eksakte verdiene i praksis) er unntaksfritt trygt, uendret fra
    før denne fiksen.
    """
    if not signalert_head_sha:
        return False, False, None, None, (
            "Mangler signalert head-sha fra Chief-ready-signalet -- avviser "
            "ready-overgang (fail-closed)."
        )

    if issue_nummer is None:
        return False, False, None, None, "Mangler issue-nummer -- avviser ready-overgang (fail-closed)."

    issue_labels = list(issue_labels or [])
    livssyklus_i_bruk = [e for e in issue_labels if e in LIVSSYKLUS_ETIKETTER]
    if livssyklus_i_bruk != ["status:review"]:
        return False, False, None, None, (
            f"Issue #{issue_nummer} er ikke (lenger) eksklusivt status:review "
            f"ved refetch (livssyklus-etiketter funnet: {livssyklus_i_bruk}) -- "
            "avviser ready-overgang (fail-closed)."
        )

    pr = _apen_pr_pa_branch(prs, branch_navn)
    if pr is None:
        return False, False, None, None, (
            f"Fant ikke nøyaktig én åpen PR mot master på branch {branch_navn!r} "
            "ved refetch -- avviser ready-overgang (fail-closed)."
        )

    pr_nummer = pr.get("number")
    live_head_sha = pr.get("headRefOid")
    if live_head_sha != signalert_head_sha:
        return False, False, pr_nummer, live_head_sha, (
            f"PR #{pr_nummer}s live head ({live_head_sha}) er ikke lenger den "
            f"signalerte hoden ({signalert_head_sha}) -- stale head, avviser "
            "ready-overgang (fail-closed)."
        )

    antall_markorer = _tell_markorer(eksisterende_kommentarer, issue_nummer, signalert_head_sha)
    if antall_markorer != 1:
        return False, False, pr_nummer, signalert_head_sha, (
            f"Fant {antall_markorer} markør(er) for issue #{issue_nummer}/head "
            f"{signalert_head_sha} (forventet nøyaktig 1) -- avviser ready-overgang "
            "(fail-closed; 0 er manglende markør, >=2 er en konflikt/duplikat)."
        )

    if _review_finnes_for_head(pr_reviews, signalert_head_sha):
        return False, False, pr_nummer, signalert_head_sha, (
            f"Fant allerede en formell review for head {signalert_head_sha} på "
            f"PR #{pr_nummer} -- avviser ready-overgang (fail-closed; en ny "
            "overgang ville trigget en overflødig/forvirrende re-review)."
        )

    if not pr.get("isDraft"):
        if trigger_label != "status:changes-requested":
            return False, True, pr_nummer, signalert_head_sha, (
                f"PR #{pr_nummer} er allerede Ready (ikke Draft) -- trigger-etikett "
                f"{trigger_label!r} går aldri via Draft (runde 1) -- unntaksfritt "
                "idempotent no-op."
            )

        antall_ferdig = _tell_ready_done_markorer(eksisterende_kommentarer, issue_nummer, signalert_head_sha)
        if antall_ferdig >= 1:
            return False, True, pr_nummer, signalert_head_sha, (
                f"PR #{pr_nummer} er allerede Ready (ikke Draft), MEN en "
                f"{MARKER_READY_DONE_VERSJON}-markør for nettopp issue #{issue_nummer}/"
                f"head {signalert_head_sha} beviser at DENNE mekanismen alt utførte "
                "overgangen -- idempotent no-op (bevist gjentatt kjøring)."
            )

        return False, False, pr_nummer, signalert_head_sha, (
            f"status:changes-requested-runde: PR #{pr_nummer} er allerede Ready "
            f"(ikke Draft), men INGEN {MARKER_READY_DONE_VERSJON}-markør finnes for "
            f"issue #{issue_nummer}/head {signalert_head_sha} -- kan ikke bevise at "
            "DENNE mekanismen utførte overgangen (PR-en kan ha blitt eksternt/"
            "prematurt undraftet før dette steget fikk kjøre) -- avviser "
            "ready-overgang (fail-closed); en stille godkjenning her ville tapt "
            "nettopp den re-review-vekkingen issue #44 skal garantere."
        )

    return True, False, pr_nummer, signalert_head_sha, (
        f"Issue #{issue_nummer} eksklusivt status:review, PR #{pr_nummer} (head "
        f"{signalert_head_sha}) bekreftet Draft med nøyaktig én gyldig markør og "
        "ingen eksisterende review -- overgang til Ready for review."
    )


def main(argv=None):
    argv = sys.argv if argv is None else argv
    output_path = argv[1] if len(argv) > 1 else None

    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    set_ready, already_ready, pr_nummer, head_sha, begrunnelse = vurder_ready(
        issue_nummer=data.get("issue_number"),
        issue_labels=data.get("issue_labels"),
        prs=data.get("prs"),
        branch_navn=data.get("branch"),
        signalert_head_sha=data.get("signaled_head_sha"),
        eksisterende_kommentarer=data.get("comments"),
        pr_reviews=data.get("reviews"),
        trigger_label=data.get("trigger_label"),
    )

    print(begrunnelse, file=sys.stderr)
    print(f"set_ready={'true' if set_ready else 'false'}")
    print(f"already_ready={'true' if already_ready else 'false'}")
    if pr_nummer is not None:
        print(f"pr_number={pr_nummer}")
    if head_sha is not None:
        print(f"head_sha={head_sha}")
    print(f"reason={begrunnelse}")

    if set_ready and output_path and head_sha is not None and data.get("issue_number") is not None:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(bygg_ready_done_marker(data.get("issue_number"), head_sha))

    if set_ready or already_ready:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
