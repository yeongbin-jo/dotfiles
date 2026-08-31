# Visual and interaction QA

Use this gate for designed, diagrammatic, animated, multi-page, or revised Artifacts. Judge the
rendered Artifact, not Claude's prose description of it.

## Content fidelity

- Compare every contract invariant with the rendered result.
- For design-only updates, reject renamed components, changed topology, missing caveats, altered
  numbers, or new conclusions even if the visual looks better.
- Make the end-to-end story understandable before deep implementation or experiment detail.
- Use specific architecture labels when the source provides them; placeholders must communicate a
  real repeated pattern rather than conceal an unfinished design.

## Readability and composition

- Inspect the user-specified target first. When none is given, use a desktop reference around
  1440×900 and a narrower 1280×800 check.
- Reject clipped content, unintended horizontal scroll, overlapping labels, illegible diagrams,
  low-contrast text, and controls hidden outside the viewport.
- Default body copy should normally be at least 16px; deck-like narrative copy should normally be
  at least 18px. Small diagram labels still need to be readable at the target viewport. Follow an
  explicit design system when it sets a different accessible scale.
- A page should have a clear focal point and hierarchy. Dense evidence belongs behind progressive
  disclosure or on a detail page rather than shrinking all text.
- Derive reusable color, typography, spacing, border, and motion tokens from supplied references;
  do not preserve only superficial colors while discarding their layout character.

## Diagrams and motion

- A topology view must expose trigger → control → orchestration → collection → evidence/output and
  the relevant authority boundaries without requiring narration to decode it.
- Animation must explain state, flow, or causality. Reject decorative perpetual motion, unreadably
  fast transitions, and animations whose static frame is meaningless.
- Honor reduced-motion preferences and provide a stable state after animation completes.

## Interaction and publication check

1. Capture representative screenshots before and after an update.
2. Exercise navigation, tabs/pages, expanders, filters, tooltips, and any simulated controls.
3. Check browser console errors and failed external resources.
4. Repeat the critical visual and interaction checks on the public unauthenticated URL.
5. Publish only when the result passes the contract. A renderable page is not automatically an
   acceptable page.
