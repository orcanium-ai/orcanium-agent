"""CLI compatibility stubs — maps reference-agent imports to orcanium.

The reference-agent's orcanium-cli imports extensively from agent.*, tools.*,
providers.*, orcanium.channel.compat, and utils. This compat module patches
sys.modules at import time so the CLI can load within orcanium.
"""

import logging
import os
import sys
import types
from pathlib import Path

from orcanium.orcanium_constants import (
    display_orcanium_home,
    get_default_orcanium_root,
    get_orcanium_dir as _real_orcanium_dir,
    get_orcanium_home as _real_orcanium_home,
    is_container,
    is_termux,
    is_wsl,
)

logger = logging.getLogger(__name__)


# ── Path functions ──────────────────────────────────────────────
# These delegate to orcanium.orcanium_constants so all code resolves
# to ~/.orcanium (or $ORCANIUM_HOME), never a repo-local data/ dir.

def get_orcanium_home(*subdirs):
    path = _real_orcanium_home()
    for s in subdirs:
        path = path / s
    return path

def get_orcanium_dir(*subdirs):
    path = _real_orcanium_dir()
    for s in subdirs:
        path = path / s
    return path

def secure_parent_dir(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


# ── Utility stubs ───────────────────────────────────────────────

_TRUTHY = {"true", "1", "yes", "y", "on", "enabled"}

def is_truthy_value(val):
    if isinstance(val, bool): return val
    if isinstance(val, str): return val.strip().lower() in _TRUTHY
    return bool(val)

def env_var_enabled(key, default=False):
    return os.getenv(key, "1" if default else "0").lower() in _TRUTHY

def env_int(key, default=0):
    try: return int(os.getenv(key, str(default)))
    except: return default

def atomic_replace(src, dst):
    import shutil
    shutil.move(src, dst)

def atomic_yaml_write(path, data, **kwargs):
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        import yaml
        yaml.dump(data, f, default_flow_style=False)
    atomic_replace(tmp, str(path))


def atomic_json_write(path, data, indent=None):
    """Atomically write JSON data to a file."""
    import json, tempfile, os
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(str(path)) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


# ── Agent stubs ─────────────────────────────────────────────────

class _StubCallable:
    def __init__(self, name=""):
        self._name = name
    def __call__(self, *a, **kw):
        logger.debug(f"Stub called: {self._name}")
        return []
    def __getattr__(self, name):
        return _StubCallable(f"{self._name}.{name}")
    def __iter__(self):
        return iter([])
    def __len__(self):
        return 0
    def __getitem__(self, key):
        raise KeyError(key)

_agent_stub = _StubCallable()

# Register orcanium.channel.compat — import the real module directly.
# It only imports from orcanium.orcanium_constants + stdlib (no heavy deps),
# so there's no startup-cost reason to maintain a separate stub.
import orcanium.channel.compat as _real_gw_compat
sys.modules["orcanium.channel.compat"] = _real_gw_compat

# Register utils
_utils = types.ModuleType("utils")
_utils.is_truthy_value = is_truthy_value
_utils.env_var_enabled = env_var_enabled
_utils.env_int = env_int
_utils.atomic_replace = atomic_replace
_utils.atomic_yaml_write = atomic_yaml_write
_utils.normalize_proxy_url = lambda url: url
sys.modules["utils"] = _utils

# Agent stubs — all agent.* imports resolve here
_agent_mod = types.ModuleType("agent")
sys.modules["agent"] = _agent_mod

# Credential pool stub — supports auth list/remove/add commands.
class _StubCredentialPool:
    """Minimal stub that satisfies auth_commands' use of CredentialPool."""
    def __init__(self):
        self._entries: list = []
    def entries(self):
        return list(self._entries)
    def peek(self):
        return self._entries[0] if self._entries else None
    def add_entry(self, entry):
        self._entries.append(entry)
    def remove(self, entry_id):
        self._entries = [e for e in self._entries if e.id != entry_id]
    def __len__(self):
        return len(self._entries)

class _StubPooledCredential:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

def _stub_load_pool(provider: str):
    return _StubCredentialPool()

def _stub_list_custom_pool_providers():
    return []

def _stub_get_custom_provider_pool_key(base_url, provider_name=None):
    """Resolve a configured custom provider to its credential-pool key."""
    if not base_url:
        return None
    try:
        from orcanium.cli.config import get_compatible_custom_providers, load_config

        normalized_url = str(base_url).strip().rstrip("/")
        providers = get_compatible_custom_providers(load_config())
        if provider_name:
            wanted = str(provider_name).strip().lower().replace(" ", "-")
            for entry in providers:
                name = str(entry.get("name") or "").strip().lower().replace(" ", "-")
                if name == wanted:
                    return f"custom:{name}"
        for entry in providers:
            entry_url = str(entry.get("base_url") or "").strip().rstrip("/")
            if entry_url and entry_url == normalized_url:
                name = str(entry.get("name") or "").strip().lower().replace(" ", "-")
                if name:
                    return f"custom:{name}"
    except Exception:
        pass
    return None

_cred_pool_mod = types.ModuleType("agent.credential_pool")
_cred_pool_mod.load_pool = _stub_load_pool
_cred_pool_mod.list_custom_pool_providers = _stub_list_custom_pool_providers
_cred_pool_mod.get_custom_provider_pool_key = _stub_get_custom_provider_pool_key
_cred_pool_mod.PooledCredential = _StubPooledCredential
_cred_pool_mod.CredentialPool = _StubCredentialPool
_cred_pool_mod.AUTH_TYPE_API_KEY = "api_key"
_cred_pool_mod.AUTH_TYPE_OAUTH = "oauth"
_cred_pool_mod.CUSTOM_POOL_PREFIX = "custom:"
_cred_pool_mod.SOURCE_MANUAL = "manual"
_cred_pool_mod.SOURCE_MANUAL_DEVICE_CODE = "manual_device_code"
_cred_pool_mod.STATUS_EXHAUSTED = "exhausted"
_cred_pool_mod.STRATEGY_FILL_FIRST = "fill_first"
_cred_pool_mod.STRATEGY_ROUND_ROBIN = "round_robin"
_cred_pool_mod.STRATEGY_RANDOM = "random"
_cred_pool_mod.STRATEGY_LEAST_USED = "least_used"
_cred_pool_mod._exhausted_until = lambda e: None
_cred_pool_mod._normalize_custom_pool_name = lambda n: n
_cred_pool_mod.get_pool_strategy = lambda p: "round_robin"
_cred_pool_mod.label_from_token = lambda t, p: "stub"
sys.modules["agent.credential_pool"] = _cred_pool_mod
# Register agent.skill_utils from real module
try:
    from orcanium.app.tools import skills_utils as _real_skill_utils
    sys.modules["agent.skill_utils"] = _real_skill_utils
except Exception:
    pass


_AGENT_SUB_MODULES = [
    "agent.credential_persistence", "agent.skill_bundles",
    "agent.skill_commands", "agent.skill_utils", "agent.model_metadata",
    "agent.context_engine", "agent.prompt_builder", "agent.redact",
    "agent.secret_sources", "agent.secret_sources.bitwarden",
    "agent.usage_pricing", "agent.anthropic_adapter", "agent.auxiliary_client",
    "agent.azure_identity_adapter", "agent.bedrock_adapter",
    "agent.browser_provider", "agent.browser_registry",
    "agent.credential_sources",
    "agent.credits_tracker", "agent.gemini_native_adapter",
    "agent.google_code_assist", "agent.google_oauth",
    "agent.image_gen_provider", "agent.image_gen_registry",
    "agent.insights", "agent.max_turns", "agent.models_dev",
    "agent.plugin_llm", "agent.system_prompt",
    "agent.transcription_provider", "agent.transcription_registry",
    "agent.tts_provider", "agent.tts_registry",
    "agent.video_gen_provider", "agent.lsp.cli",
    "agent.transports.codex_app_server",
    "agent.memory_manager", "agent.memory_provider",
    "agent.account_usage", "agent.async_utils", "agent.i18n",
]
for mod_name in _AGENT_SUB_MODULES:
    sys.modules[mod_name] = _agent_stub

# Override agent.skill_utils with the real module
try:
    from orcanium.app.tools import skills_utils as _real_skill_utils
    sys.modules["agent.skill_utils"] = _real_skill_utils
except Exception:
    pass

# Other stubs — register real modules where they exist in orcanium,
# so `from toolsets import ...` works instead of getting a stub.
try:
    import cron  # now at repo-root/cron/
    sys.modules["cron"] = cron
except Exception:
    sys.modules["cron"] = _agent_stub

try:
    from orcanium import toolsets as _real_toolsets
    sys.modules["toolsets"] = _real_toolsets
except Exception:
    sys.modules["toolsets"] = _agent_stub

try:
    from orcanium.app import tools as _real_tools
    sys.modules["tools"] = _real_tools
except Exception:
    sys.modules["tools"] = _agent_stub

try:
    from orcanium import providers as _real_providers
    sys.modules["providers"] = _real_providers
except Exception:
    sys.modules["providers"] = _agent_stub

# skills don't exist as a real module yet — keep stub
sys.modules["skills"] = _agent_stub


def base_url_host_matches(url1, url2):
    """Check if two URLs have the same host."""
    from urllib.parse import urlparse
    try:
        h1 = urlparse(url1).hostname
        h2 = urlparse(url2).hostname
        return h1 == h2
    except Exception:
        return False


def setup_logging(*args, **kwargs):
    """Stub for orcanium_logging.setup_logging."""
    import logging
    logging.basicConfig(level=logging.INFO)


def get_config_path():
    """Stub for config path."""
    from pathlib import Path
    return Path.home() / ".orcanium"


def normalize_proxy_url(url: str) -> str:
    """Stub for URL normalization."""
    return url


def base_url_hostname(url):
    """Extract hostname from a base URL."""
    from urllib.parse import urlparse
    try:
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return urlparse(url).hostname or ''
    except Exception:
        return ''


# ── Config stubs ────────────────────────────────────────────────

def load_config(*args, **kwargs):
    """Stub for config loading."""
    return {}

def save_config(*args, **kwargs):
    """Stub for config saving."""
    return True

def read_raw_config(*args, **kwargs):
    """Stub for raw config reading."""
    return {}

def cfg_get(config, key, default=None):
    """Stub for config get."""
    if isinstance(config, dict):
        return config.get(key, default)
    return default

# ── Env stubs ───────────────────────────────────────────────────

def get_env_value(key, default=None):
    """Stub for env value lookup."""
    import os
    return os.getenv(key, default)

OPTIONAL_ENV_VARS = {}

def load_env(*args, **kwargs):
    """Stub for env loading."""
    pass

# ── Plugin stubs ────────────────────────────────────────────────

def discover_plugins(*args, **kwargs):
    """Stub for plugin discovery."""
    return []

def get_plugin_manager(*args, **kwargs):
    """Stub for plugin manager."""
    return _agent_stub

def invoke_hook(*args, **kwargs):
    """Stub for plugin hooks."""
    return None

def _ensure_plugins_discovered(*args, **kwargs):
    """Stub for plugin discovery."""
    pass

def _get_disabled_plugins(*args, **kwargs):
    """Stub for disabled plugins."""
    return []

# ── Provider stubs ──────────────────────────────────────────────

def resolve_runtime_provider(*args, **kwargs):
    """Stub for provider resolution."""
    return None

def has_named_custom_provider(*args, **kwargs):
    """Stub for custom provider check."""
    return False

def get_active_profile_name(*args, **kwargs):
    """Stub for profile name."""
    return "default"

def _detect_api_mode_for_url(*args, **kwargs):
    """Stub for API mode detection."""
    return None
