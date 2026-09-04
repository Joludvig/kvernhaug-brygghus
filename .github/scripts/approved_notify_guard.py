#!/usr/bin/env python3
"""
Kvernhaug Agent Bridge -- trigger-autorisasjon for GO/NO-GO-varselet
(issue #66).

BAKGRUNN: se go_notify_signal.py sin moduldocstring for hele
resonnementet bak selve varselet. Denne modulen dekker KUN
autorisasjonshalvparten -- SKAL et `status:approved`-labeled-event i
det hele tatt lov til å kjøre "notify"-jobben -- og er en BEVISST
duplisert, forenklet søsken av trigger_guard.py (issue #9/V1.1), IKKE
en gjenbruk av den: trigger_guard.py sin `TRIGGER_ETIKETTER` styrer
også `execute`-jobben (som INVOKERER Claude); å legge `status:approved`
til DEN listen ville feilaktig fått Claude til å kjøre på et
godkjennings-event. Denne modulen portvokter i stedet en HELT EGEN,
Claude-fri "notify"-jobb -- se claude-agent-bridge.yml.

SAMME race-fiks som trigger_guard.py (issue #9): `agent:claude` må ha
vært til stede i etikettene PÅ SELVE event-tidspunktet
(github.event.issue.labels), ikke bare live når guarden kjører --
ellers kunne et `agent:claude` lagt til ETTER et `status:approved`-
event retroaktivt autorisere en runde som aldri var det da eventet
faktisk fyrte.

SAMME aktør-sperre: kun en `status:approved`-etikett satt av selve
repo-eieren (aldri en Bot, aldri denne workflowens egen aktør) kan
autorisere et varsel -- identisk anti-loop-begrunnelse som
trigger_guard.py: enhver etikett-endring WORKFLOWEN selv gjør skjer via
dens eget token/aktør, aldri eierens login, så den kan aldri
tilfredsstille denne betingelsen og re-trigge seg selv.

Ren, avhengighetsfri stdlib-Python, kalt fra
.github/workflows/claude-agent-bridge.yml og enhetstestet i
tests/test_agent_bridge_approved_notify_guard.py -- selve
beslutningen er dermed testbar uten å kjøre noe mot GitHub.
"""
import json
import os
import sys

AGENT_ETIKETT = "agent:claude"
NOTIFY_ETIKETT = "status:approved"


def vurder_notify_trigger(
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
    Returnerer (proceed: bool, begrunnelse: str).

    `event_labels` er etikettene slik de lå I SELVE trigger-eventet
    (github.event.issue.labels) -- IKKE live-tilstanden. `live_labels`
    er etikettene slik de er akkurat nå (gh issue view). Se
    trigger_guard.py for identisk resonnement -- denne modulen er en
    bevisst duplisert, énetikett-variant av samme logikk (se
    moduldocstring for hvorfor den ikke gjenbruker trigger_guard.py).
    """
    live = list(live_labels or [])

    if event_name != "issues":
        return False, f"Event {event_name!r} er ikke 'issues' -- GO/NO-GO-varsel trigges kun av issue-etiketter."

    if event_action != "labeled":
        return False, f"Event-action {event_action!r} er ikke 'labeled'."

    if event_label != NOTIFY_ETIKETT:
        return False, f"Etiketten {event_label!r} er ikke {NOTIFY_ETIKETT!r}."

    hendelses_etiketter = list(event_labels or [])
    if AGENT_ETIKETT not in hendelses_etiketter:
        return False, (
            f"{AGENT_ETIKETT} fantes IKKE i etikettene på event-tidspunktet "
            f"({hendelses_etiketter}) -- dette {event_label}-eventet er permanent "
            "uautorisert, uansett hvordan live-tilstanden ser ut nå."
        )

    if sender_login != repo_owner:
        return False, (
            f"Etiketten ble satt av {sender_login!r}, ikke repo-eier {repo_owner!r} "
            "(anti-loop/tillits-sperre)."
        )

    if sender_type == "Bot":
        return False, "Etiketten ble satt av en Bot-aktør (anti-loop/tillits-sperre)."

    if AGENT_ETIKETT not in live:
        return False, f"{AGENT_ETIKETT} er fjernet fra live-tilstanden -- avvist."

    if event_label not in live:
        return False, (
            f"{event_label} finnes ikke lenger live (allerede håndtert av en "
            "annen/tidligere kjøring) -- avvist."
        )

    return True, f"Autorisert: {event_label} både på event-tidspunktet og live."


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
    stderr -- samme CLI-kontrakt som trigger_guard.py."""
    proceed, begrunnelse = vurder_notify_trigger(
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
