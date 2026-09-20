"""Sample production-style order processing agent.

Demonstrates:
1. Idempotency key usage when executing state-mutating financial calls.
2. Resilient retry handling when tools fail or time out.
3. Writing persistent audit artifacts to the sandbox environment.
"""

from typing import Any

from agenteval.core.models import StepRecord, ToolCall


def charge_payment(
    order_id: str,
    amount: float,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Custom financial charge tool."""
    return {
        "status": "APPROVED",
        "order_id": order_id,
        "amount": amount,
        "idempotency_key": idempotency_key,
        "transaction_id": f"tx-{order_id}",
    }


# Export tools for automatic CLI discovery
TOOLS = {
    "charge_payment": charge_payment,
}


def run_agent(
    prompt: str,
    history: list[StepRecord],
) -> tuple[str | None, list[ToolCall], bool]:
    """Agent loop handler for order processing workflow."""
    order_id = "ORD-90210"
    idempotency_key = f"idem-key-{order_id}"

    # Step 1: Initialize payment
    if not history:
        return (
            "Initiating payment charge with idempotency key",
            [
                ToolCall(
                    call_id="call-charge-1",
                    tool_name="charge_payment",
                    arguments={"order_id": order_id, "amount": 150.00},
                    idempotency_key=idempotency_key,
                )
            ],
            False,
        )

    last_step = history[-1]
    last_results = last_step.tool_results

    # Check if last tool was payment
    payment_result = next((r for r in last_results if r.tool_name == "charge_payment"), None)
    if payment_result:
        if payment_result.is_error:
            # Step 2 (if failed): Resilient retry with SAME idempotency key
            return (
                f"Payment failed with '{payment_result.error_message}'. Retrying with same idempotency key.",
                [
                    ToolCall(
                        call_id=f"call-charge-retry-{len(history)}",
                        tool_name="charge_payment",
                        arguments={"order_id": order_id, "amount": 150.00},
                        idempotency_key=idempotency_key,
                    )
                ],
                False,
            )
        else:
            # Step 2/3: Payment succeeded, write sealed order record
            return (
                "Payment approved. Generating sealed order record.",
                [
                    ToolCall(
                        call_id="call-write-order",
                        tool_name="write_file",
                        arguments={
                            "filename": f"orders/{order_id}.json",
                            "content": f'{{"order_id": "{order_id}", "status": "COMPLETED", "amount": 150.00}}',
                        },
                    )
                ],
                False,
            )

    # Check if order record was written
    write_result = next((r for r in last_results if r.tool_name == "write_file"), None)
    if write_result and not write_result.is_error:
        return ("Order successfully processed and sealed to storage.", [], True)

    return ("Order processing completed.", [], True)
