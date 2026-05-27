import re
from difflib import SequenceMatcher


def _likhet(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _finn_beste_treff(navn_sokt, db, terskel=0.6):
    """
    Søker i db etter beste match på kanonisk ID, display_name og aliases.
    Returnerer (master_id, display_name, score) eller (None, None, 0).
    """
    sokt = navn_sokt.lower().strip()
    best_id, best_navn, best_score = None, None, 0.0

    for m_id, info in db.items():
        if not isinstance(info, dict):
            continue
        kandidater = [
            m_id.replace("_", " "),
            info.get("display_name", ""),
        ] + [a for a in info.get("aliases", []) if a]

        for kandidat in kandidater:
            score = _likhet(sokt, kandidat.lower())
            if score > best_score:
                best_score = score
                best_id = m_id
                best_navn = info.get("display_name", m_id)

    if best_score >= terskel:
        return best_id, best_navn, best_score
    return None, None, best_score


_UNICODE_SPACES = "   ⁠​­"

def _normaliser_tekst(text):
    """Renser tekst for BOM, CRLF og uvanlige whitespace-varianter."""
    text = text.lstrip("﻿")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for tegn in _UNICODE_SPACES:
        text = text.replace(tegn, " ")
    text = text.replace("`", "")
    return text


def parse_recipe_text(text):
    """
    Parser fritekst-oppskrift til lister av malt, humle og gjær.

    Støttede formater:
      5 kg Maris Otter          (malt i kg)
      300 g CaraMunich          (malt i gram)
      20 g Magnum 60 min        (humle)
      Wyeast 1318 London Ale III (gjær)

      Total malt: 6 kg          (kreves for prosentformat)
      90% Maris Otter           (malt i prosent)

    Returnerer dict med nøklene: malt, humle, gjaer, warnings
    """
    text = _normaliser_tekst(text)

    # Humle: <tall> g <navn> <tall> min
    re_humle = re.compile(
        r"^\s*(\d+[\.,]?\d*)\s*g\s+(.+?)\s+(\d+)\s*min\s*$", re.IGNORECASE
    )
    # Malt i kg
    re_malt_kg = re.compile(
        r"^\s*(\d+[\.,]?\d*)\s*kg\s+(.+?)\s*$", re.IGNORECASE
    )
    # Malt i gram (ingen "min")
    re_malt_g = re.compile(
        r"^\s*(\d+[\.,]?\d*)\s*g\s+(.+?)\s*$", re.IGNORECASE
    )
    # Total maltmengde: "Total malt: 6 kg" / "Totalt malt 6 kg" (norsk og engelsk)
    re_total_malt = re.compile(
        r"^totalt?\s*malt\s*:?\s*(\d+[\.,]?\d*)\s*(kg|g)\b", re.IGNORECASE
    )
    # Malt i prosent: "90% Maris Otter"
    re_malt_pct = re.compile(
        r"^\s*(\d+[\.,]?\d*)\s*%\s+(.+?)\s*$", re.IGNORECASE
    )
    # Kjente metadata-linjer som skal ignoreres (ikke sendes til gjær-bøtta)
    re_metadata = re.compile(
        r"^(?:batch(?:\s*size)?|volum(?:e)?|boil|kok(?:etid)?|efficiency|effektivitet|og|fg|ibu|abv)\s*:",
        re.IGNORECASE
    )
    # Batchvolum: "Batch: 20 L" / "Batch size: 25 L" / "Volum: 20 L"
    re_batch = re.compile(
        r"^(?:batch(?:\s*size)?|volum(?:e)?)\s*:\s*(\d+[\.,]?\d*)\s*[Ll]?\b", re.IGNORECASE
    )

    malt_liste, humle_liste, gjaer_liste, pct_malt_liste = [], [], [], []
    total_malt_kg = None
    oppskrift_navn = None
    batch_liter = None
    warnings = []

    for linje in text.split("\n"):
        linje = linje.strip()
        if not linje or linje.startswith("#"):
            continue
        m = re_batch.match(linje)
        if m:
            batch_liter = float(m.group(1).replace(",", "."))
            continue
        if re_metadata.match(linje):
            continue

        # Total maltmengde-deklarasjon — sjekk FØR kg-mønsteret (starter med tekst, ikke tall)
        m = re_total_malt.match(linje)
        if m:
            verdi = float(m.group(1).replace(",", "."))
            total_malt_kg = verdi if m.group(2).lower() == "kg" else verdi / 1000.0
            continue

        m = re_humle.match(linje)
        if m:
            humle_liste.append({
                "navn": m.group(2).strip(),
                "gram": float(m.group(1).replace(",", ".")),
                "tid": int(m.group(3)),
            })
            continue

        m = re_malt_pct.match(linje)
        if m:
            pct_malt_liste.append({
                "navn": m.group(2).strip(),
                "pct": float(m.group(1).replace(",", ".")),
            })
            continue

        m = re_malt_kg.match(linje)
        if m:
            malt_liste.append({
                "navn": m.group(2).strip(),
                "mengde": float(m.group(1).replace(",", ".")),
            })
            continue

        m = re_malt_g.match(linje)
        if m:
            malt_liste.append({
                "navn": m.group(2).strip(),
                "mengde": float(m.group(1).replace(",", ".")) / 1000.0,
            })
            continue

        # Ingen mengde — behandles som gjær
        # Unntak: første linje uten siffer og uten ingredienser er trolig oppskriftnavn
        if (oppskrift_navn is None
                and not any(c.isdigit() for c in linje)
                and len(malt_liste) + len(humle_liste) + len(pct_malt_liste) == 0):
            m_label = re.match(r"^(?:recipe|navn|name|oppskrift)\s*:\s*(.+)$", linje, re.IGNORECASE)
            oppskrift_navn = m_label.group(1).strip() if m_label else linje
        else:
            gjaer_liste.append({"navn": linje})

    # Konverter prosent-malt → kg etter hele teksten er skannet
    if pct_malt_liste:
        total_pct = sum(p["pct"] for p in pct_malt_liste)
        if abs(total_pct - 100.0) > 5.0:
            warnings.append(
                f"Maltprosentene summerer til {total_pct:.1f}% (forventet ~100%)."
            )
        if total_malt_kg is None:
            warnings.append(
                "Mangler 'Total malt: X kg' — oppgi total maltmengde for å konvertere prosenter til kg."
            )
        else:
            for p in pct_malt_liste:
                malt_liste.append({
                    "navn": p["navn"],
                    "mengde": round(p["pct"] / 100.0 * total_malt_kg, 3),
                })

    return {"malt": malt_liste, "humle": humle_liste, "gjaer": gjaer_liste, "warnings": warnings,
            "navn": oppskrift_navn, "batch_liter": batch_liter}


def match_imported_ingredients(parsed, malt_db, humle_db, gjaer_db):
    """
    Fuzzy-matcher parsede ingredienser mot master-databaser.

    Returnerer:
      {
        "matched":   {"malt": [...], "humle": [...], "gjaer": {...} | None},
        "unmatched": [{"navn": ..., "kategori": ...}],
      }
    """
    matched_malt, matched_humle, unmatched = [], [], []

    for item in parsed["malt"]:
        m_id, m_navn, score = _finn_beste_treff(item["navn"], malt_db)
        if m_id:
            matched_malt.append({
                "navn": item["navn"], "id": m_id, "display_name": m_navn,
                "mengde": item["mengde"], "score": round(score, 2),
            })
        else:
            unmatched.append({"navn": item["navn"], "kategori": "malt"})

    for item in parsed["humle"]:
        h_id, h_navn, score = _finn_beste_treff(item["navn"], humle_db)
        if h_id:
            matched_humle.append({
                "navn": item["navn"], "id": h_id, "display_name": h_navn,
                "gram": item["gram"], "tid": item["tid"],
                "score": round(score, 2),
            })
        else:
            unmatched.append({"navn": item["navn"], "kategori": "humle"})

    # Gjær: ta beste match blant alle gjær-linjer
    matched_gjaer = None
    best_score = 0.0
    for item in parsed["gjaer"]:
        g_id, g_navn, score = _finn_beste_treff(item["navn"], gjaer_db)
        if g_id and score > best_score:
            best_score = score
            matched_gjaer = {
                "navn": item["navn"], "id": g_id,
                "display_name": g_navn, "score": round(score, 2),
            }

    if not matched_gjaer:
        for item in parsed["gjaer"]:
            unmatched.append({"navn": item["navn"], "kategori": "gjaer"})

    return {
        "matched": {"malt": matched_malt, "humle": matched_humle, "gjaer": matched_gjaer},
        "unmatched": unmatched,
    }


def apply_import_to_session_state(import_result):
    """
    Skriver matchede ingredienser til st.session_state.
    Kaller ikke st.rerun() — det er UI-lagets ansvar.
    """
    import streamlit as st

    matched = import_result["matched"]

    metadata = import_result.get("metadata", {})
    if metadata.get("navn"):
        st.session_state.gjeldende_navn = metadata["navn"]
    if metadata.get("batch_liter"):
        st.session_state.batch_volum_input = metadata["batch_liter"]

    if matched["malt"]:
        st.session_state.valgt_malt = [
            {"id": m["id"], "mengde": m["mengde"]} for m in matched["malt"]
        ]
    if matched["humle"]:
        st.session_state.valgt_humle = [
            {"id": h["id"], "gram": h["gram"], "tid": h["tid"]} for h in matched["humle"]
        ]
    if matched["gjaer"]:
        st.session_state.valgt_gjaer_id = matched["gjaer"]["id"]

    # Øk versjonstelleren så alle widget-nøkler i malt/humle-panelene får nye nøkler
    # og Streamlit tvinges til å bruke index-parameteren ved neste render
    st.session_state.import_versjon = st.session_state.get("import_versjon", 0) + 1
