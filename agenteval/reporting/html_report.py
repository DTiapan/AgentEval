"""Allure-class standalone HTML run report generator for AgentEval (B8 report).

Self-contained single-file HTML report: zero external dependencies, dark slate
OLED aesthetic, interactive test case explorer, regression diff spotlight,
and multi-axis coverage reporting.
"""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from typing import Any

from agenteval.planning.models import SuiteManifest, SuiteRunReport, TestPack


class HTMLReportGenerator:
    """Render a self-contained, interactive HTML report from a SuiteRunReport and TestPack."""

    @classmethod
    def generate(
        cls,
        report: SuiteRunReport,
        pack: TestPack,
        manifest: SuiteManifest | None = None,
        title: str | None = None,
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

        for res in report.results:
            test_def = pack_tests_by_id.get(res.test_id)
            lat = res.observation.latency_ms
            if lat > 0:
                total_latency_ms += lat
                latency_count += 1

            is_regression = res.test_id in regressions_set
            is_fix = res.test_id in fixes_set

            cat_val = "general"
            if test_def:
                cat_val = (
                    test_def.category.value
                    if hasattr(test_def.category, "value")
                    else str(test_def.category)
                )

            merged_tests.append({
                "test_id": res.test_id,
                "title": test_def.name if test_def else res.test_id,
                "category": cat_val,
                "capability_id": test_def.capability_id if test_def else "unknown",
                "persona_slug": test_def.persona_id if test_def else "default",
                "input_prompt": test_def.user_prompt if test_def else res.observation.user_prompt,
                "expected_behavior": test_def.expected_behavior if test_def else "",
                "coverage_tags": test_def.coverage_tags if test_def else [],
                "rationale": res.rationale or (test_def.rationale if test_def else ""),
                "verdict": res.verdict,
                "http_status": res.observation.http_status,
                "latency_ms": res.observation.latency_ms,
                "response_text": res.observation.response_text,
                "raw_json": res.observation.raw_json,
                "is_regression": is_regression,
                "is_fix": is_fix,
            })

        avg_latency = round(total_latency_ms / latency_count, 1) if latency_count > 0 else 0.0
        total_tests = len(report.results)
        pass_rate = round((report.passed / total_tests) * 100, 1) if total_tests > 0 else 0.0

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
            "diff": diff,
            "coverage": report.coverage_report.model_dump() if report.coverage_report else None,
            "tests": merged_tests,
        }

        embedded_json = json.dumps(embedded_data, ensure_ascii=False).replace("<", "\\u003c")

        return cls._render_template(report_title, embedded_json, embedded_data)

    @classmethod
    def _render_template(cls, title: str, embedded_json: str, data: dict[str, Any]) -> str:
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
        generated_at = html.escape(str(data.get("generated_at", "")))

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

        # Precompute sub-blocks
        diff_banner_html = ""
        if has_diff:
            diff_title = "⚠️ Regressions Detected" if regressions else "✅ Regression Check Clean"
            reg_chip = (
                f'<span class="diff-chip chip-reg">{len(regressions)} Regressions</span>'
                if regressions
                else ""
            )
            fix_chip = f'<span class="diff-chip chip-fix">{len(fixes)} Fixes</span>' if fixes else ""
            stable_chip = f'<span class="diff-chip" style="background: var(--bg-surface-elevated); color: var(--text-muted);">{len(diff.get("stable_pass", []))} Stable Passed</span>'
            prior_id = html.escape(str(diff.get("prior_run_id", "baseline")))
            diff_class = "diff-banner has-regression" if regressions else "diff-banner"
            diff_banner_html = f"""
            <div class="{diff_class}">
              <div>
                <div class="diff-title"><span>{diff_title}</span></div>
                <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
                  Compared to prior run: <code>{prior_id}</code>
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
            or '<span style="color: var(--color-pass);">100% Tags Covered</span>'
        )
        limitations_items = (
            "".join(f"<li>{html.escape(item)}</li>" for item in limitations)
            or "<li>Endpoint-level observations only; internal state mutations not asserted without dedicated probes.</li>"
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title}</title>
  <style>
    :root {{
      --bg-base: #09090B;
      --bg-surface: #121214;
      --bg-surface-elevated: #18181B;
      --bg-hover: #27272A;
      --border-subtle: #27272A;
      --border-strong: #3F3F46;
      --text-main: #FAFAFA;
      --text-muted: #A1A1AA;
      --text-faint: #71717A;
      --color-pass: #10B981;
      --color-pass-bg: rgba(16, 185, 129, 0.12);
      --color-fail: #F43F5E;
      --color-fail-bg: rgba(244, 63, 94, 0.12);
      --color-unverifiable: #F59E0B;
      --color-unverifiable-bg: rgba(245, 158, 11, 0.12);
      --color-accent: #E4E4E7;
      --color-accent-bg: rgba(228, 228, 231, 0.10);
      --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding: 24px;
      -webkit-font-smoothing: antialiased;
    }}

    .container {{
      max-width: 1280px;
      margin: 0 auto;
    }}

    /* Header */
    header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border-subtle);
      flex-wrap: wrap;
      gap: 16px;
    }}

    .brand-title {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .brand-badge {{
      background: #FAFAFA;
      color: #09090B;
      font-weight: 700;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: 4px;
    }}

    h1 {{
      font-size: 22px;
      font-weight: 700;
      color: var(--text-main);
    }}

    .metadata-line {{
      font-size: 13px;
      color: var(--text-muted);
      margin-top: 4px;
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
    }}

    .meta-item {{ display: inline-flex; align-items: center; gap: 4px; }}
    .meta-val {{ color: var(--text-main); font-family: var(--font-mono); }}

    .header-actions {{
      display: flex;
      gap: 10px;
    }}

    .btn {{
      background-color: var(--bg-surface-elevated);
      color: var(--text-main);
      border: 1px solid var(--border-strong);
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }}

    .btn:hover {{
      background-color: var(--bg-hover);
      border-color: #4B5563;
    }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}

    .kpi-card {{
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 14px 16px;
      position: relative;
      overflow: hidden;
    }}

    .kpi-label {{
      font-size: 12px;
      font-weight: 500;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 6px;
    }}

    .kpi-value {{
      font-size: 26px;
      font-weight: 700;
      line-height: 1;
      font-family: var(--font-mono);
    }}

    .kpi-card.pass .kpi-value {{ color: var(--color-pass); }}
    .kpi-card.fail .kpi-value {{ color: var(--color-fail); }}
    .kpi-card.unverifiable .kpi-value {{ color: var(--color-unverifiable); }}
    .kpi-card.accent .kpi-value {{ color: var(--color-accent); }}

    /* Regression Banner */
    .diff-banner {{
      background-color: var(--bg-surface);
      border: 1px solid var(--border-strong);
      border-radius: 8px;
      padding: 14px 18px;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}

    .diff-banner.has-regression {{
      border-color: rgba(239, 68, 68, 0.4);
      background: linear-gradient(90deg, rgba(239, 68, 68, 0.08), var(--bg-surface));
    }}

    .diff-title {{
      font-size: 14px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

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

    .chip-reg {{ background: var(--color-fail-bg); color: var(--color-fail); border: 1px solid var(--color-fail); }}
    .chip-fix {{ background: var(--color-pass-bg); color: var(--color-pass); border: 1px solid var(--color-pass); }}

    /* Collapsible Coverage & Limitations */
    .collapsible-box {{
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      margin-bottom: 20px;
      overflow: hidden;
    }}

    .collapsible-header {{
      padding: 12px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      font-weight: 600;
      font-size: 13px;
      background-color: rgba(255, 255, 255, 0.02);
      user-select: none;
    }}

    .collapsible-header:hover {{ background-color: rgba(255, 255, 255, 0.04); }}

    .collapsible-body {{
      padding: 16px;
      border-top: 1px solid var(--border-subtle);
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      font-size: 13px;
    }}

    .cov-column h4 {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 8px;
    }}

    .tag-list {{ display: flex; flex-wrap: wrap; gap: 6px; }}

    .tag-pill {{
      background-color: var(--bg-surface-elevated);
      color: var(--text-main);
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-family: var(--font-mono);
      border: 1px solid var(--border-strong);
    }}

    .tag-pill.warn {{
      border-color: var(--color-fail);
      color: var(--color-fail);
      background-color: var(--color-fail-bg);
    }}

    /* Filter Toolbar */
    .toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .filter-group {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .filter-btn {{
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }}

    .filter-btn:hover {{
      background-color: var(--bg-surface-elevated);
      color: var(--text-main);
    }}

    .filter-btn.active {{
      background-color: var(--bg-surface-elevated);
      color: var(--text-main);
      border-color: var(--color-accent);
    }}

    .search-input {{
      background-color: var(--bg-surface);
      border: 1px solid var(--border-strong);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      width: 240px;
    }}

    .search-input:focus {{
      outline: none;
      border-color: var(--color-accent);
    }}

    /* Test Case List */
    .test-list {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    .test-card {{
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      overflow: hidden;
      transition: border-color 0.15s ease;
    }}

    .test-card:hover {{
      border-color: var(--border-strong);
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

    .badge-pass {{ background-color: var(--color-pass-bg); color: var(--color-pass); border: 1px solid var(--color-pass); }}
    .badge-fail {{ background-color: var(--color-fail-bg); color: var(--color-fail); border: 1px solid var(--color-fail); }}
    .badge-unverifiable {{ background-color: var(--color-unverifiable-bg); color: var(--color-unverifiable); border: 1px solid var(--color-unverifiable); }}

    .test-title {{
      font-weight: 600;
      font-size: 13px;
      color: var(--text-main);
    }}

    .test-id {{
      color: var(--text-faint);
      font-family: var(--font-mono);
      font-size: 11px;
      margin-left: 6px;
    }}

    .test-right {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 12px;
      color: var(--text-muted);
    }}

    .metric-badge {{
      font-family: var(--font-mono);
      font-size: 11px;
      background: var(--bg-surface-elevated);
      padding: 2px 6px;
      border-radius: 4px;
      color: var(--text-muted);
    }}

    .test-card-body {{
      padding: 16px;
      border-top: 1px solid var(--border-subtle);
      background-color: #0d121f;
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
      color: var(--text-muted);
      margin-bottom: 6px;
    }}

    .detail-content {{
      font-size: 13px;
      color: var(--text-main);
      background: var(--bg-surface);
      padding: 10px 14px;
      border-radius: 6px;
      border: 1px solid var(--border-subtle);
    }}

    .code-block {{
      font-family: var(--font-mono);
      font-size: 12px;
      white-space: pre-wrap;
      word-break: break-word;
      background-color: #070a11;
      padding: 12px;
      border-radius: 6px;
      border: 1px solid var(--border-subtle);
      max-height: 280px;
      overflow-y: auto;
    }}

    .empty-state {{
      text-align: center;
      padding: 40px 20px;
      color: var(--text-muted);
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <div class="brand-title">
          <span class="brand-badge">AgentEval</span>
          <h1>{safe_title}</h1>
        </div>
        <div class="metadata-line">
          <span class="meta-item">Agent ID: <span class="meta-val">{agent_id}</span></span>
          <span class="meta-item">Suite Version: <span class="meta-val">v{suite_version}</span></span>
          <span class="meta-item">Run ID: <span class="meta-val">{run_id}</span></span>
          <span class="meta-item">Executed: <span class="meta-val">{generated_at}</span></span>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn" onclick="window.print()">Print / PDF</button>
        <button class="btn" onclick="toggleAllCards()">Toggle All</button>
      </div>
    </header>

    <!-- KPI Grid -->
    <div class="kpi-grid">
      <div class="kpi-card accent">
        <div class="kpi-label">Total Tests</div>
        <div class="kpi-value">{total}</div>
      </div>
      <div class="kpi-card pass">
        <div class="kpi-label">Passed ({pass_rate}%)</div>
        <div class="kpi-value">{passed}</div>
      </div>
      <div class="kpi-card fail">
        <div class="kpi-label">Failed</div>
        <div class="kpi-value">{failed}</div>
      </div>
      <div class="kpi-card unverifiable">
        <div class="kpi-label">Unverifiable</div>
        <div class="kpi-value">{unverifiable}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Avg Latency</div>
        <div class="kpi-value">{avg_latency}ms</div>
      </div>
    </div>

    <!-- Regression Diff Spotlight -->
    {diff_banner_html}

    <!-- Coverage & Limitations Collapsible -->
    <div class="collapsible-box">
      <div class="collapsible-header" onclick="toggleCollapsible(this)">
        <span>Assurance Coverage & Verified Limitations</span>
        <span class="collapsible-indicator">▼</span>
      </div>
      <div class="collapsible-body">
        <div class="cov-column">
          <h4>Covered Assurance Tags ({len(covered_tags)})</h4>
          <div class="tag-list">
            {covered_pills}
          </div>
        </div>
        <div class="cov-column">
          <h4>Uncovered / Critical Gaps ({len(uncovered_tags)})</h4>
          <div class="tag-list">
            {uncovered_pills}
          </div>
        </div>
        <div class="cov-column" style="grid-column: 1 / -1;">
          <h4>Assurance Boundary & Limitations</h4>
          <ul style="color: var(--text-muted); padding-left: 18px;">
            {limitations_items}
          </ul>
        </div>
      </div>
    </div>

    <!-- Filter & Search Toolbar -->
    <div class="toolbar">
      <div class="filter-group">
        <button class="filter-btn active" onclick="setFilter('all', this)">All ({total})</button>
        <button class="filter-btn" onclick="setFilter('fail', this)">Failed ({failed})</button>
        {reg_filter_btn}
        <button class="filter-btn" onclick="setFilter('pass', this)">Passed ({passed})</button>
        <button class="filter-btn" onclick="setFilter('unverifiable', this)">Unverifiable ({unverifiable})</button>
      </div>
      <div>
        <input type="text" id="searchInput" class="search-input" placeholder="Search tests, prompt, tags..." oninput="handleSearch()" />
      </div>
    </div>

    <!-- Test Cases Container -->
    <div class="test-list" id="testList"></div>
  </div>

  <script>
    const reportData = {embedded_json};
    let currentFilter = 'all';
    let searchQuery = '';

    function renderTests() {{
      const container = document.getElementById('testList');
      container.innerHTML = '';

      const filtered = reportData.tests.filter(t => {{
        if (currentFilter === 'pass' && t.verdict !== 'PASS') return false;
        if (currentFilter === 'fail' && t.verdict !== 'FAIL') return false;
        if (currentFilter === 'unverifiable' && t.verdict !== 'UNVERIFIABLE') return false;
        if (currentFilter === 'regression' && !t.is_regression) return false;

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
              ${{regBadge}}
              <span class="test-title">${{escapeHtml(t.title)}}</span>
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

    // Initial Render
    renderTests();
  </script>
</body>
</html>
"""
