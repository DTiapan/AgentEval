"""E2E: sample refund agent + suite init + suite run (MVP backbone)."""

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from agenteval.core.manifest import AgentCard
from agenteval.planning.blackbox_runner import BlackboxRunner
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.suite_store import SuiteStore

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST = _REPO_ROOT / "examples/blackbox/refund_agent.card.yaml"
_SERVER_MOD = importlib.util.spec_from_file_location(
    "refund_agent_server",
    _REPO_ROOT / "examples/blackbox/refund_agent_server.py",
)
assert _SERVER_MOD and _SERVER_MOD.loader
_refund_mod = importlib.util.module_from_spec(_SERVER_MOD)
_SERVER_MOD.loader.exec_module(_refund_mod)


class _RefundHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        prompt = body.get("prompt", "")
        result = _refund_mod.handle_refund_agent(str(prompt))
        payload = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)


def test_blackbox_mvp_init_run(tmp_path: Path) -> None:
    server = HTTPServer(("127.0.0.1", 0), _RefundHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{port}/"

    card = AgentCard.from_yaml(_MANIFEST)
    bootstrap = SuiteBootstrap(max_tests=10)
    fp = "test-fp"
    pool, pack, _ = bootstrap.build(card, fp)
    assert len(pool) > len(pack.tests)

    store = SuiteStore(tmp_path / "suites")
    manifest = SuiteStore.new_manifest(card.id, fp, endpoint)
    store.init_suite(manifest, pool, pack, force=True)

    report = BlackboxRunner(endpoint).run_pack(pack)
    assert report.passed + report.failed + report.unverifiable == len(pack.tests)
    assert report.passed > 0
    assert report.failed == 0, report.results

    server.shutdown()
