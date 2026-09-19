#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge V1.2 -- fast, deterministisk branch-navngiving og
en faktisk håndhevet push-policy (Chief review på PR #13, blokker 1+2).

BLOKKER 1 (push-håndheving): `--allowedTools` inneholdt `Bash(git push *)`.
Den regelen tillater i praksis ALT `git push` kan gjøre, inkludert
`git push origin master` og refspec-varianter som
`git push origin <branch>:master` -- prompten sa riktignok "never push
master", men det er ren modelladferd-tillit, ikke håndheving, og issue
#12 krever eksplisitt fail-closed.

BLOKKER 2 (leveranse-assosiering): leveranse-porten fant kandidat-PR-er
via GitHubs issue-tidslinje (`cross-referenced`-events) -- en
tekst-heuristikk basert på at PR-body/tittel nevner "#N" på en måte
GitHub selv gjenkjenner. Men `status:ready`-prompten krevde aldri at
Claude faktisk skriver en slik referanse, så en fullstendig korrekt PR
kunne bli feilaktig avvist som "ingen leveranse".

RETTELSEN på begge, med ÉN mekanisme: hver bridge-kjøring for en issue
bruker ETT fast, forutsigbart branch-navn -- samme navn gjennom HELE
issuens levetid (status:ready oppretter det, enhver senere
status:changes-requested-runde gjenbruker det UENDRET, jf. "state lives
on the issue"-designet i AGENT_WORKFLOW.md). Det faste navnet brukes
til to uavhengige ting:

1. `--allowedTools` gir Claude EKSAKTE (wildcard-frie) push-regler for
   NØYAKTIG dette navnet (`tillatte_push_kommandoer` under). Enhver
   annen push-kommando -- master, en annen branch, en refspec-trick som
   `<branch>:master`, `--force`, ekstra argumenter -- er en annen
   tekststreng og matcher derfor INGEN regel: avvist per konstruksjon,
   ikke per modell-lydighet.
2. Leveranse-porten finner den assosierte PR-en med
   `gh pr list --head <navn> --base master --state open`
   (`gh_pr_list_args` under) -- eksakt streng-likhet i GitHubs egen
   PR-indeks, ikke en tekst-tolket kryssreferanse. En PR uten dette
   nøyaktige head-navnet kan per konstruksjon aldri dukke opp i
   resultatet, uansett hva PR-body inneholder.

Ren, avhengighetsfri stdlib-Python -- selve navnet bygges her ÉN gang og
brukes identisk av workflowen (claude-agent-bridge.yml kaller
`python3 .github/scripts/branch_policy.py <issue>` for å få navnet, og
gjenbruker det samme steget-outputet i --allowedTools, i prompten og i
begge `gh pr list`-kallene -- ingen duplisert formel) og av
tests/test_agent_bridge_branch_policy.py, slik at policyen er testbar
uten noe reelt GitHub- eller Claude Code-kall.
"""
import sys

MASTER = "master"


def agent_branch_navn(issue_nummer):
    """Det ENE, faste branch-navnet for en issues hele bridge-levetid.
    Ingen tidsstempel/run-id -- status:ready og enhver senere
    status:changes-requested-runde MÅ lande på nøyaktig samme streng."""
    return f"agent/issue-{int(issue_nummer)}"


def tillatte_push_kommandoer(branch_navn):
    """De to (og KUN de to) push-kommando-strengene som skal stå som
    EKSAKTE --allowedTools-regler for en gitt branch. Ingen av dem
    inneholder noe mål utenfor `branch_navn` selv -- og siden
    `branch_navn` per `agent_branch_navn` aldri kan bli MASTER (heltalls-
    issue-nummer kan ikke produsere strengen "master"), kan INGEN
    refspec/flagg-variant av en master-push noen gang være tekstlik
    identisk med en av disse to."""
    if branch_navn == MASTER:
        raise ValueError("branch_navn kan aldri være 'master' -- det ville brutt hele poenget med denne modulen.")
    return (
        f"git push -u origin {branch_navn}",
        f"git push origin {branch_navn}",
    )


def tillatte_switch_kommandoer(branch_navn):
    """V1.7 (issue #259): to eksakte `git switch`-strenger, samme
    avgrensning som `tillatte_push_kommandoer` -- Claude Code bruker ofte
    moderne `git switch -c <branch>` for branch-oppretting selv når en
    prompt foreslår `git checkout -b`. Issue #257 feilet to ganger i
    nøyaktig dette mønsteret: prosessen fullførte, men
    `permission_denials_count=1` og INGEN `agent/issue-257`-branch fantes
    etterpå -- fordi `--allowedTools` kun tillot `git checkout *`, aldri
    `git switch`. Samme wildcard-frie logikk som push-reglene: siden
    `branch_navn` aldri kan bli MASTER, kan ingen variant av disse to
    strengene noensinne bytte til/opprette en lokal branch ved navn
    "master". (Selve push-grensen håndheves fortsatt utelukkende av
    `tillatte_push_kommandoer` -- denne funksjonen gjør kun branch-
    oppsettet robust, ikke push-policyen.)"""
    if branch_navn == MASTER:
        raise ValueError("branch_navn kan aldri være 'master' -- det ville brutt hele poenget med denne modulen.")
    return (
        f"git switch -c {branch_navn} origin/master",
        f"git switch {branch_navn}",
    )


def tillatte_checkout_kommandoer(branch_navn):
    """V1.9 (issue #329): `git checkout` var den SISTE gjenværende
    git-wildcard-regelen i `--allowedTools` (`Bash(git checkout *)`), og den
    fantes utelukkende fordi Claude selv måtte finne og checkoute
    arbeidsbranchen. Fra og med #329 eier wrapperen den jobben på
    `status:changes-requested`-banen (den fetcher branchen, checkouter det
    verifiserte pre-run-hodet og beviser lokal HEAD før Claude i det hele
    tatt starter), så wildcarden er ikke lenger nødvendig for noen av de to
    banene: `status:ready` trenger kun branch-OPPRETTING, og en
    changes-requested-runde starter allerede PÅ riktig branch.

    Samme wildcard-frie logikk som `tillatte_push_kommandoer`/
    `tillatte_switch_kommandoer`, og med samme garanti: siden `branch_navn`
    per `agent_branch_navn` aldri kan bli MASTER, kan ingen variant av disse
    to strengene noensinne checkoute/opprette en lokal branch ved navn
    "master". Dette SNEVRER INN permission-flaten -- ingenting som var
    forbudt før blir tillatt her."""
    if branch_navn == MASTER:
        raise ValueError("branch_navn kan aldri være 'master' -- det ville brutt hele poenget med denne modulen.")
    return (
        f"git checkout -b {branch_navn} origin/master",
        f"git checkout {branch_navn}",
    )


def gh_pr_list_args(repo, branch_navn):
    """De eksakte argumentene workflowen sender til `gh pr list` for å
    finne PR-en assosiert med denne branchen -- selve
    leveranse-assosieringsmekanismen etter blokker 2. `--head` alene
    (uten `--base master`/`--state open`) ville f.eks. matchet en
    allerede merget eller feil-target PR fra samme branch-navn i en
    tidligere, urelatert sammenheng."""
    return [
        "pr", "list", "--repo", repo, "--head", branch_navn,
        "--base", MASTER, "--state", "open",
        "--json", "number,state,baseRefName,headRefOid,additions,deletions,changedFiles",
    ]


def main(argv):
    if len(argv) != 2:
        print("bruk: branch_policy.py <issue-nummer>", file=sys.stderr)
        return 2
    try:
        print(agent_branch_navn(argv[1]))
    except (TypeError, ValueError):
        print(f"{argv[1]!r} er ikke et gyldig issue-nummer.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
