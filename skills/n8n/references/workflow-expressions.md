# Route: Expressions

Owns `{{ }}` syntax, variable access, and the decision of *where* a transform belongs.

## Format

An expression field starts with `=` and wraps the expression in `{{ }}`:
`={{ $json.body.email }}`. Always use `{{ }}` — a bare value is a literal string. Quote
keys containing spaces or special characters: `{{ $json["first name"] }}`.

## Core variables

| Variable | Is |
|---|---|
| `$json` | the **current** node's incoming item |
| `$('Node Name').item.json` | a specific node's item, matched by pairing |
| `$now` | current timestamp, a Luxon `DateTime` |
| `$env` | environment variables (often restricted on hosted n8n) |

## The single most common mistake: webhook data is not at the root

The Webhook node wraps incoming data under `.body` to preserve headers, params and query:

```javascript
{
  "headers": {...}, "params": {...}, "query": {...},
  "body": { "name": "John", "email": "john@example.com" }   // ⚠️ user data is HERE
}
```

```javascript
{{ $json.name }}        // ❌ undefined
{{ $json.body.name }}   // ✅
{{ $json.body.email }}  // ✅
```

If a webhook-driven field is mysteriously empty, check for the missing `.body` first.
Depth: [deep/expressions/COMMON_MISTAKES.md](deep/expressions/COMMON_MISTAKES.md).

## The transform gatekeeper

Before adding any node — or writing any code — to transform data, walk this order and stop
at the first that fits.

1. **Expression in the consuming field.** Property access, method chains
   (`.map().filter().join()`), ternaries, string building, Luxon date math. If it is "take
   A, produce B" with no intermediate variables, it is an expression. This covers most
   cases.
2. **Arrow-function IIFE inside an Edit Fields field.** When the logic needs intermediate
   variables, branching or comments but still operates on one item:

   ```
   ={{ (() => {
       const items = $json.line_items;
       const subtotal = items.reduce((sum, it) => sum + it.price * it.qty, 0);
       const tax = subtotal * 0.08;
       return (subtotal + tax).toFixed(2);
   })() }}
   ```

   The outer `(...)` brackets the function, the trailing `()` invokes it — drop either and
   n8n refuses to run. Inside you get the full expression scope (`$json`, `$('Node')`,
   `$now`, Luxon) plus `const`/`let`, `if`/`switch`, `try`/`catch` and regex. No
   `require`, no `await`.
3. **Code node — last resort.** Only for multi-item aggregation across the whole dataset
   (`$input.all()`), an allowlisted library, or async work. See
   [workflow-code.md](workflow-code.md).

**Why the order matters, beyond style.** The Code node runs in a sandboxed VM with
per-invocation setup and value marshaling — a cold-start cost that can reach 500–1000 ms
before your logic runs. (It amortizes on warm, high-item-count runs, so treat that as a
common-case cost, not a constant.) The same logic in an expression or an Edit Fields IIFE
runs in-process in single-digit milliseconds and skips the sandbox entirely. For pure
single-item shaping that is a large gap with no functional difference, and it compounds on
hot paths like per-request webhooks. The expression also stays visible in the field that
uses it instead of hiding in an upstream node someone has to open.

## The Set-node antipattern

A Set / Edit Fields node whose only job is to extract a value and hand it to **one**
downstream node is dead weight.

```
❌  Webhook → Set { customer_id: {{ $json.body.customer_id }} }
            → Postgres: WHERE id = {{ $json.customer_id }}

✅  Webhook → Postgres: WHERE id = {{ $('Webhook').item.json.body.customer_id }}
```

**Quick test:** count how many downstream nodes reference each field the Set produces.
**0 or 1** → delete it and inline at the consumer. **2+** → it may earn its place.

To remove one cleanly with `n8n_update_partial_workflow`: `removeConnection` from the Set's
source and target, `addConnection` straight from source to consumer, `patchNodeField` the
consumer's expression to reference the original source by node name, then `removeNode` the
Set.

**Legitimate exceptions — keep the Set when:**

- **2+ consumers** read the same non-trivially derived value (a name aids readability and
  you compute it once).
- **It is a sub-workflow's final Return node**, shaping the output contract. Here the
  "single consumer" is every caller, so the Set *is* the API boundary — and with
  `Include Other Fields: false` it whitelists the output shape so internal scratch fields
  do not leak.
- **You are renaming or whitelisting fields** and want that visible in one place.

## Branch convergence: anchor with a NoOp

When branches converge (after IF / Switch / Merge), `$json` becomes "whichever branch fired
last" — non-deterministic, and a silent source of wrong data. Insert a **NoOp** at the
convergence, name it descriptively, and reference it by name downstream:

```
Branch A ──┐
           ├─→ [NoOp: Combine Inputs] ──→ $('Combine Inputs').item.json.x
Branch B ──┘
```

The NoOp survives refactors: inserting a transform later between it and the consumer does
not break the reference. If the branches produce *different* shapes, use a Set node instead
to normalize them.

More broadly in branchy flows, **prefer `$('Node').item.json.x` over deep `$json.x`.**
`$json` breaks the moment an intermediate node is inserted or a node clears item context
(Aggregate, Code with Run for All, branching merges) — and the failure is silent, with
downstream getting wrong data and no error.

## When NOT to use an expression

- **Inside Code nodes.** Code uses `$input` / `$json` directly, without `{{ }}`.
- **Webhook paths.** Static values only.
- **Credential fields.** Use the credential system — see
  [shared/non-negotiables.md](shared/non-negotiables.md).

## Date math

Inline Luxon is almost always right; a DateTime node is rarely needed.
`{{ $now.minus({days: 7}).toISO() }}`.

## Deeper references

| Read when | File |
|---|---|
| An expression returns undefined or the wrong value | [deep/expressions/COMMON_MISTAKES.md](deep/expressions/COMMON_MISTAKES.md) |
| You want a worked example of a shape you are building | [deep/expressions/EXAMPLES.md](deep/expressions/EXAMPLES.md) |
