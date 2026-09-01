# Changelog

## 0.1.0 — 2026-09-01

Initial release of the fork, diverged from
[czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) v1.34.0
at commit `72470a0`.

### Changed

- **One skill instead of fifteen.** `skills/n8n/SKILL.md` is an orchestrator
  that routes to `references/workflow-*.md` files read on demand. The fifteen
  separate skills are gone; their knowledge is preserved verbatim under
  `references/deep/`.
- **No always-on context injection.** Upstream's `SessionStart` hook loaded the
  router skill body into every session regardless of topic, costing roughly 700
  tokens in sessions with no n8n involvement. It is replaced by a silent hook
  that only resets the PreToolUse dedup markers on `/clear` and `/compact`.
- **Local MCP server by default.** `mcp.json` no longer points at the hosted
  `https://api.n8n-mcp.com/mcp` endpoint. It launches `n8n-mcp` locally over
  stdio, pinned to an exact version, against your own n8n instance.
- **Telemetry disabled.** `n8n-mcp` ships telemetry enabled by default;
  `mcp.json` now sets `N8N_MCP_TELEMETRY_DISABLED=true`.
- **Credentials from the environment.** `N8N_API_URL` and `N8N_API_KEY` are read
  via `${VAR}` expansion, so no secret is committed.

### Added

- `scripts/validate-pack.py`, a structural validator covering skill
  frontmatter, route-file existence, reference-link integrity, relative-link
  resolution, hook wiring, MCP configuration, manifest agreement, and the eval
  suite.
