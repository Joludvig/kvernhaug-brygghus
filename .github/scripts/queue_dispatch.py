#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- PÅ JOBB sekvensiell kø (issue #260).

BAKGRUNN: eieren vil kunne forhåndsgodkjenne flere avgrensede issues for
ubevoktet Claude-arbeid mens de er borte/sover ("PÅ JOBB"), uten å
risikere at flere Bridge-kjøringer starter samtidig (parallelle
scope-kollisjoner), eller at automasjonen får lov til å merge/deploye
på egen hånd. Køen legger derfor til NØYAKTIG ETT nytt lag foran den
eksisterende, allerede portvoktede Bridge-mekanikken (trigger_guard.py
/ lifecycle_labels.py / deliverable_guard.py) -- den endrer ingenting i
den mekanikken selv, og introduserer ingen ny merge/deploy-vei.

MODELL: to nye, additive etiketter (ikke en del av den eksklusive
`status:*`-livssyklusen fra lifecycle_labels.py):
  - `queue:pa-jobb`  -- markerer en issue som et køelement. Krever
                        ALLTID `agent:claude` i tillegg (samme
                        autorisasjonsgrense som resten av broen) -- en
                        issue med `queue:pa-jobb` men UTEN
                        `agent:claude` telles ikke som et køelement.
  - `queue:priority` -- valgfritt: flytter et køelement FØRST i køen
                        (blant andre `queue:priority`-elementer,
                        fortsatt i stigende issue-nummer-rekkefølge).
                        Dette er ownerens verktøy for å OMPRIORITERE
                        rekkefølgen uten å måtte endre issue-numre.

Et køelements TILSTAND leses av dets EKSISTERENDE `status:*`-etikett
(lifecycle_labels.py sitt eksklusive sett -- aldri en egen kø-tilstand):
  - ingen status:*-etikett -> "ikke_startet" (venter i køen)
  - ENHVER status:*-etikett (ready/working/changes-requested/review/
    approved) -> "aktiv"

status:ready telles bevisst som "aktiv", ikke "ikke_startet": det er
akkurat det dispatcheren selv setter idet den bevæpner et element (se
pa-jobb-queue.yml), rett før den kaller
`gh workflow run claude-agent-bridge.yml`. Om selve dispatch-kallet
skulle feile ETTER at etiketten er satt, skal et duplikat-event ALDRI
bevæpne et nytt element eller dispatche på nytt for samme element --
fail-closed, ikke fail-open (issue #260, akseptansetest 7).

ENDRING (issue #405, "full conveyor"): status:review og status:approved
telte TIDLIGERE som "ferdig" -- de blokkerte ALDRI neste køelement, ut
fra tanken om at "Chief-review-løpet overtar herfra". I praksis betyr
det at neste implementasjonsjobb kunne starte FØR forrige PR faktisk var
owner-GO'et og merget -- to samtidige "main write lane"-forsøk, stikk i
strid med den nye én-skriver-om-gangen-samlebåndsmodellen (issue #405,
seksjon 5: "Det passer ikke den nye én-main-write-lane
samlebåndsmodellen"). ALLE fem status:*-etikettene teller derfor nå som
"aktiv" -- et element slutter først å blokkere køen når det er faktisk
LUKKET (issue closed, typisk via GitHubs egen "Closes #N"-merge-
autolukking, se pa-jobb-queue.yml) og dermed forsvinner helt fra
`gh issue list --label queue:pa-jobb --state open`-snapshotten
`velg_neste()` under mottar -- se `_ko`-filtreringen der. Det finnes
derfor ikke lenger noe eget "ferdig"-bøtte: et køelement er enten
"ikke_startet" (ingen status:*-etikett, fortsatt åpent) eller "aktiv"
(en status:*-etikett, fortsatt åpent) -- eller det er rett og slett ikke
lenger med i snapshotten (lukket).

VALG: et NYTT element velges KUN når INGEN køelement er "aktiv". Om ett
er "aktiv" stopper hele køen der, uansett hvor mange andre
"ikke_startet"-elementer som venter -- det er nettopp "maks én aktiv
Bridge-kjøring om gangen"-kravet (issue #260, akseptansetest 3/4; issue
#405, "main WIP = 1 gjennom review/approved/merge"). Når det IKKE finnes
noe "aktivt" element blant de ÅPNE køelementene, kan et nytt starte --
det dekker både "forrige lukket/fullført" (issue #405, minstekrav 6) og
en helt tom/fersk kø (akseptansetest 2).

Ren, avhengighetsfri stdlib-Python (samme mønster som resten av
.github/scripts/ -- ingen skript krysser-importerer et annet) -- selve
utvelgelseslogikken er enhetstestet i
tests/test_agent_bridge_queue_dispatch.py uten å kjøre noe mot GitHub.
Selve BEVÆPNINGEN (å sette status:ready) gjenbruker det EKSISTERENDE
`lifecycle_labels.py` (`... | python3 lifecycle_labels.py status:ready |
gh api --method PUT ...`, identisk mønster som claude-agent-bridge.yml
allerede bruker for status:working/status:review) -- ingen ny
etikett-overgangslogikk er skrevet for dette; se pa-jobb-queue.yml.

REPO-VID BRO-AKTIVITET (Chief review, PR #263 -- BLOCKER): køens egen
"aktiv"-sjekk over leser bare status:*-etiketten til queue:pa-jobb-
issuene selv. Men claude-agent-bridge.yml bruker PER-ISSUE
`concurrency` (`claude-agent-bridge-<issue_number>`), IKKE ett globalt
lag -- så en helt vanlig, IKKE-kølagt Bridge-kjøring på issue A kan
kjøre samtidig med en kølagt kjøring dispatcheren nettopp startet på
issue B. Det bryter issue #260s eget krav om at høyst ÉN
implementasjonskjøring skal være aktiv om gangen, kølagt eller ikke.
Fikset ved at dispatcheren i tillegg henter REPO-VID GitHub
Actions-kjøretilstand for selve `claude-agent-bridge.yml`-workflowen
(`gh api repos/<repo>/actions/workflows/claude-agent-bridge.yml/runs`,
se pa-jobb-queue.yml) og sender den inn som JSON i miljøvariabelen
`AKTIVE_BRO_KJORINGER`. `har_aktiv_bro_kjoring()` under avgjør om NOEN
av disse kjøringene fortsatt er i en ikke-fullført GitHub
Actions-status -- uavhengig av om den tilhører et køelement -- og
`velg_neste()` pauser køen om så er tilfelle, FØR den i det hele tatt
ser på queue:pa-jobb-issuenes egne status:*-etiketter. Dette er additivt:
`AKTIVE_BRO_KJORINGER` er valgfri (tom/fraværende = ingen kjent
repo-vid aktivitet), så eksisterende kall uten den er uendret.

REPO-VID BRO-AKTIVITET, RUNDE 2 (Chief review, PR #263 -- BLOCKER):
runde 1 sin `har_aktiv_bro_kjoring()` sjekket status mot en HARDKODET
liste kjente ikke-fullførte statuser og telte ukjent/manglende status
IKKE som aktiv -- fail-OPEN på uventet evidens, stikk i strid med resten
av køens fail-closed-design. Workflowen forhåndsfiltrerer allerede
`AKTIVE_BRO_KJORINGER` til `status != "completed"`
(`pa-jobb-queue.yml`), så ETHVERT element som faktisk kommer inn her ER
allerede bevis på en ikke-fullført kjøring -- uansett hvilken konkret
statusstreng GitHub Actions måtte returnere, også en fremtidig/ukjent
en. Fikset ved å snu klassifiseringen: `"completed"` er nå den ENESTE
statusen som IKKE teller som aktiv; alt annet -- kjent ikke-fullført
status, en ukjent fremtidig status, eller et helt manglende/tomt
status-felt -- teller som aktiv og pauser køen. En falsk pause
(malformert evidens blokkerer køen unødig) er trygt og reverserbart;
en falsk fravær-av-aktivitet (to Bridge-kjøringer samtidig) er nettopp
scope-kollisjonen issue #260 skal forhindre -- se
`har_aktiv_bro_kjoring()` under.

CLI-bruk (det workflowen gjør):
    gh issue list --repo "$REPO" --label queue:pa-jobb --state open \
      --json number,labels,state \
      --jq '[.[] | {number:.number, state:.state, labels:[.labels[].name]}]' \
      | AKTIVE_BRO_KJORINGER="$(cat bridge_runs.json)" \
        python3 .github/scripts/queue_dispatch.py >> "$GITHUB_OUTPUT"
Skriver `dispatch=true`/`dispatch=false`, og `issue_number=<N>` når
`dispatch=true`, som GITHUB_OUTPUT-linjer på stdout, og en
menneskelesbar begrunnelse til stderr.
"""
import json
import os
import sys

AGENT_ETIKETT = "agent:claude"
KO_ETIKETT = "queue:pa-jobb"
PRIORITET_ETIKETT = "queue:priority"

# Samme sett som lifecycle_labels.py sin LIVSSYKLUS_ETIKETTER --
# duplisert bevisst (samme mønster som deliverable_guard.py sin
# GYLDIGE_TRIGGER_ETIKETTER): hvert skript i .github/scripts/ er
# selvstendig og avhengighetsfritt.
LIVSSYKLUS_ETIKETTER = (
    "status:ready",
    "status:working",
    "status:review",
    "status:changes-requested",
    "status:approved",
)
# Issue #405: ALLE fem livssyklus-etikettene teller nå som "aktiv" -- se
# moduldoc "ENDRING (issue #405, ...)". Duplisert (ikke aliasert til
# LIVSSYKLUS_ETIKETTER) for et eksplisitt, lesbart navn på akkurat denne
# betydningen på kall-stedet i elementets_tilstand().
AKTIVE_LIVSSYKLUS_ETIKETTER = LIVSSYKLUS_ETIKETTER

# GitHub Actions' egen, FULLFØRTE kjøre-"status"-verdi -- uansett hvilken
# "conclusion" kjøringen endte med (success/failure/cancelled/... er
# ALLE "completed"). Dette er den ENESTE statusen har_aktiv_bro_kjoring()
# under klassifiserer som "ikke aktiv" -- se moduldoc "REPO-VID
# BRO-AKTIVITET, RUNDE 2".
FULLFORT_KJORINGSSTATUS = "completed"

# Kjente ikke-fullførte GitHub Actions-statuser -- kun til dokumentasjon
# og testdekning (se TestHarAktivBroKjoring.test_hver_kjent_ikke_fullfort_status_gjenkjennes
# i tests/test_agent_bridge_queue_dispatch.py); har_aktiv_bro_kjoring()
# selv gater IKKE på denne listen (fail-closed mot UKJENTE statuser
# krever nettopp at den ikke gjør det).
AKTIVE_KJORINGSSTATUSER = ("in_progress", "queued", "requested", "waiting", "pending")


def er_ko_element(labels):
    """Et køelement krever BEGGE agent:claude og queue:pa-jobb -- samme
    autorisasjonsgrense som resten av broen (issue #260: "only
    pre-authorized bounded issues may enter queue")."""
    labels = set(labels or [])
    return AGENT_ETIKETT in labels and KO_ETIKETT in labels


def gjeldende_livssyklus(labels):
    """Returnerer den ene status:*-etiketten issuen bærer, eller None om
    ingen gjør det. lifecycle_labels.py garanterer at det aldri er mer
    enn én samtidig."""
    labels = list(labels or [])
    for etikett in LIVSSYKLUS_ETIKETTER:
        if etikett in labels:
            return etikett
    return None


def elementets_tilstand(labels):
    """"ikke_startet" | "aktiv" -- se moduldoc for begrunnelsen. Issue
    #405: det finnes ikke lenger noe eget "ferdig"-utfall her -- et
    element som faktisk er ferdig er LUKKET, og forsvinner dermed helt
    fra `velg_neste()`s input før denne funksjonen noensinne kalles på
    det (se `_ko`-filtreringen der)."""
    livssyklus = gjeldende_livssyklus(labels)
    if livssyklus is None:
        return "ikke_startet"
    assert livssyklus in AKTIVE_LIVSSYKLUS_ETIKETTER  # alle fem, se moduldoc
    return "aktiv"


def har_aktiv_bro_kjoring(kjoringer):
    """True hvis MINST ÉN Claude Agent Bridge-workflowkjøring repo-vidt
    fortsatt er i en ikke-fullført GitHub Actions-status -- uavhengig av
    om den kjøringen tilhører et queue:pa-jobb-element eller en helt
    vanlig, ikke-kølagt issue (Chief review, PR #263: claude-agent-
    bridge.yml bruker PER-ISSUE `concurrency`, ikke ett globalt lag, så
    en vanlig kjøring på én issue kan kjøre samtidig med en kølagt
    kjøring på en annen -- se moduldoc "REPO-VID BRO-AKTIVITET").

    `kjoringer`: liste av {"status": str, ...} -- rå (eller
    jq-forhåndsfiltrert) `gh api .../actions/workflows/
    claude-agent-bridge.yml/runs`-utdata. FAIL-CLOSED (Chief review
    runde 2, PR #263): `"completed"` er den ENESTE statusen som IKKE
    teller som aktiv. Enhver annen verdi -- en kjent ikke-fullført
    status, en ukjent/fremtidig status, ELLER et manglende/tomt
    `status`-felt -- teller som aktiv og pauser køen. Se moduldoc
    "REPO-VID BRO-AKTIVITET, RUNDE 2" for begrunnelsen.
    """
    for kjoring in kjoringer or []:
        status = str((kjoring or {}).get("status", "")).strip().lower()
        if status != FULLFORT_KJORINGSSTATUS:
            return True
    return False


def velg_neste(issues, aktive_bro_kjoringer=None):
    """
    `issues`: liste av {"number": int, "state": "OPEN"/"CLOSED",
    "labels": [str, ...]} -- rå `gh issue list --label queue:pa-jobb`-
    utdata, normalisert til strengnavn.
    `aktive_bro_kjoringer`: valgfri liste av {"status": str, ...} --
    repo-vid GitHub Actions-kjøretilstand for claude-agent-bridge.yml,
    se `har_aktiv_bro_kjoring` over. Utelates/tom = ingen kjent
    repo-vid aktivitet (bakoverkompatibelt med eksisterende kall).

    Returnerer (issue_number: int|None, begrunnelse: str).
    `issue_number` er None når køen ikke skal starte noe nytt element nå
    (tom kø, en repo-vid aktiv Bridge-kjøring, satt på pause av et
    aktivt køelement, eller ingen gyldig kandidat igjen) -- aldri et
    gjettet fallback-nummer.
    """
    ko = [
        i for i in (issues or [])
        if str(i.get("state", "OPEN")).upper() == "OPEN" and er_ko_element(i.get("labels", []))
    ]
    if not ko:
        return None, "Tom kø: ingen åpne issues har både agent:claude og queue:pa-jobb."

    if har_aktiv_bro_kjoring(aktive_bro_kjoringer):
        return (
            None,
            "Køen er satt på pause: minst én Claude Agent Bridge-kjøring er "
            "aktiv et sted i repoet akkurat nå (ikke nødvendigvis et "
            "køelement -- claude-agent-bridge.yml bruker per-issue "
            "concurrency) -- maks én aktiv implementasjonskjøring om "
            "gangen, kølagt eller ikke.",
        )

    aktive = [i for i in ko if elementets_tilstand(i.get("labels", [])) == "aktiv"]
    if aktive:
        blokkerer = sorted(aktive, key=lambda i: i["number"])[0]
        tilstand_etikett = gjeldende_livssyklus(blokkerer.get("labels", []))
        return (
            None,
            f"Køen er satt på pause: issue #{blokkerer['number']} er fortsatt aktiv "
            f"({tilstand_etikett}) -- maks én aktiv Bridge-kjøring om gangen.",
        )

    kandidater = [i for i in ko if elementets_tilstand(i.get("labels", [])) == "ikke_startet"]
    if not kandidater:
        return None, "Ingen nye kandidater: alle køelementer er allerede ferdige (status:review/status:approved)."

    def sorteringsnokkel(i):
        prioritert = 0 if PRIORITET_ETIKETT in (i.get("labels", []) or []) else 1
        return (prioritert, i["number"])

    vinner = sorted(kandidater, key=sorteringsnokkel)[0]
    return vinner["number"], f"Valgte issue #{vinner['number']} (neste i PÅ JOBB-køen)."


def main():
    try:
        raatekst = sys.stdin.read()
        issues = json.loads(raatekst) if raatekst.strip() else []
    except (TypeError, ValueError) as e:
        print(f"stdin er ikke gyldig JSON: {e}", file=sys.stderr)
        print("dispatch=false")
        return 2
    if not isinstance(issues, list):
        print("stdin må være et JSON-array med issue-objekter.", file=sys.stderr)
        print("dispatch=false")
        return 2

    try:
        bro_raatekst = os.environ.get("AKTIVE_BRO_KJORINGER", "")
        aktive_bro_kjoringer = json.loads(bro_raatekst) if bro_raatekst.strip() else []
    except (TypeError, ValueError) as e:
        print(f"AKTIVE_BRO_KJORINGER er ikke gyldig JSON: {e}", file=sys.stderr)
        print("dispatch=false")
        return 2
    if not isinstance(aktive_bro_kjoringer, list):
        print("AKTIVE_BRO_KJORINGER må være et JSON-array med kjøre-objekter.", file=sys.stderr)
        print("dispatch=false")
        return 2

    issue_number, begrunnelse = velg_neste(issues, aktive_bro_kjoringer)
    print(begrunnelse, file=sys.stderr)
    if issue_number is None:
        print("dispatch=false")
        return 0
    print("dispatch=true")
    print(f"issue_number={issue_number}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
