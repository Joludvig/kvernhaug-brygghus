#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- branch-uavhengig runtime-ignorering for
`.agent_bridge_run/` (issue #333).

BAKGRUNN: `status:changes-requested`-handoffen (#329/#330/#331) skriver
verifisert Chief-arbeidskontekst til `.agent_bridge_run/chief_review.md`,
og issue #333 legger til en tilsvarende staget kopi av gjeldende
`docs/development/AGENT_WORKFLOW.md` i samme katalog
(`.agent_bridge_run/AGENT_WORKFLOW.md`, se "Stage current authoritative
Agent Workflow contract" i claude-agent-bridge.yml) -- begge FØR wrapperen
bytter arbeidstreet til en gammel feature-branch sitt eksakte reviewede
hode ("Prepare existing agent branch for changes-requested round").

Den nåværende, klarerte checkouten (current master) ignorerer
`.agent_bridge_run/` via det SPOREDE `.gitignore`-et. Men en gammel
feature-branch (som PR #328s pre-#329-hode) kan predate den regelen og
ikke inneholde den i det hele tatt -- dermed er runtime-handoffen ikke
lenger beskyttet av branchens EGEN `.gitignore` etter at wrapperen bytter
til den, og en bred `git add -A` kunne i prinsippet fange den opp ved et
uhell.

DENNE MODULEN legger ignoreringen i LOKAL Git-metadata
(`.git/info/exclude`) i stedet for i noe sporet, branch-avhengig
`.gitignore` -- `.git/info/exclude` er en usporet fil per klone som
`git checkout`/`git switch` ALDRI rører, uansett hvilken branch som
sjekkes ut etterpå. Idempotent: den ankrede linjen legges kun til hvis den
ikke allerede finnes der; sporet `.gitignore` endres ALDRI av denne
modulen.

Beslutningslogikken for selve linje-beregningen
(`beregn_ny_exclude_innhold`) er ren, avhengighetsfri stdlib-Python --
ingen filsystem-/git-kall -- så den er fritt testbar uten et ekte repo.
Selve BEVISET at beskyttelsen faktisk virker er ETT `git check-ignore`-kall
mot en probe-sti under `.agent_bridge_run/`: fail-closed exit 1 hvis
ignoreringen ikke kan bevises, ALDRI en antakelse. Samme exit-kode-kontrakt
som changes_requested_context.py/pr_draft_handoff.py/chief_ready_signal.py:
exit 0 = bevist, exit 1 = reell fail-closed avvisning.

CLI-bruk (det workflowen gjør, FØR noen `.agent_bridge_run/`-fil skrives og
FØR noe branch-bytte):

    python3 .github/scripts/runtime_ignore.py install >> "$GITHUB_OUTPUT"

Skriver `runtime_ignore_verified=true/false` og `reason=...` til stdout,
begrunnelsen til stderr. Exit 0 kun når ignoreringen er bevist; exit 1
ellers -- som med hvert annet fail-closed steg på denne banen stopper
dette workflow-jobben før "Run Claude Code" (standard GitHub
Actions-oppførsel: et feilende steg stopper resten av jobben).

Ren, avhengighetsfri stdlib-Python, kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_runtime_ignore.py -- inkludert en ekte
temporær-git-regresjon (en fixture-branch UTEN `.gitignore`-regelen,
`.git/info/exclude` alene, runtime-filer opprettet, branch byttet,
`git add -A` kjørt, filene bevist å forbli usporet).
"""
import os
import subprocess
import sys

ANKER_LINJE = "/.agent_bridge_run/"
EXCLUDE_STI = os.path.join(".git", "info", "exclude")
PROBE_STI = os.path.join(".agent_bridge_run", ".runtime_ignore_probe")


def beregn_ny_exclude_innhold(eksisterende, linje=ANKER_LINJE):
    """Idempotent: returnerer `eksisterende` UENDRET hvis `linje` allerede
    finnes som en eksakt linje, ellers legger den til `linje` på slutten
    (med en ledende linjeskift-normalisering hvis innholdet ikke allerede
    slutter med ett). Ren streng-logikk -- ingen filsystem-/git-kall."""
    linjer = eksisterende.splitlines() if eksisterende else []
    if linje in linjer:
        return eksisterende
    if eksisterende and not eksisterende.endswith("\n"):
        eksisterende += "\n"
    return eksisterende + linje + "\n"


def _les_eksisterende(sti):
    if os.path.exists(sti):
        with open(sti, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _skriv(sti, innhold):
    mappe = os.path.dirname(sti)
    if mappe:
        os.makedirs(mappe, exist_ok=True)
    with open(sti, "w", encoding="utf-8") as f:
        f.write(innhold)


def _bevis_ignorert(probe_sti):
    """Kjører `git check-ignore -q` mot `probe_sti` og returnerer
    (bevist: bool, begrunnelse: str). Oppretter probe-filen hvis den ikke
    finnes -- `check-ignore` krever ikke at filen faktisk eksisterer, men
    vi lager den likevel slik at beviset gjelder nøyaktig den samme stien
    resten av handoffen faktisk bruker, ikke bare et mønster på papiret."""
    mappe = os.path.dirname(probe_sti)
    if mappe:
        os.makedirs(mappe, exist_ok=True)
    if not os.path.exists(probe_sti):
        with open(probe_sti, "w", encoding="utf-8") as f:
            f.write("")
    try:
        resultat = subprocess.run(
            ["git", "check-ignore", "-q", probe_sti],
            capture_output=True,
        )
    except OSError as e:
        return False, (
            f"Kunne ikke kjøre 'git check-ignore' ({e}) -- kan ikke bevise "
            "runtime-ignorering uavhengig av branchens egen .gitignore "
            "(fail-closed)."
        )
    if resultat.returncode == 0:
        return True, (
            f"'git check-ignore' bekrefter at {probe_sti!r} er ignorert "
            "(via .git/info/exclude, uavhengig av sporet .gitignore)."
        )
    return False, (
        f"'git check-ignore' rapporterer at {probe_sti!r} IKKE er ignorert "
        f"(exit {resultat.returncode}) -- runtime-handoffen er ikke bevist "
        "beskyttet uavhengig av branchens egen .gitignore (fail-closed)."
    )


def _kjor_install():
    eksisterende = _les_eksisterende(EXCLUDE_STI)
    ny = beregn_ny_exclude_innhold(eksisterende)
    if ny != eksisterende:
        _skriv(EXCLUDE_STI, ny)

    bevist, begrunnelse = _bevis_ignorert(PROBE_STI)
    try:
        if bevist:
            os.remove(PROBE_STI)
    except OSError:
        pass

    print(begrunnelse, file=sys.stderr)
    print(f"runtime_ignore_verified={'true' if bevist else 'false'}")
    print(f"reason={begrunnelse}")
    return 0 if bevist else 1


def main():
    modus = sys.argv[1] if len(sys.argv) > 1 else "install"
    if modus == "install":
        return _kjor_install()
    print(f"ukjent modus {modus!r} -- bruk 'install'.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
