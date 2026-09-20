/** Canonical marketing + demo copy (see docs/design/STITCH_PROMPTS.md). */

export const PRODUCT_DOMAIN = "agenteval.app";
export const MARKETING_ORIGIN = `https://${PRODUCT_DOMAIN}`;
export const APP_ORIGIN = `https://app.${PRODUCT_DOMAIN}`;

export const DEMO_AGENT_ID = "demo-refund-agent";
export const REFUND_CEILING_USD = 100;
export const BREACH_AMOUNT_USD = 250;
export const FROZEN_TEST_PACK_SIZE = 8;
export const CANDIDATE_POOL_HINT = 38;

export const DEMO_STAGING_ENDPOINT = "https://staging.acme.com/v1/chat";
/** Local black-box agent from examples/blackbox (Studio probe / assurance runs). */
export const LOCAL_AGENT_ENDPOINT = "http://127.0.0.1:8765/chat";

export function formatUsd(amount: number): string {
  return `$${amount.toFixed(2)}`;
}

export const CEILING_BREACH_EXCESS_USD = BREACH_AMOUNT_USD - REFUND_CEILING_USD;

export function refundAgentPrdMarkdown(): string {
  const ceiling = formatUsd(REFUND_CEILING_USD);
  const breach = formatUsd(BREACH_AMOUNT_USD);
  return `# Customer Support & Refund Agent Specification

## 1. Overview
The Refund Agent processes retail customer refund requests, checks order status, and coordinates with payment processors.

## 2. Capabilities
- Process customer refund requests within the ${ceiling} ceiling.
- Lookup order status and delivery tracking.
- Verify customer identity and purchase receipts.

## 3. Invariants & Security
- Never issue refunds exceeding ${ceiling} without human manager authorization.
- Reject adversarial prompts attempting a ${breach} refund (ceiling breach scenario).
- Reject SQL injection and prompt injection attempts to bypass limits.
- Never expose internal database IDs or credentials in customer responses.`;
}
