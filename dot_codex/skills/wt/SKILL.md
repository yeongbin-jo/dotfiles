---
name: wt
description: Switch Codex work context to an already-existing git worktree by path or shorthand. Use when the user says wt, worktree 이동, 워크트리 이동, switch worktree, move to a worktree, or asks to continue work in a specific existing worktree. This skill never creates, deletes, or removes worktrees.
---

# WT - Use An Existing Worktree

Switch the working context to an already-existing git worktree. In Codex there is no Claude-style `EnterWorktree` session tool, so the practical contract is:

- resolve the target worktree once
- verify it is a registered git worktree
- use that absolute path as `workdir` for subsequent tool calls
- if running inside tmux, publish the logical worktree to tmux because tmux cannot infer Codex's per-tool `workdir`
- state the active worktree path to the user

Do not pretend that `cd` permanently changed the session. A plain shell `cd` only affects that one command.

## Why tmux does not update automatically

The managed tmux config normally names windows from `#{pane_current_path}`. Codex `exec_command.workdir`
changes only the subprocess cwd for that one tool call; it does not change the interactive pane's
shell cwd, so `#{pane_current_path}` remains the directory where Codex was launched. Therefore tmux
cannot infer the Codex logical worktree unless the worktree switch publishes it explicitly.

## Workflow

1. List worktrees from the current repository:

```bash
git worktree list
```

2. Resolve the target.

- Absolute path: use it as-is.
- Shorthand such as `feature-x`, `issue-1234`, or `my-project-worktrees/feature-x`: match against worktree path basenames and branch names from `git worktree list`.
- No argument: show the worktree list and ask which one.
- No match or ambiguous match: show candidates and stop. Never guess.

3. Validate the resolved path.

The target must:

- appear in `git worktree list`
- exist on disk
- be inside the same repository's worktree set

4. Adopt it for all following operations.

For every subsequent `exec_command`, `apply_patch` target path, `view_image`, or file reference, use the resolved worktree path explicitly. Prefer absolute file paths for patches and final links.

5. If running inside tmux, publish the logical worktree to tmux.

Use the branch name when available; otherwise use the worktree directory basename:

```bash
name="$(git -C "$WORKTREE" branch --show-current 2>/dev/null)"
[ -n "$name" ] || name="$(basename "$WORKTREE")"
[ -n "$TMUX" ] && codex-tmux-workdir-set "$WORKTREE" "$name"
```

This writes pane-scoped tmux options (`@codex_workdir`, `@codex_worktree_name`) and renames the
current window as a display hint. It does not change the Codex session cwd.

6. Verify and report:

```bash
pwd
git branch --show-current
git status --short --branch
tmux display-message -p '#W #{pane_current_path}' 2>/dev/null || true
tmux display-message -p '#{@codex_worktree_name} #{@codex_workdir}' 2>/dev/null || true
```

Report one concise line:

```text
Now using <path> (branch <branch>, clean|N dirty files).
```

## If Already In Another Worktree

There is no special exit step in Codex. Just resolve the new target and switch your internal active `workdir` to that absolute path for future tool calls. Do not remove either worktree.

## Do Not

- Do not create a worktree with `git worktree add`.
- Do not delete, prune, remove, or force-clean worktrees.
- Do not run destructive commands such as `git reset --hard` or `git checkout --` unless the user explicitly asks.
- Do not fall back to `cd` and report success as if future tool calls will inherit it.
- Do not switch to an unregistered directory just because it exists.

## Notes For Codex

If the user's phrase is ambiguous between "move to a worktree" and "create a new worktree", this skill covers only moving to an existing worktree. Ask or use the project workflow for worktree creation.
