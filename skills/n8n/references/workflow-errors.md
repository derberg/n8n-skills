# Route: Error handling

Owns making failures loud, structured and recoverable — and, best case, self-healing so
transient blips never reach a human.

By default, when an n8n node throws, the **whole workflow halts**. For an interactive run
you are watching that is fine. For anything unattended it is the wrong default: the caller
gets a timeout or an empty 500, the operator gets no alert, and the symptom is "the
integration just stopped working" with no log and no clue.

## When you actually need this

| Workflow shape | Posture |
|---|---|
| Webhook / API (anything with `Respond to Webhook`) | **Required.** Every fallible node's error output wired; status code matches cause |
| Scheduled / cron / queue worker / agent tool | **Required.** A workflow-level error workflow, plus `retryOnFail` on network nodes |
| Internal one-off you run and watch yourself | Optional. Default `onError: "stopWorkflow"` is fine |

The dividing line: **if anyone other than you sees the output** — a downstream system, an
end user, an on-call engineer — the failure has to be handled, not swallowed.

## ⚠️ `n8n_test_workflow` executes real nodes

Before running a test: `n8n_test_workflow` executes real nodes. Code, HTTP Request,
database writes, Slack and email sends and sub-workflow calls **all fire for real**. Ask the
user before running if any node has user-visible side effects, and afterwards tell them
which nodes ran live.

## The #1 silent trap: per-node error output is a TWO-step setup

Routing a node's failure to a handler takes **two** changes. Doing only one looks complete
and misbehaves.

1. **Set `onError: "continueErrorOutput"`** on the node. This is what *creates* the second
   output. Without it, `main[1]` does not exist no matter what you wire.
2. **Wire that error output** (`connections.<node>.main[1]`, i.e. `sourceIndex: 1`) to a
   real handler. Without a target the error data is emitted into the void.

| What you did | What happens at runtime |
|---|---|
| `onError` set, error output **not** wired | Error data silently discarded. Downstream does not fire. **The dashboard shows the run as succeeded.** Worst case — nothing logged anywhere |
| Error output wired, `onError` **not** set | The slot never fires; the handler is unreachable. On failure the workflow just halts |
| Both done | Failure routes down `main[1]` to your handler ✅ |

```javascript
// 1) Turn on the error output (creates main[1])
{ type: "updateNode", nodeName: "HTTP Request",
  changes: { onError: "continueErrorOutput" } }

// 2) Wire it. sourceIndex: 1 = the error output.
{ type: "addConnection", source: "HTTP Request", target: "Handle Error",
  sourceIndex: 1 }
```

`sourceIndex: 0` is the success path, `1` is the error path. (For IF nodes the aliases
`branch: "true"` / `"false"` map to 0/1; for a generic fallible node use explicit
`sourceIndex: 1`.)

**Then verify.** This trap does not surface in `validate_workflow` — a half-wired error
output validates clean. Pull the workflow with `n8n_get_workflow` and confirm **both**
halves: the node's `onError` is `"continueErrorOutput"`, and
`connections["HTTP Request"].main[1]` contains your handler.

| `onError` value | Effect |
|---|---|
| `"stopWorkflow"` (default) | Error halts the whole workflow |
| `"continueRegularOutput"` | Error item flows out the **normal** output. Rare, usually wrong |
| `"continueErrorOutput"` | Error item flows out `main[1]`. The one you wire |

Full failure-mode catalog, fan-in/fan-out shapes and verification:
[deep/errors/NODE_ERROR_OUTPUTS.md](deep/errors/NODE_ERROR_OUTPUTS.md).

## Self-healing first: `retryOnFail` before you wire error paths

On **any node calling a network service** — HTTP Request, comms, databases, AI nodes,
third-party integrations — set node-level retry:

```javascript
{ type: "updateNode", nodeName: "HTTP Request",
  changes: { retryOnFail: true, maxTries: 3, waitBetweenTries: 5000 } }
```

Why first: a 429 or brief upstream hiccup retries and usually succeeds on its own. The error
output then fires only on *real, persistent* failures, so your 5xx responses and on-call
alerts reflect actual problems instead of noise.

Engine limits: retry fires on **any** error (no per-status-code filter), `maxTries` caps at
5, and `waitBetweenTries` caps at 5000 ms — so 5000 is both the max and a sensible default.

## API workflows: the canonical shape

One rule overrides everything: **no hanging branches.** Every path — success and every
error — must end at a `Respond to Webhook`, or the caller waits until it times out.

```
Webhook (responseMode: "responseNode")
  ├── validate input → process → Respond (200, body)
  └── (any fallible node's error output → sourceIndex 1)
            → Respond (4xx/5xx, structured error body)
            → optional: log full error privately / notify
```

1. **Fan in to one error responder.** Many fallible nodes can route `main[1]` to a single
   `Respond` node.
2. **Validation failures (4xx) are checked *upstream*, not via error outputs.** A missing
   field is not a node *crashing* — it is an expected outcome with a known response. Branch
   on it with IF/Switch and return 400/401/403/404 directly. Error outputs are for
   *unexpected* failures (5xx).
3. **`responseCode` defaults to 200 — even on error branches.** An error branch returning
   200 with an error body looks like success to the caller's HTTP client, so their error
   handling never fires. Set `responseCode` explicitly on **every** Respond node.

For structured input validation, run the check as an IIFE inside a single **Set** node
rather than a chain of IF/Switch nodes per field. Full pattern:
[deep/errors/API_WORKFLOWS.md](deep/errors/API_WORKFLOWS.md).

## Response shapes: map cause → status code

Match the status code to *why* the request failed, because the caller branches on it: their
monitoring alerts on 5xx (your fault) but not 4xx (their fault), and 5xx suggests "retry"
while 4xx suggests "don't".

**The common mistake:** wiring everything — including bad input — to one `Respond` returning
500 `internal_error`. Now the caller cannot tell their bug from your outage.

| Cause | Status | `error` code | Handled where |
|---|---|---|---|
| Required field missing / wrong type | 400 | `validation_error` | Upstream check |
| Auth missing or invalid | 401 | `unauthorized` | Upstream check |
| Authenticated but not allowed | 403 | `forbidden` | Upstream check |
| ID valid in request, absent in your data | 404 | `not_found` | Branch on the lookup *result* |
| Conflicts with current state | 409 | `conflict` | Detect with logic |
| Caller exceeded rate limit | 429 | `rate_limit_exceeded` | Set `Retry-After` |
| Node threw, cause unknown | 500 | `internal_error` | Error output path |
| Third-party API returned an error | 502 | `upstream_error` | Error output of the HTTP node |
| Cannot process right now | 503 | `service_unavailable` | Detect specific error |
| Third-party API timed out | 504 | `upstream_timeout` | Error output filtered by message |

Two distinct flows: **4xx is decided before the work** (IF/Switch + dedicated Respond);
**5xx comes out of error outputs**.

**One Respond, expression-driven code.** When error paths differ only by number and message,
do not fan out to N Respond nodes through a Switch:

```javascript
// Response Code field on a single Respond to Webhook:
{{ (() => {
    const msg = $json.error?.message || $json.message || '';
    if (msg.includes('INVALID_ID')) return 400;
    if (/429|too many/i.test(msg)) return 429;
    if (/timeout/i.test(msg))      return 504;
    if (/upstream|llm|api/i.test(msg)) return 502;
    return 500;
})() }}
```

Reserve Switch + multiple Responds for paths that diverge *structurally*.

The default envelope is `{ "error": "<code>", "message": "<human text>" }` — the HTTP status
already says success-vs-failure, so no `ok: false` flag. **Never leak internals** (stack
traces, SQL, upstream bodies, tokens) into the response; log those privately and return a
sanitized message. → [deep/errors/RESPONSE_SHAPES.md](deep/errors/RESPONSE_SHAPES.md)

## Workflow-level error workflow (the catch-all)

Per-node outputs handle the failures you anticipated on the nodes you remembered to wire. An
**error workflow** catches everything else: a node you forgot to wire, a crash between
nodes, a whole-workflow timeout, a trigger failure.

Build it as a separate workflow starting with an **Error Trigger** node. Minimal version —
capture then notify:

```
Error Trigger → Set (build alert from execution + error) → Slack/email (#incidents)
```

A good alert includes the workflow name, a link to the editor and to the failed execution,
the failed node name, and the **real** error message — not "Workflow failed".

Two traps:

- **The recursion trap.** If the error workflow notifies Slack and Slack is what is down,
  the error workflow fails too and the original error vanishes. Notify on a *different*
  channel than your monitored workflows use, and add a fallback (write to a Data Table) so a
  failed notification still leaves a trace.
- **A "handled" error will not bubble up.** If a node's error output is wired to a no-op
  that drops the data, n8n considers the error *handled* and the error workflow does **not**
  fire. Only catch per-node when you are actually doing something with the error.

→ [deep/errors/ERROR_WORKFLOWS.md](deep/errors/ERROR_WORKFLOWS.md)

**What the MCP cannot do:** assigning the error workflow is an n8n **UI setting** — Workflow
Settings → Error Workflow. There is no MCP tool for it. Build the error workflow with the
MCP, then tell the user the exact UI step, and to repeat it (or set the instance default)
for every unattended workflow.

## Checklist

- [ ] `retryOnFail` on every network-calling node
- [ ] `onError: "continueErrorOutput"` **and** `main[1]` wired, both verified with `n8n_get_workflow`
- [ ] No hanging branches in a webhook workflow
- [ ] `responseCode` set explicitly on every Respond node
- [ ] 4xx decided upstream; 5xx from error outputs
- [ ] No internals leaked in responses
- [ ] Error workflow built, and the user told to wire it in the UI
