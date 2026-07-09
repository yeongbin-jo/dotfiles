---
name: autodrive
description: >-
  Autonomous SDLC driver for a single well-understood CrossCheck issue. Takes it
  worktree → (right-sized) spec → build → adversarial review → PR → cc-merge in ONE
  autonomous run, pausing ONLY at hard gates. A thin orchestrator over the canonical
  cc-* skills; it adds rigor-calibration, an autonomous-by-default posture, and the
  stop-gates. Use when the user says "autodrive", "self-drive this", "run the autonomous
  loop", "ship this end-to-end", or hands over a self-evident/already-discussed issue
  (RND-XXXX) to take all the way to merge without per-phase babysitting. NOT for
  exploratory work, ambiguous scope, or anything the user hasn't agreed to ship.
---

# autodrive — autonomous SDLC driver

Personal skill. Drives one issue end-to-end (prepare → spec → build → adversarial review → PR → merge),
**autonomous by default**, stopping only at the hard gates below. It does NOT reimplement the SDLC — it
**orchestrates the canonical skills** (`cc-prepare-ticket`, `cc-spec-phase`, `cc-build-phase`, `cc-merge`)
and layers on rigor-calibration + the autonomous posture.

## Entry — required before driving
- An issue ref (`RND-XXXX`) or an unambiguous task the user has explicitly agreed to ship.
- A current-turn go ("autodrive RND-2744", "self-drive it"). Never infer from prior discussion alone.
- If scope is ambiguous or the issue is exploratory → STOP, do not autodrive; clarify first.

## Step 1 — Classify rigor tier (auto, overridable via `--tier=trivial|standard|high`)
Inspect the issue + the likely diff scope:
- **trivial** — single-file / few-line / config / no behavior change, no migration, no shared infra.
- **standard** — self-evident feature/bugfix, scope clear and ideally already measured, bounded blast radius, NO schema migration, NOT shared-infra/multi-tenant/security/IaC.
- **high** — ANY of: schema/prisma migration, shared infrastructure (feature-flags, auth, queue/worker core, snapshot/merge_save core), multi-tenant isolation, security, CDK/IaC, destructive/data-touching ops.

A single issue may be **mixed** (e.g. RND-2744 = standard S3-concurrency + high feature-flag migration). Classify **per change-area** and apply the highest tier's gates to that area.

State the classification + reasoning before proceeding.

## Step 2 — Right-sized pipeline per tier
| Phase | trivial | standard | high |
|---|---|---|---|
| Prepare (`cc-prepare-ticket`) | ✓ | ✓ | ✓ |
| Ground in code first (scouts, no guessing) | ✓ | ✓ | ✓ |
| Spec (`cc-spec-phase`) | skip | **light**: discussion-lock (+ spec if AC needed); open forks resolved by independent-reviewer + Codex consensus | **full**: discussion→spec→plan→tasks + **4-reviewer parallel audit** (arch / eng-rubric / domain / Codex) |
| **coreGoalDrift + pivot verdict gate (Phase 0 — spec)** | n/a | **REQUIRED** (lightweight: the consensus pair returns explicit `coreGoalDrift`/`pivot`) | **REQUIRED** (the 4-reviewer audit returns it) |
| Build (`cc-build-phase`, TDD) | direct edit ok | ✓ | ✓ |
| Adversarial review of the diff (**+coreGoalDrift/pivot verdict — Phase 1**; INDEPENDENT — fresh context / different model — and must emit the `preflight` **assumption ledger** artifact, not just a verdict) | quick | 1 round (fix→re-review to APPROVE) | full loop (parallel adversarial reviewers, bounded iters) |
| **Pre-PR gate = run the `preflight` skill** (deterministic local mirror of CI's own gates + the independent seam review; local-green is NECESSARY-NOT-SUFFICIENT — codex stays the out-of-band net) | ✓ | ✓ | ✓ |
| **Runtime-verify the changed behavior** (run the REAL path E2E, not unit-only) | n/a | ✓ when feasible | ✓ when feasible |
| PR (push + `gh api` to bypass stale-main hook) | ✓ | ✓ | ✓ |
| Merge (`cc-merge`, merge-commit, squash forbidden) | ✓ | ✓ | ✓ |

**The drift/pivot gate runs at BOTH checkpoints — the Phase 0 spec audit AND the Phase 1 post-build adversarial review.** The *implementation* can drift from the core goal (scope creep, an approach pivot, an AC quietly dropped) even when the spec didn't — so every reviewer at BOTH checkpoints MUST end with an explicit `coreGoalDrift: yes|no` / `pivot: yes|no` line, judging the built diff against the *approved ACs*, not only hunting bugs. **NON-NEGOTIABLE for standard AND high** (only `trivial` skips it). If it trips at either checkpoint → STOP (see gates).

## Step 3 — HARD STOP gates (pause for human; everything else is autonomous through merge)
Stop and surface — do NOT proceed past:
1. **coreGoalDrift = yes** OR **pivot = yes** (from the verdict gate).
2. **Schema migration / destructive op** (prisma migrate, data delete/backfill, irreversible). The gate is about *applying* to a real DB — authoring + committing the migration file is fine. AUTHOR + commit it, but before applying it anywhere **and, for deploy-applied migrations, before MERGE** (merge → next deploy auto-applies), present the SQL + a deploy-ordering note and get explicit go.
3. **Production IAM / infra change** (CDK prod, IAM policy, secrets, prod data writes).
4. **Repeated build/review failure** (cc-build evaluator FAIL after its bounded loop; adversarial review can't reach APPROVE) — escalate with findings.
5. Anything the issue's spec marks as a human gate.

Otherwise: drive autonomously all the way to **cc-merge** + Linear Done (M3/RND-2718 was driven this way).

## Handling a mid-run change
- **User adds scope after spec-approval** (e.g. "also handle X" — RND-2744's ops-dashboard editor was pulled in this way): fold it into the approved spec's ACs (don't silently expand or quietly drop scope), run a *focused* build + adversarial review on just the addition with the drift/pivot gate re-applied, then continue. Record the pull-in in the spec + commit message.
- **A reviewer finding implies a different approach** = a *pivot* → HARD STOP (gate #1), not an autonomous redirect.

## Cross-cutting principles (apply throughout)
- **Measure, don't guess** — for any perf/behavior claim, get real data (prod CloudWatch, real-client bench against the actual code path, DB). Never ship a fix justified by code-reading alone when it's measurable.
- **Verify behavior at runtime, not just in tests.** Green unit tests + reviewer code-traces prove *plausibility*, not that the feature actually runs. For a behavior-changing feature, exercise the REAL path end-to-end before calling it done — trigger the actual job/snapshot, hit the live endpoint, watch the log line you added — when feasible. It both confirms the change and surfaces env/integration issues unit tests can't. (RND-2744 looked done on unit tests; the real merge_save run `resolved=64 source=flag` is what closed the gap — and incidentally exposed an unrelated bundle-deploy/JAVA_HOME env trap.) Real-runtime verification may require full-stack bring-up (`cc-dev-up` + worker + ngrok); budget for it and don't let env-debugging derail the ticket.
- **Adversarially review the experiment design too**, before trusting its result.
- **Codex is non-blocking** — run `codex exec "…" < /dev/null` with a `timeout`; on hang (0% CPU) pkill and fall back to an independent reviewer. Never gate on Codex completing.
- **Intellectual honesty** — when measurement refutes your own claim, correct it in the open. "No viable fix / not worth it" is an allowed terminal outcome; never fabricate a fix to justify a ticket.
- **No silent fallback** (CLAUDE.md [spec-103]); **right-size rigor to blast radius**; new commits for fixes (no amend/force-push).
- **Never skip the independent spawn (preflight's measured #1 failure).** No push until the independent seam review has actually run as a *separate* agent — a DIFFERENT model / clean context, recall→refute — and produced its findings artifact. Self-reviewing in the authoring context does NOT count; that's how the "verify against real source" class reached CI every time. The aim is to catch locally what CI codex would otherwise be first to find, not to wait for CI to spoon-feed it.
- **No WIP / incremental pushes** (per `feedback_no_incremental_push`). Reach local-green on the WHOLE change — `pnpm build` (the real CI type gate, not `typecheck` alone) + lint + the independent pass + any live-contract probe — before the FIRST push; don't push half-done and fix-forward against CI. (30-day audit: Build was the #1 CI blocker and its churn concentrated in the 27/41-commit fix-forward PRs.)
- **Pre-mortem is project-scope, at spec time — not a per-diff checklist.** During discussion/spec, name which anti-pattern CLASSES the work is exposed to (multi-tenant mass-write, worker idempotency, external-contract, silent-fallback) and lock the invariant into the ACs, so every downstream diff is checked against it. This lowers the base rate before any diff exists; the per-diff detection lives in `preflight`.
- **Review-finding triage — Occam's razor.** CRITICAL/HIGH and real correctness/safety/silent-failure findings → fix. **NIT/suggestion-level findings → apply ONLY when they are a *pure* improvement at minimal cost.** Do not gold-plate: reject (with a one-line "Not taking, reason" per cc-merge protocol) any suggestion that adds fragile machinery (private-field/SDK-internal access, heavy test scaffolding), couples a generic surface to a special case, or speculatively generalizes beyond the spec. Prefer the simplest change that resolves the kernel of the finding. The re-review loop after fixes is itself right-sized — re-run a *focused* check (not the full panel) on small, test-covered refinements.

## Preflight-miss retrospective → improvement proposal (completion routine)
**Trigger (during the merge loop):** any out-of-band reviewer (CI codex, gemini, claude-domain-expert, human) lands a **P1/HIGH+** finding on the PR that `preflight` did NOT surface locally. For EACH such finding, before just fixing it, record a one-line retrospective row:

`finding → seam CLASS → was the class already in preflight's scope? → gap type → generalizable fix (or "overfit, reject")`

Classify the **gap type** — this is the whole point, because the fix differs:
- **EXECUTION gap** — the seam class WAS already in `preflight`'s list (e.g. crash-window/redelivery "two writers race → guarded CAS"; silent-fallback; contract-vs-real), but the actual seam-review run didn't *execute* that enumeration (it did the external-existence ledger and stopped). The finding was in-scope but under-run. **Fix = a MECHANICAL trigger that FORCES the enumeration when the diff matches, so it cannot be skipped** — not a new class. (This is the common case, and it's a real gap: an assumption-ledger that only proves "X exists / matches" will pass a diff whose bug is *internal logic* — concurrency, retryable-vs-terminal error taxonomy, shared-key state mutation, fail-loud-on-bad-input.)
- **COVERAGE gap** — a genuinely new seam class preflight's flat list doesn't name. **Fix = add the class** (flat, generalized, not the instance).
- **OVERFIT** — instance-specific, won't generalize. **Reject** — do not add a one-off check (per `feedback_preflight_self_improve`: fold GENERALIZABLE, reject overfit).
- **UNPREVENTABLE-LOCALLY** — needs a capability the local pass can't have (e.g. calling a real external system CI also can't). **Acceptable** — this is exactly codex's out-of-band job; note it, don't force a local check that can't run.

**Also self-audit the fix-verification gap:** if an EARLIER local reviewer flagged the right AREA but the fix was incomplete (e.g. RND-2843: the adversarial reviewer's `W2` double-forward fix caught the duplicate *receipt* via P2002 but not the duplicate *egress*, which CI codex then re-found as `P1-c`), the lesson is: **after fixing a finding, adversarially re-check that the fix closed the ACTUAL failure mode, not an adjacent symptom** — fold that into the re-review step.

**At autodrive completion (post-merge)**, emit a **Preflight Improvement Proposal**: aggregate the run's retrospective rows into concrete, generalizable edits to the `preflight` skill (new/《strengthened》Part-2 required enumerations, a new seam CLASS, or a mechanically-derived invariant). Then either apply them directly to `~/.claude/skills/preflight/SKILL.md` (when clearly generalizable and consistent with its existing structure — keep the seam-class list FLAT, prune don't pile) or surface them for the user to approve. If the run had **zero** preflight-misses, say so — a clean run is signal, not a prompt to invent checks. Never tune preflight toward a scored bug corpus (overfit); the proposal is append-generalized-lessons-only.

## Per-run report
At each phase boundary emit a 1-line status; at every HARD STOP, a structured pause with the decision needed. On completion: PR link, merge commit, Linear status, follow-ups, **and the Preflight Improvement Proposal (or "no preflight-misses this run")**.

## Merge-loop ops (cc-merge)
- A full-pipeline PR (spec docs + tests + impl) usually trips the **oversize policy-check** → proactively add the `oversize-approved` label + a one-line rationale (most of the bulk is tests + spec docs).
- CI flakes seen on RND-2744: `claude-domain-expert` can hit **`max_turns`** on a large diff (a re-run / next push usually clears it — it's not a finding); soft lanes (`API integration lane (soft)`) failing on infra (CI Postgres setup dying) are **non-blocking**. Don't treat either as a real blocker — verify the failure reason first.
- Re-check reviewer threads against the **HEAD SHA at merge time** (bots re-review each push; a P2 can downgrade to P3, or a new one can appear). `mergeable=MERGEABLE / state=CLEAN` is the green light.

## Delegates to
`cc-prepare-ticket`, `cc-spec-phase`, `cc-build-phase`, `cc-merge` (single source of truth — update those, not this skill, for SDLC mechanics). This skill owns only: tier classification, the autonomous posture, the stop-gates, and the cross-cutting principles.
