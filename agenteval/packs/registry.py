"""Discover installed domain packs via entry points."""

from importlib.metadata import entry_points

from agenteval.packs.protocol import DomainPack


def discover_domain_packs() -> dict[str, DomainPack]:
    """Return pack id → instance for all installed ``agenteval.domain_packs`` entry points."""
    found: dict[str, DomainPack] = {}
    eps = entry_points(group="agenteval.domain_packs")
    for ep in eps:
        loaded = ep.load()
        pack = loaded() if isinstance(loaded, type) else loaded
        if not isinstance(pack, DomainPack):
            raise TypeError(
                f"Domain pack entry '{ep.name}' must implement DomainPack, got {type(pack)!r}"
            )
        found[ep.name] = pack
    return found


def load_domain_pack(pack_id: str) -> DomainPack | None:
    return discover_domain_packs().get(pack_id)
