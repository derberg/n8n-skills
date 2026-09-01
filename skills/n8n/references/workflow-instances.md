# Route: Instance lifecycle

Owns everything that touches a live n8n instance: creating and updating workflows, folders,
credentials, data tables, security audit — and choosing *which* instance you are talking to.

Read [shared/mcp-tools.md](shared/mcp-tools.md) first for `nodeType` formats and the
two-tier tool model. Every tool named here is an `n8n_*` tool, so it exists only when an
instance is connected.

## Workflow lifecycle

Prefer `n8n_update_partial_workflow` over full replacement — it is the most-used tool in the
set. Always include `intent`. `updateNode` takes `updates: {...}`, not `parameters: {...}`.

**After every create or update, verify `connections` with `n8n_get_workflow`.** Validation
does not catch every multi-input wiring trap, and a half-wired error output validates clean.
See [workflow-validate.md](workflow-validate.md).

**Testing runs for real.** `n8n_test_workflow` executes real nodes — HTTP calls, database
writes, Slack and email sends and sub-workflow calls all fire. Ask the user before running if
any node has user-visible side effects, and afterwards say which nodes ran live.
`method: "prepare"` names the nodes needing data, `method: "pinned"` runs with data you
build (needs `N8N_MCP_ACCESS_TOKEN` and the workflow's "Available in MCP" setting). A
sub-workflow has no HTTP trigger, so the default `method: "auto"` cannot run it.

Full actions, list filters and semantics:
[deep/instances/WORKFLOW_GUIDE.md](deep/instances/WORKFLOW_GUIDE.md).

## Credentials

`n8n_manage_credentials` — actions `list`, `get`, `create`, `update`, `delete`, `getSchema`.

- **It never returns secrets.** `get` / `create` / `update` strip the `data` field.
- **Use `getSchema` before `create`** to discover required fields rather than guessing.
- **`includeUsage: true`** (on `list` / `get`) reverse-scans workflows and attaches
  `usedIn: [{id, name, active}]` plus `usageCount`. Use it **before deleting or rotating** a
  credential to see what breaks. It triggers a full client-side scan, caps at 5000
  workflows, excludes archived, and degrades to a `usageScanError` field on failure.
- **Never inline a token into a text field** — see
  [shared/non-negotiables.md](shared/non-negotiables.md). And never emit a placeholder
  credential ID; it permanently disables the selector in the n8n UI. See
  [shared/mcp-tools.md](shared/mcp-tools.md).

## Folders

`n8n_manage_folders` — `create`, `list`, `get`, `rename`, `move`, `delete` (n8n 2.19+).
`projectId` defaults to `'personal'`.

Placing a workflow happens in the *workflow* tools: `parentFolderId` on
`n8n_create_workflow`, or the `moveToFolder` operation of `n8n_update_partial_workflow`
(both n8n 2.32+; `null` means project root).

Two things to internalize: a workflow's folder is **write-only** in n8n's API — verify
placement via a folder's `get` counts, never by reading the workflow. And `delete` without
`transferToFolderId` **archives** the folder's workflows; `transferToFolderId: "0"` moves
them to the project root instead, keeping them active.

## Data tables

`n8n_manage_datatable` manages tables and rows from *outside* a workflow. Do not confuse it
with the in-workflow `nodes-base.dataTable` node, which reads and writes rows *during
execution* — see
[deep/nodes/OPERATION_PATTERNS.md](deep/nodes/OPERATION_PATTERNS.md). Rule of thumb: MCP
tool to set a table up once, workflow node to read and write on every execution.

`deleteRows` requires a filter. Use `dryRun: true` before bulk changes.

**Column actions** — `addColumn`, `deleteColumn`, `renameColumn` — need
`N8N_MCP_ACCESS_TOKEN` (n8n 2.34+). **`deleteColumn` drops the column's values with the
column, and there is no undo.** That bites hardest where you least expect it: a column's
type cannot be changed after creation, so "make this column a number" really means
drop-and-re-add, which throws away everything in it. Read the values out with `getRows`
first if they matter, and **confirm with the user before dropping a populated column.**

## Security audit

`n8n_audit_instance` combines n8n's built-in audit (`credentials`, `database`, `nodes`,
`instance`, `filesystem`) with a custom deep scan (`hardcoded_secrets`,
`unauthenticated_webhooks`, `error_handling`, `data_retention`). All parameters optional.
Detected secrets are masked. Output is an actionable markdown report with a remediation
playbook split into auto-fixable / requires-review / requires-user-action.

## Preflight for token-gated tools

`n8n_health_check({mode: "diagnostic"})` returns an **`officialMcp`** block —
`{configured, endpoint, reachable, toolCount, agentTools}`. It is the preflight for
everything gated on `N8N_MCP_ACCESS_TOKEN`: the agent tools, `n8n_test_workflow`'s routed
methods, native version history, the data-table column actions. Read it once before reaching
for any of them, rather than discovering the gap through a `NOT_CONFIGURED` envelope
mid-task.

---

## Multiple instances

**This section applies only when the `n8n_instances` tool is present.** If it is absent the
account is single-instance — ignore this section and use the tools directly.

When it is present, one MCP connection can reach several instances (`prod`, `staging`, one
per client). **Every other n8n tool runs against whichever instance this session is
currently targeting.** There is no per-call instance argument; you change the target only by
switching. Target the wrong instance and a read returns the wrong data and a write lands in
the wrong place — usually with **no error**.

### Six golden rules

1. **Discover first.** `n8n_instances({mode:"list"})` before acting, so you know the names
   and which is `current`.
2. **Switch by name** before work on a non-default instance:
   `n8n_instances({mode:"switch", name:"<name>"})`. Case-insensitive.
3. **Switch in its own turn.** Never put a `switch` and a dependent operation in the **same
   parallel tool-call batch** — calls in one batch have no guaranteed order, so the dependent
   call can resolve against the *previous* instance. Switch, let it return, *then* operate.
4. **Verify before high-stakes ops.** Immediately before creating, updating or deleting
   **credentials** (and before destructive workflow edits), confirm `current` is the instance
   you intend via `n8n_instances({mode:"list"})`. The system fail-closes only the *ambiguous*
   case; an explicit switch to the **wrong** instance still writes there silently, so this
   check is on you.
5. **An unexpected `NOT_FOUND` is almost always a wrong-instance misroute, not a deletion.**
   Do **not** recreate the object. Re-check the current instance and retry.
6. **On `INSTANCE_AMBIGUOUS`, switch on *this* session, then retry.** The system is refusing
   to write a secret because this session never picked a target. Comply — run `switch` here
   to confirm the instance, then retry the write. Do not work around it or retry blindly.

### Core sequence

```
1. n8n_instances({mode:"list"})                  # available[] + current + default
2. n8n_instances({mode:"switch", name:"prod"})   # bind THIS session
   → returns {previous, current}; confirm current.name == "prod"
3. do the work (n8n_list_workflows / n8n_get_workflow / …)
4. before a credential write or a delete:
   n8n_instances({mode:"list"}) → re-confirm current, THEN the write
```

`{mode:"list"}` has no side effects and returns `{current, default, available}`; each
instance is `{id, name, url, isDefault}`, and `available` entries carry `isCurrent`. **Match
by `name`; never hard-code `id`.**

## Deeper references

| Read when | File |
|---|---|
| Workflow, credential, folder or audit tool detail | [deep/instances/WORKFLOW_GUIDE.md](deep/instances/WORKFLOW_GUIDE.md) |
| Templates, data tables, self-help tools | [deep/instances/OPERATIONS_GUIDE.md](deep/instances/OPERATIONS_GUIDE.md) |
