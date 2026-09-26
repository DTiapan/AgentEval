/** Canonical marketing + demo copy (see docs/design/STITCH_PROMPTS.md). */

export const PRODUCT_DOMAIN = "agenteval.app";
export const MARKETING_ORIGIN = `https://${PRODUCT_DOMAIN}`;
export const APP_ORIGIN = `https://app.${PRODUCT_DOMAIN}`;

/** Illustrative ceiling amounts for marketing copy only (not console run data). */
export const REFUND_CEILING_USD = 100;
export const BREACH_AMOUNT_USD = 250;
export const CANDIDATE_POOL_HINT = 38;

export function formatUsd(amount: number): string {
  return `$${amount.toFixed(2)}`;
}

export const CEILING_BREACH_EXCESS_USD = BREACH_AMOUNT_USD - REFUND_CEILING_USD;
