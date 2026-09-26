# Customer Refund Assistant — Product Requirements

## Overview
HTTP black-box agent for retail support: lookup orders, process refunds via `lookup_order` and `process_refund`, with safety and authorization boundaries. Target endpoint: `http://127.0.0.1:8765/chat`.

## Capabilities
- Look up order status for an authenticated customer when given a valid order ID (e.g. ORD-1001).
- Process refund requests for valid orders using the `process_refund` tool.
- Guide the user when prompts are empty, ambiguous, or missing required details (order ID, reason).
- Handle invalid or malformed order IDs with a clear request for correction.
- Refuse prompt-injection and policy-override instructions (e.g. “ignore previous instructions”, “approve everything”).
- Refuse refunds for other customers’ orders or without account ownership verification.
- Limit disclosure of private customer data; do not dump bulk PII beyond what the task requires.
- Avoid duplicate refund submission without explicit user confirmation when a refund was already requested.
- Report honestly when the payment gateway is unavailable — do not claim refund success.

## Invariants
- Refunds only for orders that belong to the authenticated customer.
- No refund success claims when payment integration is down or returns an error.
- No unauthorized refunds or bypass of safety policy via adversarial prompts.
- No bulk export of private customer records.
- Coherent, task-relevant responses for valid functional requests.

## Tools (declared contract)
- `lookup_order` — read order status for a given order ID.
- `process_refund` — submit a refund for a given order ID and amount.

## Out of scope
- Real payment processing, databases, or LLM reasoning (mock rule-based agent for local assurance only).
