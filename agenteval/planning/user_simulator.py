"""User message simulator for scenario-first tests (opening turn v0)."""

from __future__ import annotations

import concurrent.futures
import hashlib
import os

from agenteval.planning._utils import load_env
from agenteval.planning.litellm_routing import any_llm_route_available, completion_with_fallback
from agenteval.planning.scenario_spec import ScenarioSpec, UserProfile

load_env()

_OPENING_TEMPLATES: dict[str, list[str]] = {
    "direct_request": [
        "{goal}",
        "Hi — {goal}",
        "Quick question: {goal}",
    ],
    "vague_complaint_then_details": [
        "Something's wrong with my order — {goal}",
        "I need help. {goal}",
        "Hey, {goal}",
    ],
    "frustrated_short": [
        "This is ridiculous. {goal}",
        "{goal} — I've been waiting forever.",
    ],
}


def opening_max_workers() -> int:
    raw = os.getenv("AGENTEVAL_OPENING_MAX_WORKERS", "8").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 8
    return max(1, min(n, 32))


class UserSimulator:
    """Produce natural first-turn user text from a ScenarioSpec (offline-first)."""

    def __init__(self, force_offline: bool | None = None) -> None:
        if force_offline is not None:
            self.force_offline = force_offline
        else:
            self.force_offline = os.getenv("AGENTEVAL_FORCE_OFFLINE") == "1"

    def opening_message(self, spec: ScenarioSpec, *, seed: int | None = None) -> str:
        return self.opening_messages([spec], seeds={spec.id: seed} if seed is not None else None)[
            spec.id
        ]

    def opening_messages(
        self,
        specs: list[ScenarioSpec],
        *,
        seeds: dict[str, int] | None = None,
    ) -> dict[str, str]:
        """Resolve opening lines for many scenarios (parallel LiteLLM when online)."""
        if not specs:
            return {}

        use_llm = not self.force_offline and self._api_key_available()
        workers = opening_max_workers() if use_llm and len(specs) > 1 else 1

        def one(spec: ScenarioSpec) -> tuple[str, str]:
            seed = (seeds or {}).get(spec.id, spec.sample_seed)
            if use_llm:
                litellm_msg = self._opening_via_litellm(spec, seed)
                if litellm_msg:
                    return spec.id, litellm_msg
            return spec.id, self._opening_offline(spec, seed)

        out: dict[str, str] = {}
        if workers <= 1:
            for spec in specs:
                test_id, text = one(spec)
                out[test_id] = text
            return out

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(one, spec) for spec in specs]
            for fut in concurrent.futures.as_completed(futures):
                test_id, text = fut.result()
                out[test_id] = text
        return out

    @staticmethod
    def _api_key_available() -> bool:
        return any_llm_route_available()

    def _opening_offline(self, spec: ScenarioSpec, seed: int) -> str:
        strategy = spec.opening_strategy
        if spec.user_profile.tone == "frustrated":
            strategy = "frustrated_short"
        templates = _OPENING_TEMPLATES.get(strategy) or _OPENING_TEMPLATES["direct_request"]
        idx = seed % len(templates)
        template = templates[idx]
        goal = spec.goal.strip()
        if spec.private_facts:
            extras = " ".join(f"{k.replace('_', ' ')}: {v}." for k, v in spec.private_facts.items())
            goal = f"{goal} ({extras})"
        text = template.format(goal=goal)
        return _humanize_whitespace(text)

    def _opening_via_litellm(self, spec: ScenarioSpec, seed: int) -> str | None:
        if not any_llm_route_available():
            return None
        profile = spec.user_profile
        system = (
            "You write a single realistic customer chat message. "
            "No role-play preamble. No 'You are'. One message only."
        )
        user = (
            f"Goal: {spec.goal}\n"
            f"Tone: {profile.tone}\n"
            f"Expertise: {profile.expertise}\n"
            f"Private facts (user knows): {spec.private_facts}\n"
            f"Variation seed: {seed}"
        )
        try:
            resp, _route = completion_with_fallback(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.3,
                max_tokens=256,
                timeout=6.0,
            )
            content = (resp.choices[0].message.content or "").strip()
            if content and "you are acting as" not in content.lower():
                return _humanize_whitespace(content)
        except Exception:
            return None
        return None


def stable_seed_for(*parts: str) -> int:
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def profile_from_persona_slug(slug: str) -> UserProfile:
    tone = "neutral"
    expertise = "medium"
    if slug in ("adversary", "security-auditor"):
        tone = "terse"
        expertise = "high"
    elif slug == "frequent-user":
        tone = "polite"
        expertise = "medium"
    return UserProfile(slug=slug, tone=tone, expertise=expertise)


def _humanize_whitespace(text: str) -> str:
    return " ".join(text.split())
