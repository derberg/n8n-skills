# Design: single-skill orchestrator for the n8n skills pack

**Date:** 2026-09-01
**Status:** approved, pending implementation plan
**Fork point:** `czlonkowski/n8n-skills` @ `72470a0` (upstream v1.34.0)

## Problem

The upstream pack ships 15 skills plus a hooks layer. Three things are wrong with it
for our purposes.

**1. It pays context rent in every session, n8n or not.** `hooks/session-start.sh`
injects the entire `using-n8n-mcp-skills/SKILL.md` body via `additionalContext` on
`startup|resume|clear|compact`, with no check for whether the session has anything to
do with n8n. The script's own comment says so: "Loads the meta-skill into every
session." Its only guard is `if [[ ! -r "${META_SKILL}" ]]`.

Measured, by capturing the real API request in a project containing nothing but a
`app.py` that prints a string:

| Component | Cost | Conditional? |
|---|---|---|
| SessionStart injection (truncated by the harness to a 2 KB preview) | 2,311 chars ≈ 577 tokens | no |
| 15 skill names in the Skill listing | 524 chars ≈ 131 tokens | no |
| Router body if the pointer file is then read | ~4.3k tokens | if read |

So ~708 tokens of unconditional overhead, re-injected after every compaction. The
17 KB the author intended to inject does not all arrive — the harness truncates hook
`additionalContext` at 2 KB and writes the rest to a file, handing the model a path.
That is arguably worse than either extreme: the model gets a fragment plus an
invitation to spend 4.3k tokens on the rest, in a session about Python.

**2. Fifteen skills is fifteen routing decisions.** Three of them (`n8n-code-javascript`,
`n8n-code-python`, `n8n-code-tool`) need `EXCEPTION —` clauses in their descriptions to
disambiguate from each other. That is the packaging fighting itself.

**3. The MCP config points at a hosted third party.** `mcp.json` declares
`{"type": "streamable-http", "url": "https://api.n8n-mcp.com/mcp"}`. Node lookups and
workflow queries leave the machine, and you cannot point it at your own n8n. The repo
already contains the local alternative it should have shipped, in `.mcp.json.example`.

## Approach

One skill with a strong trigger description, whose `SKILL.md` is an orchestrator: MCP
inventory, shared rules, and a route table pointing at `references/workflow-*.md` files
read on demand. This is the pattern proven in `ai-docs/plugins/docs/skills/docs` — a
6.8 KB `SKILL.md` routing research, diagram, create, five review workflows, and fix
under a single entry point.

The ~800 KB of n8n knowledge in the 70 supporting files is the pack's actual value and
it is accurate. **It is preserved, not rewritten.** This redesign changes the entry
surface only.

## 1. Fork identity

| | Upstream | Fork |
|---|---|---|
| repo | `czlonkowski/n8n-skills` | `derberg/n8n-skills` |
| plugin name | `n8n-mcp-skills` | `n8n-skills` |
| skill invoked as | 15 × `n8n-mcp-skills:n8n-*` | 1 × `n8n-skills:n8n` |
| version | 1.34.0 | `0.1.0` |

The plugin is renamed so both can be installed side by side without a name collision.
Version resets to `0.1.0`; `CHANGELOG.md` records the fork point and the structural
divergence.

`LICENSE` (MIT), `NOTICES` and `NOTICES-APACHE-2.0.txt` are preserved verbatim. The
Apache-2.0 attribution to `n8n-io/skills` is a licence obligation, not a courtesy.
`NOTICES` gains an entry attributing the forked content to `czlonkowski/n8n-skills`.

## 2. Skill surface

```
skills/n8n/
├── SKILL.md                      ~7 KB — the only file read first
├── references/
│   ├── workflow-design.md        patterns + subworkflows
│   ├── workflow-nodes.md
│   ├── workflow-expressions.md
│   ├── workflow-code.md          JS + Python + Code Tool, split inside
│   ├── workflow-agents.md
│   ├── workflow-binary.md
│   ├── workflow-errors.md
│   ├── workflow-validate.md
│   ├── workflow-instances.md     lifecycle + credentials + multi-instance
│   ├── workflow-self-host.md
│   ├── shared/
│   │   ├── mcp-tools.md          tool inventory, nodeType formats
│   │   ├── non-negotiables.md
│   │   └── drift.md              trust the live tool over this pack
│   └── deep/                     70 upstream files, content unchanged
│       ├── design/  nodes/  expressions/
│       ├── code/{js,python,tool}/
│       ├── agents/  binary/  errors/
│       └── validate/  instances/  self-host/
└── assets/                       docker-compose, Caddyfile, .env examples
```

**`deep/` filenames stay exactly as upstream** (`DATA_ACCESS.md`, `ERROR_CATALOG.md`,
`WORKFLOW_GUIDE.md`, …). Two reasons: the eval suite asserts on those names in
`expected_content`, and identical filenames keep future upstream content merges
tractable.

### Route mapping

| Old skill | New route |
|---|---|
| `n8n-workflow-patterns`, `n8n-subworkflows` | `workflow-design.md` |
| `n8n-node-configuration` | `workflow-nodes.md` |
| `n8n-expression-syntax` | `workflow-expressions.md` |
| `n8n-code-javascript`, `n8n-code-python`, `n8n-code-tool` | `workflow-code.md` |
| `n8n-agents` | `workflow-agents.md` |
| `n8n-binary-and-data` | `workflow-binary.md` |
| `n8n-error-handling` | `workflow-errors.md` |
| `n8n-validation-expert` | `workflow-validate.md` |
| `n8n-mcp-tools-expert`, `n8n-multi-instance` | `workflow-instances.md` + `shared/mcp-tools.md` |
| `n8n-self-hosting` | `workflow-self-host.md` |
| `using-n8n-mcp-skills` | becomes `SKILL.md` itself |

`n8n-mcp-tools-expert` is the one skill that does not map to a single route — it is
cross-cutting tool knowledge. Its own four sub-guides split by subject rather than
following the parent:

| Upstream file | Destination |
|---|---|
| `SEARCH_GUIDE.md` (node discovery) | `deep/nodes/` |
| `VALIDATION_GUIDE.md` (config validation) | `deep/validate/` |
| `WORKFLOW_GUIDE.md` (workflow management, 42 KB) | `deep/instances/` |
| `OPERATIONS_GUIDE.md` (templates, data tables) | `deep/instances/` |

What remains of its `SKILL.md` — the tool inventory, `nodeType` format rules
(`nodes-base.*` vs `n8n-nodes-base.*`), validation profiles, smart parameters — becomes
`shared/mcp-tools.md`, referenced by every route that calls an MCP tool.

Merging the three Code skills is the point of the consolidation: it replaces a
cross-referencing `EXCEPTION —` clause in each of three descriptions with one heading
inside one file.

## 3. SKILL.md anatomy

Sections, in order:

1. **Frontmatter** — `name: n8n`, plus the description below.
2. **MCP server** — requires `n8n-mcp`. If its tools are absent, say so and stop rather
   than guessing node schemas from memory.
3. **Shared rules** — condensed from `using-n8n-mcp-skills`, including the rule the
   upstream pack lacks and the `docs` skill has: *read the referenced file with the Read
   tool before acting on a step; never reconstruct a referenced procedure from memory.*
4. **Route table** — intent | trigger | reference to read.
5. **Mixed intents** — overlapping intents mean reading several reference files.

### Description

```
Use for ANY n8n task — building, editing, validating, testing, debugging, or deploying
n8n workflows through the n8n-mcp MCP server. Covers workflow architecture, node
configuration, expressions ({{}}, $json, $node), Code nodes (JavaScript/Python) and the
AI-agent Code Tool, AI agents and tool calling, binary/file handling, sub-workflows,
error handling and retries, validation errors, credentials and multi-instance
targeting, and self-hosting n8n with Docker. If the user mentions n8n, n8n-mcp, a
workflow node, or an n8n expression, this skill applies.
```

~620 characters, within the 1024 cap. This description is the entire trigger mechanism
now that nothing is injected — it has to carry the vocabulary that the 15 separate
descriptions used to spread out.

## 4. Hooks

**`session-start.sh` → `reset-markers.sh`.** Matcher narrows from
`startup|resume|clear|compact` to `clear|compact`. It wipes the per-session marker files
and **emits no `additionalContext` at all** — zero tokens.

This piece is load-bearing and must not simply be deleted. The PreToolUse reminders
dedup through marker files at `$TMPDIR/n8n-mcp-skills-state/<session_id>-<marker>.loaded`.
The SessionStart hook is what clears them on `/clear` and `/compact`. Delete it outright
and markers never reset, so after a compaction the reminders stay silent forever even
though the model's memory of them was just discarded. Keeping a silent reset hook
preserves the correctness while removing the entire token cost.

Also add stale-marker garbage collection, so `$TMPDIR` stops accumulating one file per
session per marker indefinitely.

**The 7 PreToolUse hooks are retargeted.** Their reminder texts currently name the old
skills — `n8n-workflow-patterns` (9 mentions), `n8n-validation-expert` (7),
`n8n-node-configuration` (7), and others. Each becomes a pointer to the new structure:

```
"invoke n8n-validation-expert … via the Skill tool"
  → "invoke the n8n skill and read references/workflow-validate.md"
```

The substantive content is kept **verbatim**, because it is the part that earns its
place — it arrives at the only moment it matters:

- `validate-workflow.sh`: the antipattern scan `validate_workflow` provably does not
  catch (Set nodes feeding one consumer, Code nodes doing pure field shaping, Merge
  `numberOfInputs` with 3+ wires, `$json.x` in branchy workflows, DateTime → Luxon).
- `test-workflow.sh`: `n8n_test_workflow` fires real HTTP calls, database writes and
  Slack/email sends — ask the user first, and report which nodes ran live.
- `instances.sh` / `manage-credentials.sh`: an unexpected `NOT_FOUND` is usually a
  wrong-instance misroute, not a deletion; verify the target before a credential write.

These hooks cost nothing when no n8n MCP server is present. Every matcher is anchored to
an MCP tool name:

```
^mcp__.*__get_node$
^mcp__.*__n8n_create_workflow$
^mcp__.*__(n8n_update_partial_workflow|n8n_update_full_workflow)$
^mcp__.*__(validate_workflow|n8n_validate_workflow)$
^mcp__.*__n8n_test_workflow$
^mcp__.*__n8n_instances$
^mcp__.*__n8n_manage_credentials$
```

plus one PostToolUse matcher on `^mcp__.*__validate_workflow$`. None can fire without an
n8n MCP server connected.

## 5. mcp.json

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
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

Four deliberate changes from upstream:

- **Local stdio replaces the hosted endpoint.** `https://api.n8n-mcp.com/mcp` is removed
  entirely. Nothing leaves the machine except calls to your own n8n.
- **Version pinned to `2.77.0`** (current latest). Bare `npx n8n-mcp` resolves to
  whatever is newest at spawn time — an unpinned remote dependency executing locally.
- **Telemetry disabled.** `n8n-mcp` ships telemetry that is **on by default**; it is
  opt-out only. `dist/telemetry/config-manager.js` accepts
  `N8N_MCP_TELEMETRY_DISABLED`, `TELEMETRY_DISABLED` or `DISABLE_TELEMETRY`, normalised
  lower/trimmed, treating `true` or `1` as disabled. The package carries a
  `workflow-sanitizer` and a `mutation-tracker`, i.e. it reports sanitised workflow
  content, so this matters. We set the canonical `N8N_MCP_TELEMETRY_DISABLED=true`.
- **Credentials come from the environment**, so no secret is ever committed.

`${VAR}` and `${VAR:-default}` expansion are verified working in `.mcp.json` by direct
test (a stub server printed the expanded values). Verifying it in a *plugin-level*
`mcp.json` needs an interactive session — plugin MCP servers did not launch under
headless `-p`. **Implementation must confirm this before relying on it**; if plugin-level
expansion does not work, the fallback is to document the two variables in the README and
leave them unset in `mcp.json`.

`.mcp.json.example` and `docs/INSTALLATION.md` are brought into agreement with the above;
today they disagree with `mcp.json`.

## 6. Evals, docs, build

**Evals.** 60 JSON files under `evaluations/` key off old skill names —
`"skills": ["n8n-code-javascript"]` — and their `expected_behavior` arrays say things
like `"Activate n8n-code-javascript skill"`. Remap to route names
(`"skills": ["workflow-code"]`) and reword the behaviour assertions to
`"Read references/workflow-code.md"`. Their `expected_content` assertions on `deep/`
filenames keep working unchanged, which is why those filenames are frozen.

**`build.sh`** derives the skill list from the tree, so it survives the collapse without
change. Only the hardcoded bundle name `n8n-mcp-skills-v${VERSION}.zip` needs renaming.

**Docs.** `README.md`, `CLAUDE.md`, `docs/INSTALLATION.md`, `docs/USAGE.md` and
`docs/DEVELOPMENT.md` are rewritten for the single-skill structure. README gains a
"Differences from upstream" section covering: one skill instead of 15, no session
injection, local pinned MCP, telemetry off.

## Cost comparison

| Scenario | Upstream | Fork |
|---|---|---|
| Session with no n8n involvement | ~708 tokens, unconditionally | ~40–160 tokens (one listing line) |
| An actual n8n task | 708 + 4.3k router + ~5k domain skill + deep refs | ~160 + ~1.8k `SKILL.md` + one route file + deep refs |

The fork is cheaper in both directions. The one thing it gives up: a focused task can no
longer jump straight to a single narrow skill; it reads `SKILL.md` first. That costs
~1.8k tokens per n8n task and buys back ~708 tokens on every non-n8n session, plus the
elimination of a 15-way routing decision.

## Out of scope

- Rewriting the n8n knowledge in the 70 `deep/` files.
- Adding agents, slash commands, or new capabilities.
- Restructuring `deep/` file *contents* (only their location changes).
- `skills.png`, the intro video link, `docs/MCP_TESTING_LOG.md`.
- Upstreaming any of this back to `czlonkowski/n8n-skills`.

## Risks

- **The description is now a single point of failure.** With nothing injected, if the
  description does not fire, the pack contributes nothing. Mitigated by broad trigger
  vocabulary and by the PreToolUse hooks, which still catch the case where an n8n MCP
  tool is called without the skill having been read.
- **Upstream divergence.** Restructuring the entry surface makes `git merge upstream/main`
  conflict-prone for `skills/`. Frozen `deep/` filenames limit the damage to the
  orchestrator layer, which we own outright.
- **Plugin-level `${VAR}` expansion is unconfirmed.** Fallback documented above.
