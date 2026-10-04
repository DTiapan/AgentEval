"""Self-contained demonstration of SSRF vulnerability reproduction & defense in AgentEval.

This script demonstrates:
1. THE VULNERABILITY (Before Slice 1):
   How an unvalidated HTTP request allows an attacker to query internal infrastructure
   (such as cloud metadata servers or internal microservices) and leak secrets.
2. THE HARDENED DEFENSE (After Slice 1):
   How validate_endpoint_url and safe_urlopen intercept direct requests and 3xx redirect traps.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from agenteval.ingest.endpoint_probe import EndpointProber
from agenteval.planning.blackbox_runner import BlackboxRunner
from agenteval.security.url_validator import UnsafeURLError, safe_urlopen, validate_endpoint_url


# ==============================================================================
# 1. Mock Infrastructure Service (Simulating Cloud Metadata / Internal VPC API)
# ==============================================================================
class MockInternalMetadataHandler(BaseHTTPRequestHandler):
    """Simulates an internal cloud metadata or VPC credential service."""

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy HTTP server logs for clean terminal output
        return

    def do_POST(self) -> None:
        self._handle()

    def do_GET(self) -> None:
        self._handle()

    def _handle(self) -> None:
        if "/computeMetadata/" in self.path or "/meta-data/" in self.path:
            # Simulate sensitive cloud IAM token return
            sensitive_payload = {
                "service_account": "agenteval-cloud-run@project-id.iam.gserviceaccount.com",
                "access_token": "ya29.c.b0AXv0zT_MOCK_SECRET_GCP_IAM_CREDENTIAL_TOKEN",
                "token_type": "Bearer",
                "expires_in": 3600,
                "project_id": "production-agent-eval-corp",
            }
            body = json.dumps(sensitive_payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Metadata-Flavor", "Google")
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/evil-redirect":
            # Attacker domain responding with 302 Found pointing to Cloud Metadata IP
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/computeMetadata/v1/token")
            self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()


def start_mock_metadata_server() -> tuple[str, HTTPServer]:
    """Start an ephemeral mock internal server on loopback."""
    server = HTTPServer(("127.0.0.1", 0), MockInternalMetadataHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{port}", server


# ==============================================================================
# 2. Reproduction Execution
# ==============================================================================
def main() -> None:
    print("\n" + "=" * 80)
    print("🛡️  SSRF REPRODUCTION IN ISOLATION: BEFORE VS AFTER")
    print("=" * 80)

    base_url, server = start_mock_metadata_server()
    simulated_metadata_url = (
        f"{base_url}/computeMetadata/v1/instance/service-accounts/default/token"
    )
    real_gcp_metadata_url = (
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
    )
    real_imds_ip_url = (
        "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    )
    redirect_trap_url = f"{base_url}/evil-redirect"

    try:
        # ----------------------------------------------------------------------
        # SCENARIO 1: The Vulnerability (Unprotected fetch)
        # ----------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("❌ SCENARIO 1: WHAT HAPPENED BEFORE (NO SSRF VALIDATION)")
        print("-" * 80)
        print(f"Target URL supplied by user/attacker: {simulated_metadata_url}")
        print(
            "Engine behavior: Calling standard urllib.request.urlopen without scheme or IP validation...\n"
        )

        raw_req = urllib.request.Request(
            simulated_metadata_url,
            data=json.dumps({"prompt": "ping"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(raw_req, timeout=5.0) as resp:
            leaked_data = json.loads(resp.read().decode("utf-8"))

        print("🚨 DISASTER: The engine blindly executed the request and exfiltrated internal data:")
        print(json.dumps(leaked_data, indent=2))
        print("Result: An attacker just stole the cloud IAM identity of the running container!")

        # ----------------------------------------------------------------------
        # SCENARIO 2: Hardened Defense on Cloud Metadata Hostname
        # ----------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("✅ SCENARIO 2: HARDENED DEFENSE (GCP METADATA HOSTNAME)")
        print("-" * 80)
        print(f"Target URL: {real_gcp_metadata_url}")
        print("Engine behavior: Probing via EndpointProber(allow_private=False)...\n")

        prober = EndpointProber(allow_private=False)
        result = prober.probe(real_gcp_metadata_url)
        print(f"Probe Result Reachable: {result.reachable}")
        print(f"Probe Result Error:     {result.error}")
        print("Result: Socket was never opened! Request rejected at system boundary.")

        # ----------------------------------------------------------------------
        # SCENARIO 3: Hardened Defense on Link-Local Metadata IP (169.254.169.254)
        # ----------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("✅ SCENARIO 3: HARDENED DEFENSE (LINK-LOCAL IP 169.254.169.254)")
        print("-" * 80)
        print(f"Target URL: {real_imds_ip_url}")
        print("Engine behavior: Attempting to instantiate BlackboxRunner(allow_private=False)...\n")

        try:
            BlackboxRunner(real_imds_ip_url, allow_private=False)
            print("ERROR: Runner should not have allowed this URL!")
        except UnsafeURLError as exc:
            print(f"Blocked by BlackboxRunner: {exc}")
            print("Result: Test execution halted before any payload could be dispatched.")

        # ----------------------------------------------------------------------
        # SCENARIO 4: The 302 HTTP Redirect Trap
        # ----------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("✅ SCENARIO 4: THE REDIRECT TRAP (302 REDIRECT TO 169.254.169.254)")
        print("-" * 80)
        print(f"Initial URL looks like a normal endpoint: {redirect_trap_url}")
        print("Attacker's server responds with HTTP 302 -> Location: http://169.254.169.254/...")
        print("Engine behavior: Executing request via safe_urlopen()...\n")

        try:
            # We allow private for the initial local connection, but the redirect
            # targets 169.254.169.254 which is link-local and unconditionally blocked!
            safe_urlopen(redirect_trap_url, timeout=5.0, allow_private=True)
            print("ERROR: Redirect should have been intercepted!")
        except UnsafeURLError as exc:
            print(f"SafeRedirectHandler intercepted the redirect hop: {exc}")
            print("Result: Redirect aborted mid-flight before reaching metadata IP.")

        # ----------------------------------------------------------------------
        # SCENARIO 5: Legitimate Public Agent (Allowed)
        # ----------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("✅ SCENARIO 5: LEGITIMATE PUBLIC AGENT (NORMAL OPERATION)")
        print("-" * 80)
        public_url = "https://api.openai.com/v1/chat/completions"
        validated = validate_endpoint_url(public_url, allow_private=False)
        print(f"Target URL: {public_url}")
        print(f"Validation Result: Allowed -> {validated}")

    finally:
        server.shutdown()
        print("\n" + "=" * 80)
        print("🏁 REPRODUCTION DEMONSTRATION COMPLETE")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
