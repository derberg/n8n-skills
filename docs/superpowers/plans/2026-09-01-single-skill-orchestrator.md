# Single-Skill Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the 15-skill n8n pack into one `n8n` skill whose `SKILL.md` orchestrates on-demand `references/workflow-*.md` routes, remove all always-on context injection, and replace the hosted MCP endpoint with a pinned local stdio server with telemetry disabled.

**Architecture:** One skill directory `skills/n8n/` containing a ~7 KB orchestrator `SKILL.md` (MCP inventory + shared rules + route table), ten route files under `references/`, three cross-cutting files under `references/shared/`, and the 70 preserved upstream knowledge files under `references/deep/` with their filenames frozen. The hooks layer keeps its PreToolUse reminders (retargeted at route files) and replaces the injecting SessionStart hook with a silent marker-reset hook. A Python structural validator gates every task.

**Tech Stack:** Markdown skills, bash hooks, `jq`, Python 3 stdlib (validator), `gh` CLI.

**Spec:** `docs/superpowers/specs/2026-09-01-n8n-skills-fork-redesign-design.md`

## Global Constraints

- Plugin name is `n8n-skills` in both `plugin.json` and `.claude-plugin/plugin.json`; the two versions must never disagree (`build.sh` enforces this).
- Version is `0.1.0`.
- Skill directory and frontmatter `name` are both exactly `n8n`.
- Skill `description` must stay ≤ 1024 characters.
- `SKILL.md` body must stay ≤ 12,000 bytes — this is the whole point of the redesign.
- `references/deep/**` filenames are **frozen** exactly as upstream (`DATA_ACCESS.md`, `ERROR_CATALOG.md`, `WORKFLOW_GUIDE.md`, …). The eval suite asserts on them and frozen names keep upstream merges tractable.
- Pinned MCP version: `n8n-mcp@2.77.0`.
- Telemetry env var: `N8N_MCP_TELEMETRY_DISABLED` set to `"true"`.
- No secrets in any committed file; credentials only via `${N8N_API_URL}` / `${N8N_API_KEY}`.
- `LICENSE`, `NOTICES`, `NOTICES-APACHE-2.0.txt` content is preserved; `NOTICES` may only be appended to.
- No `Co-Authored-By` trailers in commits.
- No hook may emit `additionalContext` on `SessionStart`.

---

## File Structure

**Created:**

| Path | Responsibility |
|---|---|
| `scripts/validate-pack.py` | Structural validator; the test harness for every task |
| `skills/n8n/SKILL.md` | Orchestrator: MCP inventory, shared rules, route table |
| `skills/n8n/references/shared/mcp-tools.md` | Tool inventory, `nodeType` formats, validation profiles |
| `skills/n8n/references/shared/non-negotiables.md` | The three always-apply rules |
| `skills/n8n/references/shared/drift.md` | Trust the live tool over this pack |
| `skills/n8n/references/workflow-design.md` | Architecture patterns + sub-workflow decomposition |
| `skills/n8n/references/workflow-nodes.md` | Node configuration, property dependencies, discovery |
| `skills/n8n/references/workflow-expressions.md` | `{{}}` syntax, `$json`/`$node` access |
| `skills/n8n/references/workflow-code.md` | Code node JS + Python + the AI-agent Code Tool |
| `skills/n8n/references/workflow-agents.md` | AI agents, tools, memory, structured output, RAG |
| `skills/n8n/references/workflow-binary.md` | Files, binary data, the `$binary`/`$json` split |
| `skills/n8n/references/workflow-errors.md` | Error outputs, retries, response shapes |
| `skills/n8n/references/workflow-validate.md` | Validation errors, false positives, antipattern scan |
| `skills/n8n/references/workflow-instances.md` | Workflow lifecycle, credentials, multi-instance |
| `skills/n8n/references/workflow-self-host.md` | Docker Compose + Caddy deployment |
| `hooks/reset-markers.sh` | Silent SessionStart marker reset; emits nothing |
| `CHANGELOG.md` | Fork point and divergence record |

**Relocated** (`git mv`, content unchanged):

| From | To |
|---|---|
| `skills/n8n-workflow-patterns/{ai_agent_workflow,database_operations,http_api_integration,scheduled_tasks,webhook_processing}.md` | `skills/n8n/references/deep/design/` |
| `skills/n8n-subworkflows/{NAMING_AND_DISCOVERY,SUBWORKFLOW_PATTERNS}.md` | `skills/n8n/references/deep/design/` |
| `skills/n8n-node-configuration/{DEPENDENCIES,NODE_FAMILY_GOTCHAS,OPERATION_PATTERNS}.md` | `skills/n8n/references/deep/nodes/` |
| `skills/n8n-mcp-tools-expert/SEARCH_GUIDE.md` | `skills/n8n/references/deep/nodes/` |
| `skills/n8n-expression-syntax/{COMMON_MISTAKES,EXAMPLES}.md` | `skills/n8n/references/deep/expressions/` |
| `skills/n8n-code-javascript/{BUILTIN_FUNCTIONS,COMMON_PATTERNS,DATA_ACCESS,ERROR_PATTERNS}.md` | `skills/n8n/references/deep/code/js/` |
| `skills/n8n-code-python/{COMMON_PATTERNS,DATA_ACCESS,ERROR_PATTERNS,STANDARD_LIBRARY}.md` | `skills/n8n/references/deep/code/python/` |
| `skills/n8n-code-tool/{ERROR_PATTERNS,INPUT_SCHEMA}.md` | `skills/n8n/references/deep/code/tool/` |
| `skills/n8n-agents/{CHAT_AGENT_PATTERNS,EXAMPLES,HUMAN_REVIEW,MEMORY,RAG,STRUCTURED_OUTPUT,SUBWORKFLOW_AS_TOOL,SYSTEM_PROMPT,TOOLS}.md` | `skills/n8n/references/deep/agents/` |
| `skills/n8n-binary-and-data/{AGENT_TOOL_BINARY,BINARY_BASICS,CDN_REQUIREMENT,MERGE_FOR_CONTEXT}.md` | `skills/n8n/references/deep/binary/` |
| `skills/n8n-error-handling/{API_WORKFLOWS,ERROR_WORKFLOWS,NODE_ERROR_OUTPUTS,RESPONSE_SHAPES}.md` | `skills/n8n/references/deep/errors/` |
| `skills/n8n-validation-expert/{ERROR_CATALOG,FALSE_POSITIVES,REVIEW_CHECKLIST}.md` | `skills/n8n/references/deep/validate/` |
| `skills/n8n-mcp-tools-expert/VALIDATION_GUIDE.md` | `skills/n8n/references/deep/validate/` |
| `skills/n8n-mcp-tools-expert/{WORKFLOW_GUIDE,OPERATIONS_GUIDE}.md` | `skills/n8n/references/deep/instances/` |
| `skills/n8n-self-hosting/{CREDENTIAL_OVERWRITES,DAY2,QUEUE_MODE,SECURITY,SINGLE_MODE}.md` | `skills/n8n/references/deep/self-host/` |
| `skills/n8n-self-hosting/assets/*` | `skills/n8n/assets/` |

**Deleted:** all 15 `skills/n8n-*/SKILL.md` and `skills/using-n8n-mcp-skills/`, plus the 15 per-skill `README.md` files (superseded by the route files and the top-level README), and `hooks/session-start.sh`.

**Modified:** `mcp.json`, `.mcp.json.example`, `plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `hooks/hooks.json`, all 7 `hooks/pre-tool-use/*.sh` reminder texts, `hooks/post-tool-use/validate-workflow.sh`, 57 `evaluations/**/*.json`, `build.sh`, `README.md`, `CLAUDE.md`, `docs/INSTALLATION.md`, `docs/USAGE.md`, `docs/DEVELOPMENT.md`.

---

### Task 1: Structural validator

The test harness. Everything after this task is gated on it, so it comes first and it must fail loudly against the current tree.

**Files:**
- Create: `scripts/validate-pack.py`

**Interfaces:**
- Produces: `python3 scripts/validate-pack.py` exits 0 when the pack is structurally valid, 1 otherwise, printing one `FAIL:` line per violation. Later tasks call exactly this command.

- [ ] **Step 1: Write the validator**

```python
#!/usr/bin/env python3
"""Structural validator for the n8n-skills pack.

Run: python3 scripts/validate-pack.py
Exits 0 when valid, 1 with one FAIL: line per violation.
Uses only the standard library so it runs under any python3.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAILURES = []

OLD_SKILLS = [
    "n8n-agents", "n8n-binary-and-data", "n8n-code-javascript",
    "n8n-code-python", "n8n-code-tool", "n8n-error-handling",
    "n8n-expression-syntax", "n8n-mcp-tools-expert", "n8n-multi-instance",
    "n8n-node-configuration", "n8n-self-hosting", "n8n-subworkflows",
    "n8n-validation-expert", "n8n-workflow-patterns", "using-n8n-mcp-skills",
]

ROUTES = [
    "workflow-design", "workflow-nodes", "workflow-expressions",
    "workflow-code", "workflow-agents", "workflow-binary",
    "workflow-errors", "workflow-validate", "workflow-instances",
    "workflow-self-host",
]

PINNED_MCP = "n8n-mcp@2.77.0"


def fail(msg):
    FAILURES.append(msg)


def split_frontmatter(text):
    """Return (frontmatter_text, body) or (None, text) when absent."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 3)
    if end == -1:
        return None, text
    return text[4:end + 1], text[end + 5:]


def check_single_skill():
    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        fail("skills/ directory is missing")
        return None
    found = sorted(
        d for d in skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    )
    if len(found) != 1:
        fail(f"expected exactly 1 skill, found {len(found)}: "
             f"{[d.name for d in found]}")
        return None
    skill = found[0]
    if skill.name != "n8n":
        fail(f"skill directory must be named 'n8n', found '{skill.name}'")
    return skill


def check_frontmatter(skill):
    path = skill / "SKILL.md"
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    if fm is None:
        fail("SKILL.md has no frontmatter starting on line 1")
        return
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc = re.search(r"^description:\s*(.+)$", fm, re.M | re.S)
    if not name:
        fail("SKILL.md frontmatter has no 'name'")
    elif name.group(1).strip() != skill.name:
        fail(f"SKILL.md name '{name.group(1).strip()}' != directory "
             f"'{skill.name}'")
    if not desc:
        fail("SKILL.md frontmatter has no 'description'")
    else:
        text = desc.group(1).strip().strip('"')
        if len(text) > 1024:
            fail(f"description is {len(text)} chars, max 1024")
        for token in ("n8n-mcp", "expression", "Code node", "self-host"):
            if token.lower() not in text.lower():
                fail(f"description is missing trigger vocabulary: {token!r}")
    if len(body.encode("utf-8")) > 12000:
        fail(f"SKILL.md body is {len(body.encode('utf-8'))} bytes, max 12000")


def check_routes_exist(skill):
    for route in ROUTES:
        path = skill / "references" / f"{route}.md"
        if not path.is_file():
            fail(f"missing route file: {path.relative_to(ROOT)}")
    table = (skill / "SKILL.md").read_text(encoding="utf-8")
    for route in ROUTES:
        if f"{route}.md" not in table:
            fail(f"SKILL.md route table does not mention {route}.md")


def check_reference_links(skill):
    """Every references/... path mentioned in any skill markdown must exist."""
    pattern = re.compile(r"references/[A-Za-z0-9_./-]+\.(?:md|yml|example)")
    for md in sorted(skill.rglob("*.md")):
        for match in set(pattern.findall(md.read_text(encoding="utf-8"))):
            if not (skill / match).is_file():
                fail(f"{md.relative_to(ROOT)} points at missing {match}")


def check_no_old_skill_names():
    scan = [ROOT / "skills", ROOT / "hooks", ROOT / "evaluations"]
    for base in scan:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in (".md", ".sh", ".json"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for old in OLD_SKILLS:
                if re.search(rf"\b{re.escape(old)}\b", text):
                    fail(f"{path.relative_to(ROOT)} still references old "
                         f"skill name '{old}'")


def check_hooks():
    cfg = ROOT / "hooks" / "hooks.json"
    if not cfg.is_file():
        fail("hooks/hooks.json is missing")
        return
    data = json.loads(cfg.read_text(encoding="utf-8"))
    for event, entries in data.get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                rel = cmd.replace("${CLAUDE_PLUGIN_ROOT}/", "")
                target = ROOT / rel
                if not target.is_file():
                    fail(f"hooks.json {event} points at missing {rel}")
                elif not target.stat().st_mode & 0o111:
                    fail(f"{rel} is not executable")
    if (ROOT / "hooks" / "session-start.sh").exists():
        fail("hooks/session-start.sh still exists; it must be replaced by "
             "reset-markers.sh")
    reset = ROOT / "hooks" / "reset-markers.sh"
    if reset.is_file():
        if "additionalContext" in reset.read_text(encoding="utf-8"):
            fail("reset-markers.sh must not emit additionalContext")
    else:
        fail("hooks/reset-markers.sh is missing")
    starts = data.get("hooks", {}).get("SessionStart", [])
    for entry in starts:
        matcher = entry.get("matcher", "")
        if "startup" in matcher or "resume" in matcher:
            fail(f"SessionStart matcher must be clear|compact only, got "
                 f"{matcher!r}")


def check_mcp():
    path = ROOT / "mcp.json"
    if not path.is_file():
        fail("mcp.json is missing")
        return
    raw = path.read_text(encoding="utf-8")
    if "api.n8n-mcp.com" in raw:
        fail("mcp.json still points at the hosted api.n8n-mcp.com endpoint")
    server = json.loads(raw)["mcpServers"]["n8n-mcp"]
    if server.get("command") != "npx":
        fail("mcp.json must launch the local stdio server via npx")
    if PINNED_MCP not in server.get("args", []):
        fail(f"mcp.json must pin {PINNED_MCP}, got {server.get('args')}")
    env = server.get("env", {})
    if env.get("N8N_MCP_TELEMETRY_DISABLED") != "true":
        fail("mcp.json must set N8N_MCP_TELEMETRY_DISABLED=true")
    for key in ("N8N_API_URL", "N8N_API_KEY"):
        value = env.get(key, "")
        if not value.startswith("${"):
            fail(f"mcp.json {key} must come from the environment, got "
                 f"{value!r}")
    example = ROOT / ".mcp.json.example"
    if example.is_file():
        ex = json.loads(example.read_text(encoding="utf-8"))
        ex_env = ex["mcpServers"]["n8n-mcp"].get("env", {})
        if ex_env.get("N8N_MCP_TELEMETRY_DISABLED") != "true":
            fail(".mcp.json.example disagrees with mcp.json on telemetry")
        if PINNED_MCP not in ex["mcpServers"]["n8n-mcp"].get("args", []):
            fail(".mcp.json.example disagrees with mcp.json on the pin")


def check_manifests():
    a = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    b = json.loads(
        (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    for label, manifest in (("plugin.json", a),
                            (".claude-plugin/plugin.json", b)):
        if manifest.get("name") != "n8n-skills":
            fail(f"{label} name must be 'n8n-skills', got "
                 f"{manifest.get('name')!r}")
    if a.get("version") != b.get("version"):
        fail(f"manifest versions disagree: {a.get('version')} vs "
             f"{b.get('version')}")


def check_evals():
    base = ROOT / "evaluations"
    if not base.is_dir():
        return
    allowed = set(ROUTES)
    for path in sorted(base.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for name in data.get("skills", []):
            if name not in allowed:
                fail(f"{path.relative_to(ROOT)} references unknown route "
                     f"'{name}'")


def check_readme_banner():
    readme = ROOT / "README.md"
    if not readme.is_file():
        fail("README.md is missing")
        return
    head = "\n".join(readme.read_text(encoding="utf-8").splitlines()[:15])
    if "Fork of" not in head:
        fail("README.md must open with a 'Fork of' annotation in the first "
             "15 lines")
    for token in ("one skill", "telemetry", "session"):
        if token.lower() not in head.lower():
            fail(f"README.md fork banner does not mention {token!r}")


def main():
    skill = check_single_skill()
    if skill:
        check_frontmatter(skill)
        check_routes_exist(skill)
        check_reference_links(skill)
    check_no_old_skill_names()
    check_hooks()
    check_mcp()
    check_manifests()
    check_evals()
    check_readme_banner()
    for message in FAILURES:
        print(f"FAIL: {message}")
    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed")
        return 1
    print("All structural checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it and confirm it fails against the current tree**

Run: `cd /Users/derberg/Documents/GitHub/n8n-skills && python3 scripts/validate-pack.py`

Expected: exit 1, with failures including `expected exactly 1 skill, found 15`, `mcp.json still points at the hosted api.n8n-mcp.com endpoint`, `hooks/session-start.sh still exists`, `plugin.json name must be 'n8n-skills'`, and `README.md must open with a 'Fork of' annotation`.

- [ ] **Step 3: Commit**

```bash
git add scripts/validate-pack.py
git commit -m "test: add structural validator for the skill pack"
```

---

### Task 2: Plugin identity and licensing

**Files:**
- Modify: `plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- Modify: `NOTICES`
- Create: `CHANGELOG.md`

**Interfaces:**
- Consumes: `scripts/validate-pack.py` from Task 1.
- Produces: plugin name `n8n-skills` at version `0.1.0` in both manifests; `check_manifests` passes.

- [ ] **Step 1: Confirm the manifest checks currently fail**

Run: `python3 scripts/validate-pack.py 2>&1 | grep -E "plugin.json|version"`
Expected: `FAIL: plugin.json name must be 'n8n-skills', got 'n8n-mcp-skills'` and the same for `.claude-plugin/plugin.json`.

- [ ] **Step 2: Update both plugin manifests**

In `plugin.json` and `.claude-plugin/plugin.json` set:

```json
"name": "n8n-skills",
"version": "0.1.0",
"repository": "https://github.com/derberg/n8n-skills",
"homepage": "https://github.com/derberg/n8n-skills"
```

Set the description in both to:

```
Single-skill n8n expert pack for Claude Code — one orchestrator skill routing to on-demand workflow references, no always-on context injection, local pinned MCP server with telemetry off.
```

Keep the existing `author` block (it credits the upstream author) and add:

```json
"contributors": [{"name": "Lukasz Gornicki", "url": "https://github.com/derberg"}]
```

- [ ] **Step 3: Update the marketplace manifest**

In `.claude-plugin/marketplace.json`: set the top-level and plugin-entry `name` to `n8n-skills`, `version` to `0.1.0`, repository and homepage to the fork URL, and replace the 15-entry `skills` array with:

```json
"skills": ["./skills/n8n"]
```

Replace the plugin-entry `description` with:

```
One n8n skill that routes to ten on-demand workflow references covering architecture, node configuration, expressions, Code nodes, AI agents, binary data, error handling, validation, instance lifecycle, and self-hosted deployment. No session injection; local pinned MCP server with telemetry disabled.
```

- [ ] **Step 4: Append fork attribution to NOTICES**

Append, without altering any existing text:

```
--------------------------------------------------------------------------------

This project is a fork of n8n-skills (https://github.com/czlonkowski/n8n-skills),
Copyright (c) Romuald Czlonkowski, licensed under the MIT License. The skill
knowledge content in skills/n8n/references/deep/ is derived from that project.

The fork restructures the entry surface (one orchestrator skill instead of
fifteen), removes the SessionStart context injection, and changes the MCP
server configuration. See CHANGELOG.md.
```

- [ ] **Step 5: Create CHANGELOG.md**

```markdown
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
  frontmatter, route-file existence, reference-link integrity, hook wiring, MCP
  configuration, manifest agreement, and the eval suite.
```

- [ ] **Step 6: Verify the manifest checks pass**

Run: `python3 scripts/validate-pack.py 2>&1 | grep -E "plugin.json|manifest version" || echo "manifest checks clean"`
Expected: `manifest checks clean`

- [ ] **Step 7: Commit**

```bash
git add plugin.json .claude-plugin/ NOTICES CHANGELOG.md
git commit -m "chore: rename plugin to n8n-skills, reset version, add fork attribution"
```

---

### Task 3: MCP configuration

**Files:**
- Modify: `mcp.json`, `.mcp.json.example`

**Interfaces:**
- Produces: `check_mcp` passes. Both files agree on command, pinned version and env keys.

- [ ] **Step 1: Confirm the MCP checks currently fail**

Run: `python3 scripts/validate-pack.py 2>&1 | grep -i mcp.json`
Expected: `FAIL: mcp.json still points at the hosted api.n8n-mcp.com endpoint`.

- [ ] **Step 2: Replace mcp.json**

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

- [ ] **Step 3: Bring .mcp.json.example into agreement**

Same server block without the `$schema` line, and with a trailing comment-free shape identical to the above. The example exists for people wiring the server into their own project config rather than installing the plugin, so it must not drift.

- [ ] **Step 4: Verify plugin-level `${VAR}` expansion actually works**

This is the spec's open checkpoint. `${VAR}` and `${VAR:-default}` are confirmed working in a project `.mcp.json`; plugin-level `mcp.json` is unverified because plugin MCP servers do not launch under headless `-p`.

In an interactive Claude Code session with the plugin installed, run `/mcp` and confirm the `n8n-mcp` server connects and that `N8N_API_URL` reached it (an n8n management tool such as `n8n_list_workflows` appearing in the tool list proves the API URL and key arrived; without them only the read-only node tools appear).

If expansion does **not** work at plugin level: remove `N8N_API_URL` and `N8N_API_KEY` from `mcp.json` entirely, and document in `docs/INSTALLATION.md` that users must set them in their own `.mcp.json` or shell environment. Record the outcome in `CHANGELOG.md`. Do not leave a `${VAR}` literal being passed through to the server as a value.

- [ ] **Step 5: Verify the MCP checks pass**

Run: `python3 scripts/validate-pack.py 2>&1 | grep -i "mcp.json" || echo "mcp checks clean"`
Expected: `mcp checks clean`

- [ ] **Step 6: Commit**

```bash
git add mcp.json .mcp.json.example
git commit -m "fix: replace hosted MCP endpoint with pinned local stdio server, telemetry off"
```

---

### Task 4: Relocate knowledge files and delete the old skills

The atomic restructure. It cannot be half-done — the validator requires exactly one skill directory.

**Files:**
- Relocate: every file in the "Relocated" table above, via `git mv`
- Delete: 15 `skills/n8n-*/SKILL.md`, 15 `skills/*/README.md`, `skills/using-n8n-mcp-skills/`

**Interfaces:**
- Produces: `skills/n8n/references/deep/**` populated with frozen filenames; `skills/n8n/assets/` populated. `check_single_skill` passes once Task 5 adds `SKILL.md`.

- [ ] **Step 1: Create the target directories**

```bash
cd /Users/derberg/Documents/GitHub/n8n-skills
mkdir -p skills/n8n/references/shared
mkdir -p skills/n8n/references/deep/{design,nodes,expressions,agents,binary,errors,validate,instances,self-host}
mkdir -p skills/n8n/references/deep/code/{js,python,tool}
mkdir -p skills/n8n/assets
```

- [ ] **Step 2: Relocate every knowledge file with git mv**

```bash
git mv skills/n8n-workflow-patterns/{ai_agent_workflow,database_operations,http_api_integration,scheduled_tasks,webhook_processing}.md skills/n8n/references/deep/design/
git mv skills/n8n-subworkflows/{NAMING_AND_DISCOVERY,SUBWORKFLOW_PATTERNS}.md skills/n8n/references/deep/design/
git mv skills/n8n-node-configuration/{DEPENDENCIES,NODE_FAMILY_GOTCHAS,OPERATION_PATTERNS}.md skills/n8n/references/deep/nodes/
git mv skills/n8n-mcp-tools-expert/SEARCH_GUIDE.md skills/n8n/references/deep/nodes/
git mv skills/n8n-expression-syntax/{COMMON_MISTAKES,EXAMPLES}.md skills/n8n/references/deep/expressions/
git mv skills/n8n-code-javascript/{BUILTIN_FUNCTIONS,COMMON_PATTERNS,DATA_ACCESS,ERROR_PATTERNS}.md skills/n8n/references/deep/code/js/
git mv skills/n8n-code-python/{COMMON_PATTERNS,DATA_ACCESS,ERROR_PATTERNS,STANDARD_LIBRARY}.md skills/n8n/references/deep/code/python/
git mv skills/n8n-code-tool/{ERROR_PATTERNS,INPUT_SCHEMA}.md skills/n8n/references/deep/code/tool/
git mv skills/n8n-agents/{CHAT_AGENT_PATTERNS,EXAMPLES,HUMAN_REVIEW,MEMORY,RAG,STRUCTURED_OUTPUT,SUBWORKFLOW_AS_TOOL,SYSTEM_PROMPT,TOOLS}.md skills/n8n/references/deep/agents/
git mv skills/n8n-binary-and-data/{AGENT_TOOL_BINARY,BINARY_BASICS,CDN_REQUIREMENT,MERGE_FOR_CONTEXT}.md skills/n8n/references/deep/binary/
git mv skills/n8n-error-handling/{API_WORKFLOWS,ERROR_WORKFLOWS,NODE_ERROR_OUTPUTS,RESPONSE_SHAPES}.md skills/n8n/references/deep/errors/
git mv skills/n8n-validation-expert/{ERROR_CATALOG,FALSE_POSITIVES,REVIEW_CHECKLIST}.md skills/n8n/references/deep/validate/
git mv skills/n8n-mcp-tools-expert/VALIDATION_GUIDE.md skills/n8n/references/deep/validate/
git mv skills/n8n-mcp-tools-expert/{WORKFLOW_GUIDE,OPERATIONS_GUIDE}.md skills/n8n/references/deep/instances/
git mv skills/n8n-self-hosting/{CREDENTIAL_OVERWRITES,DAY2,QUEUE_MODE,SECURITY,SINGLE_MODE}.md skills/n8n/references/deep/self-host/
git mv skills/n8n-self-hosting/assets/.env.queue.example skills/n8n-self-hosting/assets/.env.single.example skills/n8n-self-hosting/assets/Caddyfile skills/n8n-self-hosting/assets/docker-compose.queue.yml skills/n8n-self-hosting/assets/docker-compose.single.yml skills/n8n-self-hosting/assets/init-data.sh skills/n8n/assets/
```

- [ ] **Step 3: Confirm nothing was left behind, then delete the old skill directories**

```bash
# Only SKILL.md and README.md should remain in each old directory.
find skills -maxdepth 2 -type f -not -path 'skills/n8n/*' | sort
# Expected: exactly 15 SKILL.md and 15 README.md files, nothing else.
git rm -r -q skills/n8n-agents skills/n8n-binary-and-data skills/n8n-code-javascript \
  skills/n8n-code-python skills/n8n-code-tool skills/n8n-error-handling \
  skills/n8n-expression-syntax skills/n8n-mcp-tools-expert skills/n8n-multi-instance \
  skills/n8n-node-configuration skills/n8n-self-hosting skills/n8n-subworkflows \
  skills/n8n-validation-expert skills/n8n-workflow-patterns skills/using-n8n-mcp-skills
```

Note: the old `SKILL.md` bodies are the source material for Tasks 5–10. Before deleting, save copies outside the repo so later tasks can draw on them:

```bash
mkdir -p /tmp/n8n-old-skills
git show HEAD:skills/n8n-agents/SKILL.md > /tmp/n8n-old-skills/agents.md
# ...repeat per skill, or simply use `git show HEAD:<path>` on demand in later tasks.
```

`git show HEAD:<path>` retrieves any deleted file at any later point, so no copy is strictly required.

- [ ] **Step 4: Verify the file count is preserved**

Run:
```bash
git status --porcelain | grep -c '^R' # renames
find skills/n8n/references/deep -type f | wc -l   # expect 38
find skills/n8n/assets -type f | wc -l            # expect 6
```
Expected: 38 deep files, 6 assets. Every deep filename identical to upstream.

- [ ] **Step 5: Commit**

```bash
git add -A skills/
git commit -m "refactor: relocate knowledge files under skills/n8n/references/deep"
```

---

### Task 5: The orchestrator SKILL.md

**Files:**
- Create: `skills/n8n/SKILL.md`

**Interfaces:**
- Consumes: the route filenames from the Global Constraints.
- Produces: `check_single_skill`, `check_frontmatter` and the route-table half of `check_routes_exist` pass.

- [ ] **Step 1: Read the source material**

```bash
git show HEAD~1:skills/using-n8n-mcp-skills/SKILL.md
git show HEAD~1:skills/n8n-mcp-tools-expert/SKILL.md
```

The first is the upstream router being replaced; the second holds the MCP tool rules that belong in `shared/mcp-tools.md` (Task 6). Take the routing structure from `ai-docs/plugins/docs/skills/docs/SKILL.md` — MCP inventory, shared rules, intent table, mixed-intent note.

- [ ] **Step 2: Write skills/n8n/SKILL.md**

Frontmatter exactly:

```yaml
---
name: n8n
description: Use for ANY n8n task — building, editing, validating, testing, debugging, or deploying n8n workflows through the n8n-mcp MCP server. Covers workflow architecture, node configuration, expressions ({{}}, $json, $node), Code nodes (JavaScript/Python) and the AI-agent Code Tool, AI agents and tool calling, binary/file handling, sub-workflows, error handling and retries, validation errors, credentials and multi-instance targeting, and self-hosting n8n with Docker. If the user mentions n8n, n8n-mcp, a workflow node, or an n8n expression, this skill applies.
---
```

Body sections, in order:

1. `# n8n` — one sentence: single entry point for every n8n workflow task.
2. `## MCP server` — this skill requires the `n8n-mcp` server. State plainly: if its tools are absent, say so and stop; do not reconstruct node schemas or parameter shapes from memory, because they drift between n8n versions. Point at `references/shared/mcp-tools.md` for tool selection and `nodeType` formats.
3. `## Shared rules` — five numbered rules, applying to every route:
   1. **Read the referenced file before acting.** When a route or step points at another file, open it with the Read tool first, even when the action feels familiar. Never reconstruct a referenced procedure from memory.
   2. **Validate before claiming done.** A workflow is not finished until `validate_workflow` passes and the antipattern scan in `references/workflow-validate.md` has been run.
   3. **Trust the live tool over this pack** — see `references/shared/drift.md`.
   4. **Never inline secrets.** Credentials go through n8n's credential system; see `references/workflow-instances.md`.
   5. **Ask before side effects.** `n8n_test_workflow` executes real nodes. See `references/workflow-errors.md`.
   Then: the three hard rules live in `references/shared/non-negotiables.md`; read it on any workflow-modifying task.
4. `## Route table` — a markdown table with columns Intent | Trigger | Reference to read, one row per route, in this order: Design, Configure a node, Expressions, Code, AI agents, Files and binary, Error handling, Validate and debug, Instance lifecycle, Self-host. Each Trigger cell must carry concrete vocabulary a user would actually type.
5. `## Mixed intents` — overlapping intents are common ("build a webhook that calls an API and handles failures" is Design + Errors + Validate); read every relevant reference. When unsure, read more rather than fewer.

Keep the whole body under 12,000 bytes; aim for roughly 7,000.

- [ ] **Step 3: Verify frontmatter and size checks pass**

Run: `python3 scripts/validate-pack.py 2>&1 | grep -E "SKILL.md|description|skill directory" || echo "skill checks clean"`
Expected: only `missing route file:` failures remain (Tasks 6–10 fix those).

- [ ] **Step 4: Commit**

```bash
git add skills/n8n/SKILL.md
git commit -m "feat: add n8n orchestrator skill with route table"
```

---

### Task 6: Shared reference files

**Files:**
- Create: `skills/n8n/references/shared/mcp-tools.md`
- Create: `skills/n8n/references/shared/non-negotiables.md`
- Create: `skills/n8n/references/shared/drift.md`

**Interfaces:**
- Consumes: `git show HEAD~2:skills/n8n-mcp-tools-expert/SKILL.md` and `git show HEAD~2:skills/using-n8n-mcp-skills/SKILL.md`.
- Produces: the three files `SKILL.md` links to; `check_reference_links` stops failing on `references/shared/*`.

- [ ] **Step 1: Write shared/mcp-tools.md**

Source: the retained half of `n8n-mcp-tools-expert/SKILL.md`. Must cover, with the upstream specifics preserved:
- Tool selection: which tool for node discovery, which for config detail, which for validation, which for workflow management.
- `nodeType` format rules — `nodes-base.*` versus `n8n-nodes-base.*`, and which tool expects which.
- Validation profiles: `minimal`, `runtime`, `ai-friendly`, `strict`.
- Smart parameters, e.g. `branch="true"` for IF nodes.
- `get_node` detail levels and when essentials beats full info.
- Deeper material: point at `references/deep/nodes/SEARCH_GUIDE.md`, `references/deep/validate/VALIDATION_GUIDE.md`, `references/deep/instances/WORKFLOW_GUIDE.md`, `references/deep/instances/OPERATIONS_GUIDE.md`.

- [ ] **Step 2: Write shared/non-negotiables.md**

Source: the `## Non-negotiables` section of the upstream router. Three rules with no exceptions, each with the class of production failure it prevents. Reword rule 1 from "invoke the relevant skill" to "read the relevant route reference", since there is now one skill.

- [ ] **Step 3: Write shared/drift.md**

Source: the drift paragraph of the upstream router. The point: n8n and n8n-mcp move faster than any model's training data, and faster than this pack. When a tool reports a parameter shape, node `typeVersion` or behavior that contradicts anything here, the live tool wins — say so to the user and suggest updating the pack.

- [ ] **Step 4: Verify**

Run: `python3 scripts/validate-pack.py 2>&1 | grep "references/shared" || echo "shared refs clean"`
Expected: `shared refs clean`

- [ ] **Step 5: Commit**

```bash
git add skills/n8n/references/shared/
git commit -m "feat: add shared MCP tool, non-negotiable and drift references"
```

---

### Task 7: Routes — design, nodes, expressions

Each route file follows one shape: what this route owns, the rules that matter, then a table of deeper references with a one-line reason to open each.

**Files:**
- Create: `skills/n8n/references/workflow-design.md`
- Create: `skills/n8n/references/workflow-nodes.md`
- Create: `skills/n8n/references/workflow-expressions.md`

**Interfaces:**
- Consumes: old SKILL.md bodies via `git show HEAD~3:skills/n8n-workflow-patterns/SKILL.md` and the equivalent for `n8n-subworkflows`, `n8n-node-configuration`, `n8n-expression-syntax`.
- Produces: three of the ten route files.

- [ ] **Step 1: Write workflow-design.md**

Merge `n8n-workflow-patterns/SKILL.md` and `n8n-subworkflows/SKILL.md`. Cover: choosing among the five architectures; naming nodes for what they do; sticky notes capturing why; searching existing workflows with `n8n_list_workflows` and reusing a sub-workflow before duplicating logic; typed sub-workflow inputs ("Define Below"); all-versus-each execution mode; verb-first naming for discovery; stateless versus stateful; splitting by input shape; the ~10-node threshold for extraction; and the performance notes on node count and `batchSize`.

Deeper references table: `deep/design/webhook_processing.md`, `http_api_integration.md`, `database_operations.md`, `ai_agent_workflow.md`, `scheduled_tasks.md`, `SUBWORKFLOW_PATTERNS.md`, `NAMING_AND_DISCOVERY.md`.

- [ ] **Step 2: Write workflow-nodes.md**

From `n8n-node-configuration/SKILL.md`. Cover: which fields are required per operation; how `displayOptions` control field visibility; `patchNodeField` for surgical edits versus full node updates; `get_node` detail levels; node discovery.

Deeper references: `deep/nodes/DEPENDENCIES.md`, `OPERATION_PATTERNS.md`, `NODE_FAMILY_GOTCHAS.md`, `SEARCH_GUIDE.md`.

- [ ] **Step 3: Write workflow-expressions.md**

From `n8n-expression-syntax/SKILL.md`. Cover: `{{}}` syntax; `$json`/`$node`/`$('Node').item.json` access; the webhook `.body` nesting gotcha (upstream flags it as the single most common mistake — it must survive prominently); when to reach for a Code node instead; the note on complex-expression performance.

Deeper references: `deep/expressions/COMMON_MISTAKES.md`, `EXAMPLES.md`.

- [ ] **Step 4: Verify**

Run: `python3 scripts/validate-pack.py 2>&1 | grep -E "workflow-(design|nodes|expressions)" || echo "routes A clean"`
Expected: `routes A clean`

- [ ] **Step 5: Commit**

```bash
git add skills/n8n/references/workflow-design.md skills/n8n/references/workflow-nodes.md skills/n8n/references/workflow-expressions.md
git commit -m "feat: add design, nodes and expressions route references"
```

---

### Task 8: Routes — code, agents, binary

**Files:**
- Create: `skills/n8n/references/workflow-code.md`
- Create: `skills/n8n/references/workflow-agents.md`
- Create: `skills/n8n/references/workflow-binary.md`

**Interfaces:**
- Consumes: `git show HEAD~4:skills/n8n-code-javascript/SKILL.md` and the equivalents for `n8n-code-python`, `n8n-code-tool`, `n8n-agents`, `n8n-binary-and-data`.
- Produces: three route files.

- [ ] **Step 1: Write workflow-code.md**

This is the consolidation that justifies the redesign. Three upstream skills used mutually-referencing `EXCEPTION —` clauses to disambiguate; here it is one decision at the top of one file.

Open with a routing block:

```
Which runtime are you writing for?

- Workflow Code node, JavaScript  → "JavaScript" below. The default; use it
  for ~95% of cases.
- Workflow Code node, Python      → "Python" below. Only when the user
  explicitly prefers Python or needs its
  standard library (regex, hashlib, statistics).
- AI-agent Custom Code Tool       → "Code Tool" below. Different runtime
  (@n8n/n8n-nodes-langchain.toolCode)  contract: input is `query`, the return
                                    must be a string, and $fromAI / $input /
                                    $helpers do not exist.
```

Then three sections. **JavaScript:** `$input`/`$json`/`$node`, `this.helpers` and the `$helpers` global for HTTP, `DateTime` (Luxon), Code node modes and which is faster, SplitInBatches loop patterns, cross-iteration data, `pairedItem`, per-item overhead on large datasets. **Python:** `_input`/`_json`/`_node`, standard-library limits, why JavaScript is the default. **Code Tool:** return format string versus `[{json:{...}}]`, `specifyInputSchema` / `jsonSchemaExample` / `DynamicStructuredTool`, naming rules for AI invocation, when `toolWorkflow` or the HTTP Request Tool is the better choice, and the named errors — "Wrong output type returned", "No execution data available", "The response property should be a string, but it is an object", "Cannot assign to read only property 'name'".

Deeper references: `deep/code/js/{DATA_ACCESS,BUILTIN_FUNCTIONS,COMMON_PATTERNS,ERROR_PATTERNS}.md`, `deep/code/python/{DATA_ACCESS,STANDARD_LIBRARY,COMMON_PATTERNS,ERROR_PATTERNS}.md`, `deep/code/tool/{INPUT_SCHEMA,ERROR_PATTERNS}.md`.

- [ ] **Step 2: Write workflow-agents.md**

From `n8n-agents/SKILL.md`. Cover: Agent versus LLM chain versus Text Classifier versus Information Extractor; the model/memory/tools/outputParser slots; tool names and descriptions functioning as prompt; structured output with autoFix; memory and `sessionId`; RAG and vector stores; human-in-the-loop review; chat topologies; `$fromAI`.

Deeper references: `deep/agents/{TOOLS,SYSTEM_PROMPT,STRUCTURED_OUTPUT,MEMORY,RAG,HUMAN_REVIEW,SUBWORKFLOW_AS_TOOL,CHAT_AGENT_PATTERNS,EXAMPLES}.md`.

- [ ] **Step 3: Write workflow-binary.md**

From `n8n-binary-and-data/SKILL.md`. Cover: the `$binary` versus `$json` split; reading and writing binary; `binaryPropertyName`; keeping binary alive across transforms with Merge; the agent-tool binary boundary; the CDN/URL requirement for chat surfaces.

Deeper references: `deep/binary/{BINARY_BASICS,MERGE_FOR_CONTEXT,AGENT_TOOL_BINARY,CDN_REQUIREMENT}.md`.

- [ ] **Step 4: Verify**

Run: `python3 scripts/validate-pack.py 2>&1 | grep -E "workflow-(code|agents|binary)" || echo "routes B clean"`
Expected: `routes B clean`

- [ ] **Step 5: Commit**

```bash
git add skills/n8n/references/workflow-code.md skills/n8n/references/workflow-agents.md skills/n8n/references/workflow-binary.md
git commit -m "feat: add code, agents and binary route references"
```

---

### Task 9: Routes — errors, validate

**Files:**
- Create: `skills/n8n/references/workflow-errors.md`
- Create: `skills/n8n/references/workflow-validate.md`

**Interfaces:**
- Consumes: `git show HEAD~5:skills/n8n-error-handling/SKILL.md`, `git show HEAD~5:skills/n8n-validation-expert/SKILL.md`, and the hook reminder texts from `git show HEAD~5:hooks/pre-tool-use/validate-workflow.sh` and `test-workflow.sh`.
- Produces: two route files.

- [ ] **Step 1: Write workflow-errors.md**

From `n8n-error-handling/SKILL.md`. Cover: per-node error outputs (`onError`, `continueErrorOutput`, wiring `main[1]`); retries and `retryOnFail`; Error Trigger workflows; Respond to Webhook status codes with the caller-fault-4xx / your-fault-5xx rule; why silent failures are the real risk in unattended workflows.

Include the side-effect warning verbatim from `test-workflow.sh`: `n8n_test_workflow` executes real nodes — Code, HTTP Request, database writes, Slack and email sends and sub-workflow calls all fire for real. Ask the user before running if any node has user-visible side effects, and afterwards tell them which nodes ran live.

Deeper references: `deep/errors/{NODE_ERROR_OUTPUTS,ERROR_WORKFLOWS,RESPONSE_SHAPES,API_WORKFLOWS}.md`.

- [ ] **Step 2: Write workflow-validate.md**

From `n8n-validation-expert/SKILL.md`. Cover: reading validation errors and warnings; which warnings are false positives; validation profiles; the validation loop; auto-sanitization; and the framing that validation passing means the JSON is well-formed, not that the workflow is correct.

Include the antipattern scan verbatim from `validate-workflow.sh`, as a checklist to run node-by-node — `validate_workflow` catches none of it:
- Set nodes feeding only one consumer should be inlined.
- Code nodes doing pure field shaping should be Edit Fields with arrow functions.
- Merges with 3+ wires need `numberOfInputs` set explicitly.
- `$json.x` in branchy workflows should be `$('Node').item.json.x`.
- DateTime nodes should be Luxon expressions.

Also carry the connection-verification rule from `update-workflow.sh`: after applying operations, verify the `connections` object with `n8n_get_workflow`, because `validate_workflow` does not catch every multi-input wiring trap.

Deeper references: `deep/validate/{ERROR_CATALOG,FALSE_POSITIVES,REVIEW_CHECKLIST,VALIDATION_GUIDE}.md`.

- [ ] **Step 3: Verify**

Run: `python3 scripts/validate-pack.py 2>&1 | grep -E "workflow-(errors|validate)" || echo "routes C clean"`
Expected: `routes C clean`

- [ ] **Step 4: Commit**

```bash
git add skills/n8n/references/workflow-errors.md skills/n8n/references/workflow-validate.md
git commit -m "feat: add errors and validate route references"
```

---

### Task 10: Routes — instances, self-host

**Files:**
- Create: `skills/n8n/references/workflow-instances.md`
- Create: `skills/n8n/references/workflow-self-host.md`

**Interfaces:**
- Consumes: `git show HEAD~6:skills/n8n-multi-instance/SKILL.md`, `git show HEAD~6:skills/n8n-self-hosting/SKILL.md`, `git show HEAD~6:skills/n8n-mcp-tools-expert/SKILL.md`.
- Produces: the final two route files; `check_routes_exist` passes completely.

- [ ] **Step 1: Write workflow-instances.md**

Merge the workflow-lifecycle half of `n8n-mcp-tools-expert` with all of `n8n-multi-instance`. Cover: creating, updating, listing and testing workflows; folders; credential management and the rule that credentials hold live secrets so `getSchema` and the credential system are used rather than inlined tokens; instance security auditing.

Then multi-instance: every n8n tool routes to the currently-targeted instance and there is no per-call instance argument; switch in its own turn and never batch a switch with a dependent call, because parallel-batch order is not guaranteed; verify with `n8n_instances list` immediately before any credential create/update/delete; the server fail-closes only the ambiguous case (`INSTANCE_AMBIGUOUS`), so an explicit switch to the wrong instance still writes the secret there; an unexpected `NOT_FOUND` is almost always a wrong-instance misroute rather than a deletion — verify and retry, do not recreate.

Deeper references: `deep/instances/{WORKFLOW_GUIDE,OPERATIONS_GUIDE}.md`.

- [ ] **Step 2: Write workflow-self-host.md**

From `n8n-self-hosting/SKILL.md`. Preserve the interaction order that skill enforces: ask single-versus-queue mode first, then collect domain, SSH target and timezone, then generate fresh secrets on the box, then bring the stack up with TLS. Cover Docker Compose behind Caddy with automatic HTTPS, queue mode with workers, day-2 update/backup/restore, hardening, and credential overwrites (the "Sign in with Google" case). State plainly that this is for self-hosted Docker n8n, not n8n Cloud.

Asset paths, relative to the skill root: `assets/docker-compose.single.yml`, `assets/docker-compose.queue.yml`, `assets/Caddyfile`, `assets/.env.single.example`, `assets/.env.queue.example`, `assets/init-data.sh`.

Deeper references: `deep/self-host/{SINGLE_MODE,QUEUE_MODE,SECURITY,DAY2,CREDENTIAL_OVERWRITES}.md`.

- [ ] **Step 3: Verify all ten routes now exist and every link resolves**

Run: `python3 scripts/validate-pack.py 2>&1 | grep -E "route file|points at missing" || echo "all routes and links clean"`
Expected: `all routes and links clean`

- [ ] **Step 4: Commit**

```bash
git add skills/n8n/references/workflow-instances.md skills/n8n/references/workflow-self-host.md
git commit -m "feat: add instances and self-host route references"
```

---

### Task 11: Hooks

**Files:**
- Create: `hooks/reset-markers.sh`
- Delete: `hooks/session-start.sh`
- Modify: `hooks/hooks.json`, all 7 `hooks/pre-tool-use/*.sh`, `hooks/post-tool-use/validate-workflow.sh`

**Interfaces:**
- Produces: `check_hooks` and `check_no_old_skill_names` pass. No hook emits `SessionStart` `additionalContext`.

- [ ] **Step 1: Confirm the hook checks currently fail**

Run: `python3 scripts/validate-pack.py 2>&1 | grep -E "session-start|reset-markers|old skill name"`
Expected: `FAIL: hooks/session-start.sh still exists`, `FAIL: hooks/reset-markers.sh is missing`, and a batch of old-skill-name failures from the reminder texts.

- [ ] **Step 2: Write hooks/reset-markers.sh**

```bash
#!/usr/bin/env bash
# SessionStart hook. Wipes the PreToolUse dedup markers on /clear and /compact,
# because the agent's memory of those reminders is gone after a context reset
# and the markers must not keep them silent.
#
# This hook deliberately emits NOTHING on stdout. Upstream injected the whole
# router skill here, which cost every session — n8n-related or not — about 700
# tokens. Injection is gone; only the reset behavior is kept.
#
# Always exits 0. Never blocks session startup.

set -uo pipefail

STATE_DIR="${TMPDIR:-/tmp}/n8n-skills-state"
INPUT="$(cat)"

read_field() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "${INPUT}" | jq -r ".${1} // empty" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "${INPUT}" | python3 -c \
      "import json,sys; print(json.load(sys.stdin).get('$1',''))" 2>/dev/null
  fi
}

SOURCE="$(read_field source)"
SESSION_ID="$(read_field session_id)"

if [[ "${SOURCE}" == "clear" || "${SOURCE}" == "compact" ]] \
   && [[ -n "${SESSION_ID}" ]]; then
  rm -f "${STATE_DIR}/${SESSION_ID}-"*.loaded 2>/dev/null || true
fi

# Garbage-collect markers from sessions that ended long ago, so $TMPDIR does
# not accumulate one file per session per marker forever.
if [[ -d "${STATE_DIR}" ]]; then
  find "${STATE_DIR}" -name '*.loaded' -type f -mtime +7 -delete 2>/dev/null || true
fi

exit 0
```

Make it executable: `chmod +x hooks/reset-markers.sh`

- [ ] **Step 3: Rewire hooks.json**

Replace the `SessionStart` block with:

```json
"SessionStart": [
  {
    "matcher": "clear|compact",
    "hooks": [
      {
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/reset-markers.sh"
      }
    ]
  }
]
```

Leave the 7 `PreToolUse` matchers and the 1 `PostToolUse` matcher unchanged — they are already correctly anchored to MCP tool names.

- [ ] **Step 4: Update the shared state directory name in _emit.sh**

In `hooks/pre-tool-use/_emit.sh`, change `STATE_DIR="${TMPDIR:-/tmp}/n8n-mcp-skills-state"` to `STATE_DIR="${TMPDIR:-/tmp}/n8n-skills-state"` so it matches `reset-markers.sh`. A mismatch here silently breaks the reset.

- [ ] **Step 5: Retarget all 8 reminder texts**

In each of the 7 `pre-tool-use/*.sh` and `post-tool-use/validate-workflow.sh`, replace every "invoke `<old-skill-name>` via the Skill tool" with a pointer to the new structure, keeping every substantive fact verbatim. Pattern:

```
"invoke n8n-workflow-patterns ... and n8n-subworkflows ... via the Skill tool"
  →
"invoke the n8n skill (Skill tool), then read references/workflow-design.md"
```

Mapping for the reminder texts:

| Hook | Old skills named | New pointer |
|---|---|---|
| `create-workflow.sh` | workflow-patterns, subworkflows | `references/workflow-design.md` |
| `get-node.sh` | node-configuration | `references/workflow-nodes.md` |
| `update-workflow.sh` | node-configuration, validation-expert, error-handling | `references/workflow-nodes.md`, `workflow-validate.md`, `workflow-errors.md` |
| `validate-workflow.sh` | validation-expert, workflow-patterns | `references/workflow-validate.md` |
| `test-workflow.sh` | validation-expert, error-handling | `references/workflow-validate.md`, `workflow-errors.md` |
| `instances.sh` | multi-instance | `references/workflow-instances.md` |
| `manage-credentials.sh` | mcp-tools-expert, multi-instance | `references/workflow-instances.md` |
| `post-tool-use/validate-workflow.sh` | whichever it names | corresponding route |

Do not shorten the substantive content — the antipattern scan, the side-effect warning and the instance-misroute rules stay word for word.

- [ ] **Step 6: Lint and verify**

```bash
shellcheck hooks/reset-markers.sh hooks/pre-tool-use/*.sh hooks/post-tool-use/*.sh
jq empty hooks/hooks.json
python3 scripts/validate-pack.py 2>&1 | grep -E "hook|old skill name" || echo "hook checks clean"
```
Expected: shellcheck clean, valid JSON, `hook checks clean`.

- [ ] **Step 7: Verify the reset actually works end to end**

```bash
STATE_DIR="${TMPDIR:-/tmp}/n8n-skills-state"
mkdir -p "$STATE_DIR" && touch "$STATE_DIR/testsession-create-workflow.loaded"
echo '{"source":"compact","session_id":"testsession"}' | ./hooks/reset-markers.sh
test ! -f "$STATE_DIR/testsession-create-workflow.loaded" && echo "reset works"
echo '{"source":"compact","session_id":"testsession"}' | ./hooks/reset-markers.sh | wc -c
```
Expected: `reset works`, and the byte count is `0` — the hook must emit nothing.

- [ ] **Step 8: Commit**

```bash
git add hooks/
git commit -m "fix: drop SessionStart injection, retarget PreToolUse hooks at route references"
```

---

### Task 12: Eval suite remap

**Files:**
- Modify: 57 files under `evaluations/`

**Interfaces:**
- Produces: `check_evals` and the `evaluations/` half of `check_no_old_skill_names` pass.

- [ ] **Step 1: Confirm the eval checks currently fail**

Run: `python3 scripts/validate-pack.py 2>&1 | grep "evaluations/" | head -5`
Expected: failures naming unknown routes such as `n8n-code-javascript`.

- [ ] **Step 2: Remap the skills arrays**

Apply this mapping to every `"skills"` array and to the singular `"skill"` key that appears in one code-python eval:

| Old | New |
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

Deduplicate where a merge collapses two entries into one. Normalise the singular `"skill"` key to a `"skills"` array so the validator sees a single shape.

- [ ] **Step 3: Reword the expected_behavior assertions**

Every string of the form `"Activate <old-skill> skill"` becomes `"Read references/<route>.md"`. Leave `expected_content` untouched — it asserts on `deep/` filenames, which are frozen.

- [ ] **Step 4: Verify**

```bash
for f in $(git ls-files 'evaluations/*.json'); do jq empty "$f" || echo "BAD: $f"; done
python3 scripts/validate-pack.py 2>&1 | grep "evaluations/" || echo "eval checks clean"
```
Expected: all JSON valid, `eval checks clean`.

- [ ] **Step 5: Commit**

```bash
git add evaluations/
git commit -m "test: remap eval suite onto route names"
```

---

### Task 13: Build script and documentation

**Files:**
- Modify: `build.sh`, `README.md`, `CLAUDE.md`, `docs/INSTALLATION.md`, `docs/USAGE.md`, `docs/DEVELOPMENT.md`

**Interfaces:**
- Produces: `check_readme_banner` passes; `build.sh` runs clean and produces correctly-named artifacts.

- [ ] **Step 1: Update build.sh**

The skill-list derivation from the tree needs no change. Two edits: rename the bundle zip from `n8n-mcp-skills-v${VERSION}.zip` to `n8n-skills-v${VERSION}.zip`, and add `scripts/` and `CHANGELOG.md` to the bundle file list.

- [ ] **Step 2: Add the fork banner at the very top of README.md**

Above the title, badges and video — the first thing anyone sees. The validator requires "Fork of" plus the words "one skill", "telemetry" and "session" within the first 15 lines.

```markdown
> ### Fork of [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills)
>
> Same n8n knowledge, restructured packaging. What changed:
>
> - **One skill, not fifteen.** A single `n8n` skill routes to ten workflow
>   references read on demand. Upstream's fifteen skill descriptions became one.
> - **Nothing is injected into your sessions.** Upstream's `SessionStart` hook
>   loaded its router skill into *every* session regardless of topic, costing
>   roughly 700 tokens whether or not you were touching n8n. Removed.
> - **Local MCP server, pinned.** No hosted `api.n8n-mcp.com` endpoint; `n8n-mcp`
>   runs locally over stdio at a pinned version against your own n8n.
> - **Telemetry off.** `n8n-mcp` enables telemetry by default; this fork sets
>   `N8N_MCP_TELEMETRY_DISABLED=true`.
>
> Upstream owns the n8n expertise and deserves the credit for it. See
> [CHANGELOG.md](CHANGELOG.md) for detail.
```

- [ ] **Step 3: Rewrite the README body**

Replace the "The 14 Skills" section with one describing the single skill and its ten routes as a table. Update the skill count in the "What is this?" paragraph. Update the install instructions to reference `skills/n8n` rather than 15 directories. Keep the badges pointed at the fork, and keep the upstream video link with attribution.

- [ ] **Step 4: Rewrite CLAUDE.md**

It currently opens "**Purpose**: 14 complementary skills…". Rewrite for the single-skill architecture: the orchestrator pattern, where routes live, the frozen-filename rule for `deep/`, and the requirement that `python3 scripts/validate-pack.py` passes before any commit.

- [ ] **Step 5: Update docs/INSTALLATION.md**

Remove the per-skill zip instructions (there is one skill now). Make the MCP section match `mcp.json` exactly — pinned version, telemetry variable, `${VAR}` credentials — and record whatever Task 3 Step 4 established about plugin-level expansion. Keep `docs/MCP_TESTING_LOG.md` and `docs/CODE_NODE_BEST_PRACTICES.md` untouched.

- [ ] **Step 6: Update docs/USAGE.md and docs/DEVELOPMENT.md**

USAGE: replace "invoke skill X" guidance with the single skill and its routing table. DEVELOPMENT: document how to add a route (create `references/workflow-<name>.md`, add a row to the `SKILL.md` table, add the name to `ROUTES` in `scripts/validate-pack.py`, add an eval) and that the validator gates every change.

- [ ] **Step 7: Verify**

```bash
bash build.sh && ls -1 dist/
python3 scripts/validate-pack.py
```
Expected: `dist/n8n-v0.1.0.zip` and `dist/n8n-skills-v0.1.0.zip`; validator prints `All structural checks passed`.

- [ ] **Step 8: Commit**

```bash
git add build.sh README.md CLAUDE.md docs/
git commit -m "docs: rewrite for single-skill architecture, add fork banner"
```

---

### Task 14: Live verification and publish

**Files:**
- None modified unless verification finds a defect.

**Interfaces:**
- Consumes: everything.
- Produces: a pushed branch on `derberg/n8n-skills` and a confirmed-loading plugin.

- [ ] **Step 1: Full validator run**

Run: `python3 scripts/validate-pack.py`
Expected: `All structural checks passed`.

- [ ] **Step 2: Confirm the pack loads and the injection is gone**

In a scratch directory unrelated to n8n, start an interactive Claude Code session with `--plugin-dir /Users/derberg/Documents/GitHub/n8n-skills`. Confirm:
- `n8n-skills:n8n` appears in the skill list.
- No n8n content is injected at session start — nothing about n8n appears until you mention it.
- Asking an n8n question causes the skill to be invoked and a route file to be read.
- `/mcp` shows `n8n-mcp` connected (this is also Task 3 Step 4's checkpoint).

- [ ] **Step 3: Confirm the old skills are gone from the listing**

None of the 15 old names may appear. If any does, a stale install is shadowing the fork.

- [ ] **Step 4: Push the branch**

```bash
git push -u origin feat/single-skill-orchestrator
```

- [ ] **Step 5: Set the fork's repository metadata**

```bash
gh repo edit derberg/n8n-skills \
  --description "Fork of czlonkowski/n8n-skills: one orchestrator skill instead of 15, no always-on session injection, local pinned MCP server with telemetry off" \
  --homepage "https://github.com/derberg/n8n-skills"
```

- [ ] **Step 6: Open the PR into the fork's own main**

```bash
gh pr create --repo derberg/n8n-skills --base main \
  --head feat/single-skill-orchestrator \
  --title "Single-skill orchestrator redesign" \
  --body "See docs/superpowers/specs/2026-09-01-n8n-skills-fork-redesign-design.md"
```

The base must be `derberg/n8n-skills`'s `main`, **not** upstream's. `gh` defaults a PR from a fork to the upstream repository; passing `--repo derberg/n8n-skills` prevents accidentally opening a PR against `czlonkowski/n8n-skills`.

- [ ] **Step 7: Merge and confirm**

Merge the PR once CI (if any) is green, then confirm `main` on the fork carries the new structure.

---

## Self-Review

**Spec coverage:** Fork identity → Task 2. Skill surface and relocation → Task 4. `SKILL.md` anatomy and description → Task 5. Shared files → Task 6. Route mapping including the `n8n-mcp-tools-expert` split → Tasks 6–10. Hooks including the marker-reset rationale → Task 11. `mcp.json` with all four changes → Task 3, with the expansion checkpoint at Step 4. Evals, `build.sh`, docs → Tasks 12–13. Publish → Task 14. The README fork annotation is Task 13 Step 2 and is enforced by `check_readme_banner`. No spec section is unimplemented.

**Placeholder scan:** No TBD or TODO. Every code step carries literal content. The route-file steps specify exactly which topics must be covered and which deep files to link, rather than saying "port the content".

**Type consistency:** `ROUTES` in the validator matches the ten filenames in the File Structure table, the `SKILL.md` route table in Task 5, the hook mapping in Task 11 Step 5 and the eval mapping in Task 12 Step 2. The state directory is `n8n-skills-state` in both `reset-markers.sh` (Task 11 Step 2) and `_emit.sh` (Task 11 Step 4) — the rename is called out explicitly because a mismatch fails silently. `PINNED_MCP` is `n8n-mcp@2.77.0` in the validator, `mcp.json` and `.mcp.json.example`.

**One known gap, deliberately left open:** Task 3 Step 4 cannot be completed headlessly. It is written as a checkpoint with a concrete fallback rather than an assumption.
