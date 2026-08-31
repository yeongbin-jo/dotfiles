---
name: claude-artifact-publish
description: Create or revise a real Claude Artifact, preserve the requested content and design boundary, publish it on claude.ai, and verify the public result. Use when the user asks Codex to make, update, republish, or visually improve a Claude Artifact or requests a shareable Claude Artifact URL. Do not substitute CrossCheck Briefing, Linear, a downloaded HTML file, or localhost.
---

# Claude Artifact Publish

Deliver a real Claude Artifact at `https://claude.ai/public/artifacts/<uuid>`. Treat generation,
revision, publication, and public verification as separate gates. Publication is an external public
mutation and requires an explicit publish/share request; preparing or reviewing a draft does not.

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
   [references/visual-qa.md](references/visual-qa.md) and perform the applicable pre-publish checks.

## Build and publish

1. Sanitize the material before it reaches Claude. Remove credentials, customer data, account IDs,
   absolute local paths, internal database IDs, and anything not authorized for public release.
2. Prefer the user's already authenticated controllable Chrome session. If unavailable, use another
   already authenticated browser capability. Try `agent-browser --auto-connect` only after those
   routes fail. Copying browser authentication state into an isolated profile is a sensitive
   fallback and requires explicit approval; then read
   [references/browser-session.md](references/browser-session.md).
3. Give Claude the artifact contract and the actual source material. Explicitly request a
   self-contained HTML Artifact, not a prose response. In update mode, state the invariants before
   the requested changes and keep the original authoring conversation when possible.
4. Allow one active generation at a time. Wait while visible progress or network activity
   continues. Declare a stall only after the UI has shown no progress for three minutes. Stop the
   old run before one recovery retry; never create parallel duplicate candidates to race them.
5. Accept generation only when Claude shows a named HTML Artifact viewer with Preview/Code
   controls. A normal message, attachment, downloaded HTML, Briefing URL, or localhost URL is not
   success.
6. Run content-fidelity and visual QA before publishing. Repair the same Artifact when possible.
   Do not publish a known regression merely because the HTML renders.
7. In the Artifact viewer use `More options` -> `Publish artifact` -> `Publish to web` ->
   `Publish & copy link`. Extract the complete URL from the dialog or DOM; never infer a truncated
   value. In update mode, verify whether the existing public URL remained stable and report any
   replacement URL explicitly.
8. Verify the exact public URL without the authoring tab's authenticated state. Confirm HTTP success,
   HTML content, expected title/sections, interactions, and the agreed target viewport. If an
   anti-bot interstitial blocks headless rendering, verify HTTP and use a clean interactive browser
   or the requested target machine for the visual gate.
9. Stop abandoned Claude runs and clean only resources created for this invocation. Preserve normal
   browser profiles, source drafts, and the original Artifact.

## Output contract

Report the verified public URL first, then state:

- whether this was a create or update and whether the URL was preserved;
- which content/design invariants were checked;
- the public verification device or viewport and interaction result;
- any fallback, retry, duplicate cleanup, or local skill/runbook change.

If any gate fails, report that gate and do not substitute another product surface or claim success.
