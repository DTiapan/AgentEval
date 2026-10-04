"""Parallel opening generation for scenario-first compile."""

import threading
import time

from agenteval.planning.scenario_spec import DialogueMode, ScenarioOracle, ScenarioSpec, UserProfile
from agenteval.planning.user_simulator import UserSimulator, opening_max_workers


def _spec(test_id: str) -> ScenarioSpec:
    return ScenarioSpec(
        id=test_id,
        title=test_id,
        capability_id="cap",
        goal=f"help with {test_id}",
        user_profile=UserProfile(slug="frequent-user", tone="polite", expertise="medium"),
        private_facts={},
        dialogue_mode=DialogueMode.SIMULATED,
        max_turns=4,
        opening_strategy="direct_request",
        oracle=ScenarioOracle(),
        sample_seed=1,
        coverage_tags=[],
        template_id="t",
        failure_mode="fm",
        category="functional",
    )


def test_opening_messages_runs_litellm_in_parallel(monkeypatch) -> None:
    monkeypatch.setenv("AGENTEVAL_OPENING_MAX_WORKERS", "4")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    lock = threading.Lock()
    in_flight = 0
    peak = 0

    def fake_litellm(spec: ScenarioSpec, seed: int) -> str:
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        time.sleep(0.08)
        with lock:
            in_flight -= 1
        return f"msg-{spec.id}"

    sim = UserSimulator(force_offline=False)
    monkeypatch.setattr(sim, "_opening_via_litellm", fake_litellm)

    specs = [_spec(f"t{i}") for i in range(8)]
    result = sim.opening_messages(specs)

    assert len(result) == 8
    assert peak >= 2
    assert opening_max_workers() == 4

