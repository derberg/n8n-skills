# Route: Configure a node

Owns node parameters — which fields an operation actually requires, why fields appear and
disappear, and how to edit them without clobbering the rest.

Read [shared/mcp-tools.md](shared/mcp-tools.md) for `nodeType` formats before calling any
tool named here.

## The rule that prevents most breakage

**Configure from the live schema, never from memory.** Call `get_node` before you set
parameters. Remembered parameter names are often silently wrong: n8n accepts unknown keys
as plain strings, validation reports the JSON as well-formed, and the parameter does
nothing at runtime.

## Requirements are operation-aware

Not all fields are always required — it depends on `resource` + `operation`.

```javascript
// Slack, operation = 'post'
{"resource": "message", "operation": "post",
 "channel": "#general",   // required for post
 "text": "Hello!"}

// Slack, operation = 'update'
{"resource": "message", "operation": "update",
 "messageId": "123",      // required for update — different field
 "text": "Updated!"}      // channel NOT required here
```

Never carry a field list from one operation to another.

## Property dependencies: `displayOptions`

Fields appear and disappear based on other fields' values. The mechanism is
`displayOptions`, with `show` / `hide` blocks where **multiple conditions are AND-ed and
multiple values are OR-ed**.

```javascript
// HTTP Request, method = 'GET'   → sendBody is not shown at all
{"method": "GET", "url": "https://api.example.com"}

// HTTP Request, method = 'POST'  → sendBody appears, and body becomes required
{"method": "POST", "url": "https://api.example.com",
 "sendBody": true,
 "body": {"contentType": "json", "content": {}}}
```

Three recurring shapes: the **boolean toggle** (`sendBody` → `body`), the **operation
switch** (post vs update show different fields), and **type selection** (string vs boolean
conditions).

When validation flags a field you cannot see, that field is hidden behind a
`displayOptions` rule. Find what controls it with
`get_node({mode: "search_properties", propertyQuery: "..."})` or
`get_node({detail: "full"})`. Depth:
[deep/nodes/DEPENDENCIES.md](deep/nodes/DEPENDENCIES.md).

## Detail levels — a decision tree, not a preference

1. Starting a new node config → `get_node` with **`detail: "standard"`** (the default).
   ~1–2K tokens, required fields plus common options, covers ~95% of needs.
2. Standard has what you need → configure with it. Otherwise continue.
3. Looking for one specific field → `get_node({mode: "search_properties", propertyQuery})`.
4. Still short → `get_node({detail: "full"})` (~3–8K tokens).

Reaching for `detail: "full"` by reflex is one of the eight recurring mistakes in
[shared/mcp-tools.md](shared/mcp-tools.md).

## Dynamic properties: do not guess an ID

When `standard` detail marks a property with
`dynamicOptions: {methodName, methodType, dependsOn}`, its real values come from a live
`loadOptions` / `listSearch` method, not from bundled docs. Resolve it with
`n8n_explore_node_resources` (needs `N8N_MCP_ACCESS_TOKEN`, n8n 2.34+). All six parameters
are required and none are inferred:

```javascript
n8n_explore_node_resources({
  nodeType: "n8n-nodes-base.googleSheets",  // LONG form
  version: 4.5,                              // the typeVersion the method belongs to
  methodName: "getSheets",                   // verbatim from dynamicOptions
  methodType: "listSearch",                  // listSearch for resource locators,
                                             // loadOptions for plain dropdowns
  credentialType: "googleSheetsOAuth2Api",
  credentialId: "c2",                        // n8n_manage_credentials({action:"list"})
  currentNodeParameters: {                   // whatever dependsOn names
    documentId: {__rl: true, mode: "id", value: "1AbC…"}
  }
})
```

Put the returned `value` in the config; `name` is display text only. `dependsOn` names the
parameters the method needs already chosen — pass them in `currentNodeParameters`, keeping
resource-locator values in their `{__rl: true, mode, value}` shape, or the method returns
nothing useful. `methodName` is case-sensitive and specific to the `nodeType` + `version`
pair; a mismatch returns `OFFICIAL_MCP_ERROR` rather than an empty list.

## Editing: prefer surgical over wholesale

Use `n8n_update_partial_workflow` with `patchNodeField` for a single field rather than
replacing the whole node. `updateNode` takes `updates: {...}`, **not** `parameters: {...}`.
Always include `intent`.

Every node is auto-sanitized on any update (operator structures, IF/Switch metadata). That
cannot fix broken connections or branch-count mismatches — so verify `connections` with
`n8n_get_workflow` after every write.

## Node families with real traps

`Merge` defaults to 2 inputs and silently drops the third; `useDataOfInput` is 1-indexed
while the wire sits at `main[N-1]`. `Switch` drops unmatched items without
`options.fallbackOutput: "extra"`. `Respond to Webhook` defaults `responseCode` to 200 on
every path, including error branches. Database nodes interpolate `{{ }}` into SQL *before*
the driver binds parameters. `SplitInBatches v3` and Google Sheets have their own
specifics.

All of these, per family:
[deep/nodes/NODE_FAMILY_GOTCHAS.md](deep/nodes/NODE_FAMILY_GOTCHAS.md).

## Deeper references

| Read when | File |
|---|---|
| Working out what controls a hidden field | [deep/nodes/DEPENDENCIES.md](deep/nodes/DEPENDENCIES.md) |
| Configuring a resource/operation, HTTP, database or conditional node | [deep/nodes/OPERATION_PATTERNS.md](deep/nodes/OPERATION_PATTERNS.md) |
| A specific node family is misbehaving | [deep/nodes/NODE_FAMILY_GOTCHAS.md](deep/nodes/NODE_FAMILY_GOTCHAS.md) |
| Finding the right node in the first place | [deep/nodes/SEARCH_GUIDE.md](deep/nodes/SEARCH_GUIDE.md) |
