# Seam classes

Use this reference only after framing the review around the whole diff and the ticket's core thesis. The classes are triggers for required enumeration, not a substitute for independent reasoning.

## External contract and acquisition path

Trigger when the diff calls or mirrors an external route, SuiteQL/schema, MCP tool, env var, task definition, secret, IAM permission, generated catalog, or downstream consumer.

- Resolve existence against the real registry, schema, task definition, or deployed read-only surface.
- Execute derived wire shapes, coercions, defaults, and serialization; do not infer them from declarations.
- Exercise the same acquisition path production uses. A fixture or hand-fed payload may test downstream behavior but does not test acquisition.
- A bounded timeout must stay armed until the RESPONSE BODY is consumed, not only until the call resolves. `fetch()` resolves on headers, so a peer that accepts the request and then stalls the body defeats a timer cleared at that point — verify the abort budget spans the body read and that an abort there is classified as a failure.
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
   A guarded CAS only settles this if it fences the SAME read the payload was derived from. When one
   operation reads the same mutable authority (a `CURRENT` pointer, a version row, a HEAD) more than
   once, ask which read produced the data and which produced the fence, and require proof they are
   the same read. Two reads with live I/O between them is a lost-update window that every downstream
   check passes: the CAS matches the newer value, the payload was built from the older one, and the
   write lands cleanly on top of whatever the other writer committed. (RND-3248 miss: a delta pinned
   its prior corpus from read #1 and fenced activation on read #2, so a publish arriving between them
   would be silently overwritten by a corpus assembled from the version before it.)
4. Can `NOT`, `!=`, absent JSON keys, or nullable columns create three-valued-logic gaps?
5. Enumerate the queue engine's OWN redelivery paths, not just configured retries: BullMQ stall
   recovery redelivers lock-lost jobs up to `maxStalledCount` regardless of `attempts: 1`, and a
   redelivered duplicate that completes NORMALLY (e.g. an "already exists — absorbed" branch)
   suppresses the failure handler your crash backstop hangs off. Ask: does every duplicate-absorption
   path either fail the job or itself repair the orphaned durable state? (RND-3206 miss: absorbed
   duplicate completed → onFailed never fired → row stuck `running` forever.)

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

## Ordering and initialization contracts

Trigger when the diff adds or relocates a guard/precondition claimed to run "before" expensive or dangerous work, **or** adds an import to an entry point that documents a load-order contract ("nothing heavy before X", "no DB/credential access until Y verifies").

- **Execution order**: verify the claim per caller path, not by reachability. A guard inside a funnel every path eventually reaches is still defeated by a caller whose own expensive phase runs first (e.g. checkpointed extraction before a finalize funnel). Prefer a differential test that proves ordering (the guard's error is observed even when a later validation would also fail) over one that only proves the failure happens somewhere.
- **Initialization order**: a new static import executes its whole transitive graph at load. Trace it for eager side effects — singletons, connection pools, clients that capture env at construction. Importing one constant can drag in a module that builds a DB client before the code that populates its credentials has run, and the failure surfaces far away as a config error. Verify by importing the entry with the relevant env absent and asserting the heavy module was not evaluated; keep the constant in a leaf module when it must be shared.

## CI workflow runtime

Trigger when `.github/workflows/**` changes.

- Run syntax validation, but do not equate it with runtime success.
- Determine whether PR CI will actually trigger the changed workflow.
- For push/tag/schedule/release-only workflows, simulate the runner/setup-action seam or record first-run verification as a deferred gate.
- Running only the workflow's inner script does not validate setup actions, runner tools, permissions, or secret availability.
