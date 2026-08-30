# Orcanium

**Multi-agent runtime** — run multiple agents in one process, each with its own LLM provider, personality, memory, knowledge base, schedule, and messaging channel.

Orcanium is the open-source, locally runnable agent runtime: CLI, terminal UI, REST API with SSE streaming, messaging channels, plugin system, and local web dashboard. It is independent from Orcanium's private services — local and BYOK operation require no account.

<p align="center">
  <a href="https://github.com/orcanium/orcanium">
    <img src="https://img.shields.io/badge/development-active-green" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-black" />
  </a>
  <a href="https://pypi.org/project/orcanium/">
    <img src="https://img.shields.io/badge/pypi-v0.1.0-blue" />
  </a>
</p>

<p align="center">
  <b>Run Multiple Agents, Without the Complexity</b>
</p>

---

Every agent is a named entity with fully isolated state — config, provider, personality, memory, and channel. One process, many distinct assistants, zero shared-state surprises. Conversation flows through an intent-classification → retrieval → attention-scoring → prompt-assembly pipeline, then an LLM → tools → LLM loop backed by 95+ built-in tools and an event bus.

Bring your own keys, run fully local, or mix both. No account, no vendor lock-in.

---

## 🚀 Quick Start

Install Orcanium and start your first agent session:

```bash
uv pip install orcanium
orcanium setup
orcanium run
```

Or one-line install from the repo (installs to `~/.orcanium/`):

```bash
curl -fsSL https://orcanium.com/install.sh | bash
```

---

## ⚡ Core Features

| Feature | Capabilities |
|---|---|
| **Multi-agent** | Create and run multiple agents with per-agent LLM config, personality, memory, knowledge, schedule, and messaging channels — all in one process. |
| **Multi-provider LLM** | OpenAI, Anthropic, Gemini, Ollama, OpenRouter, Groq, Together, Fireworks, DeepSeek, LM Studio. |
| **Conversation pipeline** | Intent classification → context planning → retrieval → attention scoring → prompt assembly → LLM → tools → LLM loop. |
| **95+ built-in tools** | File operations, terminal, web search, browser, code execution, image generation, MCP, and more. |
| **Memory system** | Persistent memory store, working memory, snapshots, and nudge-based review cycles. |
| **Knowledge pipeline** | Document ingestion, chunking, RAG retrieval, and candidate promotion with validation gates. |
| **Event bus** | Category-based pub/sub with async dispatcher, timeline persistence, notification dispatch, SSE streaming. |
| **Messaging channels** | Telegram bot adapters, platform SDK, webhook receivers, slash commands, model picker UI. |
| **Scheduler** | Cron-job agent runs with task execution logging. |
| **Session management** | Per-agent chat sessions with FTS search. |
| **Plugin system** | Lazy-load provider plugins, dashboard extensions, and optional skill packs. |
| **CLI** | Interactive shell, agent management, config, model setup, tool discovery, kanban, health checks. |
| **Terminal UI** | Rich TUI for agent interaction. |
| **Web dashboard** | Admin UI, event viewer, channel config. |

---

## 📖 Documentation

- **[Command Surface](./docs/architecture/command-surface.md)** — full CLI command reference
- **[Release Gate](./scripts/release_gate.py)** — standalone release validation

---

## 🧠 Multi-Agent Architecture

Orcanium runs **multiple agents** in a single process, each with fully isolated state. Every agent is a named entity with its own config, LLM provider, personality, memory, and optional messaging channel.

### Per-agent resources

| Resource | Storage | Scoped by |
|---|---|---|
| System prompt / personality | `~/.orcanium/agents/{name}/SOUL.md` | Agent directory |
| LLM provider + model | `CONFIG.yml` (`model_provider`, `model_name`) | Agent directory |
| Persistent memory | `MEMORY.md` + `USER.md` | Agent directory |
| Skills description | `SKILL.md` | Agent directory |
| Promoted knowledge | `knowledge_entries` table | `agent_name` column |
| Chat sessions | `sessions` table | `agent_name` FK |
| Background review counters | `agent_runtime_state` table | `agent_id` PK |
| Scheduled tasks | `scheduled_tasks` table | `agent_name` FK |
| Messaging channels | `channel_configs` table | `agent_name` in config JSON |

### Agent lifecycle

```bash
# Create two agents with different LLM providers
curl -X POST "/api/v1/agents/create?name=researcher&model_provider=anthropic&model_name=claude-sonnet-5"
curl -X POST "/api/v1/agents/create?name=coder&model_provider=openai&model_name=gpt-4o"

# Each agent gets a per-agent directory
# ~/.orcanium/agents/researcher/SOUL.md
# ~/.orcanium/agents/researcher/CONFIG.yml
# ~/.orcanium/agents/coder/SOUL.md
# ~/.orcanium/agents/coder/MEMORY.md

# Sessions are scoped to an agent
curl -X POST "/api/v1/sessions/create?agent_name=researcher"        # → session for researcher
curl -X POST "/api/v1/sessions/{id}/chat?agent_name=researcher"     # → uses researcher's config
curl -X POST "/api/v1/sessions/create?agent_name=coder"             # → session for coder
```

### Per-agent conversation flow

```
POST /sessions/{id}/chat?agent_name=researcher
         ↓
    AgentRuntime("researcher", db)
      → loads researcher's CONFIG.yml, SOUL.md, MEMORY.md
      → ConversationLoop("researcher")
          → per-agent context retrieval
          → per-agent model provider + model
          → per-agent toolset selection
          → per-agent nudge counters for review
```

Each `ConversationLoop` is instantiated per-agent with that agent's personality, provider, and state. Background reflection cycles (memory review, skill review) use per-agent nudge counters stored in `agent_runtime_state`.

---

## </> Architecture

```
User → REST API / SSE
         ↓
    AgentRuntime.process_message()
         ↓
    ConversationLoop
      → classify() — intent detection (pattern-based)
      → ContextPlanner.plan() — deterministic retrieval plan
      → ContextBuilder.build() — conditional store retrieval
      → AttentionEngine.rank() — weighted relevance scoring
      → PromptBuilder.build() — conditional section assembly
      → run_conversation() — LLM → tools → LLM loop
         ↓
    Response + Event Bus emissions
         ↓
    TimelineStore + NotificationConsumer + ChannelConsumer
```

---

## ⌨️ CLI

```
orcanium channel     — Start/stop messaging channel adapters (Telegram, etc.)
orcanium doctor      — System health diagnostics
orcanium update      — Self-update
orcanium setup       — Initial configuration
orcanium run         — Interactive agent session
orcanium dashboard   — Launch local web admin UI
```

### Configuration files

Two top-level config files live in `~/.orcanium/`; they are distinct, not duplicates:

| File | Consumer | Contents |
|---|---|---|
| `config.yaml` | CLI / agent / gateway | Full agent & runtime settings (`_config_version`), written by `orcanium setup` |
| `dashboard.yaml` | Web dashboard / REST API | Thin UI settings (`model_providers`, theme, telemetry) |

(The dashboard file was previously `config.yml`; it was renamed to `dashboard.yaml` to avoid confusion with `config.yaml`. An existing `config.yml` is migrated automatically on the dashboard's next start.)

---

## 🔌 API

Base URL: `http://localhost:8000/api/v1`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions/{id}/chat` | Send message (SSE streaming, per-agent) |
| GET | `/sessions` | List sessions (filterable by agent) |
| POST | `/sessions/create` | Create a new session for an agent |
| GET | `/sessions/{id}/messages` | Get conversation history |
| GET | `/agents` | List all agents |
| POST | `/agents/create` | Create a new agent |
| GET | `/agents/{name}/config` | Get agent config |
| PUT | `/agents/{name}/config` | Update agent config |
| GET | `/agents/{name}/files` | Get agent SOUL/MEMORY/SKILL/USER files |
| PUT | `/agents/{name}/files` | Update agent markdown files |
| POST | `/agents/{name}/start` | Start an agent |
| POST | `/agents/{name}/stop` | Stop an agent |
| DELETE | `/agents/{name}` | Delete an agent completely |
| POST | `/agents/{name}/switch` | Switch active runtime context |
| GET | `/channels` | List messaging channel configs |
| POST | `/channels/register` | Register a channel (Telegram, etc.) |
| POST | `/channels/{id}/toggle` | Enable/disable a channel |
| DELETE | `/channels/{id}` | Delete a channel |
| GET | `/events/history` | Paginated event history |
| GET | `/events/stream` | SSE event stream |
| GET | `/models` | List available LLM providers |
| GET | `/tasks` | List scheduled tasks (per-agent) |
| POST | `/tasks/create` | Create a scheduled task for an agent |
| GET | `/tasks/{id}/logs` | Get task execution logs |

Full OpenAPI docs at `/docs`.

---

## 🧪 Maintainer checks

The standalone release gate validates package syntax, core imports, and the public `channel`, `doctor`, and `update` command surfaces:

```bash
python scripts/release_gate.py
```

---

## 📄 License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <b>Run your own multi-agent fleet</b>
</p>
