---
name: autodrive
description: Autonomous CrossCheck SDLC driver for one well-understood issue. Use when the user says autodrive/self-drive or explicitly authorizes end-to-end delivery. First assess driveability, calibrate trivial/standard/high rigor, use native preflight when available or an explicit composed fallback, and continue through PR and merge under umbrella approval, pausing only at migration, production, security, core-goal drift, material implementation pivot, new or changed product-decision, or repeated-failure gates.
---

# Autodrive

Drive one authorized issue end-to-end without phase babysitting. Reuse canonical `cc-*` mechanics where useful, but preserve this skill's autonomous posture, tier calibration, and hard-gate contract. Autonomy means continuing through routine phase transitions and approvals until a real human decision is required.

## Entry and authority

Require one issue reference or an unambiguous task already agreed for delivery, plus a current-turn `autodrive`/self-drive go. That invocation is umbrella authorization through PR and merge; do not ask again at routine phase boundaries.

Do not infer autodrive from a request that only asks to investigate, plan, or implement. Re-evaluate admission whenever evidence materially changes a premise.

## Phase -1: assess driveability

Inspect the issue and repository read-only before substantive mutation. Determine:

- `goal`: one agreed primary outcome;
- `successEvidence`: how completion can be demonstrated;
- whether open questions are empirical and safely investigable or require a human product/authority decision;
- whether the work is one coherent issue;
- whether repository, tool, highest-capability model, and verification access are sufficient;
- the expected tier, scheduled hard gates, and safe autonomous extent.

Do not require a complete spec or zero uncertainty. Empirical, reversible unknowns may be investigated autonomously. Never hide a decision-dependent unknown as an assumption.

Record:

```text
goal: <primary outcome>
successEvidence: <test, runtime observation, or other evidence>
tier: trivial|standard|high
openChecks: <empirical questions the run may resolve>
scheduledHardGates: <known stop boundaries>
safeAutonomousExtent: <how far the run can proceed before them>
driveability: DRIVE|DRIVE_WITH_INVESTIGATION|HOLD
reason: <concise evidence-based reason>
```

- `DRIVE`: the goal and success evidence are clear; continue.
- `DRIVE_WITH_INVESTIGATION`: unresolved facts are safely investigable; investigate, update the record, and continue or HOLD.
- `HOLD`: the goal, product decision, authority, access, or verification path is insufficient; request the smallest concrete input.

A known future hard gate does not by itself make the issue undriveable. Continue to its recorded boundary when safe. HOLD only when the gate applies before useful safe work can proceed.

## Classify rigor

Choose a default tier from the actual blast radius. Accept `--tier=trivial|standard|high` as an explicit user override; report any mismatch between the requested tier and observed risk. A tier changes rigor and document depth, never the invariant hard gates below.

- **trivial** — a few local lines, config, typo, or mechanical change; no meaningful behavior, schema, shared core, tenant/security boundary, or infrastructure impact.
- **standard** — a bounded feature or bug fix with a clear goal and approach; no migration, shared durability core, tenant/security boundary, or production infrastructure change.
- **high** — migration/data-touching work, auth/tenancy/security, queue/worker or snapshot durability core, shared infrastructure, CDK/IaC, destructive behavior, or production-facing operations.

For mixed work, apply the highest relevant rigor to each change area rather than flattening the whole issue to the cheapest path.

## Right-sized pipeline

| Phase | trivial | standard | high |
|---|---|---|---|
| Prepare worktree/branch | `cc-prepare-ticket` | `cc-prepare-ticket` | `cc-prepare-ticket` |
| Ground in code and real evidence | focused | focused | broad + risk inventory |
| Phase 0 | skip when truly mechanical | light contract recorded before implementation: written goal + explicit ACs + verification plan; full spec package only when risk or repository policy requires it | full discussion → spec → plan → tasks + multi-reviewer audit |
| Build | direct, tested edit | direct tested implementation after the light contract when repository policy permits; use `cc-build-phase` mechanics when useful | full `cc-build-phase` |
| Post-build adversarial review | quick independent check | one fix → re-review loop | full bounded parallel review |
| **Preflight before first push/PR** | **mandatory, lightweight** | **mandatory** | **mandatory + full seam review** |
| Runtime verification | only if behavior changed | real path when feasible | real path/prod-shaped evidence when safely feasible |
| PR, active review, merge | current repository policy + `cc-pr-review` + `cc-merge` | same | same |

Autodrive owns the decision to continue between these phases. Canonical skills supply current commands, formats, reviewer mechanics, CI interpretation, and merge mechanics; their routine approval pauses do not replace the umbrella authorization. The pre-PR gate is mandatory in every run and resolves to native or composed mode below.

## Decision checks

Run the following checks during Phase 0 review, after implementation, and whenever new evidence appears:

- `coreGoalDrift`: did the work move away from the agreed primary outcome or drop an essential AC?
- `implementationPivot`: did the approved technical approach become materially invalid, requiring a different architecture, data/operational contract, rollout shape, or risk model? Minor code-level adjustment within the approach is not a pivot.
- `productDecisionRequired`: did the work expose a new choice or require changing an existing choice about user-visible behavior, UX, scope, defaults, compatibility, rollout promise, or accepted product risk?

These are independent. A new product decision may still support the core goal and require no implementation pivot; it is still a hard gate. An implementation pivot may preserve the product decision and core goal; it is still a hard gate.

## Hard stops

Pause, report the evidence, and ask for the smallest concrete decision when any condition holds:

1. **Migration** — before applying a schema/data migration anywhere real, or before merging when deploy will auto-apply it. Authoring and committing reviewed migration files may proceed.
2. **Production** — before any production write, deploy, destructive operation, IAM/secret change, or action that can affect real customers/data.
3. **Security** — when the change adds or changes authentication, authorization, tenant isolation, secret handling, public exposure, privileged data access, or accepts a security tradeoff.
4. **Core-goal drift** — `coreGoalDrift=yes`.
5. **Material implementation pivot** — `implementationPivot=yes`.
6. **Product decision** — `productDecisionRequired=yes`, including adding or changing a previously unapproved product choice.
7. **Repeated failure** — the bounded build, verification, or review loop cannot reach PASS, or the required high-capability implementation/evaluation model is unavailable.
8. Any additional human gate explicitly written into the governing issue/spec.

Everything else remains autonomous. A user tier override never silently clears a hard gate; surface the gate and let the user decide with the actual risk visible.

## Cross-cutting rules

- Measure claims against the real path when safe; prefer local or staging read-only evidence.
- Exercise changed runtime behavior when feasible, but never turn a production side effect into an implicit verification step.
- Fail loudly on missing data, unavailable contracts, and unverified assumptions.
- Use independent review; same-context self-review does not count.
- Reach local green on the whole candidate before the first push. After review fixes, follow `cc-merge`'s exact-tree pre-push gate.
- Fix real CRITICAL/HIGH correctness or safety findings. Reject speculative or fragile NIT-level machinery with a short rationale.
- Commit fixes as new reviewable commits; do not amend or force-push unless the user explicitly requests an allowed exception.

## Resolve the mandatory pre-PR gate

Discover skills through the runtime's available-skill registry or equivalent capability surface. Do not infer availability from a Claude-, Codex-, or user-home filesystem path.

1. If `preflight` is available, invoke it against the exact candidate and record `preflightMode: native`.
2. Otherwise record `preflightMode: composed` and run all of:
   - identify the exact base/head SHA or tree OID and changed files;
   - derive and run applicable local CI-equivalent checks from current `AGENTS.md` and `.github/workflows/`;
   - run `review` with an independent capable reviewer over the exact candidate;
   - apply `cc-spec-verify`'s AC mapping when a spec governs the change;
   - report unverified evidence and `coreGoalDrift`, `implementationPivot`, and `productDecisionRequired` independently.
3. Never treat `preflight` absence as permission to skip the gate or infer PASS. State any coverage degradation and assign every `UNVERIFIED` item to a later gate.

The composed report must include candidate identity, commands and results, reviewer independence, findings, all three decision verdicts, unverified evidence, and PASS/FAIL. Any candidate change invalidates it. `cc-pr-review` and `cc-merge` are later surfaces; neither alone replaces the pre-PR gate.

## Feedback loop

For every out-of-band HIGH/P1+ finding that preflight missed, record:

```text
finding -> seam class -> already in scope? -> EXECUTION|COVERAGE|OVERFIT|UNPREVENTABLE -> correction
```

When native `preflight` runs, apply its self-improvement routine in `../preflight/references/self-improvement.md` when available. In composed mode, use the same miss classification and surface a general correction proposal without claiming the missing skill was updated. Preserve the personal-skill self-improvement path: apply only premise-conformant general corrections, otherwise request approval. If there were no misses, report that without inventing work.

## Completion report

Report the PR, merge commit, Linear state, runtime/preflight evidence, degraded or unverified gates, follow-ups, and the preflight improvement result. If stopped, report the exact resume point and the single decision required.

## Ownership

Autodrive owns driveability admission, umbrella authority, autonomous continuation, tier calibration, mandatory pre-PR gate resolution, decision checks, hard-stop aggregation, and progress reporting. Canonical `cc-*` skills own reusable mechanics; they do not redefine autodrive's autonomy contract.
