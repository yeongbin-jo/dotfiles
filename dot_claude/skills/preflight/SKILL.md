---
name: preflight
description: CrossCheck pre-PR gate that runs the current local CI-equivalent checks and an independent seam review against the exact candidate tree. Use when the user asks for preflight, before the first push or PR for a non-trivial change, and always when autodrive reaches its pre-PR phase. Local green is necessary but never replaces CI or live rollout gates.
---

# Preflight

Catch deterministic failures and probeable contract gaps before CI. Produce evidence for one exact tree; do not treat a remembered command list, a same-context self-review, or a mocked external seam as proof.

## Entry

1. Resolve the repository, primary spec, base SHA, candidate SHA or tree OID, and changed files.
   The candidate is the tree the CI gate actually evaluates. Where that gate builds a merge of head
   into base (the GitHub `pull_request` default), resolve and check THAT tree: a base that advanced
   since the branch point can break the candidate through code neither side changed alone. If the
   merge tree cannot be checked locally, record the base delta as `UNVERIFIED` with CI as its owner
   rather than reporting PASS on head alone.
2. Read the current `AGENTS.md`, the primary spec, and the actual workflows under `.github/workflows/`.
3. Stop if the candidate is not identifiable. Never review a moving or ambiguous diff.

Under autodrive, invoke preflight for every tier. Right-size its depth for trivial changes, but do not omit the gate or its exact-candidate evidence. For typo/prose-only changes, run only applicable deterministic checks. For behavior, infrastructure, workflow, integration, validator, or public-surface changes, run the independent seam review too.

## 1. Run the deterministic command set

Derive commands from the current repository and CI workflows; do not preserve stale copies in this skill. For the present CrossCheck PR Build lane, the core mirror is:

```sh
pnpm --filter @vb-crosscheck/database generate
pnpm build
pnpm test
node --test scripts/policy-check-base-policy.test.mjs
```

Then run only the diff-triggered checks whose source of truth exists in the repository:

- affected typecheck, integration, or E2E tests required by `AGENTS.md` or the spec;
- changed-file lint as an additional local signal while repo-wide lint is not a CI gate;
- bundle rebuild and byte-freshness tests for committed bundles;
- leak/denylist checks for every touched public source and generated artifact;
- version/manifest agreement and generated-wrapper freshness;
- safe live-contract probes when the changed contract can be exercised read-only.

- **the SHIPPED tree, whenever it differs from the tree you just checked.** Every check above compiles the full
  checkout; what deploys may be a *transformed* tree — pruned by `.dockerignore`, narrowed by a
  `files[]`/`include`/`exclude` list, or dependency-stripped by a `deploy`/prune step. A green check on the
  full tree is NOT evidence about the shipped one. Trigger: the diff adds, moves, or renames a file that
  another file imports; changes an import; or edits any manifest that enumerates paths individually. Then
  build the shipped artifact far enough to compile it (e.g. `docker build --target <build-stage>`) and record
  the result. Cost is minutes; the failure mode is a post-merge red `main` that no PR check can see, because
  the pruned context is first exercised on the push to the default branch.

If a required check cannot run locally, record `UNVERIFIED` with the exact reason. Never infer PASS.

Before naming a later gate as the owner of an `UNVERIFIED` item, verify that gate actually exists and will run — read the workflow/lane rather than assuming a conventional one. An owner that does not exist is a silent gap, not a deferral.

When a local failure is attributed to environment or flake rather than the candidate, prove it against the base tree (a clean checkout of the merge base, sampled enough times to compare rates) instead of reasoning from which files the diff touched.

## 2. Run an independent seam review

Use a capable reviewer that did not author the candidate, preferably a different model/vendor and always a fresh context. Give it the exact diff, spec/ACs, and repository rules. Ask it to reason over the whole behavior before enumerating specific seams.

The reviewer must return evidence, not only a verdict:

- AC-by-AC implementation status;
- an assumption ledger with a concrete file, query, command, or live read-only probe for each external claim;
- every triggered seam class and its enumeration;
- candidate findings followed by a separate refutation/filter pass;
- explicit `coreGoalDrift`, `implementationPivot`, and `productDecisionRequired` verdicts when a spec or agreed goal governs the change. Keep them independent: preserving the goal does not clear a product-decision or implementation-pivot finding.

Read [references/seam-classes.md](references/seam-classes.md) when the diff touches an external contract, queue/worker, durable transition, auth/tenancy, CI workflow, generated validator, or multi-layer projection. Do not hand the reviewer a narrow pre-baked list as its entire framing.

Triage rule: a reported contradiction between the spec/AC and the implementation can never be filed as a suggestion or wording nit. Either the code is wrong or the AC is wrong; resolve which, change that one, record the rationale, and pin the resulting property with a test. Deferring the contradiction leaves the artifact asserting something the code does not do.

## 3. Preserve seam integrity

- Prove existence claims against the canonical file or registry.
- Execute derived behavior and inspect its output; reading the declaration is insufficient.
- Do not substitute a fixture, mock, or hand-fed payload at the exact acquisition seam production uses.
- Prefer local or staging read-only probes. Production writes, IAM/secrets changes, destructive operations, and real deploys remain explicit hard gates.
- If a safe real probe is impossible, record the gap as `UNVERIFIED` for the appropriate later gate.

## 4. Write the artifact

Write the detailed report under `.context/preflight/<spec-or-branch>/report.md` when the repository supports `.context/`; otherwise present the same structure in the conversation. Include:

```text
candidate: <base/head SHA or tree OID>
deterministic_checks: <command, exit status, evidence>
unverified_checks: <check, reason, owning later gate>
reviewer_independence: <model/context relationship>
assumption_ledger: <claim -> source/probe -> result>
triggered_seams: <class -> enumeration -> result>
findings: <severity, disposition, verification>
coreGoalDrift: yes|no|n/a
implementationPivot: yes|no|n/a
productDecisionRequired: yes|no|n/a
verdict: PASS|FAIL
```

PASS requires every applicable deterministic check to pass, no unresolved blocker, and every required unverified item to have an explicit later gate. Any candidate change invalidates the artifact and requires a focused rerun against the new tree.

## Feedback loop

If CI, an app reviewer, or a human later finds a HIGH/P1+ issue that this preflight missed, read and apply [references/self-improvement.md](references/self-improvement.md). Preserve the self-improvement path, but reject instance-specific checklist growth and false claims of coverage.

## Exit

Report the candidate identity, PASS/FAIL, commands run, independent-review evidence, unverified gates, and the next authorized action. Do not push, open a PR, or merge unless the surrounding workflow separately authorizes it.
