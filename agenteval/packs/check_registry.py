"""Discover pack check callables via entry points."""

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

from agenteval.packs.protocol import CriterionVerdictDraft

PackCheckFn = Callable[..., CriterionVerdictDraft]


def discover_pack_checks() -> dict[str, PackCheckFn]:
    """Map check_kind → callable registered under ``agenteval.pack_checks``."""
    found: dict[str, PackCheckFn] = {}
    for ep in entry_points(group="agenteval.pack_checks"):
        fn = ep.load()
        if not callable(fn):
            raise TypeError(f"Pack check entry '{ep.name}' must be callable, got {type(fn)!r}")
        found[ep.name] = fn
    return found


def resolve_check_by_kind(check_kind: str, pack_checks: dict[str, PackCheckFn]) -> PackCheckFn | None:
    """Resolve check_kind (e.g. fintech.audit.refund_logged) via pack register_checks metadata."""
    from agenteval.packs.registry import discover_domain_packs

    for pack in discover_domain_packs().values():
        registrations: list[Any] = getattr(pack, "register_checks", lambda: [])()
        for reg in registrations:
            if reg.check_kind == check_kind:
                return pack_checks.get(reg.entry_point_name)
    return None
