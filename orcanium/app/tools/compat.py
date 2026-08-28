"""Tool compatibility stubs -- registers agent.* and plugins.* modules as stubs.

Auto-imported before any tool module to prevent ImportError crashes.
"""

import sys
import types


class _ToolStub:
    def __getattr__(self, name):
        return _ToolStub()

    def __call__(self, *args, **kwargs):
        return None


stub = _ToolStub()

_AGENT_PLUGIN_MODULES = [
    "agent",
    "agent.auxiliary_client",
    "agent.file_safety",
    "agent.redact",
    "agent.skill_utils",  # registered below as real module
    "agent.video_gen_provider",
    "agent.browser_provider",
    "agent.browser_registry",
    "agent.insights",
    "plugins",
    "plugins.web",
    "plugins.web.firecrawl",
    "plugins.web.firecrawl.provider",
    "plugins.web.tavily",
    "plugins.web.tavily.provider",
    "plugins.web.parallel",
    "plugins.web.parallel.provider",
    "plugins.web.exa",
    "plugins.web.exa.provider",
    "plugins.browser",
    "plugins.browser.browserbase",
    "plugins.browser.browserbase.provider",
    "plugins.browser.browser_use",
    "plugins.browser.browser_use.provider",
    "plugins.browser.firecrawl",
    "plugins.browser.firecrawl.provider",
]

for mod_name in _AGENT_PLUGIN_MODULES:
    sys.modules[mod_name] = stub


# Override agent.file_safety with the real module
try:
    from orcanium.app.domains.capability.file_safety import (
        get_read_block_error, is_forbidden_path, validate_path,
    )
    _fs_mod = types.ModuleType("agent.file_safety")
    _fs_mod.get_read_block_error = get_read_block_error
    _fs_mod.is_forbidden_path = is_forbidden_path
    _fs_mod.validate_path = validate_path
    sys.modules["agent.file_safety"] = _fs_mod
except Exception:
    pass

# Override agent.redact with the real module
try:
    from orcanium.app.domains.capability.redaction import redact_sensitive_text
    _redact_mod = types.ModuleType("agent.redact")
    _redact_mod.redact_sensitive_text = redact_sensitive_text
    sys.modules["agent.redact"] = _redact_mod
except Exception:
    pass

# Override agent.skill_utils with the real module
try:
    from orcanium.app.tools import skills_utils as _real_skill_utils
    sys.modules["agent.skill_utils"] = _real_skill_utils
except Exception:
    pass
