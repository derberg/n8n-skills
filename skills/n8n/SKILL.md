---
name: n8n
description: Use for ANY n8n task — building, editing, validating, testing, debugging, or deploying n8n workflows through the n8n-mcp MCP server. Covers workflow architecture, node configuration, expressions ({{}}, $json, $node), Code nodes (JavaScript/Python) and the AI-agent Code Tool, AI agents and tool calling, binary/file handling, sub-workflows, error handling and retries, validation errors, credentials and multi-instance targeting, and self-hosting n8n with Docker. If the user mentions n8n, n8n-mcp, a workflow node, or an n8n expression, this skill applies.
---

# n8n

Single entry point for every n8n task. This file is a **router**: it names the reference
that owns the rules for what you are about to do. The references hold the actual guidance
— read them with the Read tool. When in doubt, read more rather than fewer.

## MCP server

This skill drives the **`n8n-mcp`** server. Tool names are qualified as
`mcp__<server>__<tool>`, where `<server>` is usually `n8n-mcp`.

**Two tiers, and how to tell which you have.** The documentation and validation tools
(`search_nodes`, `get_node`, `validate_node`, `validate_workflow`, `tools_documentation`)
work offline and are always present. The `n8n_*` management tools talk to a live n8n
instance and appear **only once one is connected**.

If the `n8n_*` tools are absent, nothing is broken and there is nothing to retry. Say so
plainly: the server needs `N8N_API_URL` and `N8N_API_KEY` in its environment, exported
before the client starts. Read-only work (node lookup, validation, templates) still works.

If **no** `n8n-mcp` tools are present at all, say so and stop. Do not reconstruct node
schemas, parameter shapes or `typeVersion`s from memory — see
`references/shared/drift.md`.

For tool selection, `nodeType` formats, validation profiles and detail levels, read
`references/shared/mcp-tools.md`.

## Shared rules

These apply to every route.

1. **Read the referenced file before acting.** When a route or a step points at another
   file, open it with the Read tool first — even when the action feels familiar. Never
   reconstruct a referenced procedure from memory. Routes deliberately delegate their
   detail; skipping the read means skipping the rules.
2. **Validate *and* verify before activating.** Run `validate_workflow` before you
   activate, and call `n8n_get_workflow` after every create or update to inspect the
   `connections` object. Validation passing means the JSON is well-formed, not that the
   workflow is correct. Then run the antipattern scan in
   `references/workflow-validate.md`.
3. **Configure from the live schema, never from memory.** Call `get_node` before you set
   parameters. Remembered parameter names are often silently wrong — they validate as
   plain strings and then do nothing at runtime.
4. **Secrets never go in text fields.** Tokens, API keys and passwords always go through
   the n8n credential system. A Set node holding a token referenced via
   `{{ $json.token }}` is a leak with extra steps. See `references/workflow-instances.md`.
5. **Ask before side effects.** `n8n_test_workflow` executes real nodes — HTTP calls,
   database writes, Slack and email sends and sub-workflow calls all fire for real. Ask
   first if any node has user-visible side effects, and afterwards say which nodes ran
   live. See `references/workflow-errors.md`.

The three rules that have no exceptions are in `references/shared/non-negotiables.md`.
Read it on any workflow-modifying task.

## Route table

Determine which route the task needs, then read that reference before proceeding.

| Intent | Trigger | Reference to read |
|---|---|---|
| **Design** | Designing or building a workflow; picking an architecture (webhook / HTTP API / database / AI agent / scheduled / batch); extracting shared logic; anything reused or over ~10 nodes; Execute Workflow; "Define Below" inputs; mode each vs all | `references/workflow-design.md` |
| **Configure a node** | Configuring any node; which fields an operation requires; property dependencies and `displayOptions`; surgical field edits with `patchNodeField`; node discovery | `references/workflow-nodes.md` |
| **Expressions** | Writing `{{ }}`; `$json` / `$node` / `$now`; mapping data between nodes; referencing webhook data; Set-node discipline; date math | `references/workflow-expressions.md` |
| **Code** | Any Code node (JavaScript or Python), or the AI-agent-callable Custom Code Tool (`@n8n/n8n-nodes-langchain.toolCode`); `$input` / `this.helpers`; SplitInBatches loops; `pairedItem` | `references/workflow-code.md` |
| **AI agents** | AI Agent, LLM chain, Text Classifier, Information Extractor; tool design and `$fromAI`; system prompts; structured output; memory and `sessionId`; RAG; human review; chat bots | `references/workflow-agents.md` |
| **Files and binary** | Files, images, PDFs, attachments, uploads and downloads, base64, vision input; `$binary`; `binaryPropertyName`; Merge losing binary; passing a file to or from an agent tool | `references/workflow-binary.md` |
| **Error handling** | Any webhook / API or unattended workflow; `onError`; error branches and outputs; retries; Respond to Webhook status codes; 4xx/5xx; Error Trigger; "it fails silently" | `references/workflow-errors.md` |
| **Validate and debug** | A validation error or warning you need to interpret; false positives; the validation loop; auto-fix; reviewing an existing workflow before activation | `references/workflow-validate.md` |
| **Instance lifecycle** | Creating, updating, listing or testing workflows; folders; credentials; instance security audit; accounts with more than one instance (the `n8n_instances` tool is present); an unexpected `NOT_FOUND` or `INSTANCE_AMBIGUOUS` | `references/workflow-instances.md` |
| **Self-host** | *Deployment, not workflow-building.* Self-hosting, installing or deploying n8n on your own server or VPS (Docker Compose + Caddy, single or queue mode); updating, backing up or hardening it; credential overwrites | `references/workflow-self-host.md` |

## Red flags: "about to ___" → read ___

If you catch yourself thinking any of these, stop and read the named reference first.

| Thought | Read |
|---|---|
| "This workflow is simple, I'll just build it" | `workflow-design` — most "simple" flows ship at 10+ nodes |
| "I'll add a Set node to map these fields" | `workflow-expressions` — a Set node feeding ≤1 consumer is the #1 antipattern |
| "I'll just use a Code node, it's easier" | `workflow-code` — the bar is high; most reaches are expressions or Edit Fields |
| "The user mentioned data, I'll write Python" | `workflow-code` — JavaScript is the default; Python only on explicit ask |
| "I'm writing code an AI agent will call" | `workflow-code` — the Code Tool is a different runtime contract from the Code node |
| "Date math — I'll drop in a DateTime node" | `workflow-expressions` — inline Luxon is almost always right |
| "I'll wire a Merge with 3 sources" | `workflow-nodes` — Merge defaults to 2 inputs; the 3rd silently drops |
| "Validation passed, I'm ready to activate" | `workflow-validate` — run the antipattern scan |
| "Validation threw an error I don't understand" | `workflow-validate` — which errors must be fixed and which are advice |
| "I'll reference `$json.x` here" | `workflow-expressions` — prefer `$('Node').item.json.x` in branchy workflows |
| "This webhook or scheduled flow is happy-path only" | `workflow-errors` — wire an error branch on every fallible node |
| "I'll pass this file through as JSON" | `workflow-binary` — file contents live in `$binary` and can't cross the agent-tool boundary |
| "I'll give the model some tools" | `workflow-agents` — tool names and descriptions *are* the prompt |
| "I'll copy this logic into another workflow" | `workflow-design` — extract a sub-workflow; search before building |
| "I'll create that credential" (account has >1 instance) | `workflow-instances` — every call hits the currently-targeted instance; reads misroute silently |

## Strong defaults

Each route owns its own exceptions; these are the defaults.

- **The Code node is a last resort.** Expression first, then an arrow function inside Edit
  Fields, then a Code node only when neither can do the job.
- **A Set node feeding 0–1 consumers is almost always wrong.** Inline the expression at
  the consumer instead.
- **Per-item iteration is automatic.** Don't add a Loop Over Items node to "make it loop"
  when default per-item execution already handles the case.
- **Trust the live tool over this pack.** n8n and n8n-mcp move faster than any model's
  training data and faster than these references. See `references/shared/drift.md`.

## Mixed intents

Overlapping intents are the norm, not the exception. "Build a webhook that calls an API
and handles failures" is **Design + Error handling + Validate**. "Give this agent a tool
that reads a PDF" is **AI agents + Files and binary + Code**. Read every relevant
reference; when unsure whether a route applies, read it.
