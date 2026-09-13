#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- HO router freshness-sjekk (issue #252).

BAKGRUNN: den kanoniske HO-modellen (AGENT_WORKFLOW.md, "HO policy --
local and GitHub jobs") er #152 (router) -> nyeste gyldige
`KBH_COS_CHECKPOINT_PTR_V1`-linje -> mål-kommentaren den peker til
(`KBH_COS_LIVE_CHECKPOINT_V1`) -> fersk live GitHub. I motsetning til
hver søster-mekanisme i denne mappen (trigger_guard.py,
deliverable_guard.py, chief_ready_signal.py, pr_draft_handoff.py,
pr_ready_handoff.py, go_notify_signal.py) var denne kjeden tidligere
KUN prosa -- ingen ren/testbar funksjon fantes som faktisk beviste at
pointeren pekte til det NYESTE gyldige sjekkpunktet, kun instruksjonen
"les tilbake og verifiser". Issue #252s dokumenterte hendelse er
nøyaktig det gapet: en nyere gyldig sjekkpunkt-kommentar (#196 kommentar
5648280519) eksisterte, mens #152s nyeste pointer fortsatt pekte til en
eldre (#196 kommentar 5648254902) -- routed HO var dermed stille
foreldet inntil noen (manuelt) oppdaget og reparerte det.

DENNE MODULEN gjør akkurat denne ene sjekken -- "peker den nyeste
gyldige pointeren i #152 til det nyeste gyldige sjekkpunktet på
mål-issuen?" -- til en ren, enhetstestet funksjon med et eksplisitt,
fail-closed resultat i stedet for stille avhengighet av at en
LLM-drevet "les tilbake"-prosa ble fulgt korrekt hver gang. Den
ERSTATTER ikke HO-policyen -- den er det konkrete verifiseringssteget
policyens punkt 5 ("Immediately before publication, refetch the route,
target and affected live facts... read it back... resolve the new
pointer to verify publication") nå kan kjøre som et faktisk program i
stedet for kun prosa, og som også kan kjøres frittstående når som helst
for å oppdage om ruteren allerede har blitt foreldet (orphan-deteksjon,
uavhengig av om noen nettopp publiserte noe).

Linje-ankrede, eksakte markør-regex -- samme konvensjon som
chief_ready_signal.py (`KBH_CHIEF_REVIEW_READY_V1`) og
pr_ready_handoff.py (`KBH_PR_READY_TRANSITION_DONE_V1`): et sitert
eksempel, en kommentar som nevner markøren midt i en linje, eller en
nesten-lik variant (feil case, ekstra tekst) teller aldri som en gyldig
pointer/sjekkpunkt-linje. Dette er selve grunnen til at policy-teksten
sier "Quoted examples and unmarked status comments are not replacement
pointers."

ANTAGELSE (dokumentert, ikke skjult): GitHub-kommentar-ID-er øker
monotont med opprettelsestidspunkt for et gitt repository. "Nyeste
gyldige pointer" og "nyeste gyldige sjekkpunkt" velges derfor ved
størst kommentar-ID, ikke ved å parse `created_at`-strenger.

Ren, avhengighetsfri stdlib-Python -- ingen `gh`/GitHub-kall i denne
modulen selv (samme uavhengighets-konvensjon som hver søster-modul i
.github/scripts/). Enhetstestet i
tests/test_agent_bridge_ho_router_check.py, inkludert issue #252s
eksakte historiske hendelse som en regresjonstest.

CLI-bruk, to faser (fordi mål-issuen som skal hentes ikke er kjent før
pointeren i #152 er lest):

  Fase 1 -- finn hvilken issue/kommentar #152 nyeste pointer peker til:
    gh api repos/OWNER/REPO/issues/152/comments --paginate \
      | jq '{comments: [.[] | {id, body}]}' \
      | python3 .github/scripts/ho_router_check.py pointer
    Skriver `pointer_found`, og hvis funnet `pointer_issue`/`pointer_comment`,
    til stdout; begrunnelse til stderr. Exit 0 hvis en gyldig pointer ble
    funnet, ellers exit 1 (fail-closed -- policyen: "A missing, inaccessible
    or ambiguous route means defer the write and report the problem").

  Fase 2 -- hent MÅL-issuens kommentarer (issue-nummeret fra fase 1) OG
  #152s kommentarer FERSKT igjen (aldri gjenbruk fase 1s cache -- policyen:
  "Immediately before publication, refetch the route"), og la denne
  modulen løse pointeren PÅ NYTT selv, mot det ferske målet:
    jq -n --argjson pc "$(gh api .../issues/152/comments --paginate | jq '[.[]|{id,body}]')" \
          --argjson tc "$(gh api .../issues/196/comments --paginate | jq '[.[]|{id,body}]')" \
          '{pointer_comments: $pc, target_issue: 196, target_comments: $tc}' \
      | python3 .github/scripts/ho_router_check.py verify
    Skriver `status` (OK/ORPHAN/NO_POINTER/INVALID_TARGET/
    POINTER_ISSUE_MISMATCH), og hvis en pointer ble løst
    `pointer_issue`/`pointer_comment`, til stdout; begrunnelse til stderr.
    Exit 0 KUN for `status=OK`; alle andre utfall exit 1 (fail-closed).

    `target_issue` er en eksplisitt, uavhengig deklarasjon av hvilken
    issue `target_comments` faktisk ble hentet fra -- ikke utledet fra
    pointeren selv -- slik at et kall-feil (feil issue hentet) fanges
    som `POINTER_ISSUE_MISMATCH` i stedet for å stille validere mot data
    fra feil issue.

Denne modulen MUTERER aldri noe (ingen `gh`-kall, ingen
kommentar/label-skriving) -- den er en ren beslutningsfunksjon, akkurat
som hver søster-modul i .github/scripts/. Selve publiseringen (skrive
sjekkpunktet, deretter pointeren) forblir det eksisterende, uendrede
`gh issue comment`-mønsteret HO-policyen allerede beskriver; denne
modulen er bare det nye, faktisk kjørbare verifiseringssteget etter det.
"""
import json
import re
import sys

POINTER_VERSJON = "KBH_COS_CHECKPOINT_PTR_V1"
SJEKKPUNKT_VERSJON = "KBH_COS_LIVE_CHECKPOINT_V1"

POINTER_LINJE_RE = re.compile(
    r"(?m)^" + re.escape(POINTER_VERSJON) + r" issue=(?P<issue>[1-9]\d*) comment=(?P<comment>[1-9]\d*)$"
)
SJEKKPUNKT_LINJE_RE = re.compile(
    r"(?m)^" + re.escape(SJEKKPUNKT_VERSJON) + r"\b"
)


def nyeste_gyldig_pointer(kommentarer):
    """Returnerer {"issue": int, "comment": int, "kilde_id": int} for den
    nyeste (størst kommentar-ID) gyldige, linje-ankrede
    `KBH_COS_CHECKPOINT_PTR_V1 issue=<N> comment=<M>`-linja funnet i
    `kommentarer` (liste av {"id": int, "body": str}), eller None hvis
    ingen gyldig linje finnes. Et sitat, en midt-i-linja-forekomst eller
    en nesten-lik variant matcher bevisst ikke regexen (se moduldocstring)."""
    beste = None
    for kommentar in kommentarer or []:
        kid = kommentar.get("id")
        body = kommentar.get("body") or ""
        if kid is None:
            continue
        for m in POINTER_LINJE_RE.finditer(body):
            kandidat = {
                "issue": int(m.group("issue")),
                "comment": int(m.group("comment")),
                "kilde_id": int(kid),
            }
            if beste is None or kandidat["kilde_id"] >= beste["kilde_id"]:
                beste = kandidat
    return beste


def gyldige_sjekkpunkt_id_er(kommentarer):
    """Returnerer sortert liste av kommentar-ID-er (int) blant
    `kommentarer` hvis body har en gyldig, linje-ankret
    `KBH_COS_LIVE_CHECKPOINT_V1`-markør. Samme sitat-/midt-i-linja-
    unntak som `nyeste_gyldig_pointer`."""
    treff = []
    for kommentar in kommentarer or []:
        kid = kommentar.get("id")
        body = kommentar.get("body") or ""
        if kid is None:
            continue
        if SJEKKPUNKT_LINJE_RE.search(body):
            treff.append(int(kid))
    return sorted(treff)


def sjekk_router(*, pointer_kommentarer, target_issue_nummer, target_kommentarer):
    """
    Returnerer (status: str, pointer: dict|None, begrunnelse: str).

    status er en av:
      "NO_POINTER"            -- ingen gyldig pointer-linje i #152s kommentarer.
      "POINTER_ISSUE_MISMATCH" -- pointeren peker til en annen issue enn
                                   `target_issue_nummer` (feil mål-kommentarer hentet).
      "INVALID_TARGET"        -- pointerens mål-kommentar finnes ikke som
                                   en gyldig sjekkpunkt-kommentar på mål-issuen.
      "ORPHAN"                -- et nyere gyldig sjekkpunkt finnes på
                                   mål-issuen enn det pointeren peker til
                                   -- nøyaktig issue #252s dokumenterte
                                   regresjon.
      "OK"                    -- pointeren peker til det nyeste gyldige
                                   sjekkpunktet -- ruteren er fersk.

    Løser pointeren PÅ NYTT fra `pointer_kommentarer` her (aldri en
    forhåndsløst verdi fra en tidligere fase) -- se moduldocstring
    "Immediately before publication, refetch the route".
    """
    pointer = nyeste_gyldig_pointer(pointer_kommentarer)
    if pointer is None:
        return "NO_POINTER", None, (
            "Ingen gyldig KBH_COS_CHECKPOINT_PTR_V1-linje funnet i de oppgitte "
            "#152-kommentarene -- kan ikke rute (fail-closed)."
        )

    if pointer["issue"] != int(target_issue_nummer):
        return "POINTER_ISSUE_MISMATCH", pointer, (
            f"Nyeste pointer peker til issue #{pointer['issue']}, men "
            f"target_comments ble oppgitt som hentet fra issue "
            f"#{target_issue_nummer} -- feil mål-issue hentet, kan ikke "
            "verifisere (fail-closed)."
        )

    gyldige = gyldige_sjekkpunkt_id_er(target_kommentarer)
    if not gyldige:
        return "INVALID_TARGET", pointer, (
            f"Fant ingen gyldig KBH_COS_LIVE_CHECKPOINT_V1-kommentar i issue "
            f"#{target_issue_nummer} -- kan ikke verifisere pointer-målet "
            "(fail-closed)."
        )

    if pointer["comment"] not in gyldige:
        return "INVALID_TARGET", pointer, (
            f"Pointerens mål (kommentar {pointer['comment']}) er ikke en "
            f"gyldig sjekkpunkt-kommentar i issue #{target_issue_nummer} -- "
            "kan ikke verifisere (fail-closed)."
        )

    nyeste = max(gyldige)
    if pointer["comment"] != nyeste:
        return "ORPHAN", pointer, (
            f"Et nyere gyldig sjekkpunkt (kommentar {nyeste}) finnes i issue "
            f"#{target_issue_nummer}, men #152s nyeste pointer peker fortsatt "
            f"til kommentar {pointer['comment']} -- ruteren er foreldet "
            "(fail-closed). Dette er den samme regresjonsklassen som issue #252 "
            "dokumenterte."
        )

    return "OK", pointer, (
        f"Pointeren peker til kommentar {pointer['comment']}, som er det "
        f"nyeste gyldige sjekkpunktet i issue #{target_issue_nummer} -- "
        "ruteren er fersk."
    )


def _les_json_stdin():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return data


def _kjor_pointer():
    data = _les_json_stdin()
    pointer = nyeste_gyldig_pointer(data.get("comments"))

    if pointer is None:
        begrunnelse = (
            "Ingen gyldig KBH_COS_CHECKPOINT_PTR_V1-linje funnet i de oppgitte "
            "kommentarene -- kan ikke rute (fail-closed)."
        )
        print(begrunnelse, file=sys.stderr)
        print("pointer_found=false")
        print(f"reason={begrunnelse}")
        return 1

    begrunnelse = (
        f"Nyeste gyldige pointer (kilde-kommentar {pointer['kilde_id']}) peker "
        f"til issue #{pointer['issue']} kommentar {pointer['comment']}."
    )
    print(begrunnelse, file=sys.stderr)
    print("pointer_found=true")
    print(f"pointer_issue={pointer['issue']}")
    print(f"pointer_comment={pointer['comment']}")
    print(f"reason={begrunnelse}")
    return 0


def _kjor_verify():
    data = _les_json_stdin()
    target_issue = data.get("target_issue")
    if target_issue is None:
        begrunnelse = "Mangler target_issue i input -- kan ikke verifisere (fail-closed)."
        print(begrunnelse, file=sys.stderr)
        print("status=INVALID_TARGET")
        print(f"reason={begrunnelse}")
        return 1

    status, pointer, begrunnelse = sjekk_router(
        pointer_kommentarer=data.get("pointer_comments"),
        target_issue_nummer=target_issue,
        target_kommentarer=data.get("target_comments"),
    )

    print(begrunnelse, file=sys.stderr)
    print(f"status={status}")
    if pointer is not None:
        print(f"pointer_issue={pointer['issue']}")
        print(f"pointer_comment={pointer['comment']}")
    print(f"reason={begrunnelse}")
    return 0 if status == "OK" else 1


def main(argv):
    modus = argv[1] if len(argv) > 1 else "pointer"
    if modus == "verify":
        return _kjor_verify()
    if modus == "pointer":
        return _kjor_pointer()
    print(f"ukjent modus: {modus!r} (forventet 'pointer' eller 'verify')", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
