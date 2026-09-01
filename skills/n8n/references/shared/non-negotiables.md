# Non-negotiables

Three rules with no exceptions. Each prevents a class of workflow that looks correct and
breaks in production.

## 1. Read the relevant route reference before any n8n action

Not just before MCP calls. Before writing an expression, configuring a node, designing a
workflow, wiring a connection, or writing Code, read the route that owns it. The route
table is in `SKILL.md`.

PreToolUse hooks remind you on the highest-impact tool calls, but they exist **only in the
Claude Code plugin install**. Everywhere else — Claude.ai skill uploads, and any client
that loads this pack as an Agent Plugin (Codex, Cursor, Copilot and the rest) — nothing
nudges you and the responsibility is entirely yours. **Assume you are un-hooked unless you
have seen a hook fire this session.**

## 2. Validate *and* verify before activating

Run `validate_workflow` (or `n8n_validate_workflow` by id) before you activate, and call
`n8n_get_workflow` after every create or update to inspect the `connections` object.

Validation alone misses silently dropped wires, Merge index off-by-one, and error outputs
that were never wired. **Validation passing means the JSON is well-formed — not that the
workflow is correct.** The antipattern scan in
[../workflow-validate.md](../workflow-validate.md) catches what the validator cannot.

## 3. Secrets never go in text fields

Tokens, API keys and passwords always go through the n8n credential system. If no native
node exists, use the HTTP Request node with the official credential type.

A Set node holding a token referenced via `{{ $json.token }}` is a leak with extra steps.
Same for a token pasted into a Code node. See
[../workflow-instances.md](../workflow-instances.md) for credential discovery and the
correct `{id, name}` shape, and [mcp-tools.md](mcp-tools.md) for why a placeholder
credential ID breaks the n8n UI.

## Lean on the references, not on training data

n8n changes constantly. "Remembered" parameter names are often silently wrong — they
validate as plain strings and then do nothing at runtime. Trust these references and the
live tools (`get_node`, `search_nodes`, `tools_documentation`) over recollection.

If a reference contradicts your memory, trust the reference. If `get_node` contradicts a
reference, trust the tool and flag the drift — see [drift.md](drift.md).
