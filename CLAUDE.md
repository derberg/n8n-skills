# CLAUDE.md

Guidance for Claude Code when working **on this repository** (not on n8n workflows —
that is what `skills/n8n/` is for).

## What this repo is

A fork of [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) that
restructures the packaging: **one** `n8n` skill whose `SKILL.md` is an orchestrator routing
to on-demand references, instead of fifteen separate skills. No always-on context
injection. Local, version-pinned MCP server with telemetry disabled.

The n8n knowledge is upstream's and is preserved. This fork owns the entry surface.

## Structure

```
skills/n8n/
  SKILL.md                  orchestrator: MCP basics + shared rules + route table
  references/
    workflow-*.md           the ten routes, read on demand
    shared/                 mcp-tools, non-negotiables, drift
    deep/                   51 upstream knowledge files, filenames FROZEN
  assets/                   docker-compose, Caddyfile, .env examples
hooks/
  reset-markers.sh          SessionStart; resets dedup markers, injects NOTHING
  pre-tool-use/             7 matchers on n8n MCP tool names
  post-tool-use/            1 matcher, post-validate gate
scripts/validate-pack.py    the structural gate
evaluations/                57 eval files keyed on route names
docs/superpowers/           spec and implementation plan for this restructure
```

## Rules

1. **`python3 scripts/validate-pack.py` must pass before any commit.** It is the gate:
   frontmatter and size budget, route existence, link resolution, no old skill names, hook
   wiring, the no-injection rule, MCP config, manifest agreement, evals, README banner.
2. **`references/deep/**` filenames are frozen.** They match upstream exactly. The eval
   suite asserts on them, and identical names keep `git merge upstream/main` tractable. You
   may edit contents; do not rename or relocate.
3. **`SKILL.md` body stays under 12,000 bytes.** It is read on every n8n task — that budget
   is the entire point of the restructure. Depth belongs in a route file.
4. **No hook may emit `additionalContext` on `SessionStart`.** Removing that injection is
   the reason this fork exists. The validator enforces it.
5. **Never commit a secret.** Credentials reach the MCP server through `${N8N_API_URL}` and
   `${N8N_API_KEY}` only.
6. **No `Co-Authored-By` trailers.**

## Adding a route

1. Create `skills/n8n/references/workflow-<name>.md`.
2. Add a row to the route table in `SKILL.md`.
3. Add `"workflow-<name>"` to `ROUTES` in `scripts/validate-pack.py`.
4. Add at least one eval under `evaluations/`.
5. Run the validator.

## Pulling from upstream

`git fetch upstream && git merge upstream/main` will conflict in `skills/` because the
entry surface was restructured. Frozen `deep/` filenames limit the damage: take upstream's
content changes inside `deep/` files, and keep ours for `SKILL.md`, `references/workflow-*`
and `references/shared/*`. Re-run the validator afterwards — upstream content often
reintroduces old skill names in prose, which the validator catches.

## Commands

```bash
python3 scripts/validate-pack.py   # structural gate
bash build.sh                      # distribution zips into dist/
shellcheck hooks/**/*.sh           # SC2016 in post-tool-use is a known upstream false positive
```
