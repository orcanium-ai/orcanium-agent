import logging
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import API routers
from orcanium.app.api import (
    agents,
    auth,
    channels,
    config_api,
    events,
    keys,
    knowledge,
    logs,
    memory,
    models,
    sessions,
    skills,
    system,
    tasks,
    tools,
)
from orcanium.app.core.auth import load_persisted_tokens

# Configure logging — stdout + rotating file
from orcanium.app.core.config import LOGS_DIR, ensure_orcanium_dirs, settings
from orcanium.app.core.db import engine, init_db
from orcanium.app.core.migrations import run_pending_migrations
from orcanium.app.domains.agent.health import agent_health
from orcanium.app.domains.capability.consumers.consumer_registry import (
    consumer_registry,
)
from orcanium.app.domains.capability.consumers.channel_consumer import (
    bind_channel,
    handle_event as channel_handle_event,
)
from orcanium.app.domains.capability.consumers.notification_consumer import (
    handle_event as notification_handle_event,
)
from orcanium.app.domains.capability.consumers.timeline_consumer import (
    handle_event as timeline_handle_event,
)
from orcanium.app.domains.capability.events import event_bus
from orcanium.app.domains.channel.manager import channel_runner
from orcanium.app.domains.session.search import (
    ensure_fts_tables,
    index_existing_messages,
)
from orcanium.app.scheduler.scheduler import scheduler_service
from orcanium.cli.banner import ORCANIUM_LOGO
from rich.console import Console

LOGS_DIR.mkdir(parents=True, exist_ok=True)

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.DEBUG)
logging.getLogger("orcanium.app.core.trace").setLevel(logging.DEBUG)

# Console handler (stdout)
_console = logging.StreamHandler()
_console.setLevel(logging.INFO)
_console.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
)
_root_logger.addHandler(_console)

# File handler (rotating, 5 MB per file, 3 backups)
_file_handler = RotatingFileHandler(
    LOGS_DIR / "orcanium.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setLevel(logging.INFO)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
)
_root_logger.addHandler(_file_handler)

logger = logging.getLogger("orcanium")

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup & Shutdown hooks
@app.on_event("startup")
def startup_event():
    logger.info("Initializing Orcanium OS state directories...")
    ensure_orcanium_dirs()

    logger.info("Initializing Core State SQLite Database...")
    init_db()
    run_pending_migrations(engine)
    ensure_fts_tables(engine)
    index_existing_messages(engine)
    agent_health.start_heartbeat()
    load_persisted_tokens(engine)

    # Initialize per-agent runtime state for all existing agents
    from orcanium.app.core.db import SessionLocal
    from orcanium.app.domains.agent.runtime_state import agent_runtime_state

    _init_db = SessionLocal()
    try:
        agent_runtime_state.init_for_all_agents(_init_db)
    finally:
        _init_db.close()

    logger.info("Starting Event Bus Consumer Registry...")
    consumer_registry.register(timeline_handle_event)
    consumer_registry.register(channel_handle_event)
    consumer_registry.register(notification_handle_event)
    from orcanium.app.domains.capability.consumers.cross_talk_delivery import handle_event as cross_talk_handle_event
    consumer_registry.register(cross_talk_handle_event)
    consumer_registry.start()

    logger.info("Starting Event Bus Async Dispatcher...")
    event_bus.start_async_dispatcher(capacity=1000)
    if not event_bus.is_async:
        raise RuntimeError(
            "EventBus async dispatcher failed to start — "
            "runtime will fall back to synchroorcanium delivery, "
            "which blocks producers. Aborting startup."
        )

    # ── Startup Verification (Phase 14) ─────────────────────────
    if not event_bus.is_async:
        raise RuntimeError(
            "EventBus async dispatcher is not running after start(). "
            "Runtime would fall back to synchroorcanium delivery."
        )
    if consumer_registry.consumer_count < 1:
        raise RuntimeError(
            f"No consumers registered (count={consumer_registry.consumer_count}). "
            "Timeline, Channel, and Notification consumers are required."
        )

    logger.info(
        f"Event Bus Runtime is operational "
        f"(async dispatcher active, {consumer_registry.consumer_count} consumers)."
    )

    logger.info("Starting Background Job Scheduler...")
    scheduler_service.start()

    logger.info("Starting Active Channels...")
    try:
        channel_runner.start_all()
        bind_channel(channel_runner)
    except Exception as e:
        logger.error(f"Failed starting channels: {e}")

    _console = Console()
    _console.print(ORCANIUM_LOGO)
    logger.info("Orcanium Python Backend initialized successfully!")


@app.on_event("shutdown")
def shutdown_event():
    logger.info("Stopping Event Bus Async Dispatcher...")
    event_bus.stop_async_dispatcher(timeout=5.0)

    logger.info("Shutting down Background Job Scheduler...")
    scheduler_service.stop()

    logger.info("Stopping Channels...")
    channel_runner.stop_all()

    logger.info("Orcanium Backend shutdown successfully.")


# Route registrations
app.include_router(
    agents.router, prefix=f"{settings.API_V1_STR}/agents", tags=["Agents"]
)
app.include_router(
    sessions.router, prefix=f"{settings.API_V1_STR}/sessions", tags=["Sessions"]
)
app.include_router(
    knowledge.router, prefix=f"{settings.API_V1_STR}/knowledge", tags=["Knowledge"]
)
app.include_router(
    models.router, prefix=f"{settings.API_V1_STR}/models", tags=["Model Providers"]
)
app.include_router(
    channels.router, prefix=f"{settings.API_V1_STR}/channels", tags=["Channels"]
)
app.include_router(
    tasks.router, prefix=f"{settings.API_V1_STR}/tasks", tags=["Scheduled Tasks"]
)
app.include_router(
    keys.router, prefix=f"{settings.API_V1_STR}/keys", tags=["Credentials & Keys"]
)
app.include_router(
    auth.router, prefix=f"{settings.API_V1_STR}", tags=["Authentication"]
)
app.include_router(
    system.router, prefix=f"{settings.API_V1_STR}/system", tags=["System"]
)
app.include_router(logs.router, prefix=f"{settings.API_V1_STR}/logs", tags=["Logs"])
app.include_router(
    tools.router, prefix=f"{settings.API_V1_STR}/tools", tags=["Tools"]
)
app.include_router(
    skills.router, prefix=f"{settings.API_V1_STR}/skills", tags=["Skills"]
)
app.include_router(
    memory.router, prefix=f"{settings.API_V1_STR}/memory", tags=["Memory"]
)
app.include_router(
    config_api.router,
    prefix=f"{settings.API_V1_STR}/config",
    tags=["Config"],
)
app.include_router(
    events.router,
    prefix=f"{settings.API_V1_STR}",
    tags=["Events"],
)
@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Orcanium V1 Agent Operating System Backend",
        "docs_url": "/docs",
    }
