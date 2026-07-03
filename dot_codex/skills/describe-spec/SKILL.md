---
name: describe-spec
description: Summarize a spec package as a cognitive-friendly in-conversation explanation. Use when the user asks to describe-spec, summarize a spec, load a spec mental model, or explain docs/specs/discussions/plans/tasks without implementation detail.
---

# describe-spec

Read a spec package and produce a concise mental-model summary in the conversation. Do not write a file.

## Input Resolution

The user may provide a spec directory, a spec file, a slug, or no explicit path.

1. If a path is provided, resolve it relative to the current working directory.
2. If the path is a file, use its parent directory as the spec package.
3. If a slug is provided, search likely spec roots:
   - `docs/**/<slug>/`
   - `docs/**/*<slug>*/`
   - `.specify/specs/**/<slug>/`
4. If no path is provided, infer from the current branch name:
   - Prefer ticket-like tokens such as `RND-1234`, `MOB-1234`, or numeric issue ids.
   - Then try branch slug tokens against `docs/**` and `.specify/specs/**`.
5. If multiple plausible packages exist, list the candidates with paths and ask the user to choose.
6. If none exist, say that no matching spec package was found and include the searched roots.

Prefer `rg --files` and `find` with bounded depth over broad recursive scans.

## What To Read

Read the package documents in this order, accepting singular and plural names:

1. `discussion.md` or `discussions.md`
2. `spec.md`
3. `plan.md` or `plans.md`
4. `tasks.md`

Skip missing files. If the package contains only a single spec/plan file, read that file.

## Output

Write in the same language the user used. The output is one conversation message, not a document.

Structure:

1. Start with a 1-2 sentence anchor: what this spec does, why it exists, and the core approach.
2. Continue as prose-first narrative covering:
   - current problem/state
   - chosen decision and rationale
   - key implementation/data/UX structure
   - explicit non-goals or deferred scope
   - major risks, gates, or constraints
3. Use tables or numbered lists only when they materially clarify comparisons or ordered rollout.

Rules:

- Do not reproduce full acceptance criteria, task checklists, or file-change inventories.
- Mention where details live, for example `plans.md` for AC or `tasks.md` for execution steps.
- Explain why rejected options were rejected when the docs record that rationale.
- Keep the summary under 800 words; 300-500 words is ideal for ordinary specs.
- Do not use markdown section headers unless the user explicitly asks for a structured report.
