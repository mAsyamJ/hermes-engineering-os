"""Agent OS lifecycle sync (dirty flag + debounce)."""
from agent_os.lifecycle.sync import (
    is_dirty,
    mark_dirty,
    regenerate_if_dirty,
)

__all__ = ["is_dirty", "mark_dirty", "regenerate_if_dirty"]
