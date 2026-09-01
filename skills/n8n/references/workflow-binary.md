# Route: Files and binary

Owns file bytes — where they live, how to read and write them, how to stop them being
silently stripped, and the hard wall at the AI-agent tool boundary.

Every n8n item carries **two independent slots**: `$json` for structured data and
`$binary` for file bytes. File contents — the actual PDF, image or zip — live in `$binary`,
never in `$json`.

## The three rules that prevent 90% of binary bugs

1. **File contents are in `$binary`, not `$json`.** After an HTTP download, a "Read
   Files", or an email-attachment trigger, the bytes sit in `$binary.<key>`. `$json` holds
   metadata at most. Reading `$json.data` for file contents gives you nothing.
2. **Binary cannot cross the AI-agent tool boundary — in either direction.** Tool
   arguments and return values are JSON only. Pre-stage to storage and pass a key or URL
   through JSON instead.
3. **Chat surfaces render images by URL, not by `$binary`.** Slack, Discord, Teams,
   Telegram and embedded webhook chat never read the binary slot.

## The two slots

```json
{
  "json": { "customerId": 42, "status": "sent" },
  "binary": {
    "invoice": {
      "data": "<base64-encoded bytes>",
      "mimeType": "application/pdf",
      "fileName": "invoice-42.pdf",
      "fileExtension": "pdf"
    }
  }
}
```

The key inside `binary` (`invoice` here) is the **binary property name**. Most
file-handling nodes have a `binaryPropertyName` parameter pointing at it — the producer
names the slot, the consumer references it by that name. The default key across most nodes
is `data`, so when nothing says otherwise, assume `$binary.data`.

`$json` and `$binary` are separate namespaces and never mix.
`{{ $binary.invoice.fileName }}` reads file metadata; `{{ $json.customerId }}` reads data.

This also explains a webhook gotcha: a Webhook trigger receiving `multipart/form-data` puts
the uploaded file in `$binary` and the accompanying form fields in `$json.body` — an
uploaded file is **not** anywhere under `$json`. (The `$json.body` nesting itself is
[workflow-expressions.md](workflow-expressions.md) territory.)

Full slot anatomy, mime types and size limits:
[deep/binary/BINARY_BASICS.md](deep/binary/BINARY_BASICS.md).

## Producing binary

You rarely build a `$binary` slot by hand — nodes populate it.

| Source | How binary appears |
|---|---|
| HTTP Request with `responseFormat: "file"` | Response body lands in `$binary.data` (or the name you set) |
| Read/Write Files from Disk | File contents read into `$binary` |
| Storage downloads (S3, Drive, Dropbox, …) | Downloaded file in `$binary.<key>` |
| Email triggers with attachments | Each attachment arrives in `$binary` |
| Provider AI media nodes | Set `options.binaryPropertyOutput` so bytes land where the next node looks |

For an HTTP download the one field that matters is `responseFormat`. Confirm it with
`get_node` on `nodes-base.httpRequest` — leaving the default JSON/string format is the
classic reason a downloaded file ends up as garbled text in `$json` instead of clean bytes
in `$binary`.

## Reading and writing binary in a Code node

Most workflows never crack open the bytes — they pass binary through to a consumer. When
you do need the raw bytes, use a Code node.

**Read** with `getBinaryDataBuffer`; do not base64-decode `$binary.<key>.data` by hand:

```javascript
// Code node, "Run Once for Each Item"
const buffer = await this.helpers.getBinaryDataBuffer(0, 'data'); // (itemIndex, propertyName)
const text = buffer.toString('utf-8');

return [{
  json: { ...$json, length: buffer.length },
  binary: $input.item.binary,   // pass the binary through, or it's gone
}];
```

**Write** by building the slot yourself — base64 bytes plus mime type and file name.

## Keeping binary alive across transforms

JSON-only nodes — Edit Fields (Set), Code, IF and others — **can drop the `$binary` slot**.
The workflow validates clean and runs without error; the file simply is not there
downstream when the email node goes to attach it.

Two ways to keep it:

- **Pass-through option on the transforming node.** Edit Fields has `includeOtherFields`; a
  Code node can return `binary: $input.item.binary` explicitly. Cheapest fix when
  available.
- **Fan out and Merge by position.** Route the source into both the transform and a bypass
  branch, then recombine with a Merge in `combineByPosition` mode.

```
[Source with binary] ─┬─→ [Edit Fields: change JSON] ─┐
                      │      (binary stripped here)   ├─→ [Merge: combineByPosition] ─→ [Email: attach]
                      └───────────────────────────────┘
                          (bypass — binary passes through untouched)
```

`combineByPosition` pairs item N from each input, so item counts must line up. Wiring and
the alternatives for many-strip-point chains:
[deep/binary/MERGE_FOR_CONTEXT.md](deep/binary/MERGE_FOR_CONTEXT.md).

## The agent-tool binary boundary

The sharpest edge. An AI Agent talks to its tools over JSON; binary does not fit through
that pipe in either direction. The fix is the same shape both ways: **stage the bytes in
storage, pass a key or URL through JSON, fetch on the other side.**

**Inbound — a user uploads a file the agent's tool must operate on:**

1. The chat trigger gives you a `files[]` array. Split it out and upload each file to
   private storage under a hashed key.
2. Re-merge that branch before the agent runs — it is a synchronization barrier, not
   decoration — and set `executeOnce: true` on the agent so N files do not trigger N agent
   runs.
3. Inject the keys into the agent's system prompt, listing both the original name (human
   context) and the storage key (what the tool needs), with an explicit "use EXACTLY this
   key".
4. The tool receives the key as a string argument and downloads the file itself.

**Outbound — a tool generates a file the agent must return:**

1. The tool sub-workflow generates the binary, uploads it to storage, and returns JSON like
   `{ "ok": true, "key": "...", "url": "https://...", "mimeType": "image/png" }`.
2. The agent embeds the URL in its reply, or passes the key to another tool.

`passthroughBinaryImages: true` on the agent only changes what the **LLM sees** for vision.
It does **not** let tools receive the file, and it is image-only — no PDFs, audio or video.
You still need the upload-and-pass-key pattern for any tool.

Full patterns, hash strategy, storage choices and the long-running-tool variant:
[deep/binary/AGENT_TOOL_BINARY.md](deep/binary/AGENT_TOOL_BINARY.md). Building the tool
itself: [workflow-code.md](workflow-code.md) and [workflow-agents.md](workflow-agents.md).

## The CDN requirement for chat surfaces

When a workflow generates an image and the user wants it shown inside a chat message:

- **Binary on the item is not enough.** The chat client renders images by URL, or pushes
  bytes through the platform's own file-upload API. It never reads `$binary`.
- **The bytes must live somewhere a URL can fetch over HTTPS.** Upload to an object store
  or drive first, then embed the returned URL.
- **n8n has no built-in CDN.** The user provides the storage.

Ask which storage they already use rather than defaulting to S3 — object storage (S3, R2,
GCS, Azure Blob, Backblaze B2, Supabase Storage) and drive-style services (Dropbox, Google
Drive, OneDrive, Box) all work and all change the URL shape. Cloudflare R2 is the
lowest-friction start if they have nothing. For sensitive content use a signed URL with an
expiry rather than a permanently public one. →
[deep/binary/CDN_REQUIREMENT.md](deep/binary/CDN_REQUIREMENT.md)

## Verifying binary survived

Validation will not catch a stripped binary slot — it is a silent failure.

1. `n8n_test_workflow` (or a real run) to produce an execution. Note the side-effect
   warning in [workflow-errors.md](workflow-errors.md) first.
2. Pull that execution and inspect per-node output for the `binary` slot — it shows
   presence and metadata even when the base64 is too large to render.
3. The node where `binary` **last** appears is the node before the strip. That is where the
   pass-through or Merge goes.

## Checklist

- [ ] File contents read from `$binary.<key>`, never `$json`
- [ ] HTTP downloads use `responseFormat: "file"`
- [ ] Code nodes re-attach `binary` on return when the file must continue
- [ ] JSON transforms pass binary through or Merge it back (`combineByPosition`)
- [ ] No attempt to pass binary into or out of an agent tool — keys/URLs through JSON
- [ ] `passthroughBinaryImages` used only for LLM vision, not as a tool channel
- [ ] Chat-surface images uploaded to storage; the URL embedded, not the bytes
- [ ] Storage backend chosen *with* the user; signed URLs for sensitive content
- [ ] Binary presence confirmed by inspecting the execution, not by validation
