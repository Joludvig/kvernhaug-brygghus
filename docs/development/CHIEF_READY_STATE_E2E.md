# Chief Ready-State E2E Fixture (issue #46)

This is a controlled, docs-only fixture for issue #46 — the live E2E
proof that the issue #44 / PR #45 Draft→Ready re-review wake mechanism
actually wakes the native ChatGPT Work event task on a real
`ready_for_review` PR transition, not just the hourly fallback watch.

It carries no App/Web/Core product behavior. Its only purpose is to
give this run's PR a real Round A → (Chief CHANGES_REQUESTED) →
Round B lifecycle to observe, per issue #46's own "Round A" / "Round B"
procedure. See [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md) for the mechanism
under test.

## Fixture payload

The only semantic test value in this file is the line below. Round A
sets it to `A`; Round B (a `status:changes-requested` follow-up on this
same branch/PR, per Chief's deliberate single-instruction review)
changes it to `B` and nothing else in this file.

```
E2E_STAGE=A
```

## Do not

- Do not add any other semantic content to this file across Round A/B —
  the diff between the two rounds must be exactly that one value.
- Do not treat this fixture, or a PASS/FAIL recorded against it, as
  closing issue #40 or #44 by itself; both close only per issue #46's
  own PASS criteria, decided by the owner/Chief after the live E2E
  completes.
