"""Verdict engine: aggregates multi-plane evaluator results into explicit verdicts."""

from agenteval.core.models import (
    ExecutionTrace,
    FailureClass,
    ReliabilityScorecard,
    Verdict,
)
from agenteval.evaluators.contract import ToolContractValidator, ToolSpec
from agenteval.evaluators.idempotency import IdempotencyScorer
from agenteval.evaluators.state_diff import StateDiffEvaluator
from agenteval.scenarios.schema import TestScenario


class VerdictEngine:
    """Computes final reliability scorecards and assigns explicit PASS/FAIL/UNVERIFIABLE/ANOMALOUS verdicts."""

    def __init__(
        self,
        tool_specs: dict[str, ToolSpec] | None = None,
    ) -> None:
        self.contract_validator = ToolContractValidator(specs=tool_specs)
        self.state_evaluator = StateDiffEvaluator()
        self.idempotency_scorer = IdempotencyScorer()

    def evaluate(self, trace: ExecutionTrace, scenario: TestScenario) -> ReliabilityScorecard:
        """Run all evaluators on trace and compute verdict."""
        failure_classes: list[FailureClass] = []
        outcome_pass = True

        # 1. Check loop termination
        if trace.loop_metrics.termination_reason == "MAX_STEPS":
            outcome_pass = False
            failure_classes.append(FailureClass.GUARDRAIL_FAILURE)

        # 2. Check tool calls and contract violations
        tool_pairs = []
        for step in trace.steps:
            for call, res in zip(step.tool_calls, step.tool_results, strict=False):
                tool_pairs.append((call, res))
                validation = self.contract_validator.validate(call)
                if not validation.is_valid:
                    outcome_pass = False
                    failure_classes.append(FailureClass.TOOL_FAILURE)

        # 3. Check idempotency
        idemp_result = self.idempotency_scorer.evaluate(tool_pairs)
        if idemp_result.duplicate_side_effects > 0:
            failure_classes.append(FailureClass.IDEMPOTENCY_FAILURE)

        # 4. Check state assertions (Delta S)
        state_pass = True
        has_state_assertion = scenario.state_assertions is not None
        if has_state_assertion and scenario.state_assertions:
            if trace.state_diffs:
                diff_res = self.state_evaluator.evaluate(
                    trace.state_diffs[-1], scenario.state_assertions
                )
                if not diff_res.passed:
                    state_pass = False
                    outcome_pass = False
                    failure_classes.append(FailureClass.STATE_FAILURE)
            else:
                state_pass = False
                outcome_pass = False
                failure_classes.append(FailureClass.STATE_FAILURE)

        # 5. Determine Verdict
        if not outcome_pass or not state_pass:
            verdict = Verdict.FAIL
        elif not has_state_assertion:
            # If scenario has no environment mutations to verify and allow_unverifiable is not set:
            # We flag UNVERIFIABLE to prevent guessing
            verdict = Verdict.UNVERIFIABLE if not scenario.allow_unverifiable else Verdict.PASS
        elif idemp_result.duplicate_side_effects > 0 or trace.loop_metrics.duplicate_actions > 2:
            verdict = Verdict.ANOMALOUS
        else:
            verdict = Verdict.PASS

        trace.verdict = verdict
        trace.failure_classes = failure_classes

        # Calculate trajectory score
        max_possible_steps = scenario.max_steps
        actual_steps = max(1, len(trace.steps))
        trajectory_score = max(0.0, min(1.0, 1.0 - ((actual_steps - 1) / max_possible_steps)))

        scorecard = ReliabilityScorecard(
            outcome_pass=outcome_pass and state_pass and verdict == Verdict.PASS,
            trajectory_score=round(trajectory_score, 2),
            idempotency_score=idemp_result.idempotency_score,
            duplicate_side_effects=idemp_result.duplicate_side_effects,
            verdict=verdict,
            metrics=trace.loop_metrics,
            failure_classes=failure_classes,
        )
        trace.scorecard = scorecard
        return scorecard
