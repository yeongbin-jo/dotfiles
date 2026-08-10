---
name: handoff
description: >-
  Write a follow-up-session handoff so in-progress, multi-step work resumes cleanly in a
  fresh session (or by another agent/person) without re-deriving anything. Use when the user
  says "handoff", "핸드오프", "write a handoff", "후속세션 핸드오프", "hand this off",
  "이어서 할 수 있게 정리", "잘라도 되게 정리", or when a long/maxed session must stop mid-task
  and the remaining work is real. Produces a concise, anchored, resumable artifact + presents
  it. NOT for finished work (nothing to resume) or a trivial one-step remainder.
---

# handoff — resumable follow-up-session handoff

Capture the MINIMUM that lets the next session take one look and continue — anchors, the next
action, the gates, and the decisions already settled — not a transcript. Optimize for
"resume in one read," not completeness.

## When to reach for it
- A multi-step task is mid-flight and the session is ending / maxed / blocked, AND the
  remainder is non-trivial (more than one obvious step).
- The user asks to hand off, or asks that work be resumable if the session is cut.
- Cross-repo / hard-gated work that will span sessions (a deploy, a prod-write, a review cycle,
  a decision the user must make).

Skip it when the work is done, or the remainder is a single self-evident step.

## The artifact — 5 parts, in this order (keep each tight)
1. **State now / resume point.** The single most important thing: WHERE it stopped and the ONE
   next action. Include every ANCHOR needed to act — PR #/URL, commit SHA, branch, worktree
   path, ticket id, CI/check status at handoff time. Never "the PR" — always the number+link.
2. **Remaining steps, ordered.** Each step = the concrete command/file/endpoint + its
   verification (how you know it worked). Mark every **HARD GATE** explicitly (prod-write,
   deploy, schema migration apply, IAM/secrets, cross-repo, or a decision only the user can
   make) — the next session must pause there.
3. **Locked decisions — do NOT re-litigate.** What's already settled (design, approach, scope)
   and WHY in one line each, so the next session doesn't redo a resolved debate. If a decision
   was reached by an audit/review, name it.
4. **Key context / refs.** File paths, ids, fixed values (uuids, account/tenant ids), where
   secrets/tokens live (name the secret, never paste it), env/setup gotchas (how to run the
   tests, which venv/worktree), and the non-obvious "why" behind any surprising choice.
5. **Blow-up risks / unknowns to establish first.** What could derail the resume, and the thing
   that must be figured out before the risky step (e.g. "confirm repo X's deploy trigger before
   merging"). This is what turns a bad surprise into a planned first move.

## Where to write it (travels with the work > auto-loaded)
Prefer a real file over only chat — chat may not survive the session. Priority order:

1. **A repo-relative file committed with the work** — `HANDOFF.md`, or `docs/handoff/<task>.md`
   in repos that keep planning docs under `docs/`. This is the default. It travels with the
   branch/PR, it is visible in review, and it dies with the branch when the work merges.
   Name it by **that repo's own ticket convention** (issue number, branch slug) — never import a
   ticket-id shape from another project.
2. **Else** the agent's notes/scratch that persists across sessions.

**Persistent memory is for a POINTER, not the handoff body.** If the project has an auto-memory
dir and the work will really span sessions, add a one-line index entry pointing at the file
(`- [<task> 핸드오프](path) — resume from <one line>`). Do not paste the handoff into memory:
memory is one-fact-per-file and is loaded into *every* future session, so a multi-fact,
short-lived doc there is context you pay for on every unrelated task — and it reads as current
long after it stops being true.

Then **always present the handoff inline** too (the user asked to see it).

## Close it out when the work lands
A stale handoff is worse than none — the next session reads it as the current state and acts on
a resume point that no longer exists. So when the work completes (or is abandoned):
- delete the handoff file, and
- remove its pointer line from the memory index if you added one.

If a handoff you find is already satisfied, say so and delete it rather than leaving it to rot.
Anything in it worth keeping permanently is a *separate* durable note (a decision, a gotcha) —
promote that on its own terms, don't keep the handoff alive as its container.

## Style
- Scannable: short sections, tables for step lists / status, bold the gates and the ONE next
  action. A tired reader should get the resume point in ~10 seconds.
- Absolute over relative: real dates (not "yesterday"), full ids/links, absolute paths.
- Honest: say what's UNverified or assumed; flag the risky unknown rather than hiding it.
- Concise: it's a springboard, not a log. If it reads like a diary, cut it.

## After writing
Report: the handoff file path (+ index line if a memory), and a one-line "resume from here"
pointer. If the user asked to also stop, this is the clean stopping point.
