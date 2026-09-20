"""Protocol adapters for AgentEval."""

from agenteval.adapters.base import AgentAdapter
from agenteval.adapters.callable import CallableAdapter
from agenteval.adapters.tool import LocalToolAdapter, ToolAdapter

__all__ = ["AgentAdapter", "CallableAdapter", "LocalToolAdapter", "ToolAdapter"]
