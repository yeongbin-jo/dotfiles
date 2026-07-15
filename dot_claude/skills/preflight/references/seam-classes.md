# Seam classes

Use this reference only after framing the review around the whole diff and the ticket's core thesis. The classes are triggers for required enumeration, not a substitute for independent reasoning.

## External contract and acquisition path

Trigger when the diff calls or mirrors an external route, SuiteQL/schema, MCP tool, env var, task definition, secret, IAM permission, generated catalog, or downstream consumer.

- Resolve existence against the real registry, schema, task definition, or deployed read-only surface.
- Execute derived wire shapes, coercions, defaults, and serialization; do not infer them from declarations.
- Exercise the same acquisition path production uses. A fixture or hand-fed payload may test downstream behavior but does not test acquisition.
- For SuiteQL or API routes, prefer a safe sandbox/read-only parse or local-stack smoke over a mock.

## Conditional skip or absent result

Trigger when `skipped`, absent, empty, null, defaulted, or fallback output is treated as benign.

Enumerate every way the predecessor can reach that state: intended condition, dependency failure, forced execution followed by failure, missing input, parse failure, and empty-but-valid response. Confirm each cause maps to the correct decision and never fabricates success.

## Crash window, redelivery, and multi-writer state

Trigger when a durable transition sits next to an external side effect, queue operation, lease, marker, watchdog, or worker handler.

For each transition answer:

1. If the process dies immediately before or after the side effect, what recovers it and within what bound?
2. On redelivery, is idempotency checked before the side effect and against every terminal state?
3. Can two writers pass a check-then-act window, or is the transition a guarded compare-and-set?
4. Can `NOT`, `!=`, absent JSON keys, or nullable columns create three-valued-logic gaps?

Use a real store for persistence semantics when feasible; mocked counts cannot prove SQL/null behavior.

## Error taxonomy

Trigger when the diff catches or converts failures from HTTP, DB, queue, worker, parser, or external service calls.

- Classify each failure as retryable/transient or terminal/expected.
- Retryable failures must not be persisted as terminal empty/no-match states.
- Workers must throw retryable failures so retry/backoff actually runs.
- Routes and reducers must fail loudly on malformed or absent required input instead of defaulting into a valid-looking path.

## Untrusted-key write and principal scope

Trigger when durable state is keyed by client-controlled, free-text, header-derived, or otherwise unverified identity, or when a new READ/LIST endpoint changes authorization.

- Derive shared-row write keys from authenticated or independently verified identity.
- Mismatch/error paths must not mutate global state for the claimed unverified key.
- Enumerate every principal type that can carry the scope: human member, workspace key, environment-bound key, and service identity.
- The narrowest principal must not enumerate or mutate sibling resources.

## Independent verifier and multi-layer projection

Trigger when the deliverable claims independent verification, parity, generated coverage, or synchronization across multiple layers.

- Prove the verifier does not read the surface it is supposed to verify.
- Diff every parallel domain/allowlist against the same canonical source.
- Trace every consumer so a category cannot disappear between writer, transport, reader, and UI.
- Prefer a different-vendor reviewer for high-tier or self-certifying designs. If unavailable, record the residual rather than claiming independence.

## CI workflow runtime

Trigger when `.github/workflows/**` changes.

- Run syntax validation, but do not equate it with runtime success.
- Determine whether PR CI will actually trigger the changed workflow.
- For push/tag/schedule/release-only workflows, simulate the runner/setup-action seam or record first-run verification as a deferred gate.
- Running only the workflow's inner script does not validate setup actions, runner tools, permissions, or secret availability.
