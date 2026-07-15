# Preflight self-improvement

Use this routine when an out-of-band reviewer finds a HIGH/P1+ issue that the completed local preflight did not surface.

## Record the miss

Write one row:

```text
finding -> seam class -> was it already in scope? -> gap type -> generalizable correction or reject
```

Also check whether a local reviewer found the right area but the applied fix closed only an adjacent symptom. Re-review the actual failure mode after every correction.

## Classify before editing

- **EXECUTION** — the class already existed, but the run skipped it or was framed too narrowly. Fix the trigger, framing, or artifact requirement; do not add a new class.
- **COVERAGE** — a genuinely new reusable seam class is missing. Add the smallest general class or, preferably, a mechanically derived invariant.
- **OVERFIT** — the issue is instance-specific. Record the lesson but reject a permanent checklist entry.
- **UNPREVENTABLE-LOCALLY** — the local run lacks a real capability or independent surface. Assign it to the correct out-of-band/live gate; do not manufacture a fake local check.

Default to EXECUTION or UNPREVENTABLE until evidence shows a reusable coverage gap.

## Self-modification gate

Self-apply a change to this personal skill only when all conditions hold:

1. The change is a true COVERAGE correction or a mechanically derived invariant, or it tightens execution/framing without adding a class.
2. The seam list remains flat and general; prune or consolidate instead of piling up incidents.
3. The change adds no scored/tuned corpus and no second scanner when an existing repository invariant can own the check.
4. The change preserves the core principle: verify external contracts against their real source and forbid harness substitution at the seam.
5. The active source-of-truth and every runtime mirror can be updated and validated together.

If any condition fails or is uncertain, do not self-edit. Present the proposal and conformance analysis for user approval.

## Completion output

At the end of an autodrive or merge loop, report either:

- the classified misses and the exact general correction applied/proposed; or
- `no preflight misses observed`.

Never interpret a clean run as a reason to invent new checks, and never tune against a scored bug corpus.
