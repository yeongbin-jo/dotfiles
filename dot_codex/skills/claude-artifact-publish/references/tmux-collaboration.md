# Tmux collaboration with a Claude Artifact session

Use this route only when the user's current task explicitly names an already-running tmux target and
asks Codex to collaborate with that target. The target should be `session:window.pane`, or
`session:window` when that window has exactly one pane. A target from an unrelated earlier task, a
session Codex discovers on its own, or a generic request to use Claude is not authorization. This
permission is target-specific and does not extend to another pane or session.

The purpose is to reuse that exact Claude session's native `Artifact` capability when the current
Codex environment cannot publish directly. Authorization to collaborate does not itself authorize
public sharing; the user must also have explicitly requested publication.

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
   the source material, invariants, public-data boundary, target experience, and acceptance checks.
   Remove credentials, customer data, internal IDs, and absolute paths from content intended for
   publication. The handoff file's own path may appear in the private delegation message but must
   not appear in the Artifact.
5. Re-check that the pane is still idle immediately before input. Use literal tmux input
   (`tmux send-keys -l`) for the short delegation message and send Enter separately. Do not embed a
   long multiline contract in shell quoting when a file can carry it safely.
6. Do not change the Claude session's model, permission mode, MCP configuration, or other settings.
   Do not approve an unexpected permission prompt on the user's behalf.

## Delegate the outcome, not the browser procedure

Tell the Claude session to read the handoff file and use its **native Artifact tool** to create or
update and inspect the Artifact, then use any native public-sharing action it actually exposes.
State the user's publication authorization and whether the mode is create or update. Do not forward
Chrome setup, Cloudflare handling, DOM instructions, or this skill's browser runbook: the delegated
Claude session chooses its own native tool calls.

Do not equate a native tool's `Published` label with anonymous web visibility. Some Artifact tools
save a working Artifact to the authenticated account while explicitly keeping it private. Require a
visibility read-back. If the tool has no `Publish to web` mutation, return the exact private Artifact
link and ask the user to use its Share menu to make it public. Resume verification from the URL the
user returns; do not create a replacement Artifact.

Only one generation may be active. Do not start a local/browser candidate while the delegated
session is working. Monitor with `tmux capture-pane`; visible tool activity or changing status is
progress. Apply the normal three-minute stall rule before stopping, then allow at most one retry in
the same Claude session with the same contract.

If the Claude session requests a product decision not fixed by the contract, relay it to the user.
Do not invent the decision merely to keep the delegated run moving.

## Accept and verify the result

Require the Claude session to report:

- the exact complete public Artifact URL;
- create/update mode and, for an update, whether identity and URL were preserved;
- content and interaction checks performed;
- any verification limitation or failed gate.

Independently inspect the returned public URL from the current environment when possible. If a
Cloudflare or authentication boundary prevents independent rendering, do not restart generation or
claim that check passed. Preserve the delegate's evidence, report the verification boundary, and
ask for user-side confirmation only for the missing gate.

After the public gate is verified or the invocation is explicitly stopped, remove only temporary
files created for this invocation. Leave the user's tmux session, Claude history, and Artifact
intact. Do not reuse the named target for a later unrelated task without fresh user direction.
