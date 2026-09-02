#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge V1.1 -- trigger-autorisasjon (issue #9).

BAKGRUNN (den faktiske bugen, funnet i første ekte bridge-test):
V1 sjekket KUN issuens LIVE etiketter når guard-jobben faktisk kjørte.
På issue #8 la eieren på `status:ready` FØR `agent:claude`, og fordi
runneren brukte noen sekunder på å starte, rakk `agent:claude` å bli
lagt til før guard leste live-tilstanden. Guard så da
`agent:claude + status:ready` og godkjente kjøringen -- selv om
`agent:claude` IKKE fantes i det øyeblikket `status:ready`-eventet ble
utløst. Kjøringen stoppet trygt på manglende credentials, men
autorisasjonen i seg selv var feil.

RETTELSEN: autorisasjon må være ATOMISK i forhold til selve
trigger-eventet. Et `status:ready`/`status:changes-requested`-event får
kun fortsette hvis `agent:claude` ALLEREDE var med i etikettene som lå
i DET eventet (`github.event.issue.labels`) -- OG fortsatt ligger der
live når guard kjører. Å legge til `agent:claude` ETTERPÅ skal ALDRI
kunne autorisere et gammelt status-event med tilbakevirkende kraft.

Live-sjekken beholdes uendret ved siden av: den fanger fortsatt
foreldede/allerede-håndterte events (f.eks. en samtidig kjøring som
alt har flyttet tilstanden videre).

Ingen sleeps, ingen polling, ingen timing-antagelser, ingen PAT --
kun de to uavhengige øyeblikksbildene (event-tid og live-tid).

Ren, avhengighetsfri stdlib-Python, kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_trigger_guard.py -- selve beslutningen er
dermed testbar uten å kjøre noe mot GitHub.
"""
import json
import os
import sys

AGENT_ETIKETT = "agent:claude"
TRIGGER_ETIKETTER = ("status:ready", "status:changes-requested")


def vurder_trigger(
    *,
    event_name,
    event_action=None,
    event_label=None,
    event_labels=None,
    live_labels=None,
    sender_login=None,
    sender_type=None,
    repo_owner=None,
):
    """
    Returnerer (proceed: bool, trigger_label: str|None, begrunnelse: str).

    `event_labels` er etikettene slik de lå I SELVE trigger-eventet
    (github.event.issue.labels) -- IKKE live-tilstanden. `live_labels`
    er etikettene slik de er akkurat nå (gh issue view).

    workflow_dispatch beholder V1-semantikken uendret: manuell kjøring
    er allerede portvoktet av GitHub selv (krever write-tilgang), så
    verken event-snapshot- eller actor-sjekken gjelder der -- kun
    live-tilstanden må være gyldig.
    """
    live = list(live_labels or [])

    if event_name == "workflow_dispatch":
        if AGENT_ETIKETT not in live:
            return False, None, f"workflow_dispatch: {AGENT_ETIKETT} mangler i live-etikettene."
        for etikett in TRIGGER_ETIKETTER:
            if etikett in live:
                return True, etikett, f"workflow_dispatch: autorisert på live-tilstand ({etikett})."
        return False, None, "workflow_dispatch: ingen av trigger-etikettene finnes live."

    # ── issues:labeled ──────────────────────────────────────────────
    if event_action != "labeled":
        return False, None, f"Event-action {event_action!r} er ikke 'labeled'."

    if event_label not in TRIGGER_ETIKETTER:
        return False, None, f"Etiketten {event_label!r} er ikke en trigger-etikett."

    # KJERNEN I V1.1: autorisasjonen må gjelde på EVENT-TIDSPUNKTET.
    hendelses_etiketter = list(event_labels or [])
    if AGENT_ETIKETT not in hendelses_etiketter:
        return (
            False,
            None,
            f"{AGENT_ETIKETT} fantes IKKE i etikettene på event-tidspunktet "
            f"({hendelses_etiketter}) -- dette {event_label}-eventet er permanent "
            "uautorisert, uansett hvordan live-tilstanden ser ut nå. Riktig "
            "rekkefølge er: legg på agent:claude FØRST, deretter trigger-statusen.",
        )

    if sender_login != repo_owner:
        return (
            False, None,
            f"Etiketten ble satt av {sender_login!r}, ikke repo-eier {repo_owner!r} "
            "(anti-loop/tillits-sperre).",
        )

    if sender_type == "Bot":
        return False, None, "Etiketten ble satt av en Bot-aktør (anti-loop/tillits-sperre)."

    # Live-sjekken (uendret fra V1): fanger foreldede/superseded events.
    if AGENT_ETIKETT not in live:
        return False, None, f"{AGENT_ETIKETT} er fjernet fra live-tilstanden -- avvist."

    if event_label not in live:
        return (
            False, None,
            f"{event_label} finnes ikke lenger live (allerede håndtert av en "
            "annen/tidligere kjøring) -- avvist.",
        )

    return True, event_label, f"Autorisert: {event_label} både på event-tidspunktet og live."


def _les_json_liste(raa):
    if not raa:
        return []
    try:
        verdi = json.loads(raa)
    except (TypeError, ValueError):
        return []
    return verdi if isinstance(verdi, list) else []


def main():
    """Leser event-/live-kontekst fra miljøvariabler, skriver
    GITHUB_OUTPUT-linjer til stdout og en menneskelesbar begrunnelse til
    stderr (slik at workflowen kan gjøre `... >> "$GITHUB_OUTPUT"` og
    likevel få begrunnelsen i loggen)."""
    proceed, trigger_label, begrunnelse = vurder_trigger(
        event_name=os.environ.get("EVENT_NAME", ""),
        event_action=os.environ.get("EVENT_ACTION"),
        event_label=os.environ.get("LABEL_NAME"),
        event_labels=_les_json_liste(os.environ.get("EVENT_LABELS")),
        live_labels=_les_json_liste(os.environ.get("LIVE_LABELS")),
        sender_login=os.environ.get("SENDER_LOGIN"),
        sender_type=os.environ.get("SENDER_TYPE"),
        repo_owner=os.environ.get("REPO_OWNER"),
    )
    print(begrunnelse, file=sys.stderr)
    print(f"proceed={'true' if proceed else 'false'}")
    if proceed:
        print(f"trigger_label={trigger_label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
