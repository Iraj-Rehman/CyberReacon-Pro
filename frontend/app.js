// ==========================================================================
// CyberRecon Pro — Frontend Application
// Talks to the Flask backend at BACKEND_URL. Everything here maps 1:1 to a
// real backend route — nothing on this page is fake data once a scan runs.
// ==========================================================================

const BACKEND_URL = "http://127.0.0.1:5000";

// ---------- Global state ----------
let currentJobId = null;
let pollTimer = null;
let seenLogCount = 0;
let lastScanResults = [];
let historyCache = [];
let charts = {};

// ==========================================================================
// NAVIGATION
// ==========================================================================
const TAB_TITLES = {
  overview: ["Overview", "Real-time reconnaissance summary"],
  scan: ["Scan Console", "Launch and monitor live port scans"],
  discovery: ["Network Discovery", "Find live hosts on your subnet"],
  analytics: ["Analytics", "Visual breakdown of your latest scan"],
  history: ["Scan History", "Every scan you've run, searchable"],
  intel: ["Security Intelligence", "Reference for common port risks"],
};

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

function switchTab(tab) {
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${tab}`));
  document.getElementById("pageTitle").textContent = TAB_TITLES[tab][0];
  document.getElementById("pageSub").textContent = TAB_TITLES[tab][1];
  if (tab === "analytics") renderCharts();
  if (tab === "history") loadHistory();
  if (tab === "intel") loadIntel();
}

// ==========================================================================
// SIDEBAR / THEME / FULLSCREEN
// ==========================================================================
document.getElementById("sidebarToggle").addEventListener("click", () => {
  document.getElementById("sidebar").classList.toggle("collapsed");
  document.getElementById("sidebar").classList.toggle("mobile-open");
});

document.getElementById("themeToggle").addEventListener("click", () => {
  const html = document.documentElement;
  const isLight = html.getAttribute("data-theme") === "light";
  html.setAttribute("data-theme", isLight ? "dark" : "light");
  document.getElementById("themeToggle").innerHTML = isLight
    ? '<i class="fa-solid fa-moon"></i>'
    : '<i class="fa-solid fa-sun"></i>';
});

document.getElementById("fullscreenToggle").addEventListener("click", () => {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen();
  else document.exitFullscreen();
});

// Keyboard shortcuts: "/" focuses search on the active tab
document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement.tagName !== "INPUT") {
    e.preventDefault();
    const visible = document.querySelector(".tab-panel.active input[type='text']");
    if (visible) visible.focus();
  }
});

// clock
setInterval(() => {
  document.getElementById("clock").textContent = new Date().toLocaleTimeString();
}, 1000);

// ==========================================================================
// TOASTS
// ==========================================================================
function toast(message, type = "info") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  document.getElementById("toastContainer").appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ==========================================================================
// HERO STATS + SYSTEM WIDGETS
// ==========================================================================
function renderHeroStats(scan) {
  const items = scan
    ? [
        ["fa-bullseye", scan.target, "Last Target"],
        ["fa-network-wired", scan.resolved_ip, "Resolved IP"],
        ["fa-door-open", scan.open_ports, "Open Ports"],
        ["fa-lock", scan.closed_ports, "Closed Ports"],
        ["fa-stopwatch", `${scan.duration_sec}s`, "Scan Duration"],
        ["fa-shield-halved", `${scan.risk_score}/100`, "Risk Score"],
      ]
    : [
        ["fa-bullseye", "--", "Last Target"],
        ["fa-network-wired", "--", "Resolved IP"],
        ["fa-door-open", "0", "Open Ports"],
        ["fa-lock", "0", "Closed Ports"],
        ["fa-stopwatch", "0s", "Scan Duration"],
        ["fa-shield-halved", "0/100", "Risk Score"],
      ];

  document.getElementById("heroStats").innerHTML = items
    .map(
      ([icon, value, label]) => `
      <div class="stat-card">
        <div class="icon"><i class="fa-solid ${icon}"></i></div>
        <div class="value">${value}</div>
        <div class="label">${label}</div>
      </div>`
    )
    .join("");
}

async function refreshSystemStats() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/system-stats`);
    const data = await res.json();
    document.getElementById("cpuValue").textContent = `${data.cpu_percent}%`;
    document.getElementById("cpuBar").style.width = `${data.cpu_percent}%`;
    document.getElementById("ramValue").textContent = `${data.ram_percent}%`;
    document.getElementById("ramBar").style.width = `${data.ram_percent}%`;
    document.getElementById("packetsSent").textContent = data.packets_sent.toLocaleString();
    document.getElementById("packetsRecv").textContent = data.packets_recv.toLocaleString();
  } catch (e) {
    // backend not running yet — silently skip
  }
}
setInterval(refreshSystemStats, 3000);
refreshSystemStats();

// ==========================================================================
// SCAN CONSOLE
// ==========================================================================
const scanTypeSelect = document.getElementById("scanTypeSelect");
const customPortsInput = document.getElementById("customPortsInput");
scanTypeSelect.addEventListener("change", () => {
  customPortsInput.style.display = scanTypeSelect.value === "custom" ? "block" : "none";
});

document.getElementById("startScanBtn").addEventListener("click", startScan);
document.getElementById("stopScanBtn").addEventListener("click", stopScan);

async function startScan() {
  const target = document.getElementById("targetInput").value.trim();
  if (!target) {
    toast("Enter a target first.", "warning");
    return;
  }

  const scan_type = scanTypeSelect.value;
  const ports = customPortsInput.value.trim();

  resetTerminal();
  logToTerminal(`$ Initiating ${scan_type} scan against ${target}`, "info");

  document.getElementById("startScanBtn").disabled = true;
  document.getElementById("stopScanBtn").disabled = false;
  seenLogCount = 0;

  try {
    const res = await fetch(`${BACKEND_URL}/api/scan/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target, scan_type, ports, grab_banners: true }),
    });
    const data = await res.json();
    if (data.error) {
      toast(data.error, "error");
      resetScanButtons();
      return;
    }
    currentJobId = data.job_id;
    pollTimer = setInterval(pollScan, 600);
  } catch (e) {
    toast("Could not reach backend. Is app.py running?", "error");
    resetScanButtons();
  }
}

async function stopScan() {
  if (!currentJobId) return;
  await fetch(`${BACKEND_URL}/api/scan/stop/${currentJobId}`, { method: "POST" });
  toast("Stopping scan...", "warning");
}

function resetScanButtons() {
  document.getElementById("startScanBtn").disabled = false;
  document.getElementById("stopScanBtn").disabled = true;
}

async function pollScan() {
  if (!currentJobId) return;
  const res = await fetch(`${BACKEND_URL}/api/scan/status/${currentJobId}`);
  const job = await res.json();

  const newLogs = job.logs.slice(seenLogCount);
  newLogs.forEach((line) => {
    let cls = "info";
    if (line.includes("[OPEN]")) cls = "open";
    else if (line.includes("[WARN]")) cls = "warn";
    else if (line.includes("[ERROR]")) cls = "error";
    logToTerminal(line, cls);
  });
  seenLogCount = job.logs.length;

  document.getElementById("scanProgress").style.width = `${job.progress}%`;
  document.getElementById("scanProgressLabel").textContent =
    job.status === "running" ? `Scanning... ${job.progress}%` : job.status;

  if (job.results && job.results.length) {
    lastScanResults = job.results;
    renderPortsTable(lastScanResults);
  }

  if (job.status === "completed" || job.status === "stopped" || job.status === "error") {
    clearInterval(pollTimer);
    resetScanButtons();
    currentJobId = null;

    if (job.status === "completed" && job.record) {
      renderHeroStats(job.record);
      toast(`Scan complete — ${job.record.open_ports} open ports found`, "success");
      if (job.record.risk_score >= 50) toast("Critical exposure detected — check Security Intel", "error");
      loadHistory();
    } else if (job.status === "error") {
      toast("Scan failed — check target and try again.", "error");
    }
  }
}

function resetTerminal() {
  document.getElementById("terminal").innerHTML = "";
  document.getElementById("portsBody").innerHTML = "";
}

function logToTerminal(text, cls = "info") {
  const term = document.getElementById("terminal");
  const line = document.createElement("div");
  line.className = `term-line ${cls}`;
  line.textContent = text;
  term.appendChild(line);
  term.scrollTop = term.scrollHeight;
}

function renderPortsTable(results) {
  const search = document.getElementById("portSearch").value.toLowerCase();
  const riskFilter = document.getElementById("riskFilter").value;

  const filtered = results.filter((r) => {
    const matchesSearch = String(r.port).includes(search) || r.service.toLowerCase().includes(search);
    const matchesRisk = riskFilter === "all" || r.risk === riskFilter;
    return matchesSearch && matchesRisk;
  });

  document.getElementById("portsBody").innerHTML = filtered
    .map(
      (r) => `
      <tr>
        <td>${r.port}</td>
        <td>${r.service}</td>
        <td><span class="badge ${r.state}">${r.state}</span></td>
        <td><span class="badge ${r.risk}">${r.risk}</span></td>
        <td title="${r.description}">${r.version}</td>
      </tr>`
    )
    .join("");
}
document.getElementById("portSearch").addEventListener("input", () => renderPortsTable(lastScanResults));
document.getElementById("riskFilter").addEventListener("change", () => renderPortsTable(lastScanResults));

// ==========================================================================
// NETWORK DISCOVERY
// ==========================================================================
document.getElementById("discoverBtn").addEventListener("click", async () => {
  const cidr = document.getElementById("cidrInput").value.trim();
  if (!cidr) {
    toast("Enter a CIDR range, e.g. 192.168.1.0/24", "warning");
    return;
  }
  document.getElementById("deviceGrid").innerHTML = `<div class="empty-state">Sweeping ${cidr}... this can take 10-30s</div>`;
  try {
    const res = await fetch(`${BACKEND_URL}/api/discover`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cidr }),
    });
    const data = await res.json();
    if (data.error) {
      toast(data.error, "error");
      document.getElementById("deviceGrid").innerHTML = "";
      return;
    }
    renderDevices(data.devices);
    toast(`${data.count} device(s) discovered`, "success");
  } catch (e) {
    toast("Discovery failed — is the backend running?", "error");
  }
});

function renderDevices(devices) {
  const grid = document.getElementById("deviceGrid");
  if (!devices.length) {
    grid.innerHTML = `<div class="empty-state">No live hosts found on that range.</div>`;
    return;
  }
  grid.innerHTML = devices
    .map(
      (d) => `
      <div class="glass device-card">
        <div class="dc-top">
          <span class="dc-ip">${d.ip}</span>
          <span class="badge open">online</span>
        </div>
        <div class="dc-row"><i class="fa-solid fa-tag"></i> ${d.hostname}</div>
        <div class="dc-row"><i class="fa-solid fa-microchip"></i> ${d.mac}</div>
        <div class="dc-row"><i class="fa-solid fa-industry"></i> ${d.vendor}</div>
      </div>`
    )
    .join("");
}

// ==========================================================================
// ANALYTICS (Chart.js — all real, from lastScanResults + historyCache)
// ==========================================================================
function renderCharts() {
  const ctxState = document.getElementById("chartPortState");
  const ctxRisk = document.getElementById("chartRisk");
  const ctxServices = document.getElementById("chartServices");
  const ctxDuration = document.getElementById("chartDuration");

  const openCount = lastScanResults.filter((r) => r.state === "open").length;
  const closedCount = lastScanResults.filter((r) => r.state === "closed").length;

  const riskCounts = { critical: 0, high: 0, medium: 0, low: 0 };
  lastScanResults.filter((r) => r.state === "open").forEach((r) => riskCounts[r.risk]++);

  const serviceCounts = {};
  lastScanResults.filter((r) => r.state === "open").forEach((r) => {
    serviceCounts[r.service] = (serviceCounts[r.service] || 0) + 1;
  });

  Object.values(charts).forEach((c) => c.destroy());

  const gridColor = "rgba(255,255,255,0.06)";
  const textColor = "#7d8ba3";

  charts.state = new Chart(ctxState, {
    type: "doughnut",
    data: {
      labels: ["Open", "Closed"],
      datasets: [{ data: [openCount, closedCount], backgroundColor: ["#34d399", "#334155"] }],
    },
    options: { plugins: { legend: { labels: { color: textColor } } } },
  });

  charts.risk = new Chart(ctxRisk, {
    type: "bar",
    data: {
      labels: Object.keys(riskCounts),
      datasets: [{ label: "Findings", data: Object.values(riskCounts), backgroundColor: ["#f87171", "#fb923c", "#fbbf24", "#34d399"] }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: textColor }, grid: { color: gridColor } }, y: { ticks: { color: textColor }, grid: { color: gridColor } } },
    },
  });

  charts.services = new Chart(ctxServices, {
    type: "bar",
    data: {
      labels: Object.keys(serviceCounts),
      datasets: [{ label: "Open instances", data: Object.values(serviceCounts), backgroundColor: "#22d3ee" }],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: textColor }, grid: { color: gridColor } }, y: { ticks: { color: textColor }, grid: { color: gridColor } } },
    },
  });

  charts.duration = new Chart(ctxDuration, {
    type: "line",
    data: {
      labels: historyCache.slice(0, 10).reverse().map((h) => h.target),
      datasets: [{ label: "Duration (s)", data: historyCache.slice(0, 10).reverse().map((h) => h.duration_sec), borderColor: "#3b82f6", tension: 0.35 }],
    },
    options: {
      plugins: { legend: { labels: { color: textColor } } },
      scales: { x: { ticks: { color: textColor }, grid: { color: gridColor } }, y: { ticks: { color: textColor }, grid: { color: gridColor } } },
    },
  });
}

// ==========================================================================
// HISTORY
// ==========================================================================
async function loadHistory() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/history`);
    historyCache = await res.json();
    renderHistory();
    renderRecentActivity();
  } catch (e) {
    toast("Could not load history.", "error");
  }
}

function renderHistory() {
  const search = document.getElementById("historySearch").value.toLowerCase();
  const filtered = historyCache.filter((h) => h.target.toLowerCase().includes(search));

  document.getElementById("historyBody").innerHTML = filtered
    .map(
      (h) => `
      <tr>
        <td>${new Date(h.date).toLocaleString()}</td>
        <td>${h.target}</td>
        <td>${h.scan_type}</td>
        <td>${h.duration_sec}s</td>
        <td>${h.open_ports}</td>
        <td><span class="badge ${riskBand(h.risk_score)}">${h.risk_score}/100</span></td>
        <td>
          <button class="icon-btn" onclick="exportReport('${h.id}','pdf')" title="PDF"><i class="fa-solid fa-file-pdf"></i></button>
          <button class="icon-btn" onclick="exportReport('${h.id}','csv')" title="CSV"><i class="fa-solid fa-file-csv"></i></button>
          <button class="icon-btn" onclick="exportReport('${h.id}','json')" title="JSON"><i class="fa-solid fa-file-code"></i></button>
          <button class="icon-btn" onclick="deleteHistory('${h.id}')" title="Delete"><i class="fa-solid fa-trash"></i></button>
        </td>
      </tr>`
    )
    .join("");
}
document.getElementById("historySearch").addEventListener("input", renderHistory);

function renderRecentActivity() {
  const box = document.getElementById("recentActivity");
  if (!historyCache.length) return;
  box.classList.remove("empty-state");
  box.innerHTML = historyCache
    .slice(0, 5)
    .map((h) => `<div class="dc-row"><i class="fa-solid fa-circle-check" style="color:var(--green)"></i> Scanned <b>${h.target}</b> — ${h.open_ports} open ports, risk ${h.risk_score}/100</div>`)
    .join("");
}

function riskBand(score) {
  if (score >= 60) return "critical";
  if (score >= 35) return "high";
  if (score >= 15) return "medium";
  return "low";
}

async function exportReport(scanId, fmt) {
  window.open(`${BACKEND_URL}/api/export/${fmt}/${scanId}`, "_blank");
  toast(`Exporting ${fmt.toUpperCase()} report...`, "success");
}

async function deleteHistory(scanId) {
  await fetch(`${BACKEND_URL}/api/history/${scanId}`, { method: "DELETE" });
  toast("Scan deleted from history.", "warning");
  loadHistory();
}

// ==========================================================================
// SECURITY INTEL
// ==========================================================================
async function loadIntel() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/port-intel`);
    const data = await res.json();
    document.getElementById("intelBody").innerHTML = Object.entries(data)
      .map(
        ([port, [service, risk, desc]]) => `
        <tr>
          <td>${port}</td>
          <td>${service}</td>
          <td><span class="badge ${risk}">${risk}</span></td>
          <td>${desc}</td>
        </tr>`
      )
      .join("");
  } catch (e) {
    toast("Could not load security intel reference.", "error");
  }
}

// ==========================================================================
// FAB — quick jump to scan console
// ==========================================================================
document.getElementById("fab").addEventListener("click", () => {
  switchTab("scan");
  document.getElementById("targetInput").focus();
});

// ==========================================================================
// INIT
// ==========================================================================
renderHeroStats(null);
loadHistory();