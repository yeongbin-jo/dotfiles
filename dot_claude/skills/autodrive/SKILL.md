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
| Phase 0 | skip **only** for a typo/formatting change, the one Article 1 exception that actually waives a spec — never a bespoke skip | autodrive's own Phase 0 below: `spec.md` + `plan.md` + one independent Codex researcher | same, plus `discussion.md`/`tasks.md` when the criteria for them are met |
| Build | direct, tested edit | direct tested implementation after Phase 0; use `cc-build-phase` mechanics when useful | `cc-build-phase` mechanics under autodrive's gates |
| Post-build adversarial review | folded into preflight | folded into preflight | folded into preflight's seam review |
| **Preflight before first push/PR** | **mandatory, lightweight** | **mandatory** | **mandatory + full seam review** |
| Runtime verification | only if behavior changed | real path when feasible | real path/prod-shaped evidence when safely feasible |
| PR, active review, merge | current repository policy + `cc-pr-review` + `cc-merge` | same | same |

Autodrive owns the decision to continue between these phases. Canonical skills supply current commands, formats, reviewer mechanics, CI interpretation, and merge mechanics; their routine approval pauses do not replace the umbrella authorization. Phase 0 is no longer among the things they supply — see the next section. The pre-PR gate is mandatory in every run and resolves to native or composed mode below.

## Phase 0 is autodrive's own (user directive, 2026-07-30)

Autodrive does not delegate Phase 0 to the `cc-spec-phase` family. Author the documents directly under this contract.

**The four forms, nothing else.** `spec.md` and `plan.md` are the required core; `discussion.md` only for a real decision between two or more non-trivial options; `tasks.md` only to decompose an oversized spec. The required core is required at **every** tier: a tier is not a licence to substitute a lighter artifact for `spec.md` + `plan.md`, because "no code without a specification" is the constitution's rule. Read Article 1's exception list precisely — only **one** of its four entries waives the spec. Typo fixes and formatting changes need none. An emergency hotfix still needs one, written retroactively within 24 hours. An IaC change swaps the *traceability reference* (a Linear ticket instead of a spec ID) and still needs the documents. A meta-spec changes only the directory *slug* — Article 9 requires `spec.md` + `plan.md` for a constitution amendment, as this very exception's own spec demonstrates. So trivial-tier work skips Phase 0 only when it is genuinely a typo or formatting change. Keep the repository's directory naming and the mermaid convention, because CI and human readers depend on them. Drop every other ceremony the delegate skills assert as binding: per-phase approval locks, staged document status transitions, the multi-reviewer audit panel and its oracle framings, and the Linear-update *gate* — still update Linear, just not as a blocking step.

**One independent Codex researcher replaces the audit panel.** Before declaring Phase 0 done, hand the authored documents and the branch identity to a single `codex exec` researcher (stdin from `/dev/null`) briefed to research the load-bearing claims against the actual tree and to disagree. Reconcile every disagreement on evidence, and record the reconciliation where the claim lives. One researcher iterated to agreement — not a panel, not a vote, and never a summary standing in for its report: read its findings site by site.

**Ground every current-state claim before authoring it** — the directive below still binds, and this is the exact class the researcher exists to catch.

**Run the three decision checks at every authoring boundary** — after `discussion.md` is decided (when authored), after `spec.md`, after `plan.md`, and after the researcher reconciliation — recording all three verdicts each time. Any `yes` triggers hard stop 4, 5, or 6.

## Review converges on preflight (user directive, 2026-07-30)

`preflight` is the review gate. Autodrive runs no separate post-build adversarial review round, and repository review process — the `CLAUDE.md` SDLC gate table, `cc-pr-review`'s reviewer roster, `cc-merge`'s confidence ritual — supplies mechanics and CI interpretation only, never an additional blocking gate.

Two limits on that convergence, both measured rather than assumed:

- **`preflight` itself stays byte-unchanged.** It is user-scope, so no branch can edit the skill that reviews it. Change it only through its own self-improvement routine. (No per-gate defect count is recorded for RND-3212, so do not repeat the claims that preflight caught *most* of that run's defects, or that it ran a specific number of rounds there — both were unanchored and are retracted.)
- **The real gate is two-stage, and the second stage is not ours to remove.** `preflight` is the local gate autodrive owns; the Codex app review on the PR is the second gate, firing automatically on GitHub. On RND-3212's PR B it ran three sequential passes producing P1-class findings in the first two (`de97f5412`, `d0005ba04`) — findings that could not exist until a PR did. Read it, fix real findings under the Ralph cap, and never report a run as reviewed on preflight alone while that surface is still pending. Be precise about what that evidence is: one reviewer iterating on an open PR, not a second independent opinion. The plural evidence sits *inside* preflight — PR A (`c58fc48c2`) records two independent seam reviews each finding a real defect, alongside its preflight PASS against the merge tree.

**All repository policy still binds. What the convergence changes is who catches it — so never read "CI will catch it" into a rule below.** Verified against `.github/workflows/` on 2026-07-30, and re-verify rather than trusting this list: CI hard-fails on the `RND-XXXX:` title prefix (label-exempt via `no-spec`/`typo`/`chore`) and on a trailing `[spec/<id>]` tag's *shape* when one is present — it never requires the tag; on primary-lineage declaration; on multiple primary lineages without `multi-lineage-approved`; on the implementation-size budget without `oversize-approved`; on the forbidden-artifact list; on generated harness-wrapper freshness when prompt/adapter paths change; and on build, unit tests and the policy regression test. Not exhaustive — several lanes are path-triggered.

CI does **not** validate commit messages (no validator exists anywhere in the workflows), does **not** fail an `RND` carrying no spec (warning only), does **not** run repo-wide lint (disabled while the baseline is dirty, so the anti-pattern table has no generic gate), does **not** prove a new endpoint filters by `workspaceId`, and enforces **no** hard stop. Those are owned by preflight, the independent review, and the hard stops themselves — migration and security are hard stops precisely because no lane proves them.

**Ralph loop override (user directive, 2026-07-26):** under autodrive the post-PR review-fix loop caps at **4 iterations**, overriding `cc-merge`'s default of 2. Iterations 3–4 follow the same discipline (evidence-based fixes only, full re-verification of the exact candidate, no squash, reply-and-resolve on the review surface). If the loop has not converged after 4, stop and escalate as the repeated-failure gate — never a 5th loop.

**What counts toward the cap (user directive, 2026-07-27):** the cap governs the **post-PR review-fix loop only** — fix rounds driven by the review surface on an open PR (app reviews, human reviewers, CI failures attributable to the candidate). **Pre-PR gates do NOT count**, however many rounds they take: Phase 1 evaluation, `preflight`, and any preflight re-review are gates whose whole purpose is to find defects before a PR exists, and each is a *different* gate firing rather than the same loop failing to converge. Counting them conflates a working pipeline with a stuck one and forces a spurious escalation just as findings are shrinking.

When reporting loop state, say which surface each round came from. If iterations are accruing, check convergence before invoking the cap: severity should be strictly decreasing and no earlier finding should have reopened. A cap hit by *count* while severity is monotone decreasing is not the repeated-failure condition — report that distinction and let the user decide rather than escalating mechanically.

## Model delegation policy

Standing role→model assignments for every autodrive run. Autodrive owns this policy; canonical `cc-*` skills and repository agent wrappers supply mechanics only and never relax it. It tightens — never replaces — the repository's Phase 1 Model Quality Rule (no mini/small models anywhere).

- **Drive = the main-session orchestrator model** (currently Fable): driveability, Phase 0 authoring, gate decisions, preflight orchestration, PR, and merge. Trivial-tier edits may be implemented directly in the orchestrator context.
- **Implementation (standard/high tier) = Opus-class agent.** All delegated implementation code is written by an opus-model agent — the `generator` agent when `cc-build-phase` runs, or an explicit `model: opus` subagent on the lighter standard-tier path. Do not use `--direct` and do not write standard+ product code in the orchestrator context.
- **Planner = orchestrator-model subagent**: spawn with an explicit model override to the session's highest model, fresh context.
- **Evaluator = Codex.** Execute the canonical evaluator role prompt (`.agents/prompts/evaluator.md`) via `codex exec` (stdin from `/dev/null`) with the `.context/build/` file handoff, output to `evaluation.md`. Do not spawn a same-vendor evaluator agent. Retry a failed or zombie Codex run once.
- **Independent review = dual Codex + orchestrator model, inside preflight.** The preflight seam review runs both: `codex exec` AND a fresh-context orchestrator-model reviewer agent. There is no longer a separate post-build adversarial round to staff (2026-07-30).
- **Phase 0 research = one Codex researcher.** `codex exec`, fresh context, iterated to agreement. It replaces the retired multi-reviewer audit panel; do not staff a same-vendor auditor alongside it.
- **No silent substitution.** If an assigned model (opus implementation, Codex evaluation/review) is unavailable after retry, stop under hard stop 7. Never downgrade or reassign silently.

In a runtime where a specific engine is unreachable, preserve the structure — implementer outside the orchestrator context, evaluator cross-vendor from the implementer, dual independent review — or stop loudly; never collapse the roles into one context to keep momentum.

## Decision checks

Run the following checks during Phase 0 review, after implementation, and whenever new evidence appears:

- `coreGoalDrift`: did the work move away from the agreed primary outcome or drop an essential AC?
- `implementationPivot`: did the approved technical approach become materially invalid, requiring a different architecture, data/operational contract, rollout shape, or risk model? Minor code-level adjustment within the approach is not a pivot.
- `productDecisionRequired`: did the work expose a new choice or require changing an existing choice about user-visible behavior, UX, scope, defaults, compatibility, rollout promise, or accepted product risk?

These are independent. A new product decision may still support the core goal and require no implementation pivot; it is still a hard gate. An implementation pivot may preserve the product decision and core goal; it is still a hard gate.

**Skill precedence (user directive, 2026-07-26; Phase 0 delegation severed 2026-07-30):** when autodrive delegates to a canonical skill (`cc-build-phase`, `cc-pr-review`, `cc-merge` — the `cc-spec-phase` family is no longer delegated to at all), autodrive's judgment governs: its driveability admission, tier, decision checks, and hard stops take precedence over **any rule the delegate asserts as binding — continuation rules, self-declared "MANDATORY"/"non-skippable" gates, and required-step lists alike** (extended 2026-07-28: the earlier wording covered only "autonomous-continuation rules", which left a delegate's mandatory-review claims arguably outside the precedence). A delegate's "proceed on agent-team consensus" never overrides an autodrive hard stop, and a delegate cannot re-authorize work autodrive has paused. Precedence runs one way: autodrive may impose rigor a delegate does not require, and may decline a step the delegate calls mandatory when its own tier and hard gates are satisfied — never the reverse. Record any declined mandatory step and the reason in the completion report.

**Ground every current-state claim before authoring (user directive, 2026-07-26 — recurrence fix):** a prior gate record, benchmark, sibling spec, or completed ticket is PROVENANCE, never current state. Before writing any Phase 0 assertion about how the system behaves today, re-fetch the default branch and verify each load-bearing claim against that tree, carrying the citation (file:line, or the command and its output) into the document. Verify the MECHANISM, never the analogy — "the sibling change was inert, so mine is" is not evidence when the two act on different surfaces. Assertions about data availability (a column, key, or field exists) must be checked against the producer, not the consumer. This is the Phase 0 analogue of preflight's assumption ledger, moved earlier because the multi-reviewer audit catches these late: under project-autodrive a false premise does not merely cost a document revision, it shapes the next just-in-time issue and the pre-mortem built on it.

**Stage-boundary checks (user directive, 2026-07-26; retargeted 2026-07-30):** the three checks run at every Phase 0 authoring boundary as specified in `## Phase 0 is autodrive's own`. Researcher agreement satisfies Phase 0's review requirement but never substitutes for these checks.

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

- **Verify a project-scope skill before trusting it.** Project skills are repo-tracked and branch-supplied: the checkout in hand governs this run, including a branch that edits the skills themselves. Before relying on one, diff it against `origin/main` and report any difference rather than following it silently. Treat every capability it names — subagent type, slash command, script, file path — as absent until confirmed present in this runtime; a named-but-missing reviewer or gate is a silent gap, not a formality, so say so and degrade explicitly instead of reporting the step as done. Never bundle `.agents/skills/**` or `.agents/prompts/**` edits into a product-code PR; a skill change alters the rules of every agent working that tree, including the one reviewing that very PR.
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
