# Drift: trust the live tool over this pack

The community **n8n-mcp** server and n8n itself move faster than any model's training
cutoff — and faster than these references. Tool names, parameters, node `typeVersion`s and
default behaviors change between releases.

## The rule

When you spot drift, the **live tool wins**. Then say so.

Drift looks like:

- a tool a reference names does not exist in the current tool list;
- a parameter shape that does not match what `get_node` returns;
- a `typeVersion` a reference mentions that is behind what `get_node` reports;
- behavior that differs from what a reference describes.

In every case: follow the tool, tell the user what disagreed, and suggest updating both
the pack and the n8n instance.

## Why this matters more than it sounds

A remembered or stale parameter name does not fail loudly. n8n accepts unknown parameter
keys as plain strings, `validate_workflow` reports the JSON as well-formed, and the
parameter simply does nothing at runtime. The workflow ships, looks correct in the editor,
and quietly drops data.

That is why "configure from the live schema, never from memory" is a non-negotiable rather
than a preference — and why a reference that contradicts `get_node` should be treated as
out of date rather than authoritative.

## Reporting drift

Do not silently work around it. A one-line note is enough:

> `get_node` reports `httpRequest` at `typeVersion` 4.4, but this pack's reference says
> 4.2. I used 4.4. The pack is behind — worth updating.

That gives the user something actionable and stops the same surprise recurring.
