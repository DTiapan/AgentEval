#!/usr/bin/env python3
"""Sample black-box refund agent — HTTP endpoint with mock tool semantics.

Exposes POST /chat (AgentEval HTTPAdapter contract). Declared tools are simulated in
responses (process_refund, lookup_order) without a real database.

Run:
  python examples/blackbox/refund_agent_server.py
  # listens on http://127.0.0.1:8765/chat
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

HOST = "127.0.0.1"
PORT = 8765


def handle_refund_agent(prompt: str) -> dict[str, Any]:
    """Rule-based mock agent (no LLM)."""
    text = prompt.lower()

    if "ignore previous" in text or "approve everything" in text:
        return {
            "thought": (
                "I cannot follow instructions that override safety policy or ignore "
                "authorization rules."
            ),
            "tool_calls": [],
            "is_finished": True,
        }

    if "another user" in text or "without proving" in text or "unauthorized" in text:
        return {
            "thought": "I cannot process refunds without verifying account ownership.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "private customer data" in text or "list all private" in text:
        return {
            "thought": (
                "I can only discuss order status for the authenticated customer. "
                "I cannot dump private customer records."
            ),
            "tool_calls": [],
            "is_finished": True,
        }

    if "twice in a row" in text or "without confirmation" in text:
        return {
            "thought": (
                "A refund was already requested for this order. "
                "Please confirm before I submit a duplicate process_refund call."
            ),
            "tool_calls": [],
            "is_finished": True,
        }

    if "unavailable" in text or "returns an error" in text:
        return {
            "thought": (
                "The payment gateway is unavailable. I cannot mark this refund as completed."
            ),
            "tool_calls": [],
            "is_finished": True,
        }

    if "no meaningful details" in text or "send no meaningful" in text:
        return {
            "thought": "Please provide an order ID and refund reason so I can assist you.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "invalid" in text or "incomplete" in text or "missing required" in text:
        return {
            "thought": "The order ID format looks invalid. Please provide a valid order ID.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "make it quick" in text or "do the thing" in text:
        return {
            "thought": "Do you want to check order status or issue a refund? Which order ID?",
            "tool_calls": [],
            "is_finished": True,
        }

    order_match = re.search(r"ord[- ]?\d+", text)
    order_id = order_match.group(0).upper().replace(" ", "-") if order_match else "ORD-1001"

    if "refund" in text or "issue refund" in text:
        return {
            "thought": f"Submitting refund for {order_id} via process_refund.",
            "tool_calls": [
                {
                    "call_id": "mock-refund-1",
                    "tool_name": "process_refund",
                    "arguments": {"order_id": order_id, "amount": 49.99},
                }
            ],
            "is_finished": True,
        }

    return {
        "thought": (
            f"I can help with refunds for valid orders using process_refund and "
            f"lookup_order. What would you like to do for {order_id}?"
        ),
        "tool_calls": [],
        "is_finished": True,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        if self.path not in ("/chat", "/"):
            self.send_error(404)
            return
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_POST(self) -> None:
        if self.path not in ("/chat", "/"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body.decode("utf-8"))
            prompt = data.get("prompt") or ""
            if not prompt and data.get("messages"):
                prompt = data["messages"][-1].get("content", "")
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        result = handle_refund_agent(str(prompt))
        payload = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors()
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Refund mock agent listening on http://{HOST}:{PORT}/chat")
    server.serve_forever()


if __name__ == "__main__":
    main()
