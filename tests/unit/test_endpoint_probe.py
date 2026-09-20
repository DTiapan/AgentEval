"""E2: HTTP endpoint probe."""

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from agenteval.ingest.bootstrap import AgentBootstrap
from agenteval.ingest.endpoint_probe import EndpointProber

_REPO = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "refund_agent_server", _REPO / "examples/blackbox/refund_agent_server.py"
)
assert _SPEC and _SPEC.loader
_refund_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_refund_mod)


class _RefundHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        result = _refund_mod.handle_refund_agent(str(body.get("prompt", "")))
        payload = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)


def _ephemeral_refund_url() -> tuple[str, HTTPServer]:
    server = HTTPServer(("127.0.0.1", 0), _RefundHandler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}/", server


def test_probe_reachable_json_shape() -> None:
    url, server = _ephemeral_refund_url()
    try:
        result = EndpointProber(timeout_seconds=5.0).probe(url)
        assert result.reachable
        assert result.http_status == 200
        assert "thought" in result.response_keys
    finally:
        server.shutdown()


def test_bootstrap_from_prd_with_endpoint() -> None:
    url, server = _ephemeral_refund_url()
    prd = _REPO / "examples/blackbox/requirements.md"
    try:
        card, _fp, probe = AgentBootstrap.from_prd(
            prd, agent_id="refund-agent", endpoint_url=url
        )
        assert probe is not None and probe.reachable
        assert card.id == "refund-agent"
    finally:
        server.shutdown()
