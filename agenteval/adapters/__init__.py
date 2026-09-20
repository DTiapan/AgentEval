"""Protocol adapters for AgentEval."""

from agenteval.adapters.base import AgentAdapter
from agenteval.adapters.callable import CallableAdapter
from agenteval.adapters.http import HTTPAdapter
from agenteval.adapters.tool import LocalToolAdapter, ToolAdapter

__all__ = ["AgentAdapter", "CallableAdapter", "HTTPAdapter", "LocalToolAdapter", "ToolAdapter"]
