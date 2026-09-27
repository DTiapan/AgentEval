import os
from pathlib import Path
import re


def load_env() -> None:
    """Minimal .env loader for AgentEval: reads .env files without external dependencies."""
    candidates = (
        Path.cwd() / ".env",
        Path.cwd() / "examples" / "real-agent" / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[2] / "examples" / "real-agent" / ".env",
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ and val:
                os.environ[key] = val


def slugify(text: str) -> str:
    """Convert arbitrary string into a clean URL/file-safe slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return cleaned or "default"
