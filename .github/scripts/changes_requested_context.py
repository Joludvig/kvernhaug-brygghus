#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- deterministisk, fail-closed arbeidskontekst for
`status:changes-requested` (issue #329).

BAKGRUNN (den faktiske hendelsen): issue #327 / PR #328 fikk en ekte Chief
exact-head review med CHANGES_REQUESTED på
`6699b63b039b7cefc086fceb65b01eb48adc3542`. Eieren satte deretter
`status:changes-requested` mens `agent:claude` var beholdt, og Agent
Bridge-kjøring 35399093833 gjorde ALT det riktige på trigger-siden:
trigger-etiketten var korrekt, `agent:claude` fantes både på
event-tidspunktet og live, senderen var repo-eier, workflowen rapporterte
eksplisitt at triggeren var autorisert, fant den eksisterende PR-en,
fanget korrekt pre-run head og satte PR-en tilbake til Draft.

Likevel endte Claude-runnen `conclusion: success` med
`permission_denials_count = 11`, INGEN ny commit, uendret PR-head, og
`deliverable_guard.py` rapporterte korrekt `no_new_commits` -- issuen ble
fail-closed stående på `status:working`.

ROT-ÅRSAKEN er ikke triggeren, men HANDOFFEN: på changes-requested-banen
ga wrapperen Claude nesten ingen verifisert arbeidskontekst, og lot Claude
gjenoppdage alt selv gjennom en rekke gh/git-kall FØR den kunne begynne på
selve Chief-reviewen:

1. Runneren står på `master`, ikke på arbeidsbranchen (`actions/checkout@v4`
   på et `issues`-event sjekker ut default-ref -- kjøring 35399093833
   bekrefter `head_branch: master`). Prompten ba Claude fetche og checkoute
   branchen selv, så branch-oppdagelse ble Claudes FØRSTE oppgave i en runde
   som egentlig handler om å rette en review.
2. Claude måtte gjenoppdage PR-en (`gh pr view` / `gh pr list --head ...`)
   selv om wrapperen allerede hadde fanget nøyaktig PR-nummer og head-SHA
   to steg tidligere (`Capture pre-run PR state`) og re-verifisert dem i
   `Verify PR Draft state before Claude run`.
3. Claude måtte gjenoppdage selve reviewen ("Read the latest Chief review on
   that PR"). INGENTING verifiserte at en slik review i det hele tatt fantes,
   at den var CHANGES_REQUESTED, at forfatteren var repo-eier, eller at den
   gjaldt nøyaktig det hodet det ble jobbet på. Review-objektet ER hele
   arbeidsordren for runden, og var det ene som aldri ble bundet inn i
   handoffen.
4. Hvert eneste gjenoppdagelses-kall er en permission-flate. 11 avslag over
   50 turer med null commits er signaturen til en kjøring som brukte opp
   budsjettet sitt på oppdagelse den aldri skulle trengt å gjøre.

DENNE MODULEN lukker punkt 2-4 (og leverer forutsetningen for punkt 1):
den tar LIVE GitHub-tilstand inn, beviser -- eller avviser fail-closed --
hele arbeidskonteksten, og skriver den verifiserte review-teksten til fil
slik at workflowen kan gi Claude den DIREKTE.

FAIL-CLOSED KONTRAKT (ingen Claude-run skal starte uten alle disse):
  - nøyaktig én åpen PR med `base = master` og `head = <deterministisk branch>`;
  - PR-identiteten er den samme som ble fanget FØR kjøringen startet;
  - PR-ens ferske head er EKSAKT det pre-run-hodet (40-tegns SHA);
  - det finnes en CHANGES_REQUESTED-review fra autorisert Chief-identitet
    (repo-eier);
  - den reviewens `commit_id` er EKSAKT samme head;
  - reviewens body er ikke tom;
  - ingen NYERE beslutnings-review fra samme identitet har gjort den
    foreldet (se `_nyeste_beslutning` for den dokumenterte semantikken).

PR-kommentarer, markør-tekst og Claude-genererte oppsummeringer er ALDRI
en erstatning for selve review-objektet -- kun `reviews`-API-et teller.

TRANSPORT AV REVIEW-TEKST: review-body er fritekst skrevet av et menneske og
kan inneholde backticks, anførselstegn, `$(...)`, YAML-aktige linjer og
vilkårlige linjeskift. Den passerer derfor ALDRI gjennom shell-quoting,
`$GITHUB_OUTPUT` eller en `${{ }}`-interpolasjon. Python skriver den direkte
til en fil (`CONTEXT_BODY_PATH`, default `.agent_bridge_run/chief_review.md`,
git-ignorert), og prompten peker Claude på den filen. Alle `reason=`-linjer
denne modulen skriver til `$GITHUB_OUTPUT` er bevisst ÉN linje uten
review-innhold i seg.

Ren, avhengighetsfri stdlib-Python, kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_changes_requested_context.py -- hele beslutningen er
dermed testbar uten noe reelt GitHub- eller Claude Code-kall.

CLI-bruk (det workflowen gjør):

    echo '{"trigger_label": "status:changes-requested", "issue": "327",
           "branch": "agent/issue-327", "before_pr_number": "328",
           "before_head_sha": "<40-char-sha>", "repo_owner": "Joludvig",
           "prs": [...], "reviews": [...]}' \
      | CONTEXT_BODY_PATH=.agent_bridge_run/chief_review.md \
        python3 .github/scripts/changes_requested_context.py verify
Skriver GITHUB_OUTPUT-linjer (`context_verified`, og ved suksess
`pr_number`/`head_sha`/`branch`/`review_id`/`review_author`/
`review_submitted_at`/`review_body_path`, samt `reason`) til stdout og
begrunnelsen til stderr. Exit 0 hvis konteksten er bevist (eller ikke
påkrevd for denne trigger-etiketten), exit 1 ved en REELL fail-closed
avvisning -- samme exit-kode-kontrakt som pr_draft_handoff.py/
chief_ready_signal.py/pr_ready_handoff.py, slik at det tilhørende
workflow-steget selv feiler og "Run Claude Code" aldri kjøres (standard
GitHub Actions-oppførsel: et feilende steg stopper resten av jobben).

    TRIGGER_LABEL=status:changes-requested EXPECTED_HEAD=<sha> \
    LOCAL_HEAD=<sha> BRANCH=agent/issue-327 LOCAL_BRANCH=agent/issue-327 \
      python3 .github/scripts/changes_requested_context.py checkout-verify
Samme exit-kode-kontrakt, for steget som klargjør den EKSISTERENDE
arbeidsbranchen før Claude starter (punkt 1 over): beviser at lokal HEAD
faktisk ER det verifiserte pre-run-hodet, slik at Claude aldri trenger å
"finne riktig branch" som første arbeidsoppgave.
"""
import json
import os
import sys

TRIGGER_ETIKETT = "status:changes-requested"
MASTER = "master"
DEFAULT_BODY_PATH = os.path.join(".agent_bridge_run", "chief_review.md")

# Review-states som teller som en BESLUTNING fra Chief. `COMMENTED` og
# `PENDING` er bevisst utelatt: en ren kommentar-review er ingen ny dom og
# skal derfor ikke gjøre en gyldig CHANGES_REQUESTED foreldet (ellers ville
# en hvilken som helst oppfølgingskommentar fra eieren blokkert runden).
BESLUTNINGS_STATES = ("APPROVED", "CHANGES_REQUESTED", "DISMISSED")


def _er_sha(verdi):
    """Et ekte 40-tegns hex commit-SHA -- ikke en forkortet/tom/"HEAD"-streng."""
    if not isinstance(verdi, str) or len(verdi) != 40:
        return False
    return all(c in "0123456789abcdef" for c in verdi.lower())


def _apne_pr_kandidater(prs, branch_navn):
    """(eksakte_treff, apne_prs) for den deterministiske branchen.

    Skilt fra hverandre med vilje: `apne_prs` lar `velg_pr` gi en PRESIS
    diagnose ("feil base/head") i stedet for å kollapse alt til "ingen PR".
    """
    apne = [pr for pr in (prs or []) if (pr or {}).get("state") == "OPEN"]
    eksakte = [
        pr for pr in apne
        if pr.get("baseRefName") == MASTER and pr.get("headRefName") == branch_navn
    ]
    return eksakte, apne


def velg_pr(prs, branch_navn):
    """Returnerer (pr: dict|None, begrunnelse: str|None).

    `begrunnelse` er satt NÅR OG BARE NÅR pr er None -- dvs. en fail-closed
    avvisning. Nøyaktig én åpen PR mot `master` på nøyaktig den
    deterministiske branchen, ellers ingenting.
    """
    eksakte, apne = _apne_pr_kandidater(prs, branch_navn)

    if len(eksakte) == 1:
        return eksakte[0], None

    if len(eksakte) > 1:
        numre = ", ".join(f"#{pr.get('number')}" for pr in eksakte)
        return None, (
            f"Fant {len(eksakte)} åpne PR-er ({numre}) mot {MASTER} på branch "
            f"{branch_navn!r} -- tvetydig leveranse-assosiering, kan ikke velge "
            "én arbeids-PR (fail-closed)."
        )

    if apne:
        avvik = "; ".join(
            f"#{pr.get('number')} base={pr.get('baseRefName')!r} head={pr.get('headRefName')!r}"
            for pr in apne
        )
        return None, (
            f"Ingen åpen PR har både base={MASTER!r} og head={branch_navn!r} -- "
            f"kandidatene avviker: {avvik} (fail-closed)."
        )

    return None, (
        f"Fant ingen åpen PR mot {MASTER} på branch {branch_navn!r} -- det finnes "
        "ingen eksisterende arbeids-PR å levere en changes-requested-runde inn i "
        "(fail-closed)."
    )


def _eier_reviews(reviews, repo_owner):
    """Reviews fra den autoriserte Chief-identiteten (repo-eier), i
    innsendingsrekkefølge. Alt annet -- andre forfattere, bot-aktører,
    kommentarer på PR-en, markør-tekst -- er per konstruksjon utelatt."""
    ut = []
    for r in reviews or []:
        if not isinstance(r, dict):
            continue
        bruker = (r.get("user") or {})
        if bruker.get("login") != repo_owner:
            continue
        ut.append(r)
    ut.sort(key=lambda r: (r.get("submitted_at") or "", str(r.get("id") or "")))
    return ut


def _nyeste_beslutning(eier_reviews):
    """Den SISTE beslutnings-reviewen fra Chief, eller None.

    DOKUMENTERT FORELDELSES-SEMANTIKK (akseptansepunkt I): en
    CHANGES_REQUESTED er kun gyldig arbeidsordre så lenge den er Chiefs
    SISTE beslutning. Kommer det en nyere APPROVED (Chief ombestemte seg /
    passerte likevel) eller en nyere DISMISSED (reviewen ble trukket),
    er den gamle CHANGES_REQUESTED foreldet og runden avvises fail-closed --
    heller ingen kjøring enn en kjøring på en tilbakekalt arbeidsordre.
    `COMMENTED`/`PENDING` er IKKE beslutninger og gjør ingenting foreldet
    (se BESLUTNINGS_STATES)."""
    for r in reversed(eier_reviews):
        if r.get("state") in BESLUTNINGS_STATES:
            return r
    return None


def velg_review(reviews, repo_owner, head_sha):
    """Returnerer (review: dict|None, begrunnelse: str|None).

    `begrunnelse` er satt NÅR OG BARE NÅR review er None. Rekkefølgen på
    sjekkene er valgt slik at avvisningen forteller HVILKEN forutsetning som
    sviktet, ikke bare at noe manglet.
    """
    if not repo_owner:
        return None, (
            "Repo-eier/autorisert Chief-identitet er ikke oppgitt -- kan ikke "
            "avgjøre om noen review er skrevet av en autorisert forfatter "
            "(fail-closed)."
        )

    eiers = _eier_reviews(reviews, repo_owner)
    if not eiers:
        fremmede = sorted({
            ((r or {}).get("user") or {}).get("login")
            for r in (reviews or [])
            if isinstance(r, dict)
        } - {None})
        detalj = f" (fant kun reviews fra: {', '.join(fremmede)})" if fremmede else ""
        return None, (
            f"Ingen review fra autorisert Chief-identitet {repo_owner!r} på denne "
            f"PR-en{detalj} -- en CHANGES_REQUESTED fra en annen forfatter er "
            "ikke en gyldig arbeidsordre (fail-closed)."
        )

    beslutning = _nyeste_beslutning(eiers)
    if beslutning is None:
        return None, (
            f"{repo_owner!r} har ingen beslutnings-review på denne PR-en (kun "
            f"states utenfor {list(BESLUTNINGS_STATES)}) -- det finnes ingen "
            "CHANGES_REQUESTED å jobbe etter (fail-closed)."
        )

    if beslutning.get("state") != "CHANGES_REQUESTED":
        return None, (
            f"Chiefs SISTE beslutnings-review er {beslutning.get('state')!r} "
            f"(review {beslutning.get('id')}, {beslutning.get('submitted_at')}) -- "
            "en eventuell eldre CHANGES_REQUESTED er dermed foreldet og er ikke "
            "lenger en gyldig arbeidsordre (fail-closed)."
        )

    commit_id = beslutning.get("commit_id")
    if commit_id != head_sha:
        return None, (
            f"CHANGES_REQUESTED-review {beslutning.get('id')} gjelder commit "
            f"{commit_id!r}, ikke PR-ens eksakte nåværende head {head_sha!r} -- "
            "reviewen er knyttet til et annet/foreldet hode (fail-closed)."
        )

    if not (beslutning.get("body") or "").strip():
        return None, (
            f"CHANGES_REQUESTED-review {beslutning.get('id')} har tom body -- "
            "det finnes ingen faktiske reviewpunkter å adressere (fail-closed)."
        )

    return beslutning, None


def bygg_kontekst(
    *,
    trigger_label,
    issue_nummer,
    branch_navn,
    before_pr_number,
    before_head_sha,
    prs,
    reviews,
    repo_owner,
):
    """Returnerer (verifisert: bool, kontekst: dict|None, begrunnelse: str).

    `verifisert=True` med `kontekst=None` betyr "ikke påkrevd for denne
    trigger-etiketten" -- en `status:ready`-runde har per definisjon verken
    PR eller review ennå og skal ikke berøres av denne porten i det hele
    tatt (samme ikke-alarmerende mønster som `verifiser_draft` i
    pr_draft_handoff.py). `verifisert=False` er ALLTID en reell fail-closed
    avvisning.
    """
    if trigger_label != TRIGGER_ETIKETT:
        return True, None, (
            f"Trigger-etikett er {trigger_label!r}, ikke {TRIGGER_ETIKETT} -- "
            "verifisert review-kontekst er ikke en forutsetning for denne runden."
        )

    if not branch_navn:
        return False, None, (
            "Deterministisk branch-navn mangler -- kan ikke resolve "
            "arbeidsbranchen for changes-requested-runden (fail-closed)."
        )

    if not before_pr_number or not before_head_sha:
        return False, None, (
            "Manglende PR-nummer og/eller head-SHA fanget FØR denne kjøringen "
            "startet -- kan ikke binde handoffen til en eksakt PR/head "
            "(fail-closed)."
        )

    if not _er_sha(before_head_sha):
        return False, None, (
            f"Pre-run head {before_head_sha!r} er ikke et fullt 40-tegns "
            "commit-SHA -- handoffen kan kun bindes til et eksakt hode "
            "(fail-closed)."
        )

    pr, avvisning = velg_pr(prs, branch_navn)
    if pr is None:
        return False, None, avvisning

    pr_nummer = pr.get("number")
    if str(pr_nummer) != str(before_pr_number):
        return False, None, (
            f"PR-identiteten endret seg (var #{before_pr_number}, er nå "
            f"#{pr_nummer}) ved fersk refetch -- handoffen kan ikke bindes til "
            "en annen PR enn den som ble fanget før kjøringen (fail-closed)."
        )

    fersk_head = pr.get("headRefOid")
    if fersk_head != before_head_sha:
        return False, None, (
            f"PR #{pr_nummer} sitt hode har endret seg (var {before_head_sha!r}, "
            f"er nå {fersk_head!r}) mellom pre-run-fangsten og dette ferske "
            "refetchet -- handoffen kan ikke bindes til et hode som allerede har "
            "flyttet seg (fail-closed)."
        )

    review, avvisning = velg_review(reviews, repo_owner, fersk_head)
    if review is None:
        return False, None, avvisning

    kontekst = {
        "issue": str(issue_nummer or "").strip(),
        "pr_number": str(pr_nummer),
        "branch": branch_navn,
        "head_sha": fersk_head,
        "base": MASTER,
        "review_id": str(review.get("id")),
        "review_author": review.get("user", {}).get("login"),
        "review_submitted_at": review.get("submitted_at"),
        "review_body": review.get("body"),
    }
    return True, kontekst, (
        f"Verifisert changes-requested-kontekst: issue #{kontekst['issue']}, "
        f"PR #{kontekst['pr_number']}, branch {branch_navn}, eksakt head "
        f"{fersk_head}, CHANGES_REQUESTED-review {kontekst['review_id']} av "
        f"{kontekst['review_author']} på samme head."
    )


def verifiser_lokalt_hode(*, trigger_label, expected_head, local_head, branch_navn, local_branch):
    """Returnerer (ok: bool, begrunnelse: str) for branch-klargjøringssteget.

    Beviser at wrapperen faktisk landet på den EKSISTERENDE arbeidsbranchen
    på nøyaktig det verifiserte pre-run-hodet FØR Claude starter -- slik at
    "finn riktig branch" aldri er Claudes første arbeidsoppgave i en
    changes-requested-runde (rot-årsak punkt 1 i moduldocstringen).
    Ikke-alarmerende for alle andre trigger-etiketter: `status:ready` har
    ingen eksisterende branch å lande på.
    """
    if trigger_label != TRIGGER_ETIKETT:
        return True, (
            f"Trigger-etikett er {trigger_label!r}, ikke {TRIGGER_ETIKETT} -- "
            "branch-klargjøring er ikke en forutsetning for denne runden."
        )

    if not _er_sha(expected_head):
        return False, (
            f"Forventet head {expected_head!r} er ikke et fullt 40-tegns "
            "commit-SHA -- kan ikke verifisere branch-klargjøringen (fail-closed)."
        )

    if not _er_sha(local_head):
        return False, (
            f"Lokal HEAD {local_head!r} er ikke et fullt 40-tegns commit-SHA -- "
            "checkout av arbeidsbranchen kan ikke bevises (fail-closed)."
        )

    if local_head != expected_head:
        return False, (
            f"Lokal HEAD er {local_head!r}, men den verifiserte pre-run PR-headen "
            f"er {expected_head!r} -- arbeidstreet står ikke på det eksakte hodet "
            "Chiefs review gjelder (fail-closed)."
        )

    if branch_navn and local_branch != branch_navn:
        return False, (
            f"Lokal branch er {local_branch!r}, ikke den deterministiske "
            f"arbeidsbranchen {branch_navn!r} -- en push fra denne tilstanden "
            "ville uansett blitt avvist av den branch-scopede push-policyen "
            "(fail-closed)."
        )

    return True, (
        f"Arbeidsbranch {branch_navn!r} er klargjort på eksakt verifisert head "
        f"{expected_head} FØR Claude starter."
    )


def skriv_review_fil(kontekst, sti):
    """Skriver den verifiserte review-teksten til `sti` og returnerer stien.

    Hele poenget med å gjøre dette I PYTHON: review-body er menneskeskrevet
    fritekst som kan inneholde backticks, anførselstegn, `$(...)`,
    YAML-aktige linjer og vilkårlige linjeskift. Her blir den skrevet som
    rene bytes til en fil -- den passerer aldri gjennom shell-quoting,
    `$GITHUB_OUTPUT` eller en `${{ }}`-interpolasjon, og kan derfor hverken
    ødelegge workflow-syntaks eller bli evaluert som shell. Prompten peker
    kun på FILSTIEN; innholdet leser Claude selv med Read-verktøyet.

    Overskriften er bevisst kun verifiserte, strukturelle felter (issue-,
    PR-nummer, branch, 40-tegns SHA, review-id/forfatter/tidsstempel) --
    ingen tolkning av selve reviewen.
    """
    mappe = os.path.dirname(sti)
    if mappe:
        os.makedirs(mappe, exist_ok=True)
    linjer = [
        "# Chief review — verified work order (Agent Bridge, issue #329)",
        "",
        f"- Issue: #{kontekst['issue']}",
        f"- PR: #{kontekst['pr_number']}",
        f"- Branch: `{kontekst['branch']}`",
        f"- Base: `{kontekst['base']}`",
        f"- Exact head this review applies to: `{kontekst['head_sha']}`",
        f"- Review id: {kontekst['review_id']}",
        f"- Review author: {kontekst['review_author']}",
        f"- Submitted: {kontekst['review_submitted_at']}",
        "",
        "---",
        "",
        kontekst["review_body"] or "",
        "",
    ]
    with open(sti, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(linjer))
    return sti


def _les_stdin_json():
    raa = sys.stdin.read()
    try:
        data = json.loads(raa) if raa.strip() else {}
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def _kjor_verify():
    data = _les_stdin_json()

    verifisert, kontekst, begrunnelse = bygg_kontekst(
        trigger_label=data.get("trigger_label") or "",
        issue_nummer=data.get("issue"),
        branch_navn=data.get("branch"),
        before_pr_number=data.get("before_pr_number") or None,
        before_head_sha=data.get("before_head_sha") or None,
        prs=data.get("prs"),
        reviews=data.get("reviews"),
        repo_owner=data.get("repo_owner"),
    )

    print(begrunnelse, file=sys.stderr)
    print(f"context_verified={'true' if verifisert else 'false'}")

    if verifisert and kontekst is not None:
        sti = os.environ.get("CONTEXT_BODY_PATH") or DEFAULT_BODY_PATH
        skriv_review_fil(kontekst, sti)
        print(f"pr_number={kontekst['pr_number']}")
        print(f"head_sha={kontekst['head_sha']}")
        print(f"branch={kontekst['branch']}")
        print(f"review_id={kontekst['review_id']}")
        print(f"review_author={kontekst['review_author']}")
        print(f"review_submitted_at={kontekst['review_submitted_at']}")
        print(f"review_body_path={sti}")

    # `reason` er bevisst ÉN linje og inneholder aldri review-body -- se
    # moduldocstringen "TRANSPORT AV REVIEW-TEKST".
    print(f"reason={begrunnelse}")
    return 0 if verifisert else 1


def _kjor_checkout_verify():
    ok, begrunnelse = verifiser_lokalt_hode(
        trigger_label=os.environ.get("TRIGGER_LABEL", ""),
        expected_head=os.environ.get("EXPECTED_HEAD", ""),
        local_head=os.environ.get("LOCAL_HEAD", ""),
        branch_navn=os.environ.get("BRANCH") or None,
        local_branch=os.environ.get("LOCAL_BRANCH") or None,
    )
    print(begrunnelse, file=sys.stderr)
    print(f"checkout_verified={'true' if ok else 'false'}")
    print(f"reason={begrunnelse}")
    return 0 if ok else 1


def main():
    modus = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if modus == "checkout-verify":
        return _kjor_checkout_verify()
    if modus == "verify":
        return _kjor_verify()
    print(
        f"ukjent modus {modus!r} -- bruk 'verify' eller 'checkout-verify'.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
