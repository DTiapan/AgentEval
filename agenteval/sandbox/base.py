"""Abstract sandbox interface for ephemeral execution environments."""

from abc import ABC, abstractmethod

from agenteval.core.models import StateDiff, StateSnapshot


class Sandbox(ABC):
    """Abstract base class for all sandbox isolation environments."""

    @abstractmethod
    def snapshot(self, snapshot_id: str) -> StateSnapshot:
        """Capture the current state of the environment."""
        pass

    @abstractmethod
    def diff(self, pre_snapshot: StateSnapshot, post_snapshot: StateSnapshot) -> StateDiff:
        """Calculate the delta (Delta S) between two state snapshots."""
        pass
