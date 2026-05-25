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


def parse_recipe_text(text):
    """
    Parser fritekst-oppskrift til lister av malt, humle og gjær.

    Støttede formater:
      5 kg Maris Otter
      300 g CaraMunich
      20 g Magnum 60 min
      Wyeast 1318 London Ale III

    Returnerer dict med nøklene: malt, humle, gjaer
    """
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

    malt_liste, humle_liste, gjaer_liste = [], [], []

    for linje in text.splitlines():
        linje = linje.strip()
        if not linje or linje.startswith("#"):
            continue

        m = re_humle.match(linje)
        if m:
            humle_liste.append({
                "navn": m.group(2).strip(),
                "gram": float(m.group(1).replace(",", ".")),
                "tid": int(m.group(3)),
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
        gjaer_liste.append({"navn": linje})

    return {"malt": malt_liste, "humle": humle_liste, "gjaer": gjaer_liste}


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
