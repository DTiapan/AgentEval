import os
import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
auth_header = APIKeyHeader(name="Authorization", auto_error=False)


def get_api_key(
    api_key: Annotated[str | None, Security(api_key_header)] = None,
    bearer_token: Annotated[str | None, Security(auth_header)] = None,
) -> str | None:
    expected_key = os.environ.get("AGENTEVAL_API_KEY", "").strip()

    # If no key is configured in the environment, we bypass auth for backward compatibility
    # and local development ease, unless strictly enforced.
    if not expected_key:
        return None

    token = api_key
    if bearer_token:
        if bearer_token.lower().startswith("bearer "):
            token = bearer_token[7:].strip()
        else:
            token = bearer_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key or Bearer token",
        )

    if not secrets.compare_digest(token, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return token
