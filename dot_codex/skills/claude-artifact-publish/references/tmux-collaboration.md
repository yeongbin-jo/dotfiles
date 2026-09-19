# Tmux collaboration with a Claude Artifact session

Use this route only when the user's current task explicitly names an already-running tmux target and
asks Codex to collaborate with that target. The target should be `session:window.pane`, or
`session:window` when that window has exactly one pane. A target from an unrelated earlier task, a
session Codex discovers on its own, or a generic request to use Claude is not authorization. This
permission is target-specific and does not extend to another pane or session.

The purpose is to reuse that exact Claude session's native `Artifact` capability when the current
Codex environment cannot create or update the Artifact directly. Authorization to collaborate and
the words `publish` / `발행` authorize account save, not public sharing. Public sharing requires a
separate explicit request for public/share/anonymous access.

## Establish the handoff safely

1. Resolve only the named target with `tmux list-windows` and `tmux list-panes`. If a named window
   has multiple panes and the user did not name one, stop and ask. Never enumerate tmux sessions to
   choose a collaborator proactively.
2. Capture only enough recent output to identify the process and current state. Do not read or
   preserve unrelated scrollback. Do not interrupt unrelated work or guess a target from a similar
   name.
3. Confirm the pane is an idle Claude prompt, or that its current task can safely be stopped under
   the user's instruction. A running spinner is not an idle prompt.
4. Keep the artifact contract in a dedicated temporary handoff file outside the repository. Include
   the source material, invariants, visibility and data boundary, target experience, and acceptance
   checks.
   Remove credentials and any material outside the selected visibility boundary. The handoff file's
   own path may appear in the private delegation message but must
   not appear in the Artifact.
5. Re-check that the pane is still idle immediately before input. Use literal tmux input
   (`tmux send-keys -l`) for the short delegation message and send Enter separately. Do not embed a
   long multiline contract in shell quoting when a file can carry it safely.
6. Do not change the Claude session's model, permission mode, MCP configuration, or other settings.
   Do not approve an unexpected permission prompt on the user's behalf.

## Delegate the outcome, not the browser procedure

Tell the Claude session to read the handoff file and use its **native Artifact tool** to create or
update, save, and inspect the Artifact. State whether the mode is create or update and that private
account save is the default. Ask it to use a native public-sharing action only when the user
explicitly requested public sharing. Do not forward
Chrome setup, Cloudflare handling, DOM instructions, or this skill's browser runbook: the delegated
Claude session chooses its own native tool calls.

A native tool's `Published` label may mean the Artifact was saved to the authenticated account while
remaining private. That is success for private/account-only delivery. Require a visibility read-back
and do not equate it with anonymous web visibility. If public sharing was explicitly requested but
the tool has no `Publish to web` mutation, return the exact private Artifact link and report that the
optional public-sharing gate remains; do not create a replacement Artifact.

Only one generation may be active. Do not start a local/browser candidate while the delegated
session is working. Monitor with `tmux capture-pane`; visible tool activity or changing status is
progress. Apply the normal three-minute stall rule before stopping, then allow at most one retry in
the same Claude session with the same contract.

If the Claude session requests a product decision not fixed by the contract, relay it to the user.
Do not invent the decision merely to keep the delegated run moving.

## Accept and verify the result

Require the Claude session to report:

- the exact complete saved Artifact URL;
- create/update mode and, for an update, whether identity and URL were preserved;
- actual visibility (private/account-only or public);
- content and interaction checks performed;
- any verification limitation or failed gate.

Independently inspect the saved Artifact through an authorized surface when possible. When public
sharing was explicitly requested, also inspect the public URL without authentication. If a
Cloudflare or authentication boundary prevents the requested check, do not restart generation or
claim it passed; preserve the delegate's evidence and report the boundary.

After the requested verification gate is complete or the invocation is explicitly stopped, remove only temporary
files created for this invocation. Leave the user's tmux session, Claude history, and Artifact
intact. Do not reuse the named target for a later unrelated task without fresh user direction.
