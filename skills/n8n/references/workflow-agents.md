# Route: AI agents

Owns the LangChain family: the AI Agent node and everything that wires into it.

For *where* an agent sits in a workflow's architecture, see
[deep/design/ai_agent_workflow.md](deep/design/ai_agent_workflow.md). This route is one
level down: how to build it well.

**Node-type formats.** In workflow JSON the LangChain nodes use the long
`@n8n/n8n-nodes-langchain.*` form. For `get_node` / `validate_node` use the **short** form
(`nodes-langchain.agent`). See [shared/mcp-tools.md](shared/mcp-tools.md).

## Pick the right node first

Reaching for an Agent when the task is one-shot classification or extraction is the most
common over-build.

| You need to… | Use | Why |
|---|---|---|
| Call tools, reason over multiple turns, hold memory | **AI Agent** (`.agent`) | The full loop |
| One-shot text in → text out, no tools | **Basic LLM Chain** (`.chainLlm`) | No agent loop, easier to debug |
| Route natural language to one of **N branches** | **Text Classifier** (`.textClassifier`) | One node, N output handles — not Agent + Switch |
| Pull structured fields out of free text | **Information Extractor** (`.informationExtractor`) | Purpose-built, schema-driven |
| 3-way positive/neutral/negative split | **Sentiment Analysis** (`.sentimentAnalysis`) | Built-in branch outputs |
| Condense a long document | **Summarization Chain** (`.chainSummarization`) | Map-reduce built in |
| Generate image / audio / video | **the provider's native single-call node** | NEVER wrap media generation in an Agent — see the binary boundary below |

**Text Classifier detail (the Agent + Switch antipattern):** every category needs both a
**name and a description**. The model routes against the *description*, not the name — a
category with no description gets picked by coin-flip. Set
`options.enableAutoFixing: true` for robustness on edge inputs.

Chat-model nodes (`.lmChatOpenAi`, `.lmChatAnthropic`, `.lmChatOpenRouter`, …) are
**sub-nodes**; they do not run standalone.

## The sub-node pattern

The Agent has a main input (the prompt) and up to four sub-node slots, each wired by its
own `ai_*` connection type:

| Slot | Connection type | Required? |
|---|---|---|
| **model** | `ai_languageModel` | yes |
| **memory** | `ai_memory` | optional |
| **tools** | `ai_tool` | optional, but the point of an agent |
| **outputParser** | `ai_outputParser` | optional |

A sub-node connects **from itself to** the agent; in workflow JSON the connection lives on
the sub-node:

```json
"Main LLM":       {"ai_languageModel": [[{"node": "AI Agent", "type": "ai_languageModel", "index": 0}]]},
"Simple Memory":  {"ai_memory":        [[{"node": "AI Agent", "type": "ai_memory",        "index": 0}]]},
"Search customer DB": {"ai_tool":      [[{"node": "AI Agent", "type": "ai_tool",          "index": 0}]]}
```

Multiple tools all connect into the **same** `ai_tool` index 0 — they stack, they do not
fan into separate indices. With `n8n_update_partial_workflow`, wire each with an
`addConnection` op using `sourceOutput: "ai_tool"`.

The agent puts its final answer in **`$json.output`** — not `.text`, not `.response`.

## Two non-negotiables

1. **Tool names and descriptions ARE part of the prompt.** The model picks a tool by
   reading its name and description and nothing else. A tool named `tool1` with an empty
   description is invisible: the model skips it, mis-selects it, or hallucinates
   parameters. There is usually **no error** — just an agent that "won't use my tool".
   Treat both like API design. → [deep/agents/TOOLS.md](deep/agents/TOOLS.md)
2. **Structured output must parse *and* autoFix.** An `outputParserStructured` with
   `autoFix: true` and a **coding-capable fixer model** is the production pattern. Without
   autoFix, one malformed JSON response halts the whole workflow. →
   [deep/agents/STRUCTURED_OUTPUT.md](deep/agents/STRUCTURED_OUTPUT.md)

## Strong defaults

- **Per-tool usage goes in the tool description, not the system prompt.** It then travels
  with the tool across agents and keeps the prompt focused.
- **Sub-workflow tools (`.toolWorkflow`) for anything multi-step.** Default here when in
  doubt — see [workflow-design.md](workflow-design.md).
- **Wrap tools with user-visible side effects in human review.**
- **Raise `maxIterations`.** The default tool-call cap is **low** (single digits on most
  versions) — fine for a one-tool agent, far too low for a multi-tool agent. It surfaces
  as "max iterations reached" or empty output. Set `options.maxIterations` to 15 for a
  focused sub-agent, 50–200 for a broad orchestrator.
- **Put the current date in the system prompt** via `{{ $now }}`. A hardcoded date is
  stale immediately.

## The four tool types

Pick the lightest option that covers the job.

| Tool type | Node | Use when |
|---|---|---|
| **Native tool node** | `slackTool`, `gmailTool`, `toolCalculator`, … | The capability maps to one node + one operation. Lowest overhead |
| **Sub-workflow as tool** | `.toolWorkflow` | More than one node, reusable logic, independent testability. **Default when in doubt** |
| **HTTP Request Tool** | `.toolHttpRequest` | A single external API the agent orchestrates directly |
| **MCP Client Tool** | `.mcpClientTool` | A maintained MCP server already covers it |

There is also a **Custom Code Tool** (`.toolCode`) for pure inline computation, but its
runtime contract (string in / string out, no `$fromAI`, no `$helpers`) is owned by
[workflow-code.md](workflow-code.md) — read that before writing one. Rule of thumb: if you
find yourself reaching for `$fromAI()` inside the code, you want `.toolWorkflow` instead.

### `$fromAI()`: how the agent fills tool parameters

```
={{ $fromAI('paramName', 'what to put here — be specific: format, range, example', 'string') }}
```

- **paramName** — the name the model uses internally; be consistent.
- **description** — tells the model what value to produce. **It is part of the prompt** —
  write it like JSDoc.
- **type** *(optional)* — `'string'` (default), `'number'`, `'boolean'`, `'json'`. A
  wrong-typed value fails the call.
- **defaultValue** *(optional)* — used when the model omits it.

`$fromAI()` carries **JSON only** — it cannot carry binary. And not every parameter has to
be `$fromAI`: plumb identity, authority limits and correlation IDs (`userId`, refund caps,
`sessionId`) deterministically from workflow context, so the agent cannot get them wrong or
even see them. → [deep/agents/TOOLS.md](deep/agents/TOOLS.md)

## System prompt vs tool description

| Belongs in the **system prompt** | Belongs in the **tool's description** |
|---|---|
| Persona, role, voice | What this specific tool does |
| Global output/format rules | When to use it vs other tools |
| Refusal / safety behavior | What each parameter means and its shape |
| Display protocols | Examples of good vs bad invocations |
| Universal context (current date, user role) | Tool-specific gotchas (rate limits, edge cases) |
| Inter-tool flow | Tool-specific input transformations |

A well-described tool works in **any** agent that drops it in, tool details only load when
the model considers that tool, and you update one description instead of a paragraph buried
in a 5000-token prompt. → [deep/agents/SYSTEM_PROMPT.md](deep/agents/SYSTEM_PROMPT.md)

## Structured output

Add an `outputParserStructured` sub-node (wired `ai_outputParser`) when downstream needs
strict JSON. Two rules:

1. **Use `schemaType: 'manual'` with a real JSON Schema, not `jsonSchemaExample`.** An
   example cannot express required-vs-optional, enums, numeric ranges or array
   constraints. Reach for `fromJson` plus an example only for throwaway shapes.
2. **`autoFix: true` with a coding-capable fixer model.** Wire a *second* model into the
   parser's `ai_languageModel` slot. Reconciling broken JSON against a schema is a coding
   task; a weak fixer produces another malformed retry and burns tokens.

→ [deep/agents/STRUCTURED_OUTPUT.md](deep/agents/STRUCTURED_OUTPUT.md)

## Memory

Memory is a sub-node (`ai_memory`). Without it every call is stateless — correct for
one-shot tasks. With it the agent holds a conversation, keyed by whatever expression you
bind to `sessionKey`.

- **`memoryBufferWindow`** — last N exchanges per key, persisted across executions. The
  default for chat. **`contextWindowLength` defaults to 5, which is very low** — 50 is a
  saner start. Messages past the window are gone entirely.
- **`memoryPostgresChat` / `memoryRedisChat`** — only when memory must be read *outside*
  the agent. Not needed just to survive restarts; BufferWindow already does that.

**Plumb a stable key from the trigger to memory.** Chat triggers fill `sessionId`
automatically; elsewhere derive one (Slack `thread_ts`, a webhook conversation ID). Never
hardcode `sessionId: 'default'`, and never put `sessionId` behind `$fromAI` — the model
will fabricate a UUID. → [deep/agents/MEMORY.md](deep/agents/MEMORY.md)

## Binary and the agent boundary

The seam that trips people up:

- **The model CAN see uploaded images** (vision) via
  `options.passthroughBinaryImages: true` on the agent.
- **Tools CANNOT receive binary.** `$fromAI()` is JSON-only — no base64, no bytes.
- **The agent's output is text-shaped.** When a model returns image/audio/video bytes the
  Agent does not surface them at all; there is nothing to recover downstream.

**Workaround:** pre-stage uploads to storage before the agent runs, inject the storage keys
into the system prompt, and let tools accept the key as a string parameter and re-fetch
internally. For one-shot media generation, skip the agent and call the provider's native
node directly.

The binary mechanics are owned by [workflow-binary.md](workflow-binary.md).

## Human review: gate destructive tools

When a tool's effect needs human sign-off (sends, payments, refunds, account changes), wrap
it with a review tool node — `slackHitlTool`, `discordHitlTool`, `telegramHitlTool`,
`gmailHitlTool`. The review node sits **between** the wrapped tool and the agent on the
`ai_tool` connection: wrapped tool → review node → Agent.

Whether sign-off is needed is a product and policy call — **surface the question to the
user**, recommend based on blast radius, and let them decide.

**The critical rule: show the actual parameters the wrapped tool will receive.** Use the
literal `{{ $tool.parameters.<name> }}` in the approval message, never a `$fromAI()`
paraphrase — otherwise the human approves text the model made up, not the call about to
fire. → [deep/agents/HUMAN_REVIEW.md](deep/agents/HUMAN_REVIEW.md)

## Chat agents (Slack, Discord, Teams, Telegram)

**The one non-negotiable, regardless of complexity:** any chat-triggered workflow that
posts a reply MUST **filter out the bot's own user ID**, or its own replies re-trigger it
in an infinite loop that burns runs and tokens. Prefer trigger-level filtering where
available (Slack Trigger's `options.userIds` is an **exclusion** list — put the bot ID
there); otherwise filter `$json.user !== '<BOT_USER_ID>'` in the first node after the
trigger. → [deep/agents/CHAT_AGENT_PATTERNS.md](deep/agents/CHAT_AGENT_PATTERNS.md)

## Deeper references

| Read when | File |
|---|---|
| Designing tools, `$fromAI` anatomy | [deep/agents/TOOLS.md](deep/agents/TOOLS.md) |
| Writing the system prompt | [deep/agents/SYSTEM_PROMPT.md](deep/agents/SYSTEM_PROMPT.md) |
| Strict JSON output, parse failures | [deep/agents/STRUCTURED_OUTPUT.md](deep/agents/STRUCTURED_OUTPUT.md) |
| Conversation state, session keys | [deep/agents/MEMORY.md](deep/agents/MEMORY.md) |
| Retrieval / vector stores | [deep/agents/RAG.md](deep/agents/RAG.md) |
| Gating destructive tools | [deep/agents/HUMAN_REVIEW.md](deep/agents/HUMAN_REVIEW.md) |
| Wiring a sub-workflow as a tool | [deep/agents/SUBWORKFLOW_AS_TOOL.md](deep/agents/SUBWORKFLOW_AS_TOOL.md) |
| Slack/Discord/Teams/Telegram topologies | [deep/agents/CHAT_AGENT_PATTERNS.md](deep/agents/CHAT_AGENT_PATTERNS.md) |
| A complete worked node snippet | [deep/agents/EXAMPLES.md](deep/agents/EXAMPLES.md) |
