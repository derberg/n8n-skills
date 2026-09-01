# Route: Code

Owns all three code runtimes n8n exposes. They are **not** interchangeable — pick the
right section before you write a line.

## Which runtime are you writing for?

```
Workflow Code node, JavaScript  → "JavaScript" below.
                                  The default. ~95% of cases.

Workflow Code node, Python      → "Python" below.
                                  Only when the user explicitly prefers Python, or
                                  needs its standard library (re, hashlib, statistics).

AI-agent Custom Code Tool       → "Code Tool" below.
(@n8n/n8n-nodes-langchain.       A different runtime contract: input is `query`, the
 toolCode)                       return must be a string, and $fromAI / $input /
                                 $helpers do not exist.
```

| | Code node | Custom Code Tool |
|---|---|---|
| Node type | `n8n-nodes-base.code` | `@n8n/n8n-nodes-langchain.toolCode` |
| Invoked by | the previous node | an AI Agent (LangChain) |
| Input | `$input.all()` — item stream | `query` — string or object from the LLM |
| Return | `[{json: {...}}]` | **a string** |
| `$fromAI()` | N/A | **not available** |
| HTTP helper | `this.helpers.httpRequest` | not exposed to the sandbox |
| State | per-run execution data | no `getContext`, no `$getWorkflowStaticData` |

## Before you reach for Code at all

Walk the transform gatekeeper in [workflow-expressions.md](workflow-expressions.md):
expression → arrow-function IIFE inside an Edit Fields field → Code node, in that order.
The first two run in-process in single-digit milliseconds; the Code node's sandbox costs
~500–1000 ms of cold start on pure single-item shaping, for no functional difference.

Also check for a **native node** first: n8n has a Crypto node (`nodes-base.crypto`) for
HMAC, hashing and signing, and an XML node (`nodes-base.xml`) for XML/SOAP/RSS. Dropping
into Code for something a native node already does is one of the most common false
positives.

Code earns its place for whole-dataset aggregation (`$input.all()`), allowlisted
libraries, or async work.

---

## JavaScript

### Essential rules

1. **Choose "Run Once for All Items"** unless an item genuinely needs isolating.
2. **Access data** with `$input.all()`, `$input.first()`, `$input.item`.
3. **Return `[{json: {...}}]`** — the canonical, mode-portable form.
4. **Webhook data is under `$json.body`**, not `$json` directly.
5. **`this.helpers.httpRequest()`** is the HTTP helper — the bare `$helpers` global is
   **undefined** in the task-runner sandbox, so `$helpers.httpRequest()` throws
   `ReferenceError: $helpers is not defined`. `this.helpers.httpRequestWithAuthentication`
   is deny-listed. For anything past a trivial unauthenticated GET (auth, pagination,
   retries), use the **HTTP Request node** and keep Code for pure logic.
6. **Available**: `DateTime` (Luxon), `$jmespath()`. **Not available**: `$env` when
   `N8N_BLOCK_ENV_ACCESS_IN_NODE=true`, `require()` unless allowlisted.
7. **Instance-allowlisted libraries**: self-hosted instances can allowlist modules via
   `N8N_RUNNERS_ALLOWED_BUILT_IN_MODULES` / `N8N_RUNNERS_ALLOWED_EXTERNAL_MODULES`
   (legacy: `NODE_FUNCTION_ALLOW_BUILTIN` / `NODE_FUNCTION_ALLOW_EXTERNAL`). If the user
   says their instance allows `axios`, `lodash`, `crypto` and so on, use them via
   `require()` — do not refuse. If unsure, ask, or default to built-ins.

### Mode choice is the biggest performance lever

Measured on n8n 2.x with small records:

| What runs per item | Approx. cost |
|---|---|
| Code **All Items** (one run for the whole set) | ~0.02 ms/item |
| Expression in any node (IF / Set / …) | ~0.2 ms/item |
| Code **Each Item** (a full sandbox per item) | ~0.6 ms/item — 25–30× All Items |

`Run Once for Each Item` over 10k items is ~6 s of pure overhead versus ~0.2 s in All
Items. Use Each Item only when an item genuinely needs isolating (independent error
handling, or a per-item API call you cannot batch); otherwise loop *inside* one All Items
node. Expression complexity is essentially free — ~90% of the cost is the per-item
context, not your code — so reduce the **number** of per-item boundaries rather than
micro-optimising each one. Below a few hundred items none of this matters.

### Return format

**Canonical**: `[{json: {...}}]` — unambiguous and identical in both modes.

```javascript
return [{json: {field1: value1}}];                      // ✅ single
return [{json: {id: 1}}, {json: {id: 2}}];              // ✅ multiple
return $input.all();                                     // ✅ passthrough
return [];                                               // ✅ empty
```

In All Items mode n8n auto-wraps looser shapes, so these run but are non-canonical:

```javascript
return {json: {field: value}};   // ⚠️ auto-wrapped
return [{field: value}];         // ⚠️ auto-wrapped
```

What genuinely fails — nothing to wrap, execution stops with "Code doesn't return items
properly":

```javascript
return "processed";   // ❌ primitive
return null;          // ❌ null/undefined
```

### Production gotchas

- **SplitInBatches outputs are counterintuitive**: `main[0]` = **done** (fires once, after
  all batches), `main[1]` = **each batch** (the loop body). Add a **Limit 1** node after
  the done output as a safety.
- **Cross-iteration accumulation:** after the loop,
  `$('Node Inside Loop').all()` returns **only the last iteration's items**. Accumulate via
  `$getWorkflowStaticData('global')` — reset before, push inside, read after.
- **`pairedItem`:** when emitting items that do not map 1:1 to input, set
  `pairedItem: { item: i }` or downstream Set nodes fail with `paired_item_no_info`.
- **Node reference syntax:** `$('Node').first().json` or `$('Node').all()` — never `.json`
  directly on the reference.
- **Float precision:** compare currency at the cent level,
  `Math.round(a*100) !== Math.round(b*100)`, to avoid float noise.

### Deeper references

[deep/code/js/DATA_ACCESS.md](deep/code/js/DATA_ACCESS.md) (access patterns, mode
performance corollaries, production gotchas with code),
[deep/code/js/BUILTIN_FUNCTIONS.md](deep/code/js/BUILTIN_FUNCTIONS.md),
[deep/code/js/COMMON_PATTERNS.md](deep/code/js/COMMON_PATTERNS.md),
[deep/code/js/ERROR_PATTERNS.md](deep/code/js/ERROR_PATTERNS.md).

---

## Python

**JavaScript first.** Python is for when the user explicitly prefers it, or needs its
standard library. JavaScript has the full helper set, Luxon, and better coverage.

### Essential rules

1. **Access data** with `_input.all()`, `_input.first()`, `_input.item`.
2. **Return `[{"json": {...}}]`**.
3. **Webhook data is under `_json["body"]`**, not `_json` directly.
4. **No external libraries** — no `requests`, `pandas`, `numpy`.
5. **Standard library only**: `json`, `datetime`, `re`, `base64`, `hashlib`,
   `urllib.parse`, `math`, `random`, `statistics`.

### Two Python modes

**Python (Beta) — recommended.** Uses `_input`, `_json`, `_node`, plus `_now`, `_today`,
`_jmespath()`.

```python
items = _input.all()
return [{"json": {"count": len(items), "timestamp": _now.isoformat()}}]
```

**Python (Native) (Beta).** Only `_items` and `_item`; no helpers at all.

```python
return [{"json": {"id": item["json"].get("id"), "processed": True}} for item in _items]
```

### Deeper references

[deep/code/python/DATA_ACCESS.md](deep/code/python/DATA_ACCESS.md),
[deep/code/python/STANDARD_LIBRARY.md](deep/code/python/STANDARD_LIBRARY.md),
[deep/code/python/COMMON_PATTERNS.md](deep/code/python/COMMON_PATTERNS.md),
[deep/code/python/ERROR_PATTERNS.md](deep/code/python/ERROR_PATTERNS.md).

---

## Code Tool

For code an **AI agent** invokes. If you treat it like a Code node, it fails.

```javascript
// JavaScript — `query` is whatever the AI sent (a string by default)
return `You asked: ${query}`;
```

```python
# Python — `_query` is whatever the AI sent
return f"You asked: {_query}"
```

### Essential rules

1. **Return a string.** Numbers are auto-converted. Anything else throws
   `"The response property should be a string, but it is an object"`.
2. **The input variable is fixed**: `query` (JS), `_query` (Python). You cannot rename it.
3. **Do not use `$fromAI()`** inside the Code Tool sandbox — it throws
   `"No execution data available"`.
4. **Do not return `[{json: {...}}]`** — that is the Code node form. It throws
   `"Wrong output type returned"`.
5. **Use a descriptive tool name** (letters, numbers, underscores on v1.1+). The agent
   calls the tool by name.
6. **Write a precise description** — the LLM decides whether to invoke the tool from it.
   Tool names and descriptions *are* prompt; see [workflow-agents.md](workflow-agents.md).

### Two input modes

`specifyInputSchema: false` (default) gives unstructured input — `query` is a raw string.
`specifyInputSchema: true` gives structured arguments via `jsonSchemaExample` /
`DynamicStructuredTool`, and `query` becomes an object. Details:
[deep/code/tool/INPUT_SCHEMA.md](deep/code/tool/INPUT_SCHEMA.md).

Best practice: JSON-stringify structured results before returning, and write error
messages the agent can act on — it reads your failures.

### The named errors

| Error | Cause |
|---|---|
| `Wrong output type returned` | returned `[{json:{}}]` instead of a string |
| `The response property should be a string, but it is an object` | returned an object |
| `No execution data available` | used `$fromAI()` or `$input` in the tool sandbox |
| `Cannot assign to read only property 'name' of object` | same root cause — Code-node APIs in the tool sandbox |
| the agent never calls the tool | the name or description does not tell the LLM when to use it |

Full fixes: [deep/code/tool/ERROR_PATTERNS.md](deep/code/tool/ERROR_PATTERNS.md).

### When something else is the better tool

Reach for `toolWorkflow` (a sub-workflow as a tool) when the logic needs real workflow
nodes — see [workflow-design.md](workflow-design.md) and
[deep/agents/SUBWORKFLOW_AS_TOOL.md](deep/agents/SUBWORKFLOW_AS_TOOL.md). Reach for the
HTTP Request Tool when the tool is just an API call.
