# Installation

## Prerequisites

1. **Claude Code**, or any client that loads Agent Plugins (Codex, Cursor, Copilot, …)
2. **Node.js**, so `npx` can launch the local `n8n-mcp` server
3. An **n8n instance**, only if you want the workflow-management tools — see
   [Two tiers of tools](#two-tiers-of-tools)

## Claude Code

### Plugin install (recommended)

```bash
/plugin marketplace add derberg/n8n-skills
/plugin install n8n-skills
```

This wires the skill, the hooks and the MCP server together.

### Load from a clone

```bash
git clone https://github.com/derberg/n8n-skills.git
claude --plugin-dir ./n8n-skills
```

### Skill only, no plugin

The skill is self-contained. Copy the one directory:

```bash
git clone https://github.com/derberg/n8n-skills.git
cp -r n8n-skills/skills/n8n ~/.claude/skills/
```

You lose the hooks (the enforcement layer) and the bundled MCP config, which you then wire
yourself — see below.

## The MCP server

The plugin ships [`mcp.json`](../mcp.json) pointing at a **local, version-pinned**
`n8n-mcp` over stdio:

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

Three things to know about it.

**It is local and pinned.** Upstream pointed at the hosted `https://api.n8n-mcp.com/mcp`
endpoint, which sends node lookups and workflow queries to a third party and cannot target
your own n8n. This fork runs the server on your machine, at an exact version rather than
whatever `npx n8n-mcp` resolves to at spawn time.

**Telemetry is disabled.** `n8n-mcp` ships telemetry **enabled by default** — it is opt-out
only, and the package includes a workflow sanitizer and mutation tracker, meaning it reports
sanitized workflow content. `N8N_MCP_TELEMETRY_DISABLED=true` turns it off.
`TELEMETRY_DISABLED` and `DISABLE_TELEMETRY` are also accepted; `true` or `1` disables.

**Credentials come from your environment**, so nothing secret is committed:

```bash
export N8N_API_URL="https://your-n8n.example.com"
export N8N_API_KEY="…"
```

Export them **before** starting your client — the MCP server reads them at spawn time.

> `${VAR}` expansion is confirmed working in a project `.mcp.json`. If your client does not
> expand it in a *plugin-level* `mcp.json`, drop those two lines and set the variables in
> your own `.mcp.json` or shell profile instead. Check with `/mcp`: if the `n8n_*` tools are
> missing while `search_nodes` is present, the API URL and key did not arrive.

### Wiring it into your own project instead

Copy [`.mcp.json.example`](../.mcp.json.example) to `.mcp.json` in your project. It carries
the same server block.

## Two tiers of tools

| Tier | Tools | Needs |
|---|---|---|
| **Documentation and validation** | `search_nodes`, `get_node`, `validate_node`, `validate_workflow`, `tools_documentation`, template search | nothing — works offline |
| **Instance management** | every `n8n_*` tool: create/update/get/list/test workflows, credentials, folders, data tables, audit, instances | `N8N_API_URL` + `N8N_API_KEY` |
| **Token-gated extras** | `n8n_manage_agents`, `n8n_explore_node_resources`, data-table column actions, `n8n_test_workflow` pinned/direct methods, native version history | additionally `N8N_MCP_ACCESS_TOKEN` |

If the `n8n_*` tools are absent, nothing is broken and there is nothing to retry. The skill
is written to say so plainly and carry on with read-only work.

## Claude.ai

One skill means one upload.

1. `bash build.sh`, then take `dist/n8n-v<version>.zip` (or grab it from the
   [latest release](https://github.com/derberg/n8n-skills/releases/latest)).
2. Upload via Settings → Capabilities → Skills.

The hooks do not exist outside the Claude Code plugin install. The skill's
`references/shared/non-negotiables.md` states this explicitly — assume you are un-hooked
unless you have seen a hook fire.

## Other agents and IDEs

`skills/n8n/` is a self-contained folder with a `SKILL.md` entry point plus reference files,
so no transformation is needed. Copy it into whatever skills directory your agent uses.

## Verification

```bash
python3 scripts/validate-pack.py
```

Then in an interactive session:

1. `/mcp` — `n8n-mcp` should be connected. If the `n8n_*` tools are listed, your API URL
   and key arrived.
2. Confirm **nothing about n8n is injected at session start**. In a project unrelated to
   n8n, no n8n content should appear in context until you mention n8n. That is the point of
   this fork.
3. Ask an n8n question and confirm the `n8n` skill is invoked and a route file is read.

## Troubleshooting

**The skill never activates.** With no session injection, the description is the whole
trigger. Mention n8n, a workflow node, or an n8n expression explicitly. If it still does
not fire, check that only one copy of the skill is installed — a stale install of the
upstream fifteen-skill pack will shadow it. Uninstall `n8n-mcp-skills` if present.

**`n8n_*` tools missing.** `N8N_API_URL` / `N8N_API_KEY` did not reach the server. Confirm
they are exported in the shell that started the client, not just in a later terminal. Test
API access directly:

```bash
curl -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_API_URL/api/v1/workflows"
```

**MCP server will not start.** Check `npx -y n8n-mcp@2.77.0` runs on its own. Node must be
installed and on `PATH` for the client's environment.

**Reminders stopped firing after `/compact`.** They should not — `hooks/reset-markers.sh`
clears the dedup markers on `clear` and `compact`. If they are still silent, check that
`hooks/hooks.json` points at `reset-markers.sh` and that the state directory name matches
the one in `hooks/pre-tool-use/_emit.sh` (`n8n-skills-state` in both).
