"""
Sóti -- lokal CLI-chat (issue #315, V2-5B). Minste praktiske
eier-vendte inngangspunkt: starter én `SotiSession`, kobler den til den
ekte `SotiRuntime` via en `OllamaProvider` mot en lokal Ollama-server, og
tar imot gjentatte brukermeldinger til eksplisitt avslutning. Sesjonen
lever kun så lenge denne prosessen kjører -- ingen persistens, ingen
Web/App-overflate, ingen skylagring.

Modell/profil er overstyrbar via kommandolinjeflagg, ikke hardkodet --
`SotiRuntime` og `soti.tools`/`soti.skills` er identiske uansett hvilken
`ModelProvider` som injiseres her.

Kjøring:
    py -3 -m soti.cli
    py -3 -m soti.cli --model ministral-3:8b --num-ctx 8192
"""
import argparse
import sys

from soti.ollama_provider import (
    STANDARD_BASE_URL,
    STANDARD_NUM_CTX,
    STANDARD_TIMEOUT_S,
    OllamaProvider,
    OllamaProviderFeil,
)
from soti.runtime import SotiRuntime
from soti.session import SotiSession

# Valgt V2-5A DEFAULT-profil (issue #311/PR #312) -- overstyrbar via
# --model for FALLBACK (ministral-3:8b) eller annet, uten kodeendring.
STANDARD_MODELL = "llama3.1:8b-instruct-q4_K_M"

AVSLUTT_KOMMANDOER = {"exit", "quit", ":q", "avslutt"}


def bygg_argument_parser():
    parser = argparse.ArgumentParser(description="Sóti -- lokal CLI-chat mot en lokal Ollama-modell.")
    parser.add_argument("--model", default=STANDARD_MODELL, help=f"Ollama-modelltag (standard: {STANDARD_MODELL})")
    parser.add_argument("--base-url", default=STANDARD_BASE_URL, help=f"Ollama-server URL (standard: {STANDARD_BASE_URL})")
    parser.add_argument("--num-ctx", type=int, default=STANDARD_NUM_CTX, help=f"Kontekstvindu i tokens (standard: {STANDARD_NUM_CTX})")
    parser.add_argument("--temperature", type=float, default=0.2, help="Samplingstemperatur (standard: 0.2)")
    parser.add_argument("--timeout", type=float, default=STANDARD_TIMEOUT_S, help=f"Timeout i sekunder per modellkall (standard: {STANDARD_TIMEOUT_S})")
    parser.add_argument("--skip-healthcheck", action="store_true", help="Hopp over oppstartssjekken mot Ollama (kun for testing)")
    return parser


def kjor_chat(runtime, session, inn=input, ut=print):
    """Selve samtaleløkken. `inn`/`ut` er injiserbare slik at testene kan
    kjøre hele løkken uten en ekte terminal (se tests/test_soti_cli.py)."""
    ut(f"Sóti (lokal) -- skriv '{'/'.join(sorted(AVSLUTT_KOMMANDOER))}' for å avslutte.")
    while True:
        try:
            bruker_tekst = inn("Du: ")
        except (EOFError, KeyboardInterrupt):
            ut("\nAvslutter.")
            return

        if bruker_tekst.strip().lower() in AVSLUTT_KOMMANDOER:
            ut("Avslutter.")
            return
        if not bruker_tekst.strip():
            continue

        try:
            svar = runtime.handle_message(session, bruker_tekst)
        except OllamaProviderFeil as e:
            # Lokal Ollama-/modellfeil -- fail-visible, men samtalen kan
            # fortsette (f.eks. hvis eieren starter `ollama serve` i et
            # annet vindu og prøver igjen), i stedet for å krasje hele CLI-en.
            ut(f"[Sóti -- lokal feil]: {e}")
            continue
        except KeyError as e:
            # Modellen ba om et verktøy som ikke er registrert i denne
            # skillens ToolRegistry (soti.tools.ToolRegistry.utfoer) --
            # fail-visible i stedet for en rå traceback, se issue #315 §4.
            ut(f"[Sóti -- ukjent verktøy forespurt av modellen]: {e}")
            continue

        ut(f"Sóti: {svar}")


def main(argv=None):
    parser = bygg_argument_parser()
    args = parser.parse_args(argv)

    provider = OllamaProvider(
        model=args.model,
        base_url=args.base_url,
        num_ctx=args.num_ctx,
        temperature=args.temperature,
        timeout_s=args.timeout,
    )

    if not args.skip_healthcheck:
        try:
            provider.sjekk_tilgjengelig()
        except OllamaProviderFeil as e:
            print(f"[Sóti -- kan ikke starte]: {e}", file=sys.stderr)
            return 1

    runtime = SotiRuntime(provider)
    session = SotiSession(session_id="lokal-cli")
    kjor_chat(runtime, session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
