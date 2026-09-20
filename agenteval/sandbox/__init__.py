"""Sandbox isolation backends for AgentEval."""

from agenteval.sandbox.base import Sandbox
from agenteval.sandbox.local import LocalSandbox

__all__ = ["LocalSandbox", "Sandbox"]
