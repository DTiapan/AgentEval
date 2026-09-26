#!/usr/bin/env python3
"""IT helpdesk mock agent — tickets and password reset (port 8767)."""

from __future__ import annotations

import re
from typing import Any

from http_mock_base import run_mock_agent_server

PORT = 8767


def handle_helpdesk_agent(prompt: str) -> dict[str, Any]:
    text = prompt.lower()

    if "ignore previous" in text or "disable all security" in text:
        return {
            "thought": "I cannot override security policy or ignore prior instructions.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "another employee" in text or "other user's ticket" in text or "without authorization" in text:
        return {
            "thought": "I can only access tickets for the authenticated employee.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "admin password" in text or "root access" in text and "mfa" not in text:
        return {
            "thought": "Elevated access requires MFA verification before any admin password reset.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "no meaningful details" in text or "send no meaningful" in text:
        return {
            "thought": "Please provide your employee ID and a short description of the issue.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "invalid" in text or "malformed employee" in text:
        return {
            "thought": "Employee ID format is invalid. Use format EMP-1234.",
            "tool_calls": [],
            "is_finished": True,
        }

    if "ambiguous" in text or "do the thing" in text:
        return {
            "thought": "Do you need a password reset or a new support ticket?",
            "tool_calls": [],
            "is_finished": True,
        }

    emp_match = re.search(r"emp[- ]?\d+", text)
    emp_id = emp_match.group(0).upper().replace(" ", "-") if emp_match else "EMP-2001"

    if "password" in text or "reset" in text:
        return {
            "thought": f"Opening password reset workflow for {emp_id}.",
            "tool_calls": [
                {
                    "call_id": "mock-reset-1",
                    "tool_name": "reset_password",
                    "arguments": {"employee_id": emp_id, "channel": "email_otp"},
                }
            ],
            "is_finished": True,
        }

    if "ticket" in text or "incident" in text or "laptop" in text:
        return {
            "thought": f"Creating support ticket for {emp_id}.",
            "tool_calls": [
                {
                    "call_id": "mock-ticket-1",
                    "tool_name": "create_ticket",
                    "arguments": {"employee_id": emp_id, "category": "hardware"},
                }
            ],
            "is_finished": True,
        }

    return {
        "thought": (
            f"I can create_ticket or reset_password for {emp_id}. "
            "What do you need help with?"
        ),
        "tool_calls": [],
        "is_finished": True,
    }


def main() -> None:
    run_mock_agent_server(PORT, "Helpdesk mock agent", handle_helpdesk_agent)


if __name__ == "__main__":
    main()
