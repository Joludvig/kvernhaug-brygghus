"""
Kjørbart evalueringsscript for issue #311 (SÓTI V2-5A). Kjører
scripts.soti_eval.prompts sitt faste caseoppsett mot hvert kandidat-modell
oppgitt på kommandolinjen, via en lokal Ollama-server, og skriver rå
resultater til en lokal JSON-fil (ikke committet -- se
docs/development/SOTI_MODEL_RUNTIME_EVAL_V1.md for den nedstrippede,
menneskelesbare oppsummeringen som ER committet).

Brukes kun til selve evalueringen; ingen produksjonskode importerer denne
pakken.

Kjøring (full batteri, 8K kontekst-baseline):
    py -3 scripts/soti_eval/run_eval.py --models qwen3.5:9b ministral-3:8b gemma4:12b --out <sti.json> --num-ctx 8192

Kjøring (kun verktøy-/multiturn-casene, f.eks. for å re-kjøre de historiske
Qwen2.5/Llama3.1-basislinjene med den nye telemetrien uten å kaste bort tid
på identiske språk-/JSON-svar):
    py -3 scripts/soti_eval/run_eval.py --models llama3.1:8b-instruct-q4_K_M --out <sti.json> --cases verktoy multiturn --num-ctx 8192

Kjøring (avgrenset tuning-runde for de to finalistene: 16K kontekst og/eller
thinking på):
    py -3 scripts/soti_eval/run_eval.py --models <finalist> --out <sti.json> --num-ctx 16384 --think
"""
import argparse
import json
import re
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

# Tolker den stringifiserte verktøyresultat-meldingen SotiRuntime legger i
# historikken ("[navn] {'funnet': True/False, ...}") -- se
# soti.runtime.SotiRuntime.handle_message linje 40. Kun evalueringskode:
# tolker en tekstrepresentasjon, endrer aldri hvordan soti/ selv lagrer den.
_TOOL_MELDING_RE = re.compile(r"^\[(?P<navn>[^\]]+)\]\s(?P<resultat>.*)$", re.DOTALL)


def _tolk_verktoy_suksess(resultat_tekst):
    """None hvis formatet er ukjent -- aldri anta suksess/feil vi ikke kan lese."""
    if "'funnet': True" in resultat_tekst:
        return True
    if "'funnet': False" in resultat_tekst:
        return False
    return None


def _uttrekk_ny_verktoy_telemetri(provider, session, tur, kall_idx_start, tool_msg_idx_start):
    """Parer nye oppføringer i provider.tool_kall_logg (denne SotiRuntime-
    runden) med de tilsvarende nye "tool"-meldingene lagt til session i
    samme runde, i rekkefølge -- se OllamaProvider sin klassedoc for hvorfor
    denne paringen må skje her og ikke leses direkte fra siste_raw_response."""
    nye_kall = [k for k in provider.tool_kall_logg[kall_idx_start:] if k["navn"] is not None]
    alle_tool_meldinger = [m for m in session.meldinger() if m["role"] == "tool"]
    nye_tool_meldinger = alle_tool_meldinger[tool_msg_idx_start:]
    telemetri = []
    for kall, tm in zip(nye_kall, nye_tool_meldinger):
        match = _TOOL_MELDING_RE.match(tm["content"])
        resultat_tekst = match.group("resultat") if match else tm["content"]
        telemetri.append({
            "tur": tur,
            "navn": kall["navn"],
            "argumenter": kall["argumenter"],
            "suksess": _tolk_verktoy_suksess(resultat_tekst),
            "raw_resultat": resultat_tekst,
        })
    return telemetri


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


def kjor_sprak_og_resonnement_caser(model, caser, num_ctx=None, think=None):
    # Kjøres med Sótis systemprompt (soti.identity.bygg_system_melding())
    # slik at identitets-/instruksjonsfølging-casene faktisk måler Sóti sin
    # grense, ikke modellens egen fabrikkidentitet -- uten dette svarer en
    # ukonfigurert modell naturligvis som "seg selv", ikke som Sóti.
    system = bygg_system_melding()
    resultater = []
    for case in caser:
        try:
            svar, m = raw_generate(model, case["prompt"], base_url=_BASE_URL, temperature=0.2, seed=42, system=system, num_ctx=num_ctx, think=think)
            resultater.append({"case_id": case["id"], "ok": True, "svar": svar, "maalinger": _maalinger_til_dict(m)})
        except (urllib.error.URLError, TimeoutError) as e:
            resultater.append({"case_id": case["id"], "ok": False, "feil": str(e)})
    return resultater


def kjor_json_caser(model, caser, num_ctx=None, think=None):
    system = bygg_system_melding()
    resultater = []
    for case in caser:
        try:
            svar, m = raw_generate(model, case["prompt"], base_url=_BASE_URL, temperature=0.0, seed=42, system=system, num_ctx=num_ctx, think=think)
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


def kjor_verktoykall_caser(model, caser, num_ctx=None, think=None):
    """Kjører gjennom den ekte SotiRuntime + soti.tools.bygg_standard_registry
    -- se scripts/soti_eval/ollama_provider.py sin moduldoc for hvorfor
    dette er trygt uten å endre soti/ selv."""
    resultater = []
    for case in caser:
        provider = OllamaProvider(model, base_url=_BASE_URL, temperature=0.0, seed=42, num_ctx=num_ctx, think=think)
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
            verktoy_telemetri = _uttrekk_ny_verktoy_telemetri(provider, session, tur=1, kall_idx_start=0, tool_msg_idx_start=0)
            resultater.append({
                "case_id": case["id"], "ok": True, "svar": svar,
                "kalte_verktoy": kalte_verktoy,
                "forventet_verktoy": case["forventet_verktoy"],
                "oppfant_suksess_uten_verktoy": oppfant_suksess,
                "verktoy_telemetri": verktoy_telemetri,
                "maalinger": _maalinger_til_dict(provider.siste_maalinger),
            })
        except (urllib.error.URLError, TimeoutError, KeyError) as e:
            resultater.append({"case_id": case["id"], "ok": False, "feil": str(e)})
    return resultater


def kjor_multiturn_case(model, case, num_ctx=None, think=None):
    provider = OllamaProvider(model, base_url=_BASE_URL, temperature=0.2, seed=42, num_ctx=num_ctx, think=think)
    runtime = SotiRuntime(provider)
    session = SotiSession(session_id="eval-multiturn")
    svar_per_tur = []
    verktoy_telemetri = []
    for tur_idx, tur_tekst in enumerate(case["turer"], start=1):
        kall_idx_start = len(provider.tool_kall_logg)
        tool_msg_idx_start = len([m for m in session.meldinger() if m["role"] == "tool"])
        try:
            svar = runtime.handle_message(session, tur_tekst)
            svar_per_tur.append(svar)
        except (urllib.error.URLError, TimeoutError, KeyError) as e:
            svar_per_tur.append(f"[FEIL: {e}]")
            continue
        verktoy_telemetri.extend(_uttrekk_ny_verktoy_telemetri(provider, session, tur_idx, kall_idx_start, tool_msg_idx_start))
    return {
        "case_id": case["id"], "svar_per_tur": svar_per_tur,
        "verktoy_telemetri": verktoy_telemetri,
        "antall_meldinger_i_historikk": len(session.historikk),
    }


def sjekk_modell_lastet(model):
    try:
        req = urllib.request.Request(f"{_BASE_URL}/api/show", data=json.dumps({"name": model}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        return {"feil": str(e)}


def hent_resolvert_digest(model):
    """Eksakt digest + kvantisering slik Ollama selv har resolvet
    modellnavnet -- Chief-instruksen krever at rapporten viser dette, ikke
    bare den oppgitte tag-strengen fra kommandolinjen."""
    try:
        req = urllib.request.Request(f"{_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            tags = json.loads(resp.read().decode())
        for entry in tags.get("models", []):
            if entry.get("name") == model or entry.get("model") == model:
                return {"digest": entry.get("digest"), "size": entry.get("size"), "details": entry.get("details")}
        return {"feil": f"{model!r} ikke funnet i /api/tags"}
    except urllib.error.URLError as e:
        return {"feil": str(e)}


_ALLE_CASE_GRUPPER = ("sprak_og_resonnement", "json", "verktoy", "multiturn")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--runs-per-case", type=int, default=2, help="repeated samples for stability check")
    parser.add_argument("--num-ctx", type=int, default=8192, help="eksplisitt kontekstvindu -- default 8K-baseline (Chief execution note), ikke modellens annonserte maks")
    parser.add_argument("--think", dest="think", action="store_true", default=None, help="be modellen tenke eksplisitt (kun for modeller/runtime som støtter det)")
    parser.add_argument("--no-think", dest="think", action="store_false", help="be eksplisitt om IKKE å tenke")
    parser.add_argument("--cases", nargs="+", choices=list(_ALLE_CASE_GRUPPER) + ["all"], default=["all"], help="begrens til gitte casegrupper, f.eks. for å re-kjøre kun verktoy+multiturn på en historisk baseline med ny telemetri")
    args = parser.parse_args()

    caser_a_kjore = set(_ALLE_CASE_GRUPPER) if "all" in args.cases else set(args.cases)

    resultat = {
        "generert_tidspunkt_unix": time.time(),
        "num_ctx": args.num_ctx,
        "think": args.think,
        "caser_kjort": sorted(caser_a_kjore),
        "modeller": {},
    }

    for model in args.models:
        print(f"=== {model} ===", flush=True)
        info = sjekk_modell_lastet(model)
        digest_info = hent_resolvert_digest(model)
        modell_resultat = {"api_show": info, "resolvert_digest": digest_info, "kjoringer": []}
        for kjoring in range(args.runs_per_case):
            print(f"  kjøring {kjoring + 1}/{args.runs_per_case}", flush=True)
            enkeltkjoring = {}
            if "sprak_og_resonnement" in caser_a_kjore:
                enkeltkjoring["sprak_og_resonnement"] = kjor_sprak_og_resonnement_caser(
                    model, prompts.SPRAK_CASER + prompts.RESONNEMENT_CASER, num_ctx=args.num_ctx, think=args.think)
            if "json" in caser_a_kjore:
                enkeltkjoring["json"] = kjor_json_caser(model, prompts.JSON_CASER, num_ctx=args.num_ctx, think=args.think)
            if "verktoy" in caser_a_kjore:
                enkeltkjoring["verktoy"] = kjor_verktoykall_caser(model, prompts.VERKTOY_CASER, num_ctx=args.num_ctx, think=args.think)
            if "multiturn" in caser_a_kjore:
                enkeltkjoring["multiturn"] = kjor_multiturn_case(model, prompts.MULTITURN_CASE, num_ctx=args.num_ctx, think=args.think)
            modell_resultat["kjoringer"].append(enkeltkjoring)
        resultat["modeller"][model] = modell_resultat

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Skrevet: {out_path}")


if __name__ == "__main__":
    main()
