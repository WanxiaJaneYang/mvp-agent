const POLL_INTERVAL_MS = 4000;

const state = {
  overview: null,
  health: {},
  latestRun: {},
  artifacts: {},
  logs: {},
  runs: [],
};

const els = {
  repoName: document.getElementById("repo-name"),
  activeRunLabel: document.getElementById("active-run-label"),
  activeRunMeta: document.getElementById("active-run-meta"),
  architectureGrid: document.getElementById("architecture-grid"),
  healthGrid: document.getElementById("health-grid"),
  commandGrid: document.getElementById("command-grid"),
  decisionPill: document.getElementById("decision-pill"),
  decisionRunKind: document.getElementById("decision-run-kind"),
  decisionReason: document.getElementById("decision-reason"),
  reasonCodes: document.getElementById("reason-codes"),
  artifactLinks: document.getElementById("artifact-links"),
  recentRuns: document.getElementById("recent-runs"),
  runsCount: document.getElementById("runs-count"),
  logMeta: document.getElementById("log-meta"),
  logViewer: document.getElementById("log-viewer"),
  refreshButton: document.getElementById("refresh-button"),
};

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

function statusTone(value) {
  const normalized = String(value || "idle").toLowerCase();
  if (normalized === "publish" || normalized === "ok") return "good";
  if (normalized === "hold" || normalized === "partial" || normalized === "running") return "warn";
  if (normalized === "failed") return "bad";
  return "idle";
}

function labelize(value) {
  return String(value || "idle")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatTimestamp(value) {
  if (!value) return "No timestamp";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return parsed.toLocaleString();
}

function renderArchitecture() {
  const cards = (state.overview && state.overview.diagram_cards) || [];
  els.architectureGrid.innerHTML = cards
    .map((card) => {
      const asset = Array.isArray(card.assets) ? card.assets[0] : null;
      const assetMarkup = asset
        ? `<a class="diagram-card__asset" href="${asset.uri || "#"}" target="_blank" rel="noreferrer">Preview asset: ${asset.label || asset.path}</a>`
        : `<span class="diagram-card__asset diagram-card__asset--muted">No image asset discovered</span>`;
      return `
        <article class="diagram-card">
          <div class="diagram-card__meta">${card.id}</div>
          <h3>${card.title}</h3>
          <a class="diagram-card__link" href="${pathToHref(card.primary_path)}" target="_blank" rel="noreferrer">${card.primary_path}</a>
          ${assetMarkup}
        </article>
      `;
    })
    .join("");
}

function renderHealth() {
  const order = ["fixture", "evals", "targeted_tests", "live"];
  els.healthGrid.innerHTML = order
    .map((runKind) => {
      const entry = state.health[runKind] || {};
      const tone = statusTone(entry.publish_decision || entry.status);
      const codes = formatCodes(entry.reason_codes);
      return `
        <article class="health-card">
          <div class="health-card__header">
            <span class="health-card__title">${labelize(runKind)}</span>
            <span class="status-pill status-pill--${tone}">${labelize(entry.publish_decision || entry.status)}</span>
          </div>
          <p class="health-card__reason">${entry.reason || "No recorded decision context yet."}</p>
          <div class="health-card__meta">Updated ${formatTimestamp(entry.updated_at_utc)}</div>
          <div class="tag-row">${codes}</div>
        </article>
      `;
    })
    .join("");
}

function renderCommands() {
  const commands = (state.overview && state.overview.commands) || {};
  const entries = Array.isArray(commands)
    ? commands.map((item) => [item.run_kind, item])
    : Object.entries(commands);
  els.commandGrid.innerHTML = entries
    .map(([runKind, details]) => {
      const label = details.title || details.label || labelize(runKind);
      const command = Array.isArray(details.argv) ? details.argv.join(" ") : details.command || "";
      return `
        <article class="command-card">
          <div class="command-card__header">
            <h3>${label}</h3>
            <button class="button" type="button" data-run-kind="${runKind}">Run</button>
          </div>
          <code>${command}</code>
        </article>
      `;
    })
    .join("");

  els.commandGrid.querySelectorAll("[data-run-kind]").forEach((button) => {
    button.addEventListener("click", async () => {
      const runKind = button.getAttribute("data-run-kind");
      if (!runKind) return;
      button.disabled = true;
      try {
        await fetchJson(`/api/run/${runKind.replace("_", "-")}`, { method: "POST" });
        await refreshRuntime();
      } catch (error) {
        window.alert(`Run failed to start: ${error.message}`);
      } finally {
        button.disabled = false;
      }
    });
  });
}

function renderDecision() {
  const latest = state.artifacts.latest || state.latestRun || {};
  const tone = statusTone(latest.publish_decision || latest.status);
  els.decisionPill.className = `status-pill status-pill--${tone}`;
  els.decisionPill.textContent = labelize(latest.publish_decision || latest.status || "idle");
  els.decisionRunKind.textContent = latest.run_kind ? `${labelize(latest.run_kind)} surface` : "Artifact observer";
  els.decisionReason.textContent = latest.reason || "No decision context yet.";
  els.reasonCodes.innerHTML = formatCodes(latest.reason_codes);

  const links = [
    ["Latest HTML Brief", latest.brief_html_uri || latest.html_path],
    ["Decision Record", latest.decision_record_uri || latest.decision_record_path],
    ["Run Summary", latest.run_summary_uri || latest.run_summary_path],
  ].filter(([, href]) => href);
  els.artifactLinks.innerHTML = links.length
    ? links.map(([label, href]) => `<a href="${href}" target="_blank" rel="noreferrer">${label}</a>`).join("")
    : `<span class="artifact-links__empty">No artifact links discovered yet.</span>`;
}

function renderRuns() {
  els.runsCount.textContent = `${state.runs.length} recorded`;
  els.recentRuns.innerHTML = state.runs.length
    ? state.runs
        .map((run) => {
          const tone = statusTone(run.publish_decision || run.status);
          return `
            <article class="run-row">
              <div class="run-row__top">
                <strong>${labelize(run.run_kind)}</strong>
                <span class="status-pill status-pill--${tone}">${labelize(run.publish_decision || run.status)}</span>
              </div>
              <div class="run-row__meta">${formatTimestamp(run.finished_at_utc || run.started_at_utc)}</div>
              <p>${run.summary || run.reason || "No summary provided."}</p>
            </article>
          `;
        })
        .join("")
    : `<p class="runs-list__empty">No dashboard-triggered runs have been recorded yet.</p>`;
}

function renderLogs() {
  const lines = Array.isArray(state.logs.lines) ? state.logs.lines : [];
  els.logMeta.textContent = state.logs.run_id
    ? `${state.logs.run_id} - ${state.logs.is_running ? "running" : "latest stored output"}`
    : "No log stream yet.";
  els.logViewer.textContent = lines.length ? lines.join("\n") : "Waiting for logs...";
}

function renderActiveRun() {
  const latest = state.latestRun || {};
  els.activeRunLabel.textContent = latest.run_id || "No active run";
  els.activeRunMeta.textContent = labelize(latest.publish_decision || latest.status || "idle");
}

function formatCodes(codes) {
  const values = Array.isArray(codes) ? codes.filter(Boolean) : [];
  if (!values.length) {
    return `<span class="tag tag--muted">none</span>`;
  }
  return values.map((code) => `<span class="tag">${labelize(code)}</span>`).join("");
}

function pathToHref(path) {
  if (!path) return "#";
  if (String(path).startsWith("file:")) return path;
  return `file:///${String(path).replace(/\\/g, "/")}`;
}

async function refreshRuntime() {
  const [health, latestRun, artifacts, logs, runs] = await Promise.all([
    fetchJson("/api/health"),
    fetchJson("/api/latest-run"),
    fetchJson("/api/artifacts"),
    fetchJson("/api/logs/latest"),
    fetchJson("/api/runs"),
  ]);
  state.health = health || {};
  state.latestRun = latestRun || {};
  state.artifacts = artifacts || {};
  state.logs = logs || {};
  state.runs = Array.isArray(runs) ? runs : [];
  renderHealth();
  renderDecision();
  renderRuns();
  renderLogs();
  renderActiveRun();
}

async function refreshAll() {
  state.overview = await fetchJson("/api/overview");
  els.repoName.textContent = `${state.overview.repo_name || "Repo"} Ops Dashboard`;
  renderArchitecture();
  renderCommands();
  await refreshRuntime();
}

els.refreshButton.addEventListener("click", async () => {
  els.refreshButton.disabled = true;
  try {
    await fetchJson("/api/refresh", { method: "POST" });
    await refreshAll();
  } catch (error) {
    window.alert(`Refresh failed: ${error.message}`);
  } finally {
    els.refreshButton.disabled = false;
  }
});

refreshAll().catch((error) => {
  els.logViewer.textContent = `Dashboard bootstrap failed:\n${error.message}`;
});

window.setInterval(() => {
  refreshRuntime().catch(() => undefined);
}, POLL_INTERVAL_MS);
