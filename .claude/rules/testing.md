# Testing policy

- Run focused/relevant tests first; suppress successful-test noise where possible (`py -3 -m unittest discover -s tests -b`).
- Full Python suite (`tests/`) is required at final checkpoints and commit-ready validation.
- Intermediate rounds where the diff is demonstrably confined to `web/**` do not require the full Python suite — `tests/` has no web coverage overlap. Still run it at the final checkpoint before commit.
- Failures always get full, detailed output. Successful runs get a compact summary (counts, not per-test noise).
- Deeper guidance (isolation principles, `AppTest` pattern): [TESTING.md](../../docs/development/TESTING.md).
