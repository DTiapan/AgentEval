"""Standalone HTML assurance report (B8) aligned with Web Console (DR-017).

Self-contained HTML: Inter / JetBrains Mono, oklch light+dark tokens matching
``web/src/styles.css``, Assurance KPI strip, Studio-style coverage axes, and
honest gap/limitation blocks from engine ``CoverageReport`` only.
"""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from typing import Any

from agenteval.planning.models import CandidateTest, SuiteManifest, SuiteRunReport, TestPack
from agenteval.services.requirement_run_status import AssuranceSignoffContext


class HTMLReportGenerator:
    """Render a self-contained, interactive HTML report from a SuiteRunReport and TestPack."""

    @staticmethod
    def _format_test_label(test_def: CandidateTest | None, test_id: str, index: int) -> str:
        """Match ``web/src/lib/format-test-label.ts`` for console parity."""
        ordinal = f"{index + 1:02d}"
        tier_pfx = (
            f"[{test_def.priority_tier.value}] " if (test_def and test_def.priority_tier) else ""
        )
        if test_def is None:
            return f"[{ordinal}] {test_id}"
        persona = (test_def.persona_id or "persona").replace("-", " ")
        category = test_def.category or "test"
        failure_mode = test_def.failure_mode or ""
        mode = (
            failure_mode.replace("_", " ")
            if failure_mode and failure_mode != "hypothesis"
            else None
        )
        if (
            test_def.name
            and len(test_def.name) <= 32
            and not test_def.name.startswith("core-agent")
        ):
            return f"{tier_pfx}[{ordinal}] {test_def.name}"
        tail = f"{category} · {mode}" if mode else category
        return f"{tier_pfx}[{ordinal}] {persona} · {tail}"

    @staticmethod
    def _p95_latency(latencies: list[float]) -> float:
        if not latencies:
            return 0.0
        ordered = sorted(latencies)
        idx = max(0, int(round(0.95 * (len(ordered) - 1))))
        return round(ordered[idx], 1)

    @classmethod
    def generate(
        cls,
        report: SuiteRunReport,
        pack: TestPack,
        manifest: SuiteManifest | None = None,
        title: str | None = None,
        *,
        embed: bool = False,
        theme: str = "auto",
        signoff: AssuranceSignoffContext | None = None,
    ) -> str:
        report_title = title or f"AgentEval Report — {report.agent_id} (v{report.suite_version})"
        now_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Map tests by ID
        pack_tests_by_id = {t.id: t for t in pack.tests}

        # Build merged test items for UI
        merged_tests: list[dict[str, Any]] = []
        total_latency_ms = 0.0
        latency_count = 0

        diff = report.run_diff or {}
        regressions_set = set(diff.get("regressions") or [])
        fixes_set = set(diff.get("fixes") or [])

        latencies: list[float] = []
        for index, res in enumerate(report.results):
            test_def = pack_tests_by_id.get(res.test_id)
            lat = res.observation.latency_ms
            if lat > 0:
                total_latency_ms += lat
                latency_count += 1
                latencies.append(lat)

            is_regression = res.test_id in regressions_set
            is_fix = res.test_id in fixes_set

            cat_val = "general"
            if test_def:
                cat_val = (
                    test_def.category.value
                    if hasattr(test_def.category, "value")
                    else str(test_def.category)
                )

            tier_val = (
                test_def.priority_tier.value if (test_def and test_def.priority_tier) else "P1"
            )
            merged_tests.append(
                {
                    "test_id": res.test_id,
                    "tab_label": cls._format_test_label(test_def, res.test_id, index),
                    "title": test_def.name if test_def else res.test_id,
                    "priority_tier": tier_val,
                    "category": cat_val,
                    "capability_id": test_def.capability_id if test_def else "unknown",
                    "persona_slug": test_def.persona_id if test_def else "default",
                    "input_prompt": test_def.user_prompt
                    if test_def
                    else res.observation.user_prompt,
                    "expected_behavior": test_def.expected_behavior if test_def else "",
                    "coverage_tags": test_def.coverage_tags if test_def else [],
                    "rationale": res.rationale or (test_def.rationale if test_def else ""),
                    "verdict": res.verdict,
                    "http_status": res.observation.http_status,
                    "latency_ms": round(res.observation.latency_ms, 1),
                    "response_text": res.observation.response_text,
                    "raw_json": res.observation.raw_json,
                    "is_regression": is_regression,
                    "is_fix": is_fix,
                }
            )

        avg_latency = round(total_latency_ms / latency_count, 1) if latency_count > 0 else 0.0
        p95_latency = cls._p95_latency(latencies)
        total_tests = len(report.results)
        pass_rate = round((report.passed / total_tests) * 100, 1) if total_tests > 0 else 0.0
        pack_test_count = len(pack.tests)

        tier_counts = {"P0": 0, "P1": 0, "P2": 0}
        tier_passes = {"P0": 0, "P1": 0, "P2": 0}
        for item in merged_tests:
            pt = str(item.get("priority_tier") or "P1")
            tier_counts[pt] = tier_counts.get(pt, 0) + 1
            if item.get("verdict") == "PASS":
                tier_passes[pt] = tier_passes.get(pt, 0) + 1

        tier_summary = {
            t: {
                "total": tier_counts.get(t, 0),
                "passed": tier_passes.get(t, 0),
                "pass_rate": round((tier_passes.get(t, 0) / tier_counts[t]) * 100, 1)
                if tier_counts.get(t, 0) > 0
                else 0.0,
            }
            for t in ("P0", "P1", "P2")
        }

        # JSON data payload for embedded viewer script
        embedded_data = {
            "agent_id": report.agent_id,
            "run_id": report.run_id,
            "suite_version": report.suite_version,
            "generated_at": now_utc,
            "passed": report.passed,
            "failed": report.failed,
            "unverifiable": report.unverifiable,
            "total": total_tests,
            "pass_rate": pass_rate,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "pack_test_count": pack_test_count,
            "diff": diff,
            "coverage": report.coverage_report.model_dump() if report.coverage_report else None,
            "tests": merged_tests,
            "tier_summary": tier_summary,
            "signoff": signoff.model_dump() if signoff is not None else None,
        }

        embedded_json = json.dumps(embedded_data, ensure_ascii=False).replace("<", "\\u003c")

        return cls._render_template(
            report_title,
            embedded_json,
            embedded_data,
            embed=embed,
            theme=theme,
        )

    @classmethod
    def _render_template(
        cls,
        title: str,
        embedded_json: str,
        data: dict[str, Any],
        *,
        embed: bool = False,
        theme: str = "auto",
    ) -> str:
        theme_key = theme if theme in {"light", "dark", "auto"} else "auto"
        html_class = "dark" if theme_key == "dark" else ("light" if theme_key == "light" else "")
        data_embed = "1" if embed else "0"
        safe_title = html.escape(title)
        agent_id = html.escape(str(data.get("agent_id", "")))
        run_id = html.escape(str(data.get("run_id", "")))
        suite_version = html.escape(str(data.get("suite_version", 1)))
        passed = data.get("passed", 0)
        failed = data.get("failed", 0)
        unverifiable = data.get("unverifiable", 0)
        total = data.get("total", 0)
        pass_rate = data.get("pass_rate", 0.0)
        avg_latency = data.get("avg_latency_ms", 0.0)
        p95_latency = data.get("p95_latency_ms", 0.0)
        pack_test_count = data.get("pack_test_count", total)
        generated_at = html.escape(str(data.get("generated_at", "")))
        pass_rate_class = (
            "kpi-good" if pass_rate >= 80 else ("kpi-warn" if pass_rate >= 50 else "kpi-bad")
        )

        diff = data.get("diff") or {}
        regressions = diff.get("regressions") or []
        fixes = diff.get("fixes") or []
        has_diff = bool(regressions or fixes or diff.get("prior_run_id"))

        cov = data.get("coverage") or {}
        covered_tags = cov.get("covered_tags") or []
        uncovered_tags = cov.get("uncovered_tags") or []
        critical_uncovered = cov.get("critical_uncovered") or []
        metadata = cov.get("metadata") or {}
        limitations = metadata.get("limitations") or []

        tier_summary = data.get("tier_summary") or {}
        p0_info = tier_summary.get("P0", {"total": 0, "passed": 0, "pass_rate": 0.0})
        p1_info = tier_summary.get("P1", {"total": 0, "passed": 0, "pass_rate": 0.0})
        p2_info = tier_summary.get("P2", {"total": 0, "passed": 0, "pass_rate": 0.0})

        signoff = data.get("signoff") or {}
        signoff_reqs = signoff.get("requirements") or []
        signoff_controls = signoff.get("controls") or []
        signoff_html = ""
        if signoff_reqs or signoff_controls:
            req_rows = "".join(
                f"<tr><td><code>{html.escape(str(r.get('stable_id', '')))}</code></td>"
                f"<td>{html.escape(str(r.get('statement', '')))}</td>"
                f"<td><span class='tag-pill'>{html.escape(str(r.get('status', '')))}</span></td></tr>"
                for r in signoff_reqs
            )
            ctrl_rows = "".join(
                f"<tr><td><code>{html.escape(str(c.get('control_key', '')))}</code></td>"
                f"<td>{html.escape(str(c.get('title', '')))}</td>"
                f"<td><span class='tag-pill'>{html.escape(str(c.get('status', '')))}</span></td></tr>"
                for c in signoff_controls
            )
            signoff_html = f"""
    <div class="surface-card" style="margin-bottom: 1.25rem;">
      <h3 style="margin: 0 0 0.75rem 0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em;">Requirements sign-off (engine)</h3>
      <table class="detail-table"><thead><tr><th>ID</th><th>Requirement</th><th>Status</th></tr></thead><tbody>{req_rows}</tbody></table>
      <h3 style="margin: 1.25rem 0 0.75rem 0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em;">Compliance controls (packs)</h3>
      <table class="detail-table"><thead><tr><th>Control</th><th>Title</th><th>Status</th></tr></thead><tbody>{ctrl_rows}</tbody></table>
    </div>"""

        # Precompute sub-blocks
        diff_banner_html = ""
        if has_diff:
            diff_title = "⚠️ Regressions Detected" if regressions else "✅ Regression Check Clean"
            reg_chip = (
                f'<span class="diff-chip chip-reg">{len(regressions)} Regressions</span>'
                if regressions
                else ""
            )
            fix_chip = (
                f'<span class="diff-chip chip-fix">{len(fixes)} Fixes</span>' if fixes else ""
            )
            stable_chip = (
                f'<span class="diff-chip">{len(diff.get("stable_pass", []))} Stable Passed</span>'
            )
            prior_id = html.escape(str(diff.get("prior_run_id", "baseline")))
            diff_class = (
                "surface-card diff-banner has-regression"
                if regressions
                else "surface-card diff-banner"
            )
            diff_banner_html = f"""
            <div class="{diff_class}">
              <div>
                <div class="diff-title"><span>{diff_title}</span></div>
                <div style="font-size: 12px; color: var(--muted-foreground); margin-top: 4px;">
                  Compared to prior run: <code class="meta-val">{prior_id}</code>
                </div>
              </div>
              <div class="diff-chips">
                {reg_chip}
                {fix_chip}
                {stable_chip}
              </div>
            </div>
            """

        reg_filter_btn = ""
        if regressions:
            reg_filter_btn = f'<button class="filter-btn" onclick="setFilter(\'regression\', this)" style="color: var(--color-fail);">Regressions ({len(regressions)})</button>'

        covered_pills = (
            "".join(f'<span class="tag-pill">{html.escape(c)}</span>' for c in covered_tags)
            or '<span style="color: var(--text-faint);">None</span>'
        )
        uncovered_pills = (
            "".join(
                f'<span class="tag-pill warn">{html.escape(c)}</span>'
                for c in (critical_uncovered or uncovered_tags)
            )
            or '<span style="color: var(--pass);">100% Tags Covered</span>'
        )
        gap_count = len(critical_uncovered or uncovered_tags)
        gap_callout_html = ""
        if critical_uncovered:
            gap_callout_html = (
                "<div class='gap-callout'><strong>Critical uncovered:</strong> "
                f"{html.escape(', '.join(critical_uncovered))}</div>"
            )
        limitations_items = (
            "".join(f"<li>{html.escape(item)}</li>" for item in limitations)
            or "<li>Endpoint-level observations only; internal state mutations not asserted without dedicated probes.</li>"
        )

        return f"""<!DOCTYPE html>
<html lang="en" class="{html_class}" data-embed="{data_embed}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --background: oklch(0.9816 0.0017 247.8390);
      --foreground: oklch(0.3017 0.0073 274.7266);
      --card: oklch(1 0 0);
      --card-foreground: oklch(0.3017 0.0073 274.7266);
      --muted: oklch(0.9109 0.0070 247.9014);
      --muted-foreground: oklch(0.5575 0.0165 244.8933);
      --primary: oklch(0.5547 0.2503 297.0156);
      --border: oklch(0.7692 0.0145 248.0166);
      --destructive: oklch(0.5505 0.2155 19.8095);
      --pass: oklch(0.6250 0.1772 140.4448);
      --warn: oklch(0.6920 0.2041 42.4293);
      --font-sans: 'Inter', system-ui, sans-serif;
      --font-mono: 'JetBrains Mono', ui-monospace, monospace;
      --radius: 0.35rem;
    }}

    html.dark {{
        --background: oklch(0.2223 0.0060 271.1393);
        --foreground: oklch(0.9417 0.0052 247.8790);
        --card: oklch(0.2696 0.0093 276.7573);
        --card-foreground: oklch(0.9417 0.0052 247.8790);
        --muted: oklch(0.3479 0.0112 264.4193);
        --muted-foreground: oklch(0.6595 0.0063 264.5196);
        --primary: oklch(0.7871 0.1187 304.7693);
        --border: oklch(0.3479 0.0112 264.4193);
        --destructive: oklch(0.7556 0.1297 2.7642);
        --pass: oklch(0.8577 0.1092 142.7153);
        --warn: oklch(0.8237 0.1015 52.6294);
    }}

    @media (prefers-color-scheme: dark) {{
      html:not(.light) {{
        --background: oklch(0.2223 0.0060 271.1393);
        --foreground: oklch(0.9417 0.0052 247.8790);
        --card: oklch(0.2696 0.0093 276.7573);
        --card-foreground: oklch(0.9417 0.0052 247.8790);
        --muted: oklch(0.3479 0.0112 264.4193);
        --muted-foreground: oklch(0.6595 0.0063 264.5196);
        --primary: oklch(0.7871 0.1187 304.7693);
        --border: oklch(0.3479 0.0112 264.4193);
        --destructive: oklch(0.7556 0.1297 2.7642);
        --pass: oklch(0.8577 0.1092 142.7153);
        --warn: oklch(0.8237 0.1015 52.6294);
      }}
    }}

    html[data-embed="1"] body {{
      background: transparent;
      padding: 0 0 1rem;
      min-height: 100%;
    }}

    html[data-embed="1"] .surface-card {{
      box-shadow: none;
    }}

    html[data-embed="1"] .container {{
      max-width: none;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background-color: var(--background);
      color: var(--foreground);
      font-family: var(--font-sans);
      letter-spacing: -0.011em;
      line-height: 1.5;
      padding: 24px;
      -webkit-font-smoothing: antialiased;
    }}

    .container {{
      max-width: 80rem;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }}

    .surface-card {{
      background: var(--card);
      color: var(--card-foreground);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1rem;
    }}

    header.surface-card {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 1rem;
    }}

    .brand-row {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }}

    .brand-badge {{
      background: var(--muted);
      color: var(--foreground);
      font-weight: 600;
      font-size: 11px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 0.2rem 0.5rem;
      border-radius: var(--radius);
      font-family: var(--font-mono);
    }}

    h1 {{
      font-size: 1.125rem;
      font-weight: 600;
    }}

    .metadata-line {{
      font-size: 12px;
      color: var(--muted-foreground);
      margin-top: 0.35rem;
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }}

    .meta-val {{ font-family: var(--font-mono); color: var(--foreground); }}

    .header-actions {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}

    .btn {{
      background: var(--card);
      color: var(--foreground);
      border: 1px solid var(--border);
      padding: 0.45rem 0.75rem;
      border-radius: var(--radius);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
    }}

    .btn:hover {{ background: var(--muted); }}

    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.75rem;
    }}

    @media (min-width: 640px) {{
      .kpi-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    }}

    @media (min-width: 1024px) {{
      .kpi-grid {{ grid-template-columns: repeat(5, minmax(0, 1fr)); }}
    }}

    .kpi-card {{ padding: 1rem; }}

    .kpi-label {{
      font-size: 11px;
      font-weight: 600;
      color: var(--muted-foreground);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .kpi-value {{
      margin-top: 0.35rem;
      font-size: 1.5rem;
      font-weight: 700;
      font-family: var(--font-mono);
      line-height: 1.1;
    }}

    .kpi-sub {{
      font-size: 11px;
      color: var(--muted-foreground);
      margin-top: 0.15rem;
      font-family: var(--font-mono);
    }}

    .kpi-good {{ color: var(--pass); }}
    .kpi-bad {{ color: var(--destructive); }}
    .kpi-warn {{ color: var(--warn); }}

    .diff-banner {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      flex-wrap: wrap;
    }}

    .diff-banner.has-regression {{
      border-color: color-mix(in oklch, var(--destructive) 40%, var(--border));
      background: color-mix(in oklch, var(--destructive) 8%, var(--card));
    }}

    .diff-title {{ font-size: 14px; font-weight: 600; }}

    .diff-chips {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .diff-chip {{
      font-size: 12px;
      padding: 3px 8px;
      border-radius: 4px;
      font-weight: 600;
      font-family: var(--font-mono);
    }}

    .chip-reg {{
      color: var(--destructive);
      border: 1px solid color-mix(in oklch, var(--destructive) 50%, var(--border));
      background: color-mix(in oklch, var(--destructive) 12%, var(--card));
    }}
    .chip-fix {{
      color: var(--pass);
      border: 1px solid color-mix(in oklch, var(--pass) 50%, var(--border));
      background: color-mix(in oklch, var(--pass) 12%, var(--card));
    }}

    .collapsible-box {{ overflow: hidden; padding: 0; }}

    .collapsible-header {{
      padding: 0.75rem 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      font-weight: 600;
      font-size: 13px;
      background: color-mix(in oklch, var(--muted) 35%, var(--card));
      user-select: none;
    }}

    .collapsible-body {{
      padding: 1rem;
      border-top: 1px solid var(--border);
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1rem;
      font-size: 13px;
    }}

    .axis-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.65rem;
      grid-column: 1 / -1;
    }}

    .axis-card {{
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 0.55rem 0.65rem;
      background: var(--card);
    }}

    .axis-row {{
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: var(--muted-foreground);
      margin-bottom: 0.35rem;
    }}

    .axis-bar {{
      height: 6px;
      border-radius: 999px;
      background: var(--muted);
      overflow: hidden;
    }}

    .axis-fill {{
      height: 100%;
      background: var(--primary);
      border-radius: 999px;
    }}

    .gap-callout {{
      grid-column: 1 / -1;
      border: 1px solid color-mix(in oklch, var(--warn) 45%, var(--border));
      background: color-mix(in oklch, var(--warn) 10%, var(--card));
      border-radius: var(--radius);
      padding: 0.65rem 0.75rem;
      font-size: 12px;
    }}

    .cov-column h4 {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted-foreground);
      margin-bottom: 0.5rem;
      font-weight: 600;
    }}

    .tag-list {{ display: flex; flex-wrap: wrap; gap: 6px; }}

    .tag-pill {{
      background: var(--muted);
      color: var(--foreground);
      padding: 0.15rem 0.45rem;
      border-radius: var(--radius);
      font-size: 11px;
      font-family: var(--font-mono);
      border: 1px solid var(--border);
    }}

    .tag-pill.warn {{
      border-color: color-mix(in oklch, var(--warn) 50%, var(--border));
      color: var(--warn);
    }}

    .toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
      padding: 0.75rem 1rem;
    }}

    .filter-group {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .filter-btn {{
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--muted-foreground);
      padding: 0.35rem 0.65rem;
      border-radius: var(--radius);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }}

    .filter-btn.active {{
      color: var(--foreground);
      border-color: var(--primary);
    }}

    .search-input {{
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--foreground);
      padding: 0.35rem 0.65rem;
      border-radius: var(--radius);
      font-size: 12px;
      width: 240px;
    }}

    .search-input:focus {{ outline: 2px solid color-mix(in oklch, var(--primary) 40%, transparent); }}

    .test-list {{
      display: flex;
      flex-direction: column;
      gap: 0.65rem;
      padding: 0 1rem 1rem;
    }}

    .test-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }}

    .test-card-header {{
      padding: 12px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      user-select: none;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .test-left {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1;
      min-width: 240px;
    }}

    .status-badge {{
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      font-family: var(--font-mono);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .test-title {{
      font-weight: 600;
      font-size: 13px;
      font-family: var(--font-mono);
    }}

    .test-id {{
      color: var(--muted-foreground);
      font-family: var(--font-mono);
      font-size: 11px;
    }}

    .test-right {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 12px;
      color: var(--muted-foreground);
      flex-wrap: wrap;
    }}

    .metric-badge {{
      font-family: var(--font-mono);
      font-size: 11px;
      background: var(--muted);
      padding: 0.1rem 0.4rem;
      border-radius: var(--radius);
    }}

    .test-card-body {{
      padding: 1rem;
      border-top: 1px solid var(--border);
      background: color-mix(in oklch, var(--muted) 25%, var(--card));
      display: none;
    }}

    .test-card.open .test-card-body {{
      display: block;
    }}

    .detail-section {{
      margin-bottom: 14px;
    }}

    .detail-label {{
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted-foreground);
      margin-bottom: 0.35rem;
    }}

    .detail-content {{
      font-size: 13px;
      background: var(--card);
      padding: 0.65rem 0.85rem;
      border-radius: var(--radius);
      border: 1px solid var(--border);
    }}

    .code-block {{
      font-family: var(--font-mono);
      font-size: 12px;
      white-space: pre-wrap;
      word-break: break-word;
      background: var(--card);
      padding: 0.75rem;
      border-radius: var(--radius);
      border: 1px solid var(--border);
      max-height: 280px;
      overflow-y: auto;
    }}

    .badge-pass {{
      color: var(--pass);
      border: 1px solid color-mix(in oklch, var(--pass) 50%, var(--border));
      background: color-mix(in oklch, var(--pass) 12%, var(--card));
    }}
    .badge-fail {{
      color: var(--destructive);
      border: 1px solid color-mix(in oklch, var(--destructive) 50%, var(--border));
      background: color-mix(in oklch, var(--destructive) 12%, var(--card));
    }}
    .badge-unverifiable {{
      color: var(--warn);
      border: 1px solid color-mix(in oklch, var(--warn) 50%, var(--border));
      background: color-mix(in oklch, var(--warn) 12%, var(--card));
    }}

    .empty-state {{
      text-align: center;
      padding: 2.5rem 1rem;
      color: var(--muted-foreground);
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header class="surface-card">
      <div>
        <div class="brand-row">
          <span class="brand-badge">Assurance Report</span>
          <h1>{safe_title}</h1>
        </div>
        <div class="metadata-line">
          <span>Agent <span class="meta-val">{agent_id}</span></span>
          <span>Suite <span class="meta-val">v{suite_version}</span></span>
          <span>Run <span class="meta-val">{run_id}</span></span>
          <span>{generated_at}</span>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn" type="button" onclick="window.print()">Print / PDF</button>
        <button class="btn" type="button" onclick="toggleAllCards()">Toggle All</button>
      </div>
    </header>

    <div class="kpi-grid">
      <div class="surface-card kpi-card">
        <div class="kpi-label">Pass Rate</div>
        <div class="kpi-value {pass_rate_class}">{pass_rate}%</div>
        <div class="kpi-sub">{passed}/{total} executed</div>
      </div>
      <div class="surface-card kpi-card">
        <div class="kpi-label">Pack Tests</div>
        <div class="kpi-value">{pack_test_count}</div>
        <div class="kpi-sub">frozen in suite</div>
      </div>
      <div class="surface-card kpi-card">
        <div class="kpi-label">Failures</div>
        <div class="kpi-value {"kpi-bad" if failed > 0 else ""}">{failed}</div>
        <div class="kpi-sub">violations</div>
      </div>
      <div class="surface-card kpi-card">
        <div class="kpi-label">Unverifiable</div>
        <div class="kpi-value {"kpi-warn" if unverifiable > 0 else ""}">{unverifiable}</div>
        <div class="kpi-sub">unprovable</div>
      </div>
      <div class="surface-card kpi-card">
        <div class="kpi-label">Avg Latency</div>
        <div class="kpi-value">{avg_latency}</div>
        <div class="kpi-sub">ms · p95 {p95_latency} ms</div>
      </div>
    </div>

    <!-- Priority Tier Assurance Summary Strip -->
    <div class="surface-card" style="margin-bottom: 1.25rem; padding: 0.85rem 1.15rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem;">
      <div style="font-size: 13px; font-weight: 600; color: var(--foreground);">Assurance Priority Tiers</div>
      <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <span class="diff-chip" style="background: color-mix(in oklch, var(--destructive) 10%, var(--card)); border: 1px solid color-mix(in oklch, var(--destructive) 35%, transparent); color: var(--destructive);">
          P0 Critical: {p0_info["passed"]}/{p0_info["total"]} ({p0_info["pass_rate"]}%)
        </span>
        <span class="diff-chip" style="background: color-mix(in oklch, var(--primary) 10%, var(--card)); border: 1px solid color-mix(in oklch, var(--primary) 35%, transparent); color: var(--primary);">
          P1 Core: {p1_info["passed"]}/{p1_info["total"]} ({p1_info["pass_rate"]}%)
        </span>
        <span class="diff-chip" style="background: color-mix(in oklch, var(--warn) 10%, var(--card)); border: 1px solid color-mix(in oklch, var(--warn) 35%, transparent); color: var(--warn);">
          P2 Extended: {p2_info["passed"]}/{p2_info["total"]} ({p2_info["pass_rate"]}%)
        </span>
      </div>
    </div>

    {signoff_html}

    <!-- Regression Diff Spotlight -->
    {diff_banner_html}

    <!-- Coverage & Limitations Collapsible -->
    <div class="surface-card collapsible-box">
      <div class="collapsible-header" onclick="toggleCollapsible(this)">
        <span>Coverage breakdown & limitations</span>
        <span class="collapsible-indicator">▼</span>
      </div>
      <div class="collapsible-body">
        <div class="axis-grid" id="coverageAxes"></div>
        <div class="cov-column">
          <h4>Covered tags ({len(covered_tags)})</h4>
          <div class="tag-list">{covered_pills}</div>
        </div>
        <div class="cov-column">
          <h4>Gaps ({gap_count})</h4>
          <div class="tag-list">{uncovered_pills}</div>
        </div>
        {gap_callout_html}
        <div class="cov-column" style="grid-column: 1 / -1;">
          <h4>Assurance boundary</h4>
          <ul style="color: var(--muted-foreground); padding-left: 18px;">
            {limitations_items}
          </ul>
        </div>
      </div>
    </div>

    <div class="surface-card" style="padding: 0;">
    <div class="toolbar">
      <div class="filter-group">
        <button class="filter-btn active" onclick="setFilter('all', this)">All ({total})</button>
        <button class="filter-btn" onclick="setFilter('fail', this)">Failed ({failed})</button>
        {reg_filter_btn}
        <button class="filter-btn" onclick="setFilter('pass', this)">Passed ({passed})</button>
        <button class="filter-btn" onclick="setFilter('unverifiable', this)">Unverifiable ({unverifiable})</button>
        <button class="filter-btn" onclick="setFilter('p0', this)">P0 ({p0_info["total"]})</button>
        <button class="filter-btn" onclick="setFilter('p1', this)">P1 ({p1_info["total"]})</button>
        <button class="filter-btn" onclick="setFilter('p2', this)">P2 ({p2_info["total"]})</button>
      </div>
      <div>
        <input type="text" id="searchInput" class="search-input" placeholder="Search tests, prompt, tags..." oninput="handleSearch()" />
      </div>
    </div>
    <div class="test-list" id="testList"></div>
    </div>
  </div>

  <script>
    const reportData = {embedded_json};
    let currentFilter = 'all';
    let searchQuery = '';

    function renderCoverageAxes() {{
      const host = document.getElementById('coverageAxes');
      if (!host || !reportData.coverage || !reportData.coverage.axes) return;
      host.innerHTML = '';
      Object.entries(reportData.coverage.axes).forEach(([axis, ratio]) => {{
        const pct = Math.round((ratio || 0) * 100);
        const card = document.createElement('div');
        card.className = 'axis-card';
        card.innerHTML = `
          <div class="axis-row">
            <span>${{escapeHtml(axis)}}</span>
            <span class="meta-val">${{pct}}%</span>
          </div>
          <div class="axis-bar"><div class="axis-fill" style="width:${{pct}}%"></div></div>
        `;
        host.appendChild(card);
      }});
    }}

    function renderTests() {{
      const container = document.getElementById('testList');
      container.innerHTML = '';

      const filtered = reportData.tests.filter(t => {{
        if (currentFilter === 'pass' && t.verdict !== 'PASS') return false;
        if (currentFilter === 'fail' && t.verdict !== 'FAIL') return false;
        if (currentFilter === 'unverifiable' && t.verdict !== 'UNVERIFIABLE') return false;
        if (currentFilter === 'regression' && !t.is_regression) return false;
        if (currentFilter === 'p0' && (t.priority_tier || 'P1') !== 'P0') return false;
        if (currentFilter === 'p1' && (t.priority_tier || 'P1') !== 'P1') return false;
        if (currentFilter === 'p2' && (t.priority_tier || 'P1') !== 'P2') return false;

        if (searchQuery) {{
          const q = searchQuery.toLowerCase();
          const matchTitle = (t.title || '').toLowerCase().includes(q);
          const matchId = (t.test_id || '').toLowerCase().includes(q);
          const matchPrompt = (t.input_prompt || '').toLowerCase().includes(q);
          const matchResponse = (t.response_text || '').toLowerCase().includes(q);
          const matchTags = (t.coverage_tags || []).some(tag => tag.toLowerCase().includes(q));
          if (!matchTitle && !matchId && !matchPrompt && !matchResponse && !matchTags) {{
            return false;
          }}
        }}
        return true;
      }});

      if (filtered.length === 0) {{
        container.innerHTML = '<div class="empty-state">No test cases match the current filter.</div>';
        return;
      }}

      filtered.forEach(t => {{
        const card = document.createElement('div');
        card.className = 'test-card';
        card.dataset.id = t.test_id;

        const badgeClass = t.verdict === 'PASS' ? 'badge-pass' : (t.verdict === 'FAIL' ? 'badge-fail' : 'badge-unverifiable');
        const regBadge = t.is_regression ? '<span class="diff-chip chip-reg" style="font-size:10px; padding:2px 6px;">⚠️ REGRESSION</span>' : (t.is_fix ? '<span class="diff-chip chip-fix" style="font-size:10px; padding:2px 6px;">🎉 FIXED</span>' : '');

        card.innerHTML = `
          <div class="test-card-header" onclick="toggleCard(this.parentElement)">
            <div class="test-left">
              <span class="status-badge ${{badgeClass}}">${{t.verdict}}</span>
              <span class="tag-pill" style="font-weight: 700; font-size: 10px;">${{t.priority_tier || 'P1'}}</span>
              ${{regBadge}}
              <span class="test-title">${{escapeHtml(t.tab_label || t.title)}}</span>
              <span class="test-id">#${{escapeHtml(t.test_id)}}</span>
            </div>
            <div class="test-right">
              <span class="metric-badge">${{escapeHtml(t.category)}}</span>
              <span class="metric-badge">${{escapeHtml(t.persona_slug)}}</span>
              <span class="metric-badge">${{t.latency_ms}}ms</span>
              <span class="metric-badge">HTTP ${{t.http_status}}</span>
              <span>▼</span>
            </div>
          </div>
          <div class="test-card-body">
            <div class="detail-section">
              <div class="detail-label">Input Prompt to Agent</div>
              <div class="code-block">${{escapeHtml(t.input_prompt)}}</div>
            </div>
            <div class="detail-section">
              <div class="detail-label">Agent Response</div>
              <div class="code-block">${{escapeHtml(t.response_text)}}</div>
            </div>
            <div class="detail-section">
              <div class="detail-label">Expected Behavior</div>
              <div class="detail-content">${{escapeHtml(t.expected_behavior)}}</div>
            </div>
            <div class="detail-section">
              <div class="detail-label">Evaluation Rationale</div>
              <div class="detail-content">${{escapeHtml(t.rationale || 'None provided')}}</div>
            </div>
            <div class="detail-section">
              <div class="detail-label">Coverage Tags</div>
              <div class="tag-list">
                ${{(t.coverage_tags || []).map(tag => `<span class="tag-pill">${{escapeHtml(tag)}}</span>`).join('')}}
              </div>
            </div>
          </div>
        `;
        container.appendChild(card);
      }});
    }}

    function toggleCard(card) {{
      card.classList.toggle('open');
    }}

    function toggleAllCards() {{
      const cards = document.querySelectorAll('.test-card');
      const anyOpen = Array.from(cards).some(c => c.classList.contains('open'));
      cards.forEach(c => {{
        if (anyOpen) c.classList.remove('open');
        else c.classList.add('open');
      }});
    }}

    function toggleCollapsible(header) {{
      const body = header.nextElementSibling;
      const indicator = header.querySelector('.collapsible-indicator');
      if (body.style.display === 'none') {{
        body.style.display = 'grid';
        indicator.textContent = '▼';
      }} else {{
        body.style.display = 'none';
        indicator.textContent = '▶';
      }}
    }}

    function setFilter(filter, btn) {{
      currentFilter = filter;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTests();
    }}

    function handleSearch() {{
      searchQuery = document.getElementById('searchInput').value;
      renderTests();
    }}

    function escapeHtml(str) {{
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }}

    renderCoverageAxes();
    renderTests();
  </script>
</body>
</html>
"""
