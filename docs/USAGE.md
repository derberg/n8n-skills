# Usage

## You do not invoke it by name

There is one skill, and its description covers any n8n task. Mention n8n — or a workflow
node, or an n8n expression — and it applies:

> "Build me a workflow that receives a Stripe webhook, updates Postgres, and posts to Slack"

> "Why is `$json.name` undefined in my Code node after a webhook?"

> "My workflow validates fine but drops items somewhere"

> "Deploy n8n on my Hetzner box at n8n.example.com"

> "Give this agent a tool that reads a PDF and returns a summary"

## How routing works

1. Claude reads `SKILL.md` (~9 KB). That gives it the MCP tool basics, the five shared
   rules, and a routing table.
2. It picks the routes the task needs and reads those `references/workflow-*.md` files.
3. Those routes point into `references/deep/` for the depth — worked examples, error
   catalogs, per-node-family gotchas — read only if the task reaches that far.

So a question about a Code node return format reads `SKILL.md` → `workflow-code.md`, and
only opens `deep/code/js/ERROR_PATTERNS.md` if the answer is not already there.

**Mixed intents are normal.** "Build a webhook that calls an API and handles failures" is
Design + Error handling + Validate, and Claude should read all three. The skill tells it to
read more rather than fewer when unsure.

## The ten routes

| Ask about… | Route |
|---|---|
| Architecture, sub-workflows, batch sizing | `workflow-design` |
| Node parameters, required fields, hidden fields | `workflow-nodes` |
| `{{ }}`, `$json`, `$node`, Set nodes, date math | `workflow-expressions` |
| Code node (JS or Python), agent Code Tool | `workflow-code` |
| AI agents, tools, memory, structured output, RAG | `workflow-agents` |
| Files, images, PDFs, `$binary` | `workflow-binary` |
| `onError`, retries, status codes, error workflows | `workflow-errors` |
| Validation errors, pre-activation review | `workflow-validate` |
| Creating/updating workflows, credentials, multiple instances | `workflow-instances` |
| Deploying and operating self-hosted n8n | `workflow-self-host` |

## What the hooks add

In a Claude Code plugin install, seven `PreToolUse` hooks fire on high-impact n8n MCP tool
calls and inject a short reminder at exactly the moment it matters:

| Before | You get |
|---|---|
| `n8n_create_workflow` | pick an architecture; search for an existing sub-workflow before duplicating logic |
| `get_node` | configuration is operation-aware — plus a node-specific warning for Set, Code, Merge, Loop Over Items, DateTime, Data Table and the LangChain Agent |
| `n8n_update_*_workflow` | verify the `connections` object afterwards; Merge and error-output traps |
| `validate_workflow` | the antipattern scan, node by node |
| `n8n_test_workflow` | **this executes real nodes** — HTTP calls, DB writes, Slack and email sends all fire |
| `n8n_instances` | every call routes to the currently-targeted instance; switch in its own turn |
| `n8n_manage_credentials` | verify the target instance before writing a secret |

One `PostToolUse` hook fires after `validate_workflow` and lists the routes worth reading
based on which node types the workflow actually contains.

Each reminder fires **once per session** and resets on `/clear` and `/compact`. They cost
nothing when no n8n MCP server is connected.

## What it will push back on

The skill encodes some opinions, and Claude will surface them:

- **The Code node is a last resort.** Expression → arrow-function IIFE in Edit Fields →
  Code node, in that order.
- **A Set node feeding one consumer should be deleted** and its expression inlined.
- **Validation passing is not "done."** Expect Claude to run an antipattern scan and check
  `connections` before calling a workflow finished.
- **It will ask before running anything with side effects**, and say afterwards which nodes
  ran live.
- **It will ask single-vs-queue before a self-host deploy**, rather than guessing.
- **When a live tool contradicts the pack, the tool wins** — and Claude should tell you the
  pack is out of date rather than quietly working around it.

## When the tools are not there

If the `n8n_*` management tools are missing, Claude should say so plainly and continue with
read-only work (node lookup, validation, templates) rather than pretending. If **no**
`n8n-mcp` tools are present at all, it should stop rather than reconstruct node schemas from
memory — remembered parameter names validate as plain strings and then do nothing at
runtime, which is the single most expensive failure mode in n8n.

See [INSTALLATION.md](INSTALLATION.md#two-tiers-of-tools) for which tier needs what.
