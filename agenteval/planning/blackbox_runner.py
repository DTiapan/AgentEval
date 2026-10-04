"""Execute a frozen test pack against an HTTP endpoint (blackbox profile)."""

from __future__ import annotations

import concurrent.futures
import json
import os
import time
from collections.abc import Callable
from enum import StrEnum
from typing import Any
from uuid import uuid4

import httpx

from agenteval.evaluators.llm_judge import LLMJudgeScorer
from agenteval.logging import get_logger
from agenteval.planning.execution_trace import build_blackbox_trajectory
from agenteval.planning.models import (
    CandidateTest,
    ObservationBundle,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)
from agenteval.planning.observable_scorer import ObservableScorer
from agenteval.security.url_validator import (
    UnsafeURLError,
    create_safe_client,
    is_private_allowed,
    validate_endpoint_url,
)
from agenteval.targets import TargetConnectionProfile
from agenteval.telemetry import StatusCode, inject_trace_context, start_span

logger = get_logger("agenteval.runner")


class JudgeMode(StrEnum):
    """Evaluation strategy for black-box test runs."""

    HYBRID = (
        "hybrid"  # Tier 0 heuristics first; escalate to LLM judge when template rule is missing
    )
    DETERMINISTIC_ONLY = (
        "deterministic_only"  # Tier 0 only (no LLM calls; UNVERIFIABLE if no heuristic match)
    )
    LLM_JUDGE = "llm_judge"  # LLM judge evaluates all tests directly


class BlackboxRunner:
    """POST each test prompt to the agent endpoint; score with ObservableScorer and pluggable LLM judge."""

    def __init__(
        self,
        endpoint_url: str,
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
        judge_mode: JudgeMode | str = JudgeMode.HYBRID,
        judge_scorer: LLMJudgeScorer | None = None,
        force_offline_judge: bool | None = None,
        allow_private: bool | None = None,
        max_workers: int | None = None,
        client: httpx.Client | None = None,
        connection_profile: TargetConnectionProfile | None = None,
    ) -> None:
        self.allow_private = is_private_allowed() if allow_private is None else allow_private
        effective_url = (
            connection_profile.endpoint_url
            if connection_profile and connection_profile.endpoint_url
            else endpoint_url
        )
        validate_endpoint_url(effective_url, allow_private=self.allow_private)
        self.endpoint_url = effective_url
        effective_headers: dict[str, str] = {"Content-Type": "application/json"}
        if connection_profile is not None:
            effective_headers.update(connection_profile.resolve_headers())
        if headers is not None:
            effective_headers.update(headers)
        self.headers = effective_headers
        self.timeout_seconds = (
            connection_profile.timeout_seconds
            if connection_profile is not None
            else timeout_seconds
        )
        self.judge_mode = JudgeMode(judge_mode)
        self._scorer = ObservableScorer()
        self._judge_scorer = judge_scorer or LLMJudgeScorer(force_offline=force_offline_judge)
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            self._client = create_safe_client(
                allow_private=self.allow_private,
                timeout=self.timeout_seconds,
                headers=self.headers,
            )
            self._owns_client = True
        raw_workers = (
            max_workers
            if max_workers is not None
            else os.environ.get("AGENTEVAL_MAX_CONCURRENT_TESTS")
        )
        try:
            self.max_workers = int(raw_workers) if raw_workers else 8
        except ValueError:
            self.max_workers = 8
        self.max_workers = max(1, min(50, self.max_workers))

    def run_pack(
        self,
        pack: TestPack,
        *,
        run_id: str | None = None,
        max_workers: int | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        on_result: Callable[[TestCaseResult], None] | None = None,
    ) -> SuiteRunReport:
        effective_run_id = run_id or uuid4().hex[:12]
        effective_workers = max_workers if max_workers is not None else self.max_workers
        effective_workers = max(1, min(50, effective_workers))
        total_tests = len(pack.tests)

        logger.info(
            "suite_run_started",
            run_id=effective_run_id,
            agent_id=pack.agent_id,
            test_count=total_tests,
            workers=effective_workers,
            judge_mode=str(self.judge_mode),
        )

        with start_span(
            "suite.run_pack",
            attributes={
                "agenteval.run_id": effective_run_id,
                "agenteval.agent_id": pack.agent_id,
                "agenteval.test_count": total_tests,
                "agenteval.workers": effective_workers,
                "agenteval.judge_mode": str(self.judge_mode),
                "agenteval.pack_version": pack.version,
            },
        ) as suite_span:

            def _execute_one(test: CandidateTest) -> TestCaseResult:
                with start_span(
                    "test.case.execute",
                    attributes={
                        "agenteval.run_id": effective_run_id,
                        "agenteval.test_id": test.id,
                        "agenteval.category": test.category,
                        "agenteval.expected_verdict": getattr(test, "expected_verdict", "PASS"),
                    },
                ) as test_span:
                    try:
                        obs = self._invoke(test)
                        scored: TestCaseResult
                        if self.judge_mode == JudgeMode.LLM_JUDGE:
                            scored = self._judge_scorer.score(test, obs)
                        elif self.judge_mode == JudgeMode.DETERMINISTIC_ONLY:
                            scored = self._scorer.score(test, obs)
                        else:  # JudgeMode.HYBRID
                            scored = self._scorer.score(test, obs)
                            # Escalate to LLM judge if heuristic has no rule match
                            if (
                                scored.verdict == "UNVERIFIABLE"
                                and "external evaluator or llm judge required"
                                in scored.rationale.lower()
                            ):
                                logger.info(
                                    "hybrid_judge_escalation",
                                    run_id=effective_run_id,
                                    test_id=test.id,
                                )
                                scored = self._judge_scorer.score(test, obs)

                        logger.info(
                            "test_completed",
                            run_id=effective_run_id,
                            test_id=test.id,
                            verdict=scored.verdict,
                            latency_ms=round(obs.latency_ms, 2),
                            http_status=obs.http_status,
                        )
                        test_span.set_attribute("agenteval.verdict", scored.verdict)
                        test_span.set_attribute("agenteval.latency_ms", obs.latency_ms)
                        test_span.set_attribute("http.status_code", obs.http_status)
                        if scored.verdict == "FAIL":
                            test_span.set_status(
                                StatusCode.ERROR, f"Test {test.id} failed: {scored.rationale}"
                            )

                        trajectory = build_blackbox_trajectory(
                            obs, scored.verdict, scored.rationale
                        )
                        return scored.model_copy(update={"trajectory": trajectory})
                    except Exception as exc:
                        test_span.set_status(StatusCode.ERROR, str(exc))
                        test_span.record_exception(exc)
                        logger.error(
                            "test_execution_exception",
                            run_id=effective_run_id,
                            test_id=test.id,
                            error=str(exc),
                        )
                        fallback_obs = ObservationBundle(
                            test_id=test.id,
                            user_prompt=test.user_prompt,
                            response_text=f"Execution error: {exc}",
                            http_status=0,
                            latency_ms=0.0,
                            raw_json={"error": str(exc)},
                        )
                        trajectory = build_blackbox_trajectory(
                            fallback_obs, "UNVERIFIABLE", f"Runner execution exception: {exc}"
                        )
                        return TestCaseResult(
                            test_id=test.id,
                            verdict="UNVERIFIABLE",
                            observation=fallback_obs,
                            rationale=f"Runner execution exception: {exc}",
                            trajectory=trajectory,
                        )

            results: list[TestCaseResult] = []
            completed_count = 0

            if effective_workers <= 1 or total_tests <= 1:
                for test in pack.tests:
                    res = _execute_one(test)
                    results.append(res)
                    completed_count += 1
                    if on_result:
                        on_result(res)
                    if on_progress:
                        on_progress(completed_count, total_tests)
            else:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(effective_workers, total_tests)
                ) as pool:
                    futures = [pool.submit(_execute_one, test) for test in pack.tests]
                    for future in concurrent.futures.as_completed(futures):
                        res = future.result()
                        results.append(res)
                        completed_count += 1
                        if on_result:
                            on_result(res)
                        if on_progress:
                            on_progress(completed_count, total_tests)

            # Preserve canonical test pack ordering for deterministic reports and diffs
            order = {test.id: i for i, test in enumerate(pack.tests)}
            results.sort(key=lambda r: order.get(r.test_id, 0))

            passed = sum(1 for r in results if r.verdict == "PASS")
            failed = sum(1 for r in results if r.verdict == "FAIL")
            unverifiable = sum(1 for r in results if r.verdict == "UNVERIFIABLE")

            logger.info(
                "suite_run_finished",
                run_id=effective_run_id,
                agent_id=pack.agent_id,
                passed=passed,
                failed=failed,
                unverifiable=unverifiable,
                total=len(results),
            )

            suite_span.set_attribute("agenteval.passed", passed)
            suite_span.set_attribute("agenteval.failed", failed)
            suite_span.set_attribute("agenteval.unverifiable", unverifiable)

            return SuiteRunReport(
                agent_id=pack.agent_id,
                run_id=effective_run_id,
                suite_version=pack.version,
                results=results,
                passed=passed,
                failed=failed,
                unverifiable=unverifiable,
            )

    def _invoke(self, test: CandidateTest) -> ObservationBundle:
        turns: list[str]
        if test.steps:
            if test.steps[0] == test.user_prompt:
                turns = list(test.steps)
            else:
                turns = [test.user_prompt] + [s for s in test.steps if s != test.user_prompt]
        else:
            turns = [test.user_prompt]

        if len(turns) == 1:
            return self._invoke_single_turn(test, test.user_prompt)
        return self._invoke_multi_turn(test, turns)

    def _invoke_single_turn(self, test: CandidateTest, prompt: str) -> ObservationBundle:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "messages": [{"role": "user", "content": prompt}],
            "history": [],
        }
        with start_span(
            "agent.endpoint.invoke",
            attributes={
                "agenteval.test_id": test.id,
                "http.url": self.endpoint_url,
                "http.method": "POST",
            },
        ) as invoke_span:
            req_headers = dict(self.headers)
            inject_trace_context(req_headers)
            start = time.perf_counter()
            try:
                resp = self._client.post(self.endpoint_url, json=payload, headers=req_headers)
                status = resp.status_code
                invoke_span.set_attribute("http.status_code", status)
            except UnsafeURLError as e:
                latency_ms = (time.perf_counter() - start) * 1000
                invoke_span.set_status(StatusCode.ERROR, str(e))
                return ObservationBundle(
                    test_id=test.id,
                    user_prompt=prompt,
                    response_text=f"SSRF blocked: {e}",
                    http_status=0,
                    latency_ms=latency_ms,
                    raw_json={"error": str(e)},
                )
            except httpx.HTTPError as e:
                latency_ms = (time.perf_counter() - start) * 1000
                invoke_span.set_status(StatusCode.ERROR, str(e))
                return ObservationBundle(
                    test_id=test.id,
                    user_prompt=prompt,
                    response_text=f"HTTP error: {e}",
                    http_status=0,
                    latency_ms=latency_ms,
                    raw_json={"error": str(e)},
                )
            except Exception as e:
                latency_ms = (time.perf_counter() - start) * 1000
                invoke_span.set_status(StatusCode.ERROR, str(e))
                return ObservationBundle(
                    test_id=test.id,
                    user_prompt=prompt,
                    response_text=f"Request error: {e}",
                    http_status=0,
                    latency_ms=latency_ms,
                    raw_json={"error": str(e)},
                )

            latency_ms = (time.perf_counter() - start) * 1000
            try:
                data = resp.json()
            except Exception:
                data = {"response": resp.text}

            text = self._extract_text(data) if isinstance(data, dict) else str(data)
            return ObservationBundle(
                test_id=test.id,
                user_prompt=prompt,
                response_text=text,
                http_status=status,
                latency_ms=latency_ms,
                raw_json=data if isinstance(data, dict) else {"raw": data},
            )

    def _invoke_multi_turn(self, test: CandidateTest, turns: list[str]) -> ObservationBundle:
        messages: list[dict[str, str]] = []
        history: list[dict[str, str]] = []
        turn_bundles: list[ObservationBundle] = []
        total_latency_ms = 0.0

        for turn_idx, prompt in enumerate(turns, 1):
            messages.append({"role": "user", "content": prompt})
            payload: dict[str, Any] = {
                "prompt": prompt,
                "messages": list(messages),
                "history": list(history),
            }
            with start_span(
                "agent.endpoint.invoke",
                attributes={
                    "agenteval.test_id": test.id,
                    "agenteval.turn_index": turn_idx,
                    "http.url": self.endpoint_url,
                    "http.method": "POST",
                },
            ) as invoke_span:
                req_headers = dict(self.headers)
                inject_trace_context(req_headers)
                start = time.perf_counter()
                try:
                    resp = self._client.post(self.endpoint_url, json=payload, headers=req_headers)
                    status = resp.status_code
                    invoke_span.set_attribute("http.status_code", status)
                except UnsafeURLError as e:
                    latency_ms = (time.perf_counter() - start) * 1000
                    invoke_span.set_status(StatusCode.ERROR, str(e))
                    err_bundle = ObservationBundle(
                        test_id=f"{test.id}-turn-{turn_idx}",
                        user_prompt=prompt,
                        response_text=f"SSRF blocked: {e}",
                        http_status=0,
                        latency_ms=latency_ms,
                        raw_json={"error": str(e)},
                    )
                    turn_bundles.append(err_bundle)
                    return ObservationBundle(
                        test_id=test.id,
                        user_prompt=test.user_prompt,
                        response_text=f"SSRF blocked: {e}",
                        http_status=0,
                        latency_ms=total_latency_ms + latency_ms,
                        raw_json={"error": str(e)},
                        turn_observations=turn_bundles,
                    )
                except httpx.HTTPError as e:
                    latency_ms = (time.perf_counter() - start) * 1000
                    invoke_span.set_status(StatusCode.ERROR, str(e))
                    err_bundle = ObservationBundle(
                        test_id=f"{test.id}-turn-{turn_idx}",
                        user_prompt=prompt,
                        response_text=f"HTTP error: {e}",
                        http_status=0,
                        latency_ms=latency_ms,
                        raw_json={"error": str(e)},
                    )
                    turn_bundles.append(err_bundle)
                    return ObservationBundle(
                        test_id=test.id,
                        user_prompt=test.user_prompt,
                        response_text=f"HTTP error: {e}",
                        http_status=0,
                        latency_ms=total_latency_ms + latency_ms,
                        raw_json={"error": str(e)},
                        turn_observations=turn_bundles,
                    )
                except Exception as e:
                    latency_ms = (time.perf_counter() - start) * 1000
                    invoke_span.set_status(StatusCode.ERROR, str(e))
                    err_bundle = ObservationBundle(
                        test_id=f"{test.id}-turn-{turn_idx}",
                        user_prompt=prompt,
                        response_text=f"Request error: {e}",
                        http_status=0,
                        latency_ms=latency_ms,
                        raw_json={"error": str(e)},
                    )
                    turn_bundles.append(err_bundle)
                    return ObservationBundle(
                        test_id=test.id,
                        user_prompt=test.user_prompt,
                        response_text=f"Request error: {e}",
                        http_status=0,
                        latency_ms=total_latency_ms + latency_ms,
                        raw_json={"error": str(e)},
                        turn_observations=turn_bundles,
                    )

                latency_ms = (time.perf_counter() - start) * 1000
                total_latency_ms += latency_ms
                try:
                    data = resp.json()
                except Exception:
                    data = {"response": resp.text}

                text = self._extract_text(data) if isinstance(data, dict) else str(data)
                bundle = ObservationBundle(
                    test_id=f"{test.id}-turn-{turn_idx}",
                    user_prompt=prompt,
                    response_text=text,
                    http_status=status,
                    latency_ms=latency_ms,
                    raw_json=data if isinstance(data, dict) else {"raw": data},
                )
                turn_bundles.append(bundle)

                if status >= 500:
                    break

                # Append to conversation messages and history
                messages.append({"role": "assistant", "content": text})
                history.append({"user": prompt, "agent": text})

        last_bundle = turn_bundles[-1]
        return ObservationBundle(
            test_id=test.id,
            user_prompt=test.user_prompt,
            response_text=last_bundle.response_text,
            http_status=last_bundle.http_status,
            latency_ms=total_latency_ms,
            raw_json=last_bundle.raw_json,
            turn_observations=turn_bundles,
        )

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in ("reply", "output", "response", "message"):
            if key in data and str(data[key]).strip():
                parts.append(str(data[key]).strip())
                break
        if "thought" in data and str(data["thought"]).strip():
            parts.append(f"[thought: {data['thought']}]")
        tools = data.get("tool_calls") or []
        for t in tools:
            parts.append(f"[tool:{t.get('tool_name', t.get('name', '?'))}]")

        if parts:
            return " ".join(parts).strip()
        return json.dumps(data)

    def close(self) -> None:
        """Close underlying HTTP client if owned by this runner."""
        if getattr(self, "_owns_client", False):
            self._client.close()

    def __enter__(self) -> BlackboxRunner:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
