# Preflight self-improvement

Use this routine when an out-of-band reviewer finds a HIGH/P1+ issue that the completed local preflight did not surface.

## Record the miss

Write one row:

```text
finding -> seam class -> was it already in scope? -> gap type -> generalizable correction or reject
```

Also check whether a local reviewer found the right area but the applied fix closed only an adjacent symptom. Re-review the actual failure mode after every correction.

## Recorded misses

```text
full integration lane omitted -> test-lane execution -> already in scope YES
  -> EXECUTION -> mechanically derive lane membership from the lane's own include/exclude;
     forbid a file-filtered run standing in for the lane; and when a lane number arrives in a
     SUBORDINATE'S REPORT, treat it as filtered until its exact command is shown
```

Context, because the shape recurs: three PRs reached CI with the same soft lane red while preflight
reported PASS. The author had run the two suites they wrote; a third suite collected by the *same*
config was never executed locally. The word that did the damage in the old wording was "affected" —
it let the author decide what was affected, and an author reliably answers "the files I touched".
The companion repository-level prevention was to type-link the hand-rolled mock to the production
port it stands in for, so drift fails typecheck instead of surfacing as a remote 500.

**Fourth occurrence, 2026-07-30, RND-3217 (PR #1012)** — and the new surface is the one that matters.
The rule above was already written and the orchestrator still shipped past it, because the lane
number came from an implementation agent's report as "api integration (real scratch DB) 10/10". That
read like a lane result; it was `vitest run --config vitest.integration.config.ts <one file>`. CI then
failed `canonical-persistence.integration.test.ts` on a storage-ledger check the change was required
to keep green — a new CHECK constraint that no ledger entry claimed.

So the correction is no longer only about what the author runs. A delegated lane number is a claim
about a command, and a claim about a command is unverified until the command is quoted. Ask for it,
or run the lane. Note the gate did not lie here — the lane was recorded `UNVERIFIED` with the PR's
soft lane named as owner, which is what the skill permits when local parity genuinely cannot be
established (the implementer's own machine produced 103 failures against CI's 3). The defect was
accepting a filtered number as evidence *about the lane* in the same report.

**Fifth occurrence, 2026-07-31, RND-3220 (PR #1025)** — same file, same class, and the excuse was the
one this document had just legitimised. The change ADDED A MIGRATION. Preflight ran build, typecheck,
the api unit lane and the dashboard lane, all green, and left the integration lane unrun because it is
marked *soft* in CI and local parity is known-bad on this machine. CI then failed
`canonical-persistence.integration.test.ts` twice over: the new table was unclaimed in the storage
ledger, and its new FK blocked an existing teardown's drop of `canonical_test_runs`.

The correction is narrow and it tightens §1's own escape hatch rather than adding a class:
**naming a later gate as the owner of an UNVERIFIED lane is legitimate for coverage you cannot
reproduce — never for the one gate that is the only thing exercising the change's central artifact.**
A migration is applied by exactly one lane. If the diff adds or edits a migration, or any DDL, that
lane is mandatory no matter how it is labelled; "soft" describes whether CI blocks the merge, not
whether the check is load-bearing for *this* candidate. If it genuinely cannot run locally, that is
not a deferral — it is a FAIL until the gate that applies the migration has actually reported.

**Sixth occurrence, 2026-07-31, RND-3225 (PR #1030)** — a different surface, and a cheap one to lose.

- finding: required `policy-check` failed on first push — PR title did not match `RND-XXXX: …` and the
  diff exceeded the implementation size budget without `oversize-approved`
  -> seam class: PR-metadata policy gate
  -> already in scope? NO — §1 says derive commands from the workflows, and `policy-check.yml` *was*
     read; what was run from it was its regression test (`policy-check-base-policy.test.mjs`), which
     validates the workflow's own logic and says nothing about this PR
  -> EXECUTION
  -> correction applied to §1: evaluate required checks that gate on PR METADATA (title/branch format,
     required labels, diff-size budgets) against the local diff and the intended title before opening
     the PR.

The framing error was reading "deterministic checks" as "checks that compile or execute the tree".
A required check is required whether it reads the tree or the PR object, and both of these inputs are
fully known locally — the rule is in the workflow, the size comes from `git diff --stat`, the title is
one you are about to choose. Nothing here needed the PR to exist. The cost of the miss is small (a red
required check, a title edit, a label) but it is pure avoidable noise on a PR whose whole point was
that its verification was thorough.

**Seventh occurrence, 2026-08-04, RND-3258 (PR #1110)** — a near-miss, recorded because it was one
reviewer away from being the sixth occurrence again.

- finding: a required job, `bundle-version-check`, fires on this diff (it edits
  `netsuite/bundle/**`) and fails a bundle source change that does not bump `BUNDLE_VERSION`.
  The preflight artifact asserted the opposite in as many words: *"the repo has no bundle
  byte-freshness gate"*.
  -> seam class: CI check enumeration
  -> already in scope? YES — §1 says derive the commands from the actual workflows, and
     `policy-check.yml` *was* read
  -> EXECUTION
  -> correction applied to §1: when a workflow file is triggered, enumerate **every job in the
     file**, not the one whose name matches the file.

The framing error is embarrassingly mechanical: `policy-check.yml` contains two jobs, `policy-check`
and `bundle-version-check`. I read the first, transcribed its rules faithfully — title, lineage,
labels, size budget, forbidden artifacts — and never scrolled past it, then wrote a *positive* claim
that no such gate existed. A "not triggered" row is a claim about the repository, and a claim about
the repository is unverified until the file is read to its end.

No CI failure resulted, and that is the part worth keeping: the independent seam review found the
missing bump on its own merits (a behaviour-changing bundle edit under a version literal the previous
bundle change had bumped), so the required check was green on first push. A gate that passes because
a *different* control caught the defect is not evidence the gate was covered. Had the reviewer been
silent, a PASS artifact would have shipped into a red required check for the second time in this
document.

**Eighth occurrence, 2026-08-04, RND-3258 (PR #1110)** — same run as the seventh, and this one is the
worse of the two because the evidence was on my screen.

- finding: CI's soft integration lane failed `canonical-persistence.integration.test.ts`. The local
  run of that same lane had failed the SAME three tests an hour earlier; the artifact said *"the
  canonical suites — the ones this branch touches — all pass"*.
  -> seam class: test-lane execution / reading one's own output
  -> already in scope? YES, twice over — the lane was run, and the file was named
  -> EXECUTION
  -> correction applied to §1: when summarising a lane's failures, never truncate the failing list;
     a `| tail -N` over failing suites is a filtered claim about the lane, exactly like a filtered
     RUN of it.

What happened mechanically: the failing-file list was read with `grep FAIL … | sort -u | tail -12`
against 21 failing files, so the alphabetically-early ones — including this one — fell off the end.
I then looked for confirmation instead of refutation: I grepped the log for that file's PASSING test
names, found several, and wrote "the canonical suites all pass". Both halves were literally true and
the conclusion was false.

The rule this produces is narrow and mechanical, and it belongs beside the existing lane rules rather
than as a new class: **`head`/`tail` may bound what you READ, never what you REPORT.** If the output
is too long to include, count it (`grep -c`) and name the count in the artifact; a summary that
silently drops rows is the same defect as a filtered run wearing the lane's name.

Postscript, which is why it is worth keeping the whole entry: the failure turned out to be
PRE-EXISTING on `main`, proven by running the identical command against a clean baseline checkout.
The disposition was right in the end, but it was reached only because CI forced a second look — the
artifact had already asserted the opposite and would have carried that assertion into the merge gate.

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

## 2026-07-29 — RND-3206 (PR #996) misses

- finding: app-review P1 "source-text write fence violates repo rules" -> seam class: repo-policy compliance of new tests -> already in scope? YES (preflight seam review raised it as P2 "rule-noncompliant"; orchestrator NOT_TOOK the rewrite citing a scoped eslint rule) -> EXECUTION -> correction: when dispositioning a repo-policy finding, check the ROOT policy documents for a categorical prose rule BEFORE relying on a scoped lint rule's absence; a narrow rule's scoping never clears a root-level anti-pattern row.
- finding: app-review P1 "stall-redelivered duplicate completes normally, bypassing the onFailed backstop" -> seam class: crash window/redelivery -> already in scope? PARTIALLY (redelivery idempotency was asked; the completes-normally-suppresses-failure-handler consequence was not) -> COVERAGE -> correction applied to seam-classes.md item 5 (queue-engine-own redelivery paths; absorption must fail-or-repair).

## 2026-08-02 — RND-3248 (PR #1051) miss

- finding: PR-review P1 "delta pins the prior corpus from one `CURRENT` read and fences activation on a second, later one; a publish landing between them is silently overwritten by a corpus built from the version before it" -> seam class: crash window/multi-writer state -> already in scope? PARTIALLY (item 3 asks "check-then-act window, or a guarded compare-and-set?" and the answer here was truthfully "a guarded CAS") -> COVERAGE -> correction applied to seam-classes.md item 3.

The question as written is answerable "yes, it is a CAS" while the defect is live, because the CAS
was real and correct — it just fenced a *different snapshot* of the same authority than the payload
was derived from. Both the independent reviewer and the seam framing I gave it traced producer→
consumer for the plan's own fields and asked about resume and replay; neither asked what happens when
a **concurrent publisher** advances the shared pointer mid-operation. Nothing in the diff looks like
concurrency, which is why it reads as safe: the two reads are twenty lines apart in one function.

Generalizable form, and the reason it is worth a permanent line: count the reads of a shared mutable
authority inside one logical operation. More than one, with I/O in between, is the smell — then ask
which read is the payload and which is the fence. This is mechanical, applies to any read-modify-write
against a version pointer, and adds no class.
