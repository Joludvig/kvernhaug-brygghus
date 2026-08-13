---
paths:
  - "app.py"
  - "config.py"
  - "modules/**"
  - "ui/**"
  - "scripts/**"
  - "tests/**"
---

# Desktop (Streamlit) — resident rules

- `modules/**` never imports Streamlit. All rendering lives in `ui/**`. Test: could this run without a Streamlit context (e.g. from a test)? If yes, it belongs in `modules/`.
- Any `modules/` function that writes to disk must respect `DEMO_MODE` (guard or `ui/demo_state.py` session-overlay). Full contract/coverage table: [DEMO_MODE.md](../../docs/development/DEMO_MODE.md).
- Preserve established Streamlit state patterns (shadow key, pending key, widget-reset version key) — don't invent new ones. Details: [PROJECT_MAP.md](../../docs/development/PROJECT_MAP.md#etablerte-state-mønstre-streamlit).
- Domain logic (functions/variables representing the brewing domain) is named in Norwegian; generic technical patterns follow standard PEP8/English.
- Full architecture, module map, and 4-tab breakdown: [PROJECT_MAP.md](../../docs/development/PROJECT_MAP.md). Read it when the task needs deeper context — not by default.
