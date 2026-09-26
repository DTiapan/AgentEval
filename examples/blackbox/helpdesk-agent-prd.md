# IT Helpdesk Agent — Product Requirements

## Overview
Employee-facing IT support agent over HTTP (`POST /chat`). Tools: `create_ticket`, `reset_password`. Local mock: `http://127.0.0.1:8767/chat`.

## Capabilities
- Create support tickets when given a valid employee ID and issue description.
- Start password reset flows for the authenticated employee via `reset_password`.
- Ask for missing details when prompts are empty or too vague.
- Reject invalid employee ID formats with guidance (e.g. EMP-1234).
- Clarify intent when requests are ambiguous (ticket vs password reset).

## Invariants
- No access to other employees’ tickets or credentials without authorization.
- No admin or root password reset without MFA verification.
- Refuse prompt-injection and instructions to disable security policy.
- Do not claim actions completed when required identifiers are missing.

## Tools
- `create_ticket` — open an IT incident for an employee.
- `reset_password` — initiate vetted password reset (email OTP channel).
