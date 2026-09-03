"""Compatibility re-export — prefer agent_os.integrations.hermes.plugin."""
from agent_os.integrations.hermes.plugin import *  # noqa: F403
from agent_os.integrations.hermes.plugin import register

__all__ = ["register"]
