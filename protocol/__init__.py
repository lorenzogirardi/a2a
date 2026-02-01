"""Protocol module - MCP and REST API."""
from .mcp_server import (
    mcp,
    get_agents,
    get_storage,
    register_agent,
    set_storage,
    setup_default_agents,
)
from .api import app

__all__ = [
    "mcp",
    "app",
    "get_agents",
    "get_storage",
    "register_agent",
    "set_storage",
    "setup_default_agents",
]
