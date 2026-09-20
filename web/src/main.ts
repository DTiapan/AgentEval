import "./styles.css";
import {
  fetchHealth,
  getSuiteDetail,
  initSuite,
  listSuites,
  previewSuite,
  runSuite,
  type SuiteRunReport,
  type TestPack,
} from "./api";

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) {
  throw new Error("#app missing");
}

app.innerHTML = `
  <header class="app-header">
    <div>
      <h1>AgentEval Console</h1>
      <p>Requirements → test pack → run → verdicts (North Star E4)</p>
    </div>
    <div class="status-pill" id="health-pill" data-ok="false" aria-live="polite">
      <span class="dot" aria-hidden="true"></span>
      <span id="health-label">Connecting…</span>
    </div>
  </header>
  <div class="layout">
    <section class="panel" aria-labelledby="compose-heading">
      <h2 id="compose-heading">Compose suite</h2>
      <form id="compose-form">
        <div class="field-row">
          <div>
            <label for="agent-id">Agent ID</label>
            <input id="agent-id" name="agent_id" required placeholder="refund-bot" />
          </div>
          <div>
            <label for="endpoint">Endpoint URL (optional)</label>
            <input id="endpoint" name="endpoint" type="url" placeholder="http://127.0.0.1:8765/chat" />
          </div>
        </div>
        <label for="requirements">Requirements (markdown)</label>
        <textarea id="requirements" name="requirements" required placeholder="# My Agent&#10;&#10;## Functional requirements&#10;&#10;1. Must …"></textarea>
        <div class="actions">
          <button type="button" class="secondary" id="btn-preview">Preview pack</button>
          <button type="button" class="primary" id="btn-init">Save suite</button>
          <button type="button" class="secondary" id="btn-run">Run suite</button>
        </div>
      </form>
      <div id="toast" class="toast" hidden role="status"></div>
    </section>
    <aside class="panel" aria-labelledby="suites-heading">
      <h2 id="suites-heading">Frozen suites</h2>
      <ul class="suite-list" id="suite-list"></ul>
      <p class="empty" id="suite-empty">No suites yet. Save one from the form.</p>
    </aside>
  </div>
  <section class="panel" style="margin-top: 1.25rem" aria-labelledby="results-heading">
    <h2 id="results-heading">Results</h2>
    <div id="results-body"><p class="empty">Preview or run a suite to see tests and verdicts.</p></div>
  </section>
`;

const healthPill = document.querySelector<HTMLDivElement>("#health-pill")!;
const healthLabel = document.querySelector<HTMLSpanElement>("#health-label")!;
const agentIdInput = document.querySelector<HTMLInputElement>("#agent-id")!;
const endpointInput = document.querySelector<HTMLInputElement>("#endpoint")!;
const requirementsInput = document.querySelector<HTMLTextAreaElement>("#requirements")!;
const suiteList = document.querySelector<HTMLUListElement>("#suite-list")!;
const suiteEmpty = document.querySelector<HTMLParagraphElement>("#suite-empty")!;
const resultsBody = document.querySelector<HTMLDivElement>("#results-body")!;
const toast = document.querySelector<HTMLDivElement>("#toast")!;

function setBusy(next: boolean) {
  document.querySelectorAll("button").forEach((btn) => {
    (btn as HTMLButtonElement).disabled = next;
  });
}

function showToast(message: string, kind: "error" | "success") {
  toast.hidden = false;
  toast.textContent = message;
  toast.className = `toast ${kind}`;
}

function hideToast() {
  toast.hidden = true;
}

function verdictClass(verdict: string): string {
  if (verdict === "PASS") return "pass";
  if (verdict === "FAIL") return "fail";
  return "other";
}

function renderPackTable(pack: TestPack, title: string) {
  const rows = pack.tests
    .map(
      (t, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${escapeHtml(t.category)}</td>
        <td>${escapeHtml(t.name)}</td>
        <td><code>${escapeHtml(t.id)}</code></td>
      </tr>`,
    )
    .join("");
  return `
    <p><strong>${escapeHtml(title)}</strong> · ${pack.tests.length} tests · fingerprint <code>${escapeHtml(pack.requirements_fingerprint)}</code></p>
    <table class="results-table">
      <thead><tr><th>#</th><th>Category</th><th>Name</th><th>Test ID</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderRunReport(report: SuiteRunReport, pack?: TestPack) {
  const nameById = new Map(pack?.tests.map((t) => [t.id, t.name]) ?? []);
  const rows = report.results
    .map(
      (r) => `
      <tr>
        <td>${escapeHtml(nameById.get(r.test_id) ?? r.test_id)}</td>
        <td><span class="verdict ${verdictClass(r.verdict)}">${escapeHtml(r.verdict)}</span></td>
        <td>${escapeHtml(r.rationale)}</td>
      </tr>`,
    )
    .join("");
  return `
    <div class="summary-bar">
      <span>Run <strong>${escapeHtml(report.run_id)}</strong></span>
      <span>Passed <strong>${report.passed}</strong></span>
      <span>Failed <strong>${report.failed}</strong></span>
      <span>Unverifiable <strong>${report.unverifiable}</strong></span>
    </div>
    <table class="results-table">
      <thead><tr><th>Test</th><th>Verdict</th><th>Rationale</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formPayload() {
  return {
    agent_id: agentIdInput.value.trim(),
    requirements_text: requirementsInput.value,
    endpoint_url: endpointInput.value.trim() || undefined,
  };
}

async function refreshSuites(selectId?: string) {
  const suites = await listSuites();
  suiteList.innerHTML = "";
  suiteEmpty.hidden = suites.length > 0;
  for (const suite of suites) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.innerHTML = `${escapeHtml(suite.agent_id)}<span class="meta">v${suite.suite_version} · pack ${suite.pack_size} · pool ${suite.pool_size}${suite.has_latest_run ? " · has run" : ""}</span>`;
    btn.addEventListener("click", () => loadSuiteDetail(suite.agent_id));
    if (suite.agent_id === selectId) {
      btn.style.borderColor = "var(--accent)";
    }
    li.appendChild(btn);
    suiteList.appendChild(li);
  }
}

async function loadSuiteDetail(agentId: string) {
  agentIdInput.value = agentId;
  hideToast();
  setBusy(true);
  try {
    const detail = await getSuiteDetail(agentId);
    let html = renderPackTable(detail.optimized_pack, `Suite ${agentId}`);
    if (detail.latest_run) {
      html += renderRunReport(detail.latest_run, detail.optimized_pack);
    }
    resultsBody.innerHTML = html;
    await refreshSuites(agentId);
  } catch (err) {
    showToast(err instanceof Error ? err.message : String(err), "error");
  } finally {
    setBusy(false);
  }
}

async function initHealth() {
  try {
    const health = await fetchHealth();
    healthPill.dataset.ok = "true";
    healthLabel.textContent = `API ${health.version}`;
  } catch {
    healthLabel.textContent = "API offline — start agenteval serve";
  }
}

document.querySelector("#btn-preview")!.addEventListener("click", async () => {
  hideToast();
  setBusy(true);
  try {
    const payload = formPayload();
    const preview = await previewSuite(payload);
    resultsBody.innerHTML = renderPackTable(
      preview.optimized_pack,
      `Preview · ${preview.agent_card.name}`,
    );
    if (preview.coverage.critical_uncovered?.length) {
      showToast(`Gaps: ${preview.coverage.critical_uncovered.join(", ")}`, "success");
    }
  } catch (err) {
    showToast(err instanceof Error ? err.message : String(err), "error");
  } finally {
    setBusy(false);
  }
});

document.querySelector("#btn-init")!.addEventListener("click", async () => {
  hideToast();
  setBusy(true);
  try {
    const payload = formPayload();
    const result = await initSuite({ ...payload, force_new_version: true });
    showToast(`Suite saved for ${result.agent_id} (${result.optimized_pack_size} tests)`, "success");
    await refreshSuites(result.agent_id);
    await loadSuiteDetail(result.agent_id);
  } catch (err) {
    showToast(err instanceof Error ? err.message : String(err), "error");
  } finally {
    setBusy(false);
  }
});

document.querySelector("#btn-run")!.addEventListener("click", async () => {
  hideToast();
  setBusy(true);
  try {
    const agentId = agentIdInput.value.trim();
    const endpoint = endpointInput.value.trim() || undefined;
    const report = await runSuite(agentId, endpoint);
    const detail = await getSuiteDetail(agentId);
    resultsBody.innerHTML =
      renderPackTable(detail.optimized_pack, `Suite ${agentId}`) +
      renderRunReport(report, detail.optimized_pack);
    showToast(`Run complete: ${report.passed} passed, ${report.failed} failed`, "success");
    await refreshSuites(agentId);
  } catch (err) {
    showToast(err instanceof Error ? err.message : String(err), "error");
  } finally {
    setBusy(false);
  }
});

void initHealth();
void refreshSuites().catch(() => {
  suiteEmpty.textContent = "Could not load suites — is the API running?";
});
