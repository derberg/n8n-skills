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


def check_relative_links(skill):
    """Every relative markdown link inside the skill must resolve to a file.

    The upstream knowledge files cross-link each other with paths like
    ../n8n-node-configuration/NODE_FAMILY_GOTCHAS.md, which dangle once the
    files are relocated under references/deep/.
    """
    link = re.compile(r"\]\(([^)]+)\)")
    for md in sorted(skill.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        for target in set(link.findall(text)):
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://",
                                               "mailto:", "#")):
                continue
            resolved = (md.parent / target).resolve()
            if not resolved.exists():
                fail(f"{md.relative_to(ROOT)} has dangling link -> {target}")


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
        check_relative_links(skill)
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
