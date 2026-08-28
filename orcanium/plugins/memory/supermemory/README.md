# Supermemory Memory Provider

Semantic long-term memory with profile recall, semantic search, explicit memory tools, and full-session conversation ingest (one ingest per session) for richer profiles.

## Requirements

- `pip install supermemory`
- Supermemory API key from [supermemory.ai](https://supermemory.ai)

## Setup

```bash
orcanium memory setup    # select "supermemory"
```

Or manually:

```bash
orcanium config set memory.provider supermemory
echo 'SUPERMEMORY_API_KEY=***' >> ~/.orcanium/.env
```

## Config

Config file: `$ORCANIUM_HOME/supermemory.json`

| Key | Default | Description |
|-----|---------|-------------|
| `container_tag` | `orcanium` | Container tag used for search and writes. Supports `{identity}` template for profile-scoped tags (e.g. `orcanium-{identity}` → `orcanium-coder`). |
| `auto_recall` | `true` | Inject relevant memory context before turns |
| `auto_capture` | `true` | Store cleaned user-assistant turns after each response |
| `max_recall_results` | `10` | Max recalled items to format into context |
| `profile_frequency` | `50` | Include profile facts on first turn and every N turns |
| `capture_mode` | `all` | Skip tiny or trivial turns by default |
| `search_mode` | `hybrid` | Search mode: `hybrid` (profile + memories), `memories` (memories only), `documents` (documents only) |
| `entity_context` | built-in default | Extraction guidance passed to Supermemory |
| `api_timeout` | `5.0` | Timeout for SDK and ingest requests |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SUPERMEMORY_API_KEY` | API key (required) |
| `SUPERMEMORY_CONTAINER_TAG` | Override container tag (takes priority over config file) |

## Tools

Kebab-case names are registered for the agent; snake_case aliases remain supported.

| Tool | Alias | Description |
|------|-------|-------------|
| `supermemory-save` | `supermemory_store` | Store an explicit memory |
| `supermemory-search` | `supermemory_search` | Search memories by semantic similarity |
| `supermemory-forget` | `supermemory_forget` | Forget a memory by ID or best-match query |
| `supermemory-profile` | `supermemory_profile` | Retrieve persistent profile and recent context |

## Source attribution

All Supermemory API calls send `x-sm-source: orcanium`, and document writes stamp
`metadata.sm_source: orcanium`. This is a **functional routing key, not telemetry**:
it groups Orcanium-written memories into a dedicated "Orcanium" Space in the
Supermemory app, so you can filter, browse, and bulk-manage them per source agent
(alongside Codex, Claude Code, etc.) from the Supermemory UI.

## Behavior

When enabled, Orcanium can:

- prefetch relevant memory context before each turn
- buffer the full conversation and ingest it as **one session** at session end (or on `/reset`, branch, compression, or shutdown)
- ingest the full session to the conversations endpoint for richer profile/graph updates
- expose explicit tools for search, store, forget, and profile access

The session is written once via the conversations endpoint, which drives Supermemory's entity extraction and profile building while keeping a clean, retrievable full transcript.

## Profile-Scoped Containers

Use `{identity}` in the `container_tag` to scope memories per Orcanium profile:

```json
{
  "container_tag": "orcanium-{identity}"
}
```

For a profile named `coder`, this resolves to `orcanium-coder`. The default profile resolves to `orcanium-default`. Without `{identity}`, all profiles share the same container.

## Multi-Container Mode

For advanced setups (e.g. OpenClaw-style multi-workspace), you can enable custom container tags so the agent can read/write across multiple named containers:

```json
{
  "container_tag": "orcanium",
  "enable_custom_container_tags": true,
  "custom_containers": ["project-alpha", "project-beta", "shared-knowledge"],
  "custom_container_instructions": "Use project-alpha for coding tasks, project-beta for research, and shared-knowledge for team-wide facts."
}
```

When enabled:
- `supermemory-search`, `supermemory-save`, `supermemory-forget`, and `supermemory-profile` accept an optional `container_tag` parameter
- The tag must be in the whitelist: primary container + `custom_containers`
- Automatic operations (turn sync, prefetch, memory write mirroring, session ingest) always use the **primary** container only
- Custom container instructions are injected into the system prompt

## Support

- [Supermemory Discord](https://supermemory.link/discord)
- [support@supermemory.com](mailto:support@supermemory.com)
- [supermemory.ai](https://supermemory.ai)
