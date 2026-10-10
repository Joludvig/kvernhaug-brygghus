#!/usr/bin/env python3
"""Classify a pull request's changed files for the CI fast path.

Result is one of:
  QUIZ_CONTENT_ONLY  every changed file is an active Bryggeskole pilot quiz
                     JSON (bryggeskole/data/pilot_*.json), nothing else.
  FULL               anything else, and every case of doubt.

The classifier fails closed: a non-pull-request event, an empty file list, a
git error or any unexpected exception all yield FULL. The required status
checks `test` and `Playwright Critical Browser Gate` always run either way;
this only decides how much work they do.

Usage in CI:
  python3 scripts/ci/classify_pr_changes.py --event "$EVENT" --base "$BASE" --head "$HEAD"
Writes `mode=<result>` to $GITHUB_OUTPUT when set, and prints the decision.
"""
import argparse
import os
import re
import subprocess
import sys

QUIZ_CONTENT_ONLY = "QUIZ_CONTENT_ONLY"
FULL = "FULL"

# Deliberately narrow: directly in bryggeskole/data/, filename pilot_<name>.json.
# course_fact_registry.json and course_stage_map.json do not match, nor does
# anything in a subdirectory or with a different extension.
_PILOT_QUIZ_JSON = re.compile(r"^bryggeskole/data/pilot_[A-Za-z0-9_]+\.json$")


def classify(event_name, changed_files):
    """Pure classification. Returns (mode, reason)."""
    if event_name != "pull_request":
        return FULL, f"event is {event_name!r}, not a pull request"
    files = [f.strip() for f in changed_files if f and f.strip()]
    if not files:
        return FULL, "empty changed-file list (fail closed)"
    outside = [f for f in files if not _PILOT_QUIZ_JSON.match(f)]
    if outside:
        return FULL, "changed files outside the pilot quiz JSON set: " + ", ".join(sorted(outside)[:10])
    return QUIZ_CONTENT_ONLY, f"{len(files)} changed file(s), all pilot quiz JSON"


def changed_files(base, head):
    """Complete PR diff (merge-base of base..head to head), both sides of a rename."""
    out = subprocess.run(
        ["git", "diff", "--no-renames", "--name-only", f"{base}...{head}"],
        check=True, capture_output=True, text=True,
    ).stdout
    return out.splitlines()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="")
    args = parser.parse_args(argv)
    try:
        if args.event != "pull_request":
            mode, reason = classify(args.event, [])
        elif not args.base or not args.head:
            mode, reason = FULL, "missing base/head SHA (fail closed)"
        else:
            mode, reason = classify(args.event, changed_files(args.base, args.head))
    except Exception as exc:  # fail closed on anything unexpected
        mode, reason = FULL, f"classifier error: {exc}"
    label = "QUIZ_CONTENT_ONLY FAST PATH" if mode == QUIZ_CONTENT_ONLY else "FULL CI"
    print(f"CI path chosen: {label}")
    print(f"Reason: {reason}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"mode={mode}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
