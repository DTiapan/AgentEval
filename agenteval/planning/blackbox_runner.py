"""Execute a frozen test pack against an HTTP endpoint (blackbox profile)."""

from __future__ import annotations

import concurrent.futures
import json
import os
import time
from enum import StrEnum
from typing import Any
from uuid import uuid4

import httpx

from agenteval.evaluators.llm_judge import LLMJudgeScorer
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
    ) -> None:
        self.allow_private = is_private_allowed() if allow_private is None else allow_private
        validate_endpoint_url(endpoint_url, allow_private=self.allow_private)
        self.endpoint_url = endpoint_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout_seconds = timeout_seconds
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
        raw_workers = max_workers if max_workers is not None else os.environ.get("AGENTEVAL_MAX_CONCURRENT_TESTS")
        try:
            self.max_workers = int(raw_workers) if raw_workers else 8
        except ValueError:
            self.max_workers = 8
        self.max_workers = max(1, min(50, self.max_workers))

    def run_pack(self, pack: TestPack, *, max_workers: int | None = None) -> SuiteRunReport:
        run_id = uuid4().hex[:12]
        effective_workers = max_workers if max_workers is not None else self.max_workers
        effective_workers = max(1, min(50, effective_workers))

        def _execute_one(test: CandidateTest) -> TestCaseResult:
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
                        and "external evaluator or llm judge required" in scored.rationale.lower()
                    ):
                        scored = self._judge_scorer.score(test, obs)

                trajectory = build_blackbox_trajectory(obs, scored.verdict, scored.rationale)
                return scored.model_copy(update={"trajectory": trajectory})
            except Exception as exc:
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
        if effective_workers <= 1 or len(pack.tests) <= 1:
            for test in pack.tests:
                results.append(_execute_one(test))
        else:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(effective_workers, len(pack.tests))
            ) as pool:
                futures = [pool.submit(_execute_one, test) for test in pack.tests]
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())

        # Preserve canonical test pack ordering for deterministic reports and diffs
        order = {test.id: i for i, test in enumerate(pack.tests)}
        results.sort(key=lambda r: order.get(r.test_id, 0))

        passed = sum(1 for r in results if r.verdict == "PASS")
        failed = sum(1 for r in results if r.verdict == "FAIL")
        unverifiable = sum(1 for r in results if r.verdict == "UNVERIFIABLE")
        return SuiteRunReport(
            agent_id=pack.agent_id,
            run_id=run_id,
            suite_version=pack.version,
            results=results,
            passed=passed,
            failed=failed,
            unverifiable=unverifiable,
        )

    def _invoke(self, test: CandidateTest) -> ObservationBundle:
        payload: dict[str, Any] = {
            "prompt": test.user_prompt,
            "messages": [{"role": "user", "content": test.user_prompt}],
            "history": [],
        }
        start = time.perf_counter()
        try:
            resp = self._client.post(self.endpoint_url, json=payload)
            status = resp.status_code
        except UnsafeURLError as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return ObservationBundle(
                test_id=test.id,
                user_prompt=test.user_prompt,
                response_text=f"SSRF blocked: {e}",
                http_status=0,
                latency_ms=latency_ms,
                raw_json={"error": str(e)},
            )
        except httpx.HTTPError as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return ObservationBundle(
                test_id=test.id,
                user_prompt=test.user_prompt,
                response_text=f"HTTP error: {e}",
                http_status=0,
                latency_ms=latency_ms,
                raw_json={"error": str(e)},
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return ObservationBundle(
                test_id=test.id,
                user_prompt=test.user_prompt,
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
            user_prompt=test.user_prompt,
            response_text=text,
            http_status=status,
            latency_ms=latency_ms,
            raw_json=data if isinstance(data, dict) else {"raw": data},
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
