import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Storage paths
ORCANIUM_DIR = Path(
    os.environ.get("ORCANIUM_DIR")
    or os.environ.get("ORCANIUM_HOME")
    or Path.home() / ".orcanium"
).expanduser()
ENV_FILE_PATH = ORCANIUM_DIR / ".env"

# Load local .env if it exists before initializing settings
if ENV_FILE_PATH.exists():
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)

AGENTS_DIR = ORCANIUM_DIR / "agents"
KNOWLEDGE_DIR = ORCANIUM_DIR / "knowledge"
LOGS_DIR = ORCANIUM_DIR / "logs"
DB_PATH = ORCANIUM_DIR / "state.db"
CONFIG_PATH = ORCANIUM_DIR / "config.yml"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Orcanium Backend"
    API_V1_STR: str = "/api/v1"
    ORCANIUM_DIR_PATH: str = str(ORCANIUM_DIR)

    # Security
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", "orcanium_super_secret_dev_key_123987"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Model APIs
    OPENAI_API_KEY: Optional[str] = os.environ.get("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.environ.get("GOOGLE_API_KEY")
    OPENROUTER_API_KEY: Optional[str] = os.environ.get("OPENROUTER_API_KEY")
    OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    DEEPSEEK_API_KEY: Optional[str] = os.environ.get("DEEPSEEK_API_KEY")
    GROQ_API_KEY: Optional[str] = os.environ.get("GROQ_API_KEY")
    TOGETHER_API_KEY: Optional[str] = os.environ.get("TOGETHER_API_KEY")
    FIREWORKS_API_KEY: Optional[str] = os.environ.get("FIREWORKS_API_KEY")
    LMSTUDIO_BASE_URL: str = os.environ.get(
        "LMSTUDIO_BASE_URL", "http://localhost:1234/v1"
    )

    # App Config
    TELEGRAM_BOT_TOKEN: Optional[str] = os.environ.get("TELEGRAM_BOT_TOKEN")

    model_config = {
        "env_file": str(ENV_FILE_PATH) if ENV_FILE_PATH.exists() else ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()


def reload_settings():
    """Reload Settings dynamically from ~/.orcanium/.env"""
    global settings
    if ENV_FILE_PATH.exists():
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)
    settings = Settings()


def load_env_keys() -> Dict[str, str]:
    """Parse and load key-value pairs from ~/.orcanium/.env"""
    if not ENV_FILE_PATH.exists():
        return {}
    keys = {}
    with open(ENV_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            # Remove optional quotes
            if (v.startswith('"') and v.endswith('"')) or (
                v.startswith("'") and v.endswith("'")
            ):
                v = v[1:-1]
            keys[k.strip()] = v.strip()
    return keys


def save_env_keys(keys: Dict[str, str]):
    """Save key-value pairs to ~/.orcanium/.env and update runtime environment"""
    ensure_orcanium_dirs()
    current_keys = load_env_keys()
    current_keys.update(keys)

    with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
        for k, v in current_keys.items():
            f.write(f"{k}={v}\n")
            os.environ[k] = v

    reload_settings()


def ensure_orcanium_dirs():
    """Ensure all default directory structures exist in user home or custom path."""
    ORCANIUM_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize default config if not present
    if not CONFIG_PATH.exists():
        default_config = {
            "version": "1.0",
            "settings": {
                "theme": "dark",
                "telemetry": False,
                "auto_backup": True,
            },
            "model_providers": {
                "openai": {"api_key": settings.OPENAI_API_KEY or ""},
                "anthropic": {"api_key": settings.ANTHROPIC_API_KEY or ""},
                "gemini": {"api_key": settings.GEMINI_API_KEY or ""},
                "google": {"api_key": settings.GOOGLE_API_KEY or ""},
                "openrouter": {"api_key": settings.OPENROUTER_API_KEY or ""},
                "ollama": {"base_url": settings.OLLAMA_BASE_URL},
            },
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False)


def get_config_file_path() -> str:
    """Return the absolute path to the config.yml file."""
    ensure_orcanium_dirs()
    return str(CONFIG_PATH)


def load_system_config() -> Dict[str, Any]:
    ensure_orcanium_dirs()
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            try:
                return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to parse config.yml: {e}")
                return {}
    return {}


def update_system_config(config_data: Dict[str, Any]):
    ensure_orcanium_dirs()
    current = load_system_config()
    current.update(config_data)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(current, f, default_flow_style=False)
