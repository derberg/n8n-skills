> ### Fork of [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills)
>
> Same n8n knowledge, restructured packaging. What changed:
>
> - **One skill, not fifteen.** A single `n8n` skill routes to ten workflow
>   references read on demand. Upstream's fifteen skill descriptions became one.
> - **Nothing is injected into your sessions.** Upstream's `SessionStart` hook loaded
>   its router skill into *every* session regardless of topic, costing roughly 700
>   tokens whether or not you were touching n8n. Removed.
> - **Local MCP server, pinned.** No hosted `api.n8n-mcp.com` endpoint; `n8n-mcp` runs
>   locally over stdio at a pinned version, against your own n8n.
> - **Telemetry off.** `n8n-mcp` enables telemetry by default; this fork sets
>   `N8N_MCP_TELEMETRY_DISABLED=true`.
>
> **Install this fork:** `/plugin marketplace add derberg/n8n-skills` then
> `/plugin install n8n-skills@derberg-n8n-skills` — and
> `/plugin uninstall n8n-skills@derberg-n8n-skills` to remove it.
>
> To unlock the workflow-management tools, set `N8N_API_URL` and `N8N_API_KEY`
> once via the `env` key of a Claude Code settings file — gitignored
> `.claude/settings.local.json` in your project, or `~/.claude/settings.json`
> machine-wide. Without them the MCP server runs docs-only.
>
> Upstream owns the n8n expertise and deserves the credit for it. See
> [CHANGELOG.md](CHANGELOG.md) for detail.

# n8n-skills

**One Claude Code skill for building n8n workflows with the n8n-mcp MCP server**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![n8n-mcp](https://img.shields.io/badge/n8n--mcp-compatible-green.svg)](https://github.com/czlonkowski/n8n-mcp)

---

## What is this?

A single skill — `n8n` — that teaches Claude how to build production-ready n8n workflows,
and how to deploy the self-hosted n8n that runs them.

Its `SKILL.md` is an **orchestrator**, not a reference. It carries the MCP tool basics, the
rules that apply to every task, and a routing table. The actual guidance lives in ten
`references/workflow-*.md` files that are read only when the task needs them, backed by 51
deeper knowledge files under `references/deep/`.

That means a session that never mentions n8n pays for one line in the skill list, and a
session that does pays only for the routes it actually uses.

### Why it exists

Building n8n workflows programmatically goes wrong in predictable ways: MCP tools used with
the wrong `nodeType` format, validation error loops, workflows that validate clean and drop
data at runtime, node parameters configured from memory that silently do nothing.

## The routes

| Intent | Covers | Reference |
|---|---|---|
| **Design** | Architecture patterns (webhook / HTTP API / database / AI agent / scheduled / batch), sub-workflow extraction, `mode` and `waitForSubWorkflow`, batch sizing | `workflow-design.md` |
| **Configure a node** | Operation-aware required fields, `displayOptions`, detail levels, dynamic properties, node-family traps | `workflow-nodes.md` |
| **Expressions** | `{{ }}`, `$json` / `$node`, the webhook `.body` gotcha, the transform gatekeeper, the Set-node antipattern | `workflow-expressions.md` |
| **Code** | Code node JavaScript and Python, plus the AI-agent Custom Code Tool — all three runtimes and their different contracts | `workflow-code.md` |
| **AI agents** | Agent vs chain vs classifier, the sub-node slots, tools and `$fromAI`, structured output, memory, RAG, human review, chat loops | `workflow-agents.md` |
| **Files and binary** | The `$binary` / `$json` split, keeping binary alive across transforms, the agent-tool boundary, the CDN requirement | `workflow-binary.md` |
| **Error handling** | `onError` and the two-step error-output trap, retries, 4xx/5xx response shapes, error workflows | `workflow-errors.md` |
| **Validate and debug** | Reading validation output, advisories vs real errors, auto-sanitization, the antipattern scan | `workflow-validate.md` |
| **Instance lifecycle** | Workflow CRUD, credentials, folders, data tables, security audit, multi-instance targeting | `workflow-instances.md` |
| **Self-host** | Docker Compose behind Caddy with automatic TLS, single vs queue mode, day-2 update/backup/restore, hardening | `workflow-self-host.md` |

Cross-cutting rules live in `references/shared/`: `mcp-tools.md` (tool selection,
`nodeType` formats, validation profiles), `non-negotiables.md`, and `drift.md`.

## Enforcement layer (hooks)

The skill description is what makes Claude reach for the skill. The hooks are the backstop
for when it does not.

Seven `PreToolUse` hooks fire on high-impact n8n MCP tool calls — `n8n_create_workflow`,
`n8n_update_*_workflow`, `validate_workflow`, `n8n_test_workflow`, `n8n_instances`,
`n8n_manage_credentials`, `get_node` — and inject a short reminder pointing at the right
route, plus the specifics that arrive best at the moment of decision (the antipattern scan;
the warning that `n8n_test_workflow` fires real HTTP calls, database writes and Slack
sends). One `PostToolUse` hook gates activation after `validate_workflow`.

Every matcher is anchored to an MCP tool name, so **the hooks cost nothing in a session
with no n8n MCP server connected.**

A `SessionStart` hook runs on `/clear` and `/compact` only, and injects **nothing** — it
exists solely to reset the per-session dedup markers, so the reminders can fire again after
your context has been reset.

## Installation

### Prerequisites

- **Claude Code**, or any client that loads Agent Plugins
- **Node.js**, for the local `n8n-mcp` server
- An **n8n instance** if you want the workflow-management tools (see below)

### Claude Code

```bash
/plugin marketplace add derberg/n8n-skills
/plugin install n8n-skills@derberg-n8n-skills
```

Or clone and load it directly:

```bash
git clone https://github.com/derberg/n8n-skills.git
claude --plugin-dir ./n8n-skills
```

### The MCP server

The plugin ships [mcp.json](mcp.json) pointing at a **local, version-pinned** `n8n-mcp`
over stdio, with telemetry disabled:

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["-y", "n8n-mcp@2.77.0"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true",
        "N8N_MCP_TELEMETRY_DISABLED": "true",
        "N8N_API_URL": "${N8N_API_URL}",
        "N8N_API_KEY": "${N8N_API_KEY}"
      }
    }
  }
}
```

**Two tiers of tools.** The documentation and validation tools (`search_nodes`, `get_node`,
`validate_node`, `validate_workflow`) work offline with no configuration. The `n8n_*`
management tools need a live instance, so export these before starting your client:

```bash
export N8N_API_URL="https://your-n8n.example.com"
export N8N_API_KEY="…"
```

Nothing is committed, and nothing leaves your machine except calls to your own n8n.
[.mcp.json.example](.mcp.json.example) has the same block for wiring the server into your
own project config instead of installing the plugin.

## Usage

Mention n8n and the skill applies — you do not invoke it by name:

> "Build me a workflow that receives a Stripe webhook, updates Postgres, and posts to Slack"

> "Why is `$json.name` undefined in my Code node after a webhook?"

> "Deploy n8n on my Hetzner box at n8n.example.com"

Claude reads `SKILL.md`, picks the routes from the table, and reads deeper only where
needed.

## Development

```bash
python3 scripts/validate-pack.py   # structural gate — must pass before any commit
bash build.sh                      # build distribution zips
```

`validate-pack.py` checks the skill frontmatter and its size budget, that every route file
exists and is listed in the routing table, that every internal link resolves, that no old
skill name has crept back in, hook wiring and the no-injection rule, the MCP configuration,
manifest agreement, and the eval suite.

Adding a route: create `references/workflow-<name>.md`, add a row to the `SKILL.md` table,
add the name to `ROUTES` in `scripts/validate-pack.py`, and add an eval. See
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Documentation

- [docs/INSTALLATION.md](docs/INSTALLATION.md) — detailed install and MCP setup
- [docs/USAGE.md](docs/USAGE.md) — how routing works in practice
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — contributing and structure
- [docs/CODE_NODE_BEST_PRACTICES.md](docs/CODE_NODE_BEST_PRACTICES.md) — Code node reference
- [CHANGELOG.md](CHANGELOG.md) — what diverged from upstream

## License

MIT — see [LICENSE](LICENSE).

## Credits

**The n8n expertise in this pack is Romuald Członkowski's.** It comes from
[czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) and the
[n8n-mcp project](https://github.com/czlonkowski/n8n-mcp) — [www.aiadvisors.pl/en](https://www.aiadvisors.pl/en).
This fork changes the packaging, not the knowledge.

The hooks layer adapts patterns from the official [n8n Skills](https://github.com/n8n-io/skills)
project (Apache-2.0). See [NOTICES](NOTICES).

Upstream also has an [introduction video](https://youtu.be/e6VvRqmUY2Y) covering the
original fifteen-skill pack.

## Related

- [n8n-mcp](https://github.com/czlonkowski/n8n-mcp) — MCP server for n8n
- [n8n](https://n8n.io/) — workflow automation platform
