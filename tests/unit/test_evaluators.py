"""Unit tests for Evaluator Suite: ToolContractValidator, StateDiffEvaluator, IdempotencyScorer."""

from agenteval.core.models import StateDiff, ToolCall, ToolResult
from agenteval.evaluators.contract import ParameterSpec, ToolContractValidator, ToolSpec
from agenteval.evaluators.idempotency import IdempotencyScorer
from agenteval.evaluators.state_diff import StateDiffAssertion, StateDiffEvaluator

# -------------------------------------------------------------
# 1. ToolContractValidator Tests
# -------------------------------------------------------------


def test_contract_validator_valid_call() -> None:
    """Test clean parameter validation."""
    spec = ToolSpec(
        tool_name="transfer",
        parameters={
            "account": ParameterSpec(param_type=str, required=True),
            "amount": ParameterSpec(param_type=(int, float), required=True, min_value=0.01),
        },
    )
    validator = ToolContractValidator(specs={"transfer": spec})

    call = ToolCall(
        call_id="c1", tool_name="transfer", arguments={"account": "acc-1", "amount": 50.0}
    )
    result = validator.validate(call)
    assert result.is_valid
    assert len(result.violations) == 0


def test_contract_validator_violations() -> None:
    """Test missing required parameter, wrong type, and min value violation."""
    spec = ToolSpec(
        tool_name="transfer",
        parameters={
            "account": ParameterSpec(param_type=str, required=True),
            "amount": ParameterSpec(param_type=(int, float), required=True, min_value=0.01),
        },
    )
    validator = ToolContractValidator(specs={"transfer": spec})

    # Missing account, negative amount
    call = ToolCall(call_id="c2", tool_name="transfer", arguments={"amount": -10.0})
    result = validator.validate(call)
    assert not result.is_valid
    assert any("Missing required" in v for v in result.violations)
    assert any("below minimum" in v for v in result.violations)


# -------------------------------------------------------------
# 2. StateDiffEvaluator Tests
# -------------------------------------------------------------


def test_state_diff_evaluator_matching_assertion() -> None:
    """Test state diff matching expected files and DB tables."""
    diff = StateDiff(
        pre_snapshot_id="s1",
        post_snapshot_id="s2",
        files_added=["receipt.pdf"],
        files_modified=["db.sqlite"],
        db_mutations=[{"table": "transactions", "status": "MUTATED"}],
    )
    assertion = StateDiffAssertion(
        expected_files_created=["receipt.pdf"],
        expected_db_mutations=["transactions"],
    )
    evaluator = StateDiffEvaluator()
    result = evaluator.evaluate(diff, assertion)
    assert result.passed
    assert not result.unverifiable


def test_state_diff_evaluator_missing_side_effects() -> None:
    """Test state diff failing when expected file was not created."""
    diff = StateDiff(
        pre_snapshot_id="s1",
        post_snapshot_id="s2",
        files_added=[],
    )
    assertion = StateDiffAssertion(
        expected_files_created=["receipt.pdf"],
    )
    evaluator = StateDiffEvaluator()
    result = evaluator.evaluate(diff, assertion)
    assert not result.passed
    assert "receipt.pdf" in result.missing_files


# -------------------------------------------------------------
# 3. IdempotencyScorer Tests
# -------------------------------------------------------------


def test_idempotency_safe_retry() -> None:
    """Test retrying with identical idempotency key does not penalize score."""
    call1 = ToolCall(
        call_id="c1", tool_name="charge", arguments={"amt": 100}, idempotency_key="key-123"
    )
    res1 = ToolResult(call_id="c1", tool_name="charge", is_error=True, error_message="timeout")

    # Retry with same idempotency key
    call2 = ToolCall(
        call_id="c2", tool_name="charge", arguments={"amt": 100}, idempotency_key="key-123"
    )
    res2 = ToolResult(
        call_id="c2", tool_name="charge", output={"status": "paid"}, mutated_state=True
    )

    scorer = IdempotencyScorer()
    scorecard = scorer.evaluate([(call1, res1), (call2, res2)])
    assert scorecard.idempotency_score == 1.0
    assert scorecard.duplicate_side_effects == 0


def test_idempotency_unsafe_retry_creates_duplicate_side_effects() -> None:
    """Test retrying without idempotency key that causes duplicate mutations."""
    # First call failed with timeout, but actually mutated state on server
    call1 = ToolCall(call_id="c1", tool_name="charge", arguments={"amt": 100}, idempotency_key=None)
    res1 = ToolResult(call_id="c1", tool_name="charge", is_error=False, mutated_state=True)

    # Second call without idempotency key executed again
    call2 = ToolCall(call_id="c2", tool_name="charge", arguments={"amt": 100}, idempotency_key=None)
    res2 = ToolResult(call_id="c2", tool_name="charge", is_error=False, mutated_state=True)

    scorer = IdempotencyScorer()
    scorecard = scorer.evaluate([(call1, res1), (call2, res2)])
    assert scorecard.duplicate_side_effects == 1
    assert scorecard.idempotency_score < 1.0
