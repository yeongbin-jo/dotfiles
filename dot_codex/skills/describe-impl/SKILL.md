---
name: describe-impl
description: Summarize actual implementation changes from git diffs as a cognitive-friendly in-conversation explanation. Use when the user asks to describe-impl, explain what was implemented, summarize branch changes, compare implementation to a spec, or review shipped code at a high level.
---

# describe-impl

Read the actual code changes on the current branch and produce a concise implementation summary grounded in git state. Do not write a file.

## Input Resolution

The user may provide a commit range, base branch, spec directory, or no explicit argument.

1. If a commit range is provided, use it directly.
2. If a base branch is provided, diff `base...HEAD`.
3. If a spec path is provided, read it only for cross-reference after inspecting the diff.
4. If no argument is provided:
   - Use `origin/main...HEAD` when available.
   - If not available, use `main...HEAD`.
   - If the worktree has uncommitted changes, include them after the committed branch diff.
5. If the branch has no diff and no uncommitted changes, say so clearly.

Prefer current repository state over assumptions. Do not summarize planned work as implemented work.

## What To Inspect

Use bounded git commands first:

- `git status --short --branch`
- `git diff --stat <range>`
- `git log --oneline <base>..HEAD`
- `git diff --name-status <range>`
- `git diff <range> -- <key files>`

Read key files selectively:

- new files
- deleted files
- files with large diffs
- migrations and schema files
- API/model/store files
- tests that define behavior

If a matching spec exists, read only enough of `spec.md`, `plans.md`, or `tasks.md` to compare actual changes against stated scope and acceptance criteria.

## Output

Write in the same language the user used. The output is one conversation message, not a document.

Structure:

1. Start with a 1-2 sentence anchor: what changed, approximate file/change scope, and the net effect.
2. Continue as prose-first narrative covering:
   - what was added
   - what behavior changed
   - what was removed
   - migrations or data-shape changes, if any
   - tests or verification visible in the diff
   - spec deviations, if a spec was provided or inferred
3. Use tables or numbered lists only for direct before/after comparisons or ordered migration/deploy steps.

Rules:

- Ground every claim in the diff or the changed files.
- Do not repeat spec language as if it shipped.
- Do not list every changed file; group by purpose.
- Do not reproduce full diffs.
- Call out uncommitted changes separately from committed branch changes.
- Keep the summary under 800 words; 300-500 words is ideal for ordinary branches.
- Do not use markdown section headers unless the user explicitly asks for a structured report.
