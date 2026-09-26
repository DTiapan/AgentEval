"""Shared stdlib HTTP server for black-box sample agents (POST /chat, CORS)."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable

HOST = "127.0.0.1"

HandleFn = Callable[[str], dict[str, Any]]


def run_mock_agent_server(port: int, service_label: str, handle: HandleFn) -> None:
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

            result = handle(str(prompt))
            payload = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self._send_cors()
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer((HOST, port), Handler)
    print(f"{service_label} listening on http://{HOST}:{port}/chat")
    server.serve_forever()


def extract_prompt(data: dict[str, Any]) -> str:
    prompt = data.get("prompt") or ""
    if not prompt and data.get("messages"):
        prompt = data["messages"][-1].get("content", "")
    return str(prompt)
