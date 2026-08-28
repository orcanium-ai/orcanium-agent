import os
import sys

import click
import uvicorn
from orcanium.app.agent.agent_manager import AgentManager
from orcanium.app.core.config import (
    AGENTS_DIR,
    ORCANIUM_DIR,
    ensure_orcanium_dirs,
)
from orcanium.app.core.db import (
    AgentState,
    ChannelConfig,
    KnowledgeDocument,
    SessionLocal,
    init_db,
)


@click.group()
def cli():
    """Orcanium V1: A Lightweight Agent Operating System CLI."""
    pass


@cli.command()
def setup():
    """Initializes the ~/.orcanium folders, database, and seeds a personal agent."""
    click.echo("Initializing Orcanium configuration and directories...")
    ensure_orcanium_dirs()

    click.echo("Initializing core SQLite state database...")
    init_db()

    # Check if we should seed a default agent
    db = SessionLocal()
    try:
        AgentManager.sync_all_agents(db)
        existing = (
            db.query(AgentState).filter(AgentState.name == "PersonalAgent").first()
        )
        if not existing:
            click.echo("Seeding default agent: 'PersonalAgent'...")
            soul_content = (
                "# PersonalAgent Soul\n"
                "You are PersonalAgent, a helpful, intelligent assistant running on the Orcanium Lightweight Agent Operating System.\n"
                "You assist the user with scheduling tasks, looking up documents, and writing scripts.\n"
            )
            skills_content = (
                "# PersonalAgent Skills\n"
                "You possess advanced knowledge processing capabilities and local file utility tools.\n"
            )
            memory_content = (
                "# PersonalAgent Memory\n- User created PersonalAgent on Orcanium.\n"
            )
            user_content = "# PersonalAgent User\nFirst-time Orcanium user. Preferences and profile being established.\n"
            AgentManager.create_agent(
                db=db,
                name="PersonalAgent",
                soul=soul_content,
                skills=skills_content,
                memory=memory_content,
                user=user_content,
            )
            click.echo("Default agent 'PersonalAgent' successfully seeded.")
        else:
            click.echo("'PersonalAgent' is already configured.")
    finally:
        db.close()

    click.echo(
        f"Orcanium setup completed successfully! Storage location: {ORCANIUM_DIR}"
    )


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host address to bind to.")
@click.option("--port", default=8000, help="Port to run the backend on.")
def dashboard(host, port):
    """Starts the backend FastAPI web-server."""
    click.echo(f"Starting Orcanium V1 Backend Web Server on {host}:{port}...")
    ensure_orcanium_dirs()
    init_db()
    uvicorn.run("orcanium.app.main:app", host=host, port=port, reload=True)


@cli.group(name="agent")
def agent_group():
    """Manage agents on Orcanium OS."""
    pass


@agent_group.command(name="list")
def list_agents():
    """Lists all configured agents."""
    db = SessionLocal()
    try:
        AgentManager.sync_all_agents(db)
        agents = db.query(AgentState).all()
        if not agents:
            click.echo(
                "No agents configured yet. Use 'orcanium agent create' or run 'orcanium setup'."
            )
            return

        click.echo(
            f"{'Agent Name':<20} | {'Status':<10} | {'Provider':<12} | {'Model':<15}"
        )
        click.echo("-" * 65)
        for agent in agents:
            click.echo(
                f"{agent.name:<20} | {agent.status:<10} | {agent.model_provider or 'N/A':<12} | {agent.model_name or 'N/A':<15}"
            )
    finally:
        db.close()


@agent_group.command(name="create")
@click.argument("name")
@click.option(
    "--provider",
    default="openai",
    help="Model provider (openai, anthropic, gemini, ollama)",
)
@click.option(
    "--model",
    default="gpt-4-turbo",
    help="Model name (gpt-4-turbo, claude-3-haiku, etc.)",
)
def create_agent(name, provider, model):
    """Creates a new agent with standard templates."""
    db = SessionLocal()
    try:
        AgentManager.sync_all_agents(db)
        if db.query(AgentState).filter(AgentState.name == name).first():
            click.echo(f"Error: Agent '{name}' already exists.")
            return

        config = {"model_provider": provider, "model_name": model}
        AgentManager.create_agent(db=db, name=name, config=config)
        click.echo(
            f"Agent '{name}' created successfully with provider={provider} and model={model}!"
        )
    finally:
        db.close()


@agent_group.command(name="start")
@click.argument("name")
def start_agent(name):
    """Starts/Enables an agent."""
    db = SessionLocal()
    try:
        agent = db.query(AgentState).filter(AgentState.name == name).first()
        if not agent:
            click.echo(f"Error: Agent '{name}' not found.")
            return
        agent.status = "running"
        db.commit()
        click.echo(f"Agent '{name}' has been successfully started!")
    finally:
        db.close()


@agent_group.command(name="stop")
@click.argument("name")
def stop_agent(name):
    """Stops/Disables an agent."""
    db = SessionLocal()
    try:
        agent = db.query(AgentState).filter(AgentState.name == name).first()
        if not agent:
            click.echo(f"Error: Agent '{name}' not found.")
            return
        agent.status = "stopped"
        db.commit()
        click.echo(f"Agent '{name}' has been stopped.")
    finally:
        db.close()


@cli.group(name="knowledge")
def knowledge_group():
    """Manage indexed knowledge base / documents."""
    pass


@knowledge_group.command(name="list")
def list_knowledge():
    """Lists indexed knowledge documents."""
    db = SessionLocal()
    try:
        docs = db.query(KnowledgeDocument).all()
        if not docs:
            click.echo("No documents ingested yet.")
            return

        click.echo(
            f"{'Doc ID':<36} | {'Name':<25} | {'Type':<10} | {'Status':<10} | {'Chunks':<6}"
        )
        click.echo("-" * 95)
        for doc in docs:
            click.echo(
                f"{doc.id:<36} | {doc.name[:25]:<25} | {doc.type:<10} | {doc.status:<10} | {doc.chunk_count:<6}"
            )
    finally:
        db.close()


@cli.group(name="gateway")
def gateway_group():
    """Manage Telegram and interface gateway bot tokens."""
    pass


@gateway_group.command(name="telegram")
@click.option("--agent", required=True, help="Agent name to link the bot with.")
@click.option("--token", required=True, help="Telegram Bot HTTP API Token.")
@click.option("--enable/--disable", default=True, help="Whether to enable bot on save.")
def config_telegram_gateway(agent, token, enable):
    """Configures and registers a Telegram gateway channel."""
    db = SessionLocal()
    try:
        channel_id = f"telegram_{agent}"
        channel = (
            db.query(ChannelConfig).filter(ChannelConfig.id == channel_id).first()
        )
        config = {"token": token, "agent_name": agent}

        if not channel:
            channel = ChannelConfig(id=channel_id, platform="telegram", enabled=enable)
            channel.set_config(config)
            db.add(channel)
        else:
            channel.enabled = enable
            channel.set_config(config)

        db.commit()
        click.echo(
            f"Telegram Bot Gateway successfully configured for Agent '{agent}' (Enabled={enable})."
        )
    finally:
        db.close()


if __name__ == "__main__":
    cli()
