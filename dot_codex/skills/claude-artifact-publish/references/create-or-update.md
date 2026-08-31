# Create, update, and retry ownership

## Choose the mode

Use **create** when no existing deliverable must retain identity. Use **update** when any of these is
present: a public Artifact URL, the authoring Claude chat, an HTML draft, a named previous version,
or an instruction such as “keep the architecture/content and improve only the visualization.”

A public URL proves what is published but may not expose its authoring conversation. First inspect
the URL as a baseline, then locate the authenticated authoring chat when possible. Do not silently
replace an existing Artifact with a new URL when the user expects an in-place update. If the
authoring context cannot be recovered, explain that boundary before creating a replacement unless
the request already authorizes a new publication.

## Preserve identity and intent

For an update:

1. Capture the existing public URL, title, major sections, interactions, and representative
   screenshots before editing.
2. Separate invariant content from requested changes. “Design only” means no new architecture,
   renamed components, deleted caveats, changed numbers, or altered conclusions.
3. Continue in the original authoring chat and revise the same Artifact when the UI supports it.
4. After publication, open the original public URL again. Record whether it now serves the revision;
   if Claude issued a replacement, return the old→new mapping.

## Retry ownership

One invocation owns one active Claude generation. Slow is not stalled while text, tool status,
network traffic, or Artifact state is moving. When none changes for three minutes:

1. record the last visible state;
2. stop or cancel that exact generation;
3. retry once in the same chat with the same artifact contract;
4. stop after a second stall or repeated failure and report the failed gate.

Never start parallel candidates and pick the prettiest result: that creates duplicate public state,
loses revision identity, and makes cleanup ambiguous.
