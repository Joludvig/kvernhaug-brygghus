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

HERDING (issue #301): en oppfølgende audit av denne modulen fant fire
konkrete, ikke-hypotetiske hull i selve markør-parsingen (aldri i
`sjekk_router`s status-logikk, som er uendret):
  1. En ellers gyldig, linje-ankret markør-linje ble avvist hvis
     kommentaren brukte CRLF-linjeskift, fordi `$`/`^` i MULTILINE-modus
     kun forholder seg til `\n` -- en gjenværende `\r` gjorde at linjen
     aldri matchet slutten av mønsteret. Fikset ved å normalisere
     CRLF/CR til LF (`_normalisert_linjeskift`) før noe regex kjører.
  2. En pointer- eller sjekkpunkt-lignende linje vist som EKSEMPEL inni
     en fenced Markdown-kodeblokk (``` ... ``` eller ~~~ ... ~~~) ble
     talt som en aktiv markør, siden regexene tidligere søkte hele
     kommentar-teksten uendret. Fikset ved å fjerne fenced kodeblokker
     (`_uten_fenced_kodeblokker`) før markør-søket.
  3. og 4. To (eller flere) uavhengige, gyldige, standalone markør-linjer
     i SAMME kommentar ble tidligere stille løst til én av dem (den siste
     `finditer`-treffet vant) i stedet for å bli avvist som tvetydig. Nå
     krever begge `nyeste_gyldig_pointer` og `gyldige_sjekkpunkt_id_er`
     NØYAKTIG ett treff per (rensket) kommentar-body for at den
     kommentaren skal telle som en gyldig markør-kilde i det hele tatt --
     en kommentar med 0 eller >1 treff bidrar ikke, samme fail-closed-
     prinsip for begge markør-typene.
Alle fire er dekket av fokuserte regresjonstester i
tests/test_agent_bridge_ho_router_check.py. `sjekk_router`s egen
status-kontrakt (OK/ORPHAN/NO_POINTER/INVALID_TARGET/
POINTER_ISSUE_MISMATCH) og #152-rutingsemantikken er uendret av denne
herdingen -- kun hvilke linjer som i utgangspunktet regnes som en gyldig
markør-linje, er strammet inn.

HERDING (issue #301, runde 2 -- Chief-blocker): punkt 2 over fjernet
fenced kodeblokker, men `_uten_fenced_kodeblokker` sin egen
closing-fence-gjenkjenning fulgte ikke CommonMarks closing-fence-semantikk
-- enhver senere linje som startet med SAMME fence-tegn (uansett lengde
eller etterfølgende tekst) lukket blokken. To konkrete, ikke-hypotetiske
konsekvenser: (a) en 4-backtick-opener ble stille lukket av en påfølgende
3-backtick-linje, og (b) en fence-lignende linje med tekst etter
fence-tegnene (f.eks. "``` fortsatt eksempel") lukket blokken selv om
CommonMark aldri tillater en info-streng på en closing fence. Begge lot en
pointer-/sjekkpunkt-lignende EKSEMPEL-markør som fulgte en slik ugyldig
pseudo-closer, men lå FØR den faktiske closeren, bli feilaktig behandlet
som aktiv -- samme klasse fail-closed-brudd som punkt 2 selv ble skrevet
for å lukke. Fikset ved å la `_uten_fenced_kodeblokker` spore både
åpnerens fence-tegn OG -lengde, og kreve at en kandidat-closer har samme
tegn, minst like stor lengde, OG kun whitespace etter fence-tegnene før
den regnes som gyldig -- ellers behandles kandidat-linja som fortsatt
innhold inni den åpne blokken (uendret linjetall-bevaring). `sjekk_router`
og de fire opprinnelige herdings-punktene over er uendret.

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

# Åpner/lukker en fenced Markdown-kodeblokk (``` eller ~~~, opptil 3
# mellomrom innrykk per CommonMark). Brukes til å fjerne EKSEMPEL-tekst før
# markør-regexene kjører -- se `_uten_fenced_kodeblokker`. `fence`-gruppen
# fanger HELE den sammenhengende tegn-strengen (samme tegn, 3+); `info`-
# gruppen fanger resten av linja -- en gyldig CLOSING-fence krever i tillegg
# (utover samme tegn) at `info` kun er whitespace og at `fence` er minst like
# lang som åpnerens (issue #301 herding, runde 2: en 4-backtick-opener
# lukkes IKKE av en 3-backtick-linje, og en fence-lignende linje med
# etterfølgende tekst er aldri en gyldig closer -- kun en OPENER tillater en
# info-streng etter fence-tegnene, per CommonMark).
_FENCE_LINJE_RE = re.compile(r"^\s{0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")


def _normalisert_linjeskift(tekst):
    """Normaliserer CRLF/CR til LF før noen markør-regex kjører, slik at en
    ellers gyldig, linje-ankret markør-linje ikke avvises bare fordi
    kommentaren bruker CRLF-linjeskift (`$`/`^` i MULTILINE-modus forholder
    seg kun til `\\n`, aldri en gjenværende `\\r`)."""
    return tekst.replace("\r\n", "\n").replace("\r", "\n")


def _uten_fenced_kodeblokker(tekst):
    """Fjerner innholdet i fenced Markdown-kodeblokker (``` ... ``` eller
    ~~~ ... ~~~) fra `tekst` før markør-regexene kjøres, slik at en
    pointer-/sjekkpunkt-lignende linje vist som EKSEMPEL inni en kodeblokk
    aldri telles som en aktiv, gyldig markør-linje. Linjetall bevares
    (fjernede linjer blir tomme, ikke slettet) -- ikke at det er strengt
    nødvendig her, men det gjør resultatet lettere å resonnere om.

    CLOSING-fence-semantikk (issue #301 herding, runde 2): en kandidat-linje
    lukker kun den åpne fencen dersom (1) samme fence-tegn som åpneren, (2)
    closer-lengden er >= åpner-lengden, og (3) kun whitespace følger
    fence-tegnene på closer-linja. En 4-backtick-opener lukkes derfor IKKE
    av en 3-backtick-linje, og en fence-lignende linje med etterfølgende
    tekst (f.eks. "``` fortsatt inni blokken") lukker aldri blokken -- den
    behandles i stedet som fortsatt innhold INNI den åpne fencen, akkurat
    som enhver annen linje der. En pointer-/sjekkpunkt-lignende markør som
    står etter en slik ugyldig pseudo-closer, men før den faktiske gyldige
    closeren, forblir dermed korrekt inni blokken og ignoreres."""
    ut_linjer = []
    apen_fence_tegn = None  # tegnet ('`' eller '~') for den åpne fencen, eller None
    apen_fence_lengde = 0  # lengden (antall tegn) på åpningsfencen
    for linje in tekst.split("\n"):
        m = _FENCE_LINJE_RE.match(linje)
        if apen_fence_tegn is None:
            if m:
                apen_fence_tegn = m.group("fence")[0]
                apen_fence_lengde = len(m.group("fence"))
                ut_linjer.append("")
            else:
                ut_linjer.append(linje)
        else:
            gyldig_closer = (
                m is not None
                and m.group("fence")[0] == apen_fence_tegn
                and len(m.group("fence")) >= apen_fence_lengde
                and m.group("info").strip() == ""
            )
            if gyldig_closer:
                apen_fence_tegn = None
                apen_fence_lengde = 0
            ut_linjer.append("")
    return "\n".join(ut_linjer)


def _rensket_body(body):
    """Felles forbehandling for begge markør-søkene: CRLF-normalisering
    (issue #301, revisjon 1) etterfulgt av fenced-kodeblokk-fjerning
    (issue #301, revisjon 2), i den rekkefølgen (fence-gjenkjenningen ser
    kun etter LF-linjeskift)."""
    return _uten_fenced_kodeblokker(_normalisert_linjeskift(body))


def nyeste_gyldig_pointer(kommentarer):
    """Returnerer {"issue": int, "comment": int, "kilde_id": int} for den
    nyeste (størst kommentar-ID) gyldige, linje-ankrede
    `KBH_COS_CHECKPOINT_PTR_V1 issue=<N> comment=<M>`-linja funnet i
    `kommentarer` (liste av {"id": int, "body": str}), eller None hvis
    ingen gyldig linje finnes. Et sitat, en midt-i-linja-forekomst, en
    nesten-lik variant eller en forekomst inni en fenced kodeblokk matcher
    bevisst ikke regexen (se moduldocstring). CRLF-linjeskift godtas på
    linje med LF (issue #301). Hvis EN OG SAMME kommentar inneholder MER
    ENN ÉN aktiv, standalone pointer-linje, er den kommentaren tvetydig --
    den avvises i sin helhet som pointer-kilde (fail-closed, issue #301)
    i stedet for at en av linjene stille velges."""
    beste = None
    for kommentar in kommentarer or []:
        kid = kommentar.get("id")
        body = kommentar.get("body") or ""
        if kid is None:
            continue
        treff = list(POINTER_LINJE_RE.finditer(_rensket_body(body)))
        if len(treff) != 1:
            continue
        m = treff[0]
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
    `kommentarer` hvis body har NØYAKTIG ÉN gyldig, linje-ankret
    `KBH_COS_LIVE_CHECKPOINT_V1`-markør. Samme sitat-/midt-i-linja-/
    fenced-kodeblokk-unntak og CRLF-toleranse som `nyeste_gyldig_pointer`
    (issue #301). En kommentar med MER ENN ÉN aktiv, standalone
    sjekkpunkt-markør er tvetydig og telles ikke som gyldig (samme
    fail-closed-prinsipp som for pointer-linjer, issue #301)."""
    treff = []
    for kommentar in kommentarer or []:
        kid = kommentar.get("id")
        body = kommentar.get("body") or ""
        if kid is None:
            continue
        funn = list(SJEKKPUNKT_LINJE_RE.finditer(_rensket_body(body)))
        if len(funn) != 1:
            continue
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
