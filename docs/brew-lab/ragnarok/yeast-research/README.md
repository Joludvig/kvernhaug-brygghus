# Ragnarok yeast research archive

This folder preserves the Kvernhaug Brew Lab Ragnarok yeast-research workbooks produced in ChatGPT on 2026-09-12/13.

The exact `.xlsx` files are archived losslessly in a base64-encoded ZIP split into five text chunks under `archive/`.

## Contents

The ZIP contains these workbook snapshots:

- `Kvernhaug_Ragnarok_Yeast_Discovery_R1_2026-09-12.xlsx`
- `Kvernhaug_Ragnarok_Yeast_Discovery_R1_deduped_2026-09-12.xlsx`
- `Kvernhaug_Ragnarok_Yeast_R2A_first3_rankings_2026-09-12.xlsx`
- `Kvernhaug_Ragnarok_Yeast_R2A_six_rankings_2026-09-12.xlsx`
- `Kvernhaug_Ragnarok_Yeast_R2A_all10_rankings_2026-09-12.xlsx`
- `Kvernhaug_Ragnarok_Yeast_R3_priority_and_fatal_review_2026-09-12.xlsx`
- `Kvernhaug_Ragnarok_Yeast_R4_helper_framework_2026-09-12.xlsx`
- `Kvernhaug_Ragnarok_Yeast_R5_single_and_combo_tracks_2026-09-12.xlsx`
- `Kvernhaug_Ragnarok_Yeast_R6_case_studies_2026-09-13.xlsx`

ZIP SHA-256: `28ca60cab289d70d752c1abb276b25c9d58578eb167e3e4800f0ca862e255562`

## Restore

Linux/macOS/Git Bash:

```bash
cat archive/ragnarok-yeast-r1-r6.zip.b64.part00 \
    archive/ragnarok-yeast-r1-r6.zip.b64.part01 \
    archive/ragnarok-yeast-r1-r6.zip.b64.part02 \
    archive/ragnarok-yeast-r1-r6.zip.b64.part03 \
    archive/ragnarok-yeast-r1-r6.zip.b64.part04 \
  | base64 -d > Kvernhaug_Ragnarok_Yeast_Research_R1-R6_2026-09-13.zip
```

PowerShell:

```powershell
$parts = 0..4 | ForEach-Object { Get-Content -Raw ("archive/ragnarok-yeast-r1-r6.zip.b64.part{0:D2}" -f $_) }
[IO.File]::WriteAllBytes("Kvernhaug_Ragnarok_Yeast_Research_R1-R6_2026-09-13.zip", [Convert]::FromBase64String(($parts -join "")))
```

Then verify the SHA-256 and unzip normally.

## Governance

These are Brew Lab research artifacts, not Core canonical masterdata. Producer data, brewer observations, interpretation, hypotheses and decisions remain distinct in the workbooks. Later Brew Lab findings must not silently modify Core contracts or masterdata.
