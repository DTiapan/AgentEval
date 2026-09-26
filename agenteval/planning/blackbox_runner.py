"""Execute a frozen test pack against an HTTP endpoint (blackbox profile)."""

import json
import time
import urllib.error
import urllib.request
from typing import Any
from uuid import uuid4

from agenteval.planning.execution_trace import build_blackbox_trajectory
from agenteval.planning.models import (
    CandidateTest,
    ObservationBundle,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)
from agenteval.planning.observable_scorer import ObservableScorer


class BlackboxRunner:
    """POST each test prompt to the agent endpoint; score with ObservableScorer."""

    def __init__(
        self,
        endpoint_url: str,
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout_seconds = timeout_seconds
        self._scorer = ObservableScorer()

    def run_pack(self, pack: TestPack) -> SuiteRunReport:
        run_id = uuid4().hex[:12]
        results: list[TestCaseResult] = []
        for test in pack.tests:
            obs = self._invoke(test)
            scored = self._scorer.score(test, obs)
            trajectory = build_blackbox_trajectory(obs, scored.verdict, scored.rationale)
            results.append(scored.model_copy(update={"trajectory": trajectory}))

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
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=body,
            headers=self.headers,
            method="POST",
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                status = resp.getcode()
                raw_bytes = resp.read()
        except urllib.error.HTTPError as e:
            status = e.code
            raw_bytes = e.read()
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return ObservationBundle(
                test_id=test.id,
                user_prompt=test.user_prompt,
                response_text=f"HTTP error: {e}",
                http_status=0,
                latency_ms=latency_ms,
                raw_json={},
            )

        latency_ms = (time.perf_counter() - start) * 1000
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            data = {"response": raw_bytes.decode("utf-8", errors="replace")}

        text = self._extract_text(data)
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
        if "thought" in data:
            parts = [str(data.get("thought", ""))]
            tools = data.get("tool_calls") or []
            for t in tools:
                parts.append(f"[tool:{t.get('tool_name', t.get('name', '?'))}]")
            return " ".join(p for p in parts if p).strip()
        for key in ("reply", "output", "response", "message"):
            if key in data and str(data[key]).strip():
                return str(data[key])
        return json.dumps(data)
