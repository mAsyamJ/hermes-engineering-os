"""Compatibility re-export — prefer agent_os.core.classifier."""
from agent_os.core.classifier import *  # noqa: F403
from agent_os.core.classifier import TaskClassification, classify_task

__all__ = ["TaskClassification", "classify_task"]
