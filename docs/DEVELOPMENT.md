# Development

## Structure

```
skills/n8n/
  SKILL.md                  orchestrator: MCP basics + shared rules + route table
  references/
    workflow-*.md           the ten routes, read on demand
    shared/                 mcp-tools.md, non-negotiables.md, drift.md
    deep/                   51 upstream knowledge files — filenames FROZEN
      design/ nodes/ expressions/ agents/ binary/ errors/
      validate/ instances/ self-host/ code/{js,python,tool}/
  assets/                   docker-compose, Caddyfile, .env examples
hooks/
  reset-markers.sh          SessionStart; resets dedup markers, injects NOTHING
  pre-tool-use/             _emit.sh + 7 matchers on n8n MCP tool names
  post-tool-use/            post-validate gate
scripts/validate-pack.py    the structural gate
evaluations/                57 eval files keyed on route names
docs/superpowers/           the spec and plan behind this restructure
```

## The gate

```bash
python3 scripts/validate-pack.py
```

Must pass before any commit. It checks:

- exactly one skill, named `n8n`, with `name` matching the directory
- frontmatter present, `description` ≤ 1024 chars and carrying the trigger vocabulary
- `SKILL.md` body ≤ 12,000 bytes
- all ten route files exist **and** are listed in the routing table
- every `references/...` path mentioned anywhere resolves
- every relative markdown link resolves (code fences and syntax illustrations excluded)
- no old skill name has crept back in, anywhere under `skills/`, `hooks/`, `evaluations/`
- hook scripts exist and are executable; `session-start.sh` is gone; `reset-markers.sh`
  emits no `additionalContext`; the `SessionStart` matcher is `clear|compact` only
- `mcp.json`: no hosted endpoint, pinned version, telemetry disabled, credentials from the
  environment — and `.mcp.json.example` agreeing with it
- both plugin manifests named `n8n-skills` at the same version
- every eval's `skills` entries are known route names
- `README.md` opens with the fork banner

Stdlib only, so it runs under any `python3`.

## Invariants

**`references/deep/**` filenames are frozen.** They match upstream exactly. The eval suite
asserts on them in `expected_content`, and identical names keep `git merge upstream/main`
tractable. Edit contents freely; do not rename or relocate.

**`SKILL.md` stays under 12,000 bytes.** It is read on every n8n task — that budget is the
whole point of the restructure. Depth belongs in a route file, and a route's depth belongs
in `deep/`.

**No hook emits `additionalContext` on `SessionStart`.** Removing that injection is why this
fork exists.

**Nothing secret is committed.** Credentials reach the MCP server only through
`${N8N_API_URL}` and `${N8N_API_KEY}`.

## Adding a route

1. Create `skills/n8n/references/workflow-<name>.md`.
2. Add a row to the route table in `SKILL.md` — with a **Trigger** cell carrying concrete
   vocabulary a user would actually type, not a category label.
3. Add `"workflow-<name>"` to `ROUTES` in `scripts/validate-pack.py`.
4. Add at least one eval under `evaluations/<name>/`.
5. Run the validator.

### Route file shape

Every route follows the same shape, so they are predictable to read:

1. one line on what the route owns;
2. the rules that actually prevent failures, with the specifics inline (a rule the reader
   has to go elsewhere to act on is not a rule);
3. a table of deeper references with a one-line reason to open each.

Keep the *decision* in the route and the *catalog* in `deep/`. A reader who only opens the
route should still make the right call.

## Evals

Each file is one scenario:

```json
{
  "id": "code-js-001",
  "skills": ["workflow-code"],
  "query": "…what the user types…",
  "expected_behavior": ["Read references/workflow-code.md", "…"],
  "expected_content": ["$json.body.name", "DATA_ACCESS.md"],
  "priority": "high",
  "notes": "…"
}
```

`skills` must be route names. `expected_content` asserting on a `deep/` filename is the
reason those filenames are frozen — do not change one without changing the other.

## Hooks

`hooks/pre-tool-use/_emit.sh` is the shared emitter: it reads `session_id` from the hook
JSON on stdin, dedups on a marker file at
`$TMPDIR/n8n-skills-state/<session_id>-<marker>.loaded`, and prints
`hookSpecificOutput.additionalContext`. Different tools pointing at the same route should
share a marker so they do not double-fire.

`hooks/reset-markers.sh` clears those markers on `clear` and `compact`, and
garbage-collects markers older than 7 days. **The state directory name must match in both
files** — a mismatch silently breaks the reset, and nothing will tell you.

Keep reminders terse and *actionable at that moment*. Content that only makes sense with
surrounding context belongs in the route file.

```bash
shellcheck hooks/reset-markers.sh hooks/pre-tool-use/*.sh hooks/post-tool-use/*.sh
```

`SC2016` in `hooks/post-tool-use/validate-workflow.sh` is a known false positive — the
single-quoted `\$json\.` is an intentional literal grep pattern, and it is upstream code.

## Building

```bash
bash build.sh
```

Produces `dist/n8n-v<version>.zip` (the skill alone, for Claude.ai) and
`dist/n8n-skills-v<version>.zip` (the full plugin). The skill list is derived from the tree,
so a new skill cannot be silently left out. `dist/` is gitignored; zips ship as release
assets.

Both `plugin.json` and `.claude-plugin/plugin.json` carry a version and `build.sh` refuses
to run if they disagree.

## Pulling from upstream

```bash
git fetch upstream
git merge upstream/main
```

This will conflict in `skills/`, because the entry surface was restructured. Frozen `deep/`
filenames limit the damage:

- **Take upstream's** content changes inside `references/deep/` files.
- **Keep ours** for `SKILL.md`, `references/workflow-*.md`, `references/shared/*`,
  `mcp.json`, `hooks/hooks.json`, the manifests and the README.

Then re-run the validator. Upstream prose regularly names the old skills, and
`check_no_old_skill_names` is what catches it — remap any that arrive:

| Upstream name | Route |
|---|---|
| `n8n-workflow-patterns`, `n8n-subworkflows` | `workflow-design` |
| `n8n-node-configuration` | `workflow-nodes` |
| `n8n-expression-syntax` | `workflow-expressions` |
| `n8n-code-javascript`, `n8n-code-python`, `n8n-code-tool` | `workflow-code` |
| `n8n-agents` | `workflow-agents` |
| `n8n-binary-and-data` | `workflow-binary` |
| `n8n-error-handling` | `workflow-errors` |
| `n8n-validation-expert` | `workflow-validate` |
| `n8n-mcp-tools-expert`, `n8n-multi-instance` | `workflow-instances` |
| `n8n-self-hosting` | `workflow-self-host` |

## Bumping the pinned MCP version

`n8n-mcp@<version>` appears in three places that must agree: `mcp.json`,
`.mcp.json.example`, and `PINNED_MCP` in `scripts/validate-pack.py`. The validator enforces
the first two against the third. Read upstream's changelog before bumping — tool names and
parameter shapes drift, and the routes describe them.

## Commit conventions

Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`). No
`Co-Authored-By` trailers.
