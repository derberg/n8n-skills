# n8n-mcp tools — working knowledge from turn one

Cross-cutting reference. Every route that calls an MCP tool depends on this file.

Qualified names look like `mcp__<server>__<tool>`, where `<server>` is usually `n8n-mcp`.

## Two tiers

**Always present** — these work offline against the bundled node database:
`search_nodes`, `get_node`, `validate_node`, `validate_workflow`, `tools_documentation`,
and the template search tools.

**Present only when a live n8n instance is connected** — every `n8n_*` tool:
`n8n_create_workflow`, `n8n_update_partial_workflow`, `n8n_update_full_workflow`,
`n8n_get_workflow`, `n8n_list_workflows`, `n8n_validate_workflow`, `n8n_test_workflow`,
`n8n_autofix_workflow`, `n8n_deploy_template`, `n8n_manage_credentials`,
`n8n_manage_datatable`, `n8n_manage_folders`, `n8n_audit_instance`, `n8n_instances`,
`n8n_list_catalog`. Two more additionally need `N8N_MCP_ACCESS_TOKEN`:
`n8n_manage_agents` and `n8n_explore_node_resources`.

If the `n8n_*` tools are missing, nothing is broken and there is nothing to retry. The
server needs `N8N_API_URL` and `N8N_API_KEY` in its environment, exported before the
client starts. Say that plainly and carry on with read-only work.

## Critical: two `nodeType` formats

Getting this wrong produces "Node not found" or a silently malformed workflow.

| Format | Looks like | Used by |
|---|---|---|
| **SHORT** | `nodes-base.slack`, `nodes-langchain.agent` | `search_nodes`, `get_node`, `validate_node`, `validate_workflow` |
| **FULL** | `n8n-nodes-base.slack`, `@n8n/n8n-nodes-langchain.agent` | `n8n_create_workflow`, `n8n_update_partial_workflow`, `n8n_update_full_workflow` |

```javascript
get_node({nodeType: "slack"})                 // ❌ missing prefix → "Node not found"
get_node({nodeType: "n8n-nodes-base.slack"})  // ❌ FULL form is for workflow tools
get_node({nodeType: "nodes-base.slack"})      // ✅
```

`search_nodes` returns both, so you never have to convert by hand:

```javascript
{
  "nodeType": "nodes-base.slack",              // search / validate tools
  "workflowNodeType": "n8n-nodes-base.slack"   // workflow tools
}
```

## Tool selection

**Node discovery** — `search_nodes({query})` → `get_node({nodeType, includeExamples: true})`.
Default `detail: "standard"` covers ~95% of cases; reach for `mode: "docs"` or
`search_properties` rather than `detail: "full"`. Depth:
[../deep/nodes/SEARCH_GUIDE.md](../deep/nodes/SEARCH_GUIDE.md).

**Validation** — `validate_node({nodeType, config, profile: "runtime"})` for a single
node, `validate_workflow` for the whole thing. Depth:
[../deep/validate/VALIDATION_GUIDE.md](../deep/validate/VALIDATION_GUIDE.md).

**Workflow management** — `n8n_update_partial_workflow` is the most-used tool in the set;
prefer it over full replacement. Depth:
[../deep/instances/WORKFLOW_GUIDE.md](../deep/instances/WORKFLOW_GUIDE.md).

**Templates, data tables, folders, agents, audit** — depth:
[../deep/instances/OPERATIONS_GUIDE.md](../deep/instances/OPERATIONS_GUIDE.md).

## Validation profiles

Pass `profile` explicitly; the default is not always what you want.

| Profile | Use when |
|---|---|
| `minimal` | Fast structural sanity check only |
| `runtime` | The normal choice — what will actually fail when the workflow runs |
| `ai-friendly` | Building AI-agent nodes and tools |
| `strict` | Pre-activation review; surfaces best-practice advice as well as errors |

## Node JSON hygiene when creating workflows

Three structural mistakes break the n8n UI even when the workflow validates.

1. **Never emit a `credentials` block with a placeholder ID.** A fake ID such as
   `"id": "REPLACE_ME"` renders the credential selector permanently disabled and
   non-clickable ("No credentials yet") — the user has to rebuild the node from scratch.
   If you do not know the real ID, **omit the `credentials` block entirely**; an absent
   block shows a normal empty dropdown. Discover real IDs with
   `n8n_manage_credentials({action: "list"})`.

   ```javascript
   // ❌ breaks the credential selector
   "credentials": {"httpHeaderAuth": {"id": "REPLACE_ME", "name": "My API Key"}}
   // ✅ unknown ID → omit the block; known ID → use the real one
   ```

2. **Generate UUID v4 values for node `id`** — not readable strings like
   `"http-list-node"`. n8n's frontend binds forms and initialises credential components
   from node IDs; non-UUID IDs cause subtle breakage.

3. **Use the current `typeVersion`** for each node. Check `get_node`; do not hardcode a
   remembered version.

## The eight recurring mistakes

| # | Mistake | Fix |
|---|---|---|
| 1 | Wrong `nodeType` format | SHORT for search/validate, FULL for workflow tools |
| 2 | `detail: "full"` by default | `standard` covers 95%; use `docs` or `search_properties` |
| 3 | No validation profile | Pass `profile: "runtime"` explicitly |
| 4 | Ignoring auto-sanitization | Every node is sanitized on any update (operator structures, IF/Switch metadata). It cannot fix broken connections or branch-count mismatches |
| 5 | Not using smart parameters | Use `branch: "true"` / `case: 0` instead of fragile `sourceIndex` math |
| 6 | Omitting `intent` | Always include `intent` on `n8n_update_partial_workflow` |
| 7 | `parameters` instead of `updates` | `updateNode` takes `updates: {...}` |
| 8 | Wrong credential format | Nest by type with `{id, name}`, never a flat string |

```javascript
updates: {credentials: "myApiKey"}                                            // ❌
updates: {credentials: {httpHeaderAuth: {id: "abc123", name: "My API Key"}}}  // ✅
```

Full wrong/correct pairs for each:
[../deep/validate/VALIDATION_GUIDE.md](../deep/validate/VALIDATION_GUIDE.md).

## Do and don't

**Do** call `get_node` before setting parameters, pass `profile` explicitly, prefer
partial updates, include `intent`, and verify `connections` with `n8n_get_workflow` after
every write.

**Don't** configure from memory, hardcode `typeVersion`, use `detail: "full"` by reflex,
compute `sourceIndex` by hand when a smart parameter exists, or assume validation success
means the workflow is correct.
