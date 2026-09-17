"""
Kjørbart evalueringsscript for issue #311 (SÓTI V2-5A). Kjører
scripts.soti_eval.prompts sitt faste caseoppsett mot hvert kandidat-modell
oppgitt på kommandolinjen, via en lokal Ollama-server, og skriver rå
resultater til en lokal JSON-fil (ikke committet -- se
docs/development/SOTI_MODEL_RUNTIME_EVAL_V1.md for den nedstrippede,
menneskelesbare oppsummeringen som ER committet).

Brukes kun til selve evalueringen; ingen produksjonskode importerer denne
pakken.

Kjøring:
    py -3 scripts/soti_eval/run_eval.py --models qwen2.5:7b-instruct-q4_K_M llama3.1:8b-instruct-q4_K_M qwen2.5:14b-instruct-q4_K_M --out <sti.json>
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.soti_eval import prompts
from scripts.soti_eval.ollama_provider import OllamaProvider, raw_generate
from soti.identity import bygg_system_melding
from soti.runtime import SotiRuntime
from soti.session import SotiSession
from soti.tools import bygg_standard_registry

_BASE_URL = "http://127.0.0.1:11434"


def _maalinger_til_dict(m):
    if m is None:
        return None
    return {
        "wall_clock_s": getattr(m, "wall_clock_s", None),
        "total_duration_s": (m.total_duration_ns or 0) / 1e9 if m.total_duration_ns else None,
        "load_duration_s": (m.load_duration_ns or 0) / 1e9 if m.load_duration_ns else None,
        "prompt_eval_count": m.prompt_eval_count,
        "eval_count": m.eval_count,
        "tokens_per_sekund": m.tokens_per_sekund(),
    }


def kjor_sprak_og_resonnement_caser(model, caser):
    # Kjøres med Sótis systemprompt (soti.identity.bygg_system_melding())
    # slik at identitets-/instruksjonsfølging-casene faktisk måler Sóti sin
    # grense, ikke modellens egen fabrikkidentitet -- uten dette svarer en
    # ukonfigurert modell naturligvis som "seg selv", ikke som Sóti.
    system = bygg_system_melding()
    resultater = []
    for case in caser:
        try:
            svar, m = raw_generate(model, case["prompt"], base_url=_BASE_URL, temperature=0.2, seed=42, system=system)
            resultater.append({"case_id": case["id"], "ok": True, "svar": svar, "maalinger": _maalinger_til_dict(m)})
        except (urllib.error.URLError, TimeoutError) as e:
            resultater.append({"case_id": case["id"], "ok": False, "feil": str(e)})
    return resultater


def kjor_json_caser(model, caser):
    system = bygg_system_melding()
    resultater = []
    for case in caser:
        try:
            svar, m = raw_generate(model, case["prompt"], base_url=_BASE_URL, temperature=0.0, seed=42, system=system)
            parse_ok = False
            felt_ok = False
            try:
                parsed = json.loads(svar.strip())
                parse_ok = True
                felt_ok = all(felt in parsed for felt in case.get("krever_json_felt", []))
            except json.JSONDecodeError:
                parsed = None
            resultater.append({
                "case_id": case["id"], "ok": True, "svar": svar,
                "json_parse_ok": parse_ok, "json_felt_ok": felt_ok,
                "maalinger": _maalinger_til_dict(m),
            })
        except (urllib.error.URLError, TimeoutError) as e:
            resultater.append({"case_id": case["id"], "ok": False, "feil": str(e)})
    return resultater


def kjor_verktoykall_caser(model, caser):
    """Kjører gjennom den ekte SotiRuntime + soti.tools.bygg_standard_registry
    -- se scripts/soti_eval/ollama_provider.py sin moduldoc for hvorfor
    dette er trygt uten å endre soti/ selv."""
    resultater = []
    for case in caser:
        provider = OllamaProvider(model, base_url=_BASE_URL, temperature=0.0, seed=42)
        runtime = SotiRuntime(provider)
        # bygg_standard_registry() krever core/manifest.json + data/-filer;
        # SotiRuntime bruker sin egen skill-scopede registry internt, så vi
        # bruker den her kun til å avgjøre om verktøyet fantes -- selve
        # kallet skjer inne i SotiRuntime.handle_message.
        session = SotiSession(session_id=f"eval-{case['id']}")
        try:
            svar = runtime.handle_message(session, case["bruker_tekst"])
            kalte_verktoy = any(m["role"] == "tool" for m in session.meldinger())
            oppfant_suksess = (
                case["forventet_verktoy"] is None
                and not kalte_verktoy
                and any(ord_ in svar.lower() for ord_ in ("bestilt", "har bestilt", "ordre er lagt", "kjøpet er gjennomført"))
            )
            resultater.append({
                "case_id": case["id"], "ok": True, "svar": svar,
                "kalte_verktoy": kalte_verktoy,
                "forventet_verktoy": case["forventet_verktoy"],
                "oppfant_suksess_uten_verktoy": oppfant_suksess,
                "maalinger": _maalinger_til_dict(provider.siste_maalinger),
            })
        except (urllib.error.URLError, TimeoutError, KeyError) as e:
            resultater.append({"case_id": case["id"], "ok": False, "feil": str(e)})
    return resultater


def kjor_multiturn_case(model, case):
    provider = OllamaProvider(model, base_url=_BASE_URL, temperature=0.2, seed=42)
    runtime = SotiRuntime(provider)
    session = SotiSession(session_id="eval-multiturn")
    svar_per_tur = []
    for tur_tekst in case["turer"]:
        try:
            svar = runtime.handle_message(session, tur_tekst)
            svar_per_tur.append(svar)
        except (urllib.error.URLError, TimeoutError, KeyError) as e:
            svar_per_tur.append(f"[FEIL: {e}]")
    return {"case_id": case["id"], "svar_per_tur": svar_per_tur, "antall_meldinger_i_historikk": len(session.historikk)}


def sjekk_modell_lastet(model):
    try:
        req = urllib.request.Request(f"{_BASE_URL}/api/show", data=json.dumps({"name": model}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        return {"feil": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--runs-per-case", type=int, default=2, help="repeated samples for stability check")
    args = parser.parse_args()

    resultat = {"generert_tidspunkt_unix": time.time(), "modeller": {}}

    for model in args.models:
        print(f"=== {model} ===", flush=True)
        info = sjekk_modell_lastet(model)
        modell_resultat = {"api_show": info, "kjoringer": []}
        for kjoring in range(args.runs_per_case):
            print(f"  kjøring {kjoring + 1}/{args.runs_per_case}", flush=True)
            enkeltkjoring = {
                "sprak_og_resonnement": kjor_sprak_og_resonnement_caser(model, prompts.SPRAK_CASER + prompts.RESONNEMENT_CASER),
                "json": kjor_json_caser(model, prompts.JSON_CASER),
                "verktoy": kjor_verktoykall_caser(model, prompts.VERKTOY_CASER),
                "multiturn": kjor_multiturn_case(model, prompts.MULTITURN_CASE),
            }
            modell_resultat["kjoringer"].append(enkeltkjoring)
        resultat["modeller"][model] = modell_resultat

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Skrevet: {out_path}")


if __name__ == "__main__":
    main()
