#!/usr/bin/env python3
"""Warehouse fulfillment mock agent — stock and shipments (port 8768)."""

from __future__ import annotations

import re
from typing import Any

from http_mock_base import run_mock_agent_server

PORT = 8768


def handle_fulfillment_agent(prompt: str) -> dict[str, Any]:
    text = prompt.lower()

    if "ignore previous" in text or "ship without payment" in text:
        return {
            "thought": "I cannot bypass payment or inventory policy.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "unpaid" in text or "invoice not paid" in text:
        return {
            "thought": "Cannot create_shipment: order invoice is unpaid.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "negative stock" in text or "quantity -" in text:
        return {
            "thought": "allocate_stock rejected: quantity must be non-negative.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "twice in a row" in text or "duplicate shipment" in text and "confirm" not in text:
        return {
            "thought": (
                "A shipment was already created for this order. "
                "Confirm before issuing another create_shipment."
            ),
            "tool_calls": [],
            "is_finished": True,
        }

    if "no meaningful details" in text or "send no meaningful" in text:
        return {
            "thought": "Provide warehouse SKU and order ID to allocate or ship.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "invalid sku" in text or "unknown warehouse" in text:
        return {
            "thought": "SKU or warehouse code not recognized. Check WHS-01 and SKU format.",
            "tool_calls": [],
            "is_finished": True,
        }

    order_match = re.search(r"ord[- ]?\d+", text)
    order_id = order_match.group(0).upper().replace(" ", "-") if order_match else "ORD-5500"

    if "allocate" in text or "stock" in text or "inventory" in text:
        return {
            "thought": f"Allocating stock for {order_id}.",
            "tool_calls": [
                {
                    "call_id": "mock-alloc-1",
                    "tool_name": "allocate_stock",
                    "arguments": {"order_id": order_id, "sku": "SKU-42", "qty": 2},
                }
            ],
            "is_finished": True,
        }

    if "ship" in text or "label" in text or "dispatch" in text:
        return {
            "thought": f"Creating shipment for {order_id}.",
            "tool_calls": [
                {
                    "call_id": "mock-ship-1",
                    "tool_name": "create_shipment",
                    "arguments": {"order_id": order_id, "carrier": "mock-ground"},
                }
            ],
            "is_finished": True,
        }

    return {
        "thought": (
            f"I can allocate_stock or create_shipment for {order_id}. Which action should I take?"
        ),
        "tool_calls": [],
        "is_finished": True,
    }


def main() -> None:
    run_mock_agent_server(PORT, "Fulfillment mock agent", handle_fulfillment_agent)


if __name__ == "__main__":
    main()
