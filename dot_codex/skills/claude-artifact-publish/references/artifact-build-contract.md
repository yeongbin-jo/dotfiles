# Artifact build contract

Before generation, reduce the request to a compact contract that Claude receives with the actual
source material. Do not invent missing product decisions merely to fill the contract.

## Required fields

- **Mode and identity:** create or update; existing Artifact/chat/title when applicable.
- **Source of truth:** the exact documents, code, data, or prior Artifact that controls content.
- **Content invariants:** decisions, terminology, numbers, caveats, page/section intent, and flows
  that must survive unchanged.
- **Change budget:** content, structure, interaction, or styling changes that are authorized; name
  what is explicitly out of scope.
- **Visual references:** URLs/screenshots and the concrete qualities to preserve. Inspect references
  yourself; a URL Claude cannot see is not a usable reference.
- **Target experience:** primary viewport/device, navigation model, expected sections/pages, and
  required interactions.
- **Public-data boundary:** identifiers and material to omit or anonymize.
- **Acceptance checks:** observable facts that must be true before publication.

## Prompt discipline

Put invariants before requested changes. For a revision, tell Claude to report any requested change
that conflicts with an invariant instead of resolving it creatively. Attach a source draft when it
is more reliable than restating it in prose.

Require a self-contained HTML Artifact with no private/local dependencies. Do not ask Claude to
redesign architecture or rewrite conclusions when the task is visual polish. Conversely, when the
user authorizes content changes, identify them explicitly so fidelity checks do not reject them.

Keep a small verification ledger during the run: invariant, evidence location in the result, and
pass/fail. This is working evidence, not a speculative specification document.
