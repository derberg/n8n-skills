# Route: Design

Owns workflow architecture and decomposition — which shape the flow takes, and what gets
extracted into a sub-workflow.

Read [shared/non-negotiables.md](shared/non-negotiables.md) before modifying any workflow.

## Pick the architecture first

Six patterns cover essentially all real workflows. Choose before you place a node.

| Pattern | Shape | Use when | Depth |
|---|---|---|---|
| **Webhook processing** (most common) | Webhook → Validate → Transform → Respond/Notify | Receiving data from external systems; Slack commands, form submissions, GitHub/Stripe webhooks; instant response to events | [deep/design/webhook_processing.md](deep/design/webhook_processing.md) |
| **HTTP API integration** | Trigger → HTTP Request → Transform → Action → Error handler | Fetching from external APIs; syncing third-party services; data pipelines | [deep/design/http_api_integration.md](deep/design/http_api_integration.md) |
| **Database operations** | Schedule → Query → Transform → Write → Verify | Syncing between databases; scheduled queries; ETL | [deep/design/database_operations.md](deep/design/database_operations.md) |
| **AI agent** | Trigger → Agent (model + tools + memory) → Output | Conversational AI; AI with tool access; multi-step reasoning | [deep/design/ai_agent_workflow.md](deep/design/ai_agent_workflow.md) |
| **Scheduled tasks** | Schedule → Fetch → Process → Deliver → Log | Recurring reports; periodic fetching; maintenance | [deep/design/scheduled_tasks.md](deep/design/scheduled_tasks.md) |
| **Batch processing** | Prepare → SplitInBatches → Process → Accumulate → Aggregate | Datasets exceeding API batch limits; accumulating across calls; nested loops | below, plus [deep/design/scheduled_tasks.md](deep/design/scheduled_tasks.md) |

Most "simple" flows ship at 10+ nodes. Plan the shape rather than growing it node by node.

## Build discipline

- **Name nodes for what they do**, not `HTTP Request1`. The node name is what expressions
  reference (`$('Fetch Invoice').item.json`) and what a reader scans.
- **Add sticky notes capturing *why*.** The graph shows what; nothing else records the
  reason a branch exists.
- **Per-item iteration is automatic.** Do not add a Loop Over Items node to "make it
  loop" — n8n nodes already iterate per item.
- **Configure from the live schema.** `get_node` before setting parameters. See
  [shared/mcp-tools.md](shared/mcp-tools.md).

## batchSize is the cost lever

A SplitInBatches loop re-runs its whole body once per iteration — roughly 0.8 ms of engine
overhead per iteration plus the body's own cost, so total ≈
`⌈items / batchSize⌉ × (overhead + body)`.

- Pick the **largest batch your real constraint allows** (API page size, rate limit,
  memory). Bigger batches mean fewer iterations; the body still sees every item.
- `batchSize: 1` is the expensive extreme — one full engine pass per item. Use it only
  when you must act on one item at a time (nested-loop control, or an API taking exactly
  one id).
- If you are looping only to "go over the items" with no external constraint, **you
  probably do not need the loop.** A single All Items Code node processes the whole set far
  more cheaply.

**Cross-iteration data:** after the loop, `$('Node Inside Loop').all()` returns **only the
last batch's items**. To accumulate across iterations use
`$getWorkflowStaticData('global')` in a Code node inside the loop — see
[workflow-code.md](workflow-code.md).

**Nested-loop wiring gotcha:** for N categories × M items, the inner loop's `done[0]` must
connect back to the **outer** loop input, not to the aggregate. The outer `done[0]` feeds
the final aggregate.

## Sub-workflows: two non-negotiables

### 1. Search before you build

Before writing logic for a generic problem, check whether a sub-workflow already does it.
The community MCP cannot filter workflows by tag, so **the name is the discovery surface**:

```
n8n_list_workflows()                     # scan the library
n8n_get_workflow({ id: "<candidate>" })  # read its inputs/outputs and body
```

If something fits, use it and say so ("I found `Subworkflow: Parse RFC2822 date` — using
that"). If nothing fits, build it *with a discoverable name* so the next search finds it.
Verb-first naming conventions:
[deep/design/NAMING_AND_DISCOVERY.md](deep/design/NAMING_AND_DISCOVERY.md).

### 2. The Execute Workflow Trigger uses "Define Below" with typed fields

**Default to "Define Below"** with explicit typed fields. It is the only mode that gives
callers a schema to fill — it is what lets an AI agent pass values via `$fromAI`, and what
lets structured callers map fields cleanly. Passthrough has no schema, so the trigger
cannot be wired as a clean agent tool.

Two exceptions, and only two:

- **Binary input.** Typed fields are JSON-only. If the sub-workflow must receive an
  image, file or PDF, passthrough is required so the `binary` slot flows through.
- **Zero inputs.** Define Below requires at least one field, so a genuinely no-arg
  operation has nowhere to put an empty schema.

Outside those two cases, passthrough is a bug.

## Should this be a sub-workflow?

```
Could this plausibly be needed in another workflow?
  └─ Yes → extract.
Is it a generic concern (auth, retry, parsing, formatting, ID generation)?
  └─ Almost always → extract. These are the canonical reusable sub-workflows.
Is it >5 nodes and conceptually one thing?
  └─ Probably extract, even if reuse isn't certain. Better isolated.
Is it one HTTP call with no logic around it?
  └─ Don't. trigger → HTTP → return adds a boundary for nothing.
Is it tightly coupled to this one caller's data shape?
  └─ Don't extract yet — fix the data shape first, or you just relocate the coupling.
```

Reuse is not the only reason. **Readability** — the caller shows one node instead of five.
**Testability** — run it alone with pinned input. **Replaceability** — swap the
implementation without rippling to callers.

A 20-node workflow is fine *if it is mostly a linear sequence of Execute Workflow calls
and decisions*. A 20-node workflow of inline transformations is not. If yours has 15+ nodes
and is not mostly sub-workflow calls and branches, extract more.

## Calling sub-workflows: `mode` and `waitForSubWorkflow`

| `mode` | Sub-workflow runs | Items per run |
|---|---|---|
| `all` (default) | once | all N items |
| `each` | N times | exactly one item per run |

For a body that processes items normally the two are equivalent. **The split only matters
when the body assumes it sees exactly one item** — a per-run aggregation, "this is THE
customer to act on" logic, or a final write that should fire once per input. With `all`
that body gets all N items and the assumption breaks.

So when you need per-item iteration, prefer `mode: each` over dropping a Loop Over Items
node *inside* the sub-workflow. The mode does the iteration; the body stays single-item.

`waitForSubWorkflow` defaults to `true` — the caller blocks and continues with the output.
Set `options.waitForSubWorkflow: false` to fire-and-forget.

**The only true parallelization n8n offers** is `mode: each` +
`waitForSubWorkflow: false`: N items dispatch N runs that execute concurrently, bounded by
per-instance concurrency limits. The caller does not know when or whether any finished, so
it is only useful with separate completion tracking — typically a Data Table the
sub-workflow updates as it progresses. Full pattern:
[deep/design/SUBWORKFLOW_PATTERNS.md](deep/design/SUBWORKFLOW_PATTERNS.md).

## Splitting by input shape (the N+1 pattern)

When a sub-workflow has input paths whose contracts *genuinely* differ — binary vs JSON,
sync vs async, divergent auth — do not cram them under one trigger with passthrough plus
an internal Switch. Passthrough and Define Below are mutually exclusive on one trigger, so
"pick passthrough because it is most permissive, then branch inside" costs you the typed
schema, grows branch cruft, and turns every new input shape into more branching.

For N divergent contracts, build **N+1 sub-workflows**: one outer per contract doing its
input-specific prep, each calling **one shared downstream** sub-workflow with a normalized
shape. The shared core has a single typed contract and knows nothing about its callers.
Worked example: [deep/design/SUBWORKFLOW_PATTERNS.md](deep/design/SUBWORKFLOW_PATTERNS.md).

## Sub-workflow as an agent tool

Wiring a sub-workflow as a tool an AI agent can call needs the typed Define Below contract
above. See [workflow-agents.md](workflow-agents.md) and
[deep/agents/SUBWORKFLOW_AS_TOOL.md](deep/agents/SUBWORKFLOW_AS_TOOL.md).

## Before you call it done

- Architecture chosen deliberately, not accreted.
- Nodes named for what they do; sticky notes explain why.
- Existing sub-workflows searched before new logic was written.
- Error branches wired on fallible nodes — [workflow-errors.md](workflow-errors.md).
- `validate_workflow` clean **and** the antipattern scan run —
  [workflow-validate.md](workflow-validate.md).
- `connections` verified with `n8n_get_workflow` after every write.
