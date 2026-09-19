---
name: claude-artifact-publish
description: Create or revise a real Claude Artifact, preserve the requested content and design boundary, save it on claude.ai, and verify the result; share it publicly only when explicitly requested. Use when the user asks Codex to make, update, publish, republish, or visually improve a Claude Artifact, or requests a shareable public Artifact URL. Do not substitute CrossCheck Briefing, Linear, a downloaded HTML file, or localhost.
---

# Claude Artifact Publish

Deliver a real Claude Artifact saved on `claude.ai`. Treat generation, revision, account save, and
optional public sharing as separate gates. By default, `publish` / `발행` means create or update the
Artifact in the user's Claude account and verify it there; it does **not** mean anonymous web
access. Invoke public sharing and unauthenticated verification only when the user explicitly asks
for `public`, `공개`, `share`, `공유`, anonymous access, or a public/shareable URL. Do not infer
visibility from a URL shape such as `/artifact/` or `/public/artifacts/`; verify the requested
visibility mode.

## Route the request

1. Choose **create** only when there is no Artifact to preserve. Choose **update** when the user
   supplies an Artifact URL, authoring chat, existing draft, or says to keep the current design or
   content. For update rules and retry ownership, read
   [references/create-or-update.md](references/create-or-update.md).
2. Before asking Claude to build anything, establish a compact artifact contract: source of truth,
   content invariants, allowed changes, visual references, target viewport, required interactions,
   and sensitive material to exclude. Read
   [references/artifact-build-contract.md](references/artifact-build-contract.md).
3. If the task includes design, diagrams, animation, or revision of an existing Artifact, read
   [references/visual-qa.md](references/visual-qa.md) and perform the applicable pre-save checks.

## Build, save, and optionally share

1. Sanitize the material before it reaches Claude. Always remove credentials and secrets. Remove
   customer data, account IDs, absolute local paths, internal database IDs, and other sensitive
   material unless the user authorized it for the selected private or public visibility boundary.
2. Choose the narrowest execution surface that can produce a real Claude Artifact:
   - Use a native Claude `Artifact` tool when the current environment exposes one. Do not add
     browser automation merely to reproduce work that tool performs directly.
   - Only when the user's current task explicitly names a particular already-running tmux Claude
     session and asks Codex to collaborate with that session, delegate the sanitized contract to
     its native `Artifact` tool. A previously mentioned target, a discovered idle session, or a
     generic request to "use Claude" is insufficient. Read
     [references/tmux-collaboration.md](references/tmux-collaboration.md). Tmux is only the message
     transport; do not send this skill's browser procedure to the Claude delegate.
   - Otherwise prefer the user's already authenticated controllable Chrome session. If unavailable,
     use another already authenticated browser capability. Try `agent-browser --auto-connect` only
     after those routes fail. Copying browser authentication state into an isolated profile is a
     sensitive fallback and requires explicit approval in the current request; a machine name or
     an earlier run is not approval. Then read
     [references/browser-session.md](references/browser-session.md), use a normal-rendering Chrome
     process rather than headless mode, and destroy the ephemeral authentication copy after the
     requested verification gate.
3. Give Claude the artifact contract and the actual source material. Explicitly request a
   self-contained HTML Artifact, not a prose response. In update mode, state the invariants before
   the requested changes and keep the original authoring conversation when possible.
4. Allow one active generation at a time. Wait while visible progress or network activity
   continues. Declare a stall only after the UI has shown no progress for three minutes. Stop the
   old run before one recovery retry; never create parallel duplicate candidates to race them.
5. Accept generation only when the selected surface proves a named HTML Artifact exists. In the
   browser this requires the Artifact viewer with Preview/Code controls. With a native or delegated
   Artifact tool, require an Artifact ID/URL plus successful read-back of the created content. A
   normal message, attachment, downloaded HTML, Briefing URL, or localhost URL is not success.
6. Run content-fidelity and visual QA before saving the final revision. Repair the same Artifact
   when possible. Do not accept a known regression merely because the HTML renders.
7. Save or update the Artifact using the selected surface's native Artifact action and read it back.
   A native tool result labeled `Published` that saves the Artifact to the authenticated account is
   success for the default private mode. Record the exact Artifact URL/ID and actual visibility;
   do not mislabel a private Artifact as public.
8. Only when public sharing was explicitly requested, use the surface's native sharing action. In
   the browser viewer this is `More options` -> `Publish artifact` -> `Publish to web` ->
   `Publish & copy link`. Extract the complete URL from the tool result, dialog, or DOM; never infer
   a truncated value. In update mode, report whether the public URL was preserved or replaced.
9. Verify according to the selected visibility. For private mode, authenticated/native read-back of
   the exact Artifact, expected title/sections, interactions, and target viewport is sufficient. For
   explicit public mode, additionally verify the exact public URL without authenticated state. If
   an anti-bot interstitial blocks rendering, use a clean interactive browser or the requested
   target machine and report any remaining boundary.
10. Stop abandoned Claude runs and clean only resources created for this invocation. Preserve normal
   browser profiles, source drafts, and the original Artifact.

## Output contract

Report the exact saved Artifact URL first, then state:

- whether this was a create or update and whether the URL was preserved;
- whether it is private/account-only or explicitly public;
- which content/design invariants were checked;
- the verification surface, viewport, and interaction result;
- any fallback, retry, duplicate cleanup, or local skill/runbook change.

When public sharing was explicitly requested, also report the independently verified public URL and
anonymous-access result. Do not request public sharing merely to satisfy this skill.

If any gate fails, report that gate and do not substitute another product surface or claim success.
