# Route: Validate and debug

Owns reading validation output and knowing what actually needs fixing — plus the manual scan
the validator cannot do.

**Framing that matters:** validation passing means the JSON is **well-formed**, not that the
workflow is **correct**. Validation is iterative, not one-shot — expect 2–3 validate → fix
cycles.

## The antipattern scan — run this node by node

`validate_workflow` catches **none** of the following. Only the manual scan does, and it is
the difference between "validated" and "will work in production".

- **Set nodes feeding only one consumer** should be inlined at the consumer. →
  [workflow-expressions.md](workflow-expressions.md)
- **Code nodes doing pure field shaping** should be Edit Fields with arrow functions. →
  [workflow-code.md](workflow-code.md)
- **Merges with 3+ wires** need `numberOfInputs` set explicitly, or the third source
  silently drops.
- **`$json.x` in branchy workflows** should be `$('Node').item.json.x`.
- **DateTime nodes** should be Luxon expressions.

Also verify, every time:

- **The `connections` object**, with `n8n_get_workflow` after applying operations.
  `validate_workflow` does not catch every multi-input wiring trap.
- **Error outputs are wired *and* enabled** — the two-step trap in
  [workflow-errors.md](workflow-errors.md) validates clean while silently swallowing
  failures.
- **Binary survived** where a file must reach a consumer — a stripped `$binary` slot is a
  silent failure. → [workflow-binary.md](workflow-binary.md)

## Severity: what blocks and what advises

**Errors — must fix.** Block execution. Types: `missing_required`, `invalid_value`,
`type_mismatch`, `invalid_reference`, `invalid_expression`.

```json
{"type": "missing_required", "property": "channel",
 "message": "Channel name is required",
 "fix": "Provide a channel name (lowercase, no spaces, 1-80 characters)"}
```

**Warnings — should fix.** Do not block activation.

| Type | Surfaces under |
|---|---|
| `security` (hardcoded secrets, unauthenticated webhooks) | **every** profile — treat as real |
| `deprecated` (old API or feature) | **every** profile — treat as real |
| `best_practice` | `ai-friendly` / `strict` only — advisory |
| `performance` | `ai-friendly` / `strict` only — advisory |

**Suggestions — optional.** `optimization`, `alternative`.

## Profiles

Pass `profile` explicitly. `runtime` is the recommended default; `strict` for
pre-activation review; `ai-friendly` when building agent nodes; `minimal` for a fast
structural check. See [shared/mcp-tools.md](shared/mcp-tools.md).

## False positives: mostly gone, advisories remain

The validator overhaul (n8n-mcp ≥ 2.63.0) removed the classic false positives — template
literals inside expressions, optional chaining, omitted-operation defaults, the Webhook →
Respond-to-Webhook pattern, IF/Filter legacy shapes. **There is no standing list of "known
false positives to ignore."** If you see those fire, the server is old — upgrade.

What remains are **best-practice advisories** flagging a real trade-off that may be
acceptable in context:

| Advisory | Acceptable when | Worth fixing when |
|---|---|---|
| "…without error handling" | dev/testing, non-critical notifications | production handling important data |
| "No retry logic" | idempotent ops, APIs with their own retry, manual triggers | flaky external services, production automation |
| "…rate limits and transient failures" | internal, low-volume, server-side-limited APIs | public, high-volume APIs |
| "Unbounded query" | small known datasets, aggregations, dev/testing | production queries on large tables |

Security and deprecation warnings, by contrast, are real under every profile. →
[deep/validate/FALSE_POSITIVES.md](deep/validate/FALSE_POSITIVES.md)

## Auto-sanitization: trust it, don't hand-fix

n8n normalizes common operator structures on **any** workflow update — create, partial
update, or any save:

- **Binary operators** (equals, notEquals, contains, greaterThan, startsWith, …) — removes a
  stray `singleValue` property.
- **Unary operators** (isEmpty, isNotEmpty, true, false) — adds `singleValue: true`.
- **IF/Switch metadata** — fills in `conditions.options` for IF v2.2+ and Switch v3.2+.

Validation no longer errors on these shapes (n8n-mcp ≥ 2.63.0): n8n derives unary-ness from
the operator name and defaults the options sub-fields, so a condition is accepted whether or
not the metadata is present. The sanitizer just tidies the canonical form on save.

**Still real errors:** a v1-shaped `conditions` object on a v2 node, an empty filter with no
conditions, and legacy v1 operator names (e.g. `smaller`) inside a v2 structure.

**What the sanitizer CANNOT fix** — handle manually: broken connections to non-existent
nodes (use `cleanStaleConnections`), branch-count mismatches (add or remove connections or
rules), and paradoxical corrupt states.

→ [deep/validate/ERROR_CATALOG.md](deep/validate/ERROR_CATALOG.md)

## The validation loop

1. `validate_node({nodeType, config, profile: "runtime"})` on each node as you configure it.
2. Read `errors`, fix the config, validate again until clean.
3. `validate_workflow` on the whole thing.
4. `n8n_autofix_workflow` for mechanical fixes, then re-validate.
5. **Run the antipattern scan above.**
6. `n8n_get_workflow` and inspect `connections`.
7. Only then activate.

## Reviewing an existing workflow

For a full pre-activation or handover review, work through
[deep/validate/REVIEW_CHECKLIST.md](deep/validate/REVIEW_CHECKLIST.md) — it covers
credential hygiene, injection surfaces, silent-drop node families, and error-path coverage,
with line-level pointers into the other routes.

## Deeper references

| Read when | File |
|---|---|
| Decoding a specific error type or sanitization behavior | [deep/validate/ERROR_CATALOG.md](deep/validate/ERROR_CATALOG.md) |
| Deciding whether an advisory needs action | [deep/validate/FALSE_POSITIVES.md](deep/validate/FALSE_POSITIVES.md) |
| Reviewing a whole workflow before activation | [deep/validate/REVIEW_CHECKLIST.md](deep/validate/REVIEW_CHECKLIST.md) |
| Choosing tools and profiles | [deep/validate/VALIDATION_GUIDE.md](deep/validate/VALIDATION_GUIDE.md) |
