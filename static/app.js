// SysPulse Client Application Logic

let activeTab = 'telemetry';
let telemetrySocket = null;
let liveChart = null;
let currentSort = 'memory';
let pendingKillPid = null;
let pendingKillName = '';

const CHART_MAX_POINTS = 25;

// --- Initialize App ---
document.addEventListener('DOMContentLoaded', () => {
  initLiveChart();
  initWebSocket();
  fetchSystemSpecs();
  fetchInitialSnapshot();
  lucide.createIcons();
});

// --- Tab Switching ---
function switchTab(tab) {
  activeTab = tab;
  ['telemetry', 'procs', 'network', 'doctor'].forEach(t => {
    const el = document.getElementById(`tab-${t}`);
    const btn = document.getElementById(`tab-btn-${t}`);
    if (t === tab) {
      el.classList.remove('hidden');
      btn.classList.add('active');
    } else {
      el.classList.add('hidden');
      btn.classList.remove('active');
    }
  });

  if (tab === 'procs') fetchProcesses();
  if (tab === 'network') {
    fetchNetworkConnections();
    fetchNetworkLatency();
  }
  if (tab === 'doctor') {
    fetchHealthDiagnostics();
    fetchCacheSummary();
  }
}

// --- Live Chart.js Setup ---
function initLiveChart() {
  const ctx = document.getElementById('liveTelemetryChart').getContext('2d');
  
  // Cyberpunk gradient fills
  const gradCyan = ctx.createLinearGradient(0, 0, 0, 250);
  gradCyan.addColorStop(0, 'rgba(6, 182, 212, 0.35)');
  gradCyan.addColorStop(1, 'rgba(6, 182, 212, 0.0)');

  const gradBlue = ctx.createLinearGradient(0, 0, 0, 250);
  gradBlue.addColorStop(0, 'rgba(59, 130, 246, 0.35)');
  gradBlue.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

  liveChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'CPU %',
          data: [],
          borderColor: '#06b6d4',
          backgroundColor: gradCyan,
          fill: true,
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 4
        },
        {
          label: 'RAM %',
          data: [],
          borderColor: '#3b82f6',
          backgroundColor: gradBlue,
          fill: true,
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
        },
        y: {
          min: 0,
          max: 100,
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 }, stepSize: 20 }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: '#0f172a',
          borderColor: '#334155',
          borderWidth: 1,
          titleFont: { family: 'JetBrains Mono' },
          bodyFont: { family: 'JetBrains Mono' }
        }
      }
    }
  });
}

function updateChart(timestamp, cpuVal, ramVal) {
  if (!liveChart) return;
  liveChart.data.labels.push(timestamp);
  liveChart.data.datasets[0].data.push(cpuVal);
  liveChart.data.datasets[1].data.push(ramVal);

  if (liveChart.data.labels.length > CHART_MAX_POINTS) {
    liveChart.data.labels.shift();
    liveChart.data.datasets[0].data.shift();
    liveChart.data.datasets[1].data.shift();
  }
  liveChart.update('none');
}

// --- WebSocket Streaming ---
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

  telemetrySocket = new WebSocket(wsUrl);

  const indicator = document.getElementById('ws-indicator');
  const statusText = document.getElementById('ws-status-text');

  telemetrySocket.onopen = () => {
    indicator.className = 'w-2.5 h-2.5 rounded-full bg-emerald-500 pulse-active';
    statusText.innerText = 'Live';
    statusText.className = 'text-emerald-400 font-medium';
  };

  telemetrySocket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'telemetry_tick') {
        handleTelemetryTick(data);
      }
    } catch (e) {
      console.error('Error parsing telemetry frame:', e);
    }
  };

  telemetrySocket.onclose = () => {
    indicator.className = 'w-2.5 h-2.5 rounded-full bg-rose-500';
    statusText.innerText = 'Reconnecting...';
    statusText.className = 'text-rose-400 font-medium';
    setTimeout(initWebSocket, 2000);
  };
}

function handleTelemetryTick(data) {
  // 1. CPU
  const cpuPct = data.cpu.overall_percent;
  document.getElementById('metric-cpu-val').innerText = cpuPct.toFixed(1);
  document.getElementById('metric-cpu-bar').style.width = `${Math.min(cpuPct, 100)}%`;
  
  if (data.cpu.current_freq_mhz) {
    document.getElementById('metric-cpu-freq').innerText = `${(data.cpu.current_freq_mhz / 1000).toFixed(2)} GHz`;
  }

  // 2. RAM
  const ramPct = data.memory.ram.percent;
  document.getElementById('metric-ram-val').innerText = ramPct.toFixed(1);
  document.getElementById('metric-ram-bar').style.width = `${Math.min(ramPct, 100)}%`;
  document.getElementById('metric-ram-sub').innerText = `${data.memory.ram.used_gb} / ${data.memory.ram.total_gb} GB`;

  // 3. I/O Rates
  document.getElementById('metric-disk-read').innerText = formatRate(data.io.disk_read_kbs);
  document.getElementById('metric-disk-write').innerText = formatRate(data.io.disk_write_kbs);
  document.getElementById('metric-net-down').innerText = formatRate(data.io.net_download_kbs);
  document.getElementById('metric-net-up').innerText = formatRate(data.io.net_upload_kbs);

  // 4. Battery
  if (data.battery) {
    document.getElementById('metric-battery-val').innerText = data.battery.percent;
    document.getElementById('metric-battery-bar').style.width = `${data.battery.percent}%`;
    document.getElementById('metric-battery-status').innerText = data.battery.status_text;
  }

  // 5. Header Health Pill
  if (data.health) {
    document.getElementById('header-health-score').innerText = `${data.health.score}%`;
    document.getElementById('header-health-status').innerText = data.health.status;
  }

  // 6. Push to Scrolling Chart
  updateChart(data.timestamp, cpuPct, ramPct);

  // 7. Update Per-Core Matrix
  renderCoreMatrix(data.cpu.per_core_percent);
}

function formatRate(kbs) {
  if (kbs >= 1024) {
    return `${(kbs / 1024).toFixed(1)} MB/s`;
  }
  return `${kbs.toFixed(1)} KB/s`;
}

// --- Per-Core Load Matrix ---
function renderCoreMatrix(cores) {
  const container = document.getElementById('core-matrix-container');
  if (!cores || cores.length === 0) return;

  document.getElementById('core-count-badge').innerText = `${cores.length} Logical Cores`;

  // Render if empty or update values
  if (container.children.length !== cores.length) {
    container.innerHTML = cores.map((c, i) => `
      <div class="space-y-1">
        <div class="flex justify-between text-[11px] font-mono">
          <span class="text-slate-400">Core #${i}</span>
          <span id="core-val-${i}" class="text-cyan-400 font-semibold">${c}%</span>
        </div>
        <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
          <div id="core-bar-${i}" class="bg-cyan-500 h-1.5 progress-bar-fill" style="width: ${c}%"></div>
        </div>
      </div>
    `).join('');
  } else {
    cores.forEach((c, i) => {
      const valEl = document.getElementById(`core-val-${i}`);
      const barEl = document.getElementById(`core-bar-${i}`);
      if (valEl && barEl) {
        valEl.innerText = `${c}%`;
        barEl.style.width = `${Math.min(c, 100)}%`;
      }
    });
  }
}

// --- System Specifications & Initial Snapshot ---
async function fetchSystemSpecs() {
  try {
    const res = await fetch('/api/system');
    const data = await res.json();
    document.getElementById('spec-cpu').innerText = data.processor ? data.processor.split('@')[0].trim().slice(0, 22) : 'CPU';
    document.getElementById('spec-os').innerText = `${data.os} ${data.os_release}`;
    document.getElementById('spec-cores').innerText = `${data.logical_cores} Cores`;
  } catch (e) {
    console.error('Error fetching system specs:', e);
  }
}

async function fetchInitialSnapshot() {
  try {
    const res = await fetch('/api/snapshot');
    const data = await res.json();

    // Render Disks
    const disks = data.telemetry.disks || [];
    document.getElementById('disk-count-badge').innerText = `${disks.length} Volumes`;
    const disksGrid = document.getElementById('disks-grid');
    disksGrid.innerHTML = disks.map(d => `
      <div class="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
        <div class="flex items-center justify-between text-xs">
          <span class="font-bold font-mono text-white">${d.mountpoint} (${d.fstype})</span>
          <span class="font-mono text-emerald-400 font-semibold">${d.percent}%</span>
        </div>
        <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div class="bg-emerald-500 h-1.5" style="width: ${d.percent}%"></div>
        </div>
        <div class="flex justify-between text-[11px] text-slate-400 font-mono">
          <span>Used: ${d.used_gb} GB</span>
          <span>Free: ${d.free_gb} GB</span>
        </div>
      </div>
    `).join('');

    // Setup initial network info
    if (data.network && data.network.interfaces) {
      renderNetworkInterfaces(data.network.interfaces);
    }
  } catch (e) {
    console.error('Error fetching snapshot:', e);
  }
}

// --- TAB 2: HOG HUNTER (PROCESS MANAGER) ---
async function fetchProcesses() {
  const query = document.getElementById('proc-search-input').value.trim();
  const url = `/api/processes?sort_by=${currentSort}&limit=60&search=${encodeURIComponent(query)}`;

  try {
    const res = await fetch(url);
    const procs = await res.json();
    renderProcessTable(procs);
  } catch (e) {
    console.error('Error fetching processes:', e);
  }
}

function handleProcessSearch() {
  clearTimeout(window.searchTimeout);
  window.searchTimeout = setTimeout(fetchProcesses, 250);
}

function setProcessSort(sortKey) {
  currentSort = sortKey;
  ['memory', 'cpu', 'name'].forEach(k => {
    const btn = document.getElementById(`sort-btn-${k}`);
    if (k === sortKey) {
      btn.className = 'px-3 py-1.5 rounded-lg text-xs font-medium bg-cyan-950 text-cyan-300 border border-cyan-800/80';
    } else {
      btn.className = 'px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200';
    }
  });
  fetchProcesses();
}

function renderProcessTable(procs) {
  const tbody = document.getElementById('process-table-body');
  if (!procs || procs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-slate-500 font-sans">No matching processes found.</td></tr>`;
    return;
  }

  tbody.innerHTML = procs.map(p => `
    <tr class="hover:bg-slate-900/60 transition-colors">
      <td class="py-2.5 px-4 text-slate-400">${p.pid}</td>
      <td class="py-2.5 px-4">
        <div class="flex items-center space-x-2">
          <span class="font-semibold text-slate-200">${escapeHtml(p.name)}</span>
          ${p.is_protected ? '<span class="px-1.5 py-0.2 rounded bg-slate-800 text-[10px] text-slate-400 border border-slate-700">SYSTEM</span>' : ''}
        </div>
      </td>
      <td class="py-2.5 px-4 text-right font-bold ${p.cpu_percent > 20 ? 'text-rose-400' : 'text-slate-300'}">${p.cpu_percent}%</td>
      <td class="py-2.5 px-4 text-right font-bold ${p.memory_mb > 500 ? 'text-amber-400' : 'text-slate-300'}">${p.memory_mb.toLocaleString()} MB</td>
      <td class="py-2.5 px-4 text-slate-400">${p.threads}</td>
      <td class="py-2.5 px-4 text-slate-400">${escapeHtml(p.username.split('\\').pop() || 'N/A')}</td>
      <td class="py-2.5 px-4 text-center">
        ${p.is_protected ? 
          '<span class="text-slate-600 text-[11px]">Protected</span>' :
          `<button onclick="openKillModal(${p.pid}, '${escapeHtml(p.name)}')" class="px-2.5 py-1 rounded bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800/60 text-[11px] font-sans transition-colors">Terminate</button>`
        }
      </td>
    </tr>
  `).join('');
}

// --- Process Kill Confirmation ---
function openKillModal(pid, name) {
  pendingKillPid = pid;
  pendingKillName = name;
  document.getElementById('kill-proc-name').innerText = name;
  document.getElementById('kill-proc-pid').innerText = pid;
  document.getElementById('kill-modal').classList.remove('hidden');
}

function closeKillModal() {
  pendingKillPid = null;
  document.getElementById('kill-modal').classList.add('hidden');
}

async function executeProcessKill() {
  if (!pendingKillPid) return;
  const pid = pendingKillPid;
  const name = pendingKillName;
  closeKillModal();

  try {
    const res = await fetch(`/api/processes/${pid}/kill`, { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Process '${name}' (PID ${pid}) terminated`, 'success');
      fetchProcesses();
    } else {
      showToast(data.detail || data.message || 'Failed to terminate process', 'error');
    }
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  }
}

// --- TAB 3: NETWORK RADAR ---
async function fetchNetworkLatency() {
  try {
    const res = await fetch('/api/network/latency');
    const data = await res.json();
    const valEl = document.getElementById('net-latency-val');
    const descEl = document.getElementById('net-latency-desc');

    if (data.latency_ms !== null) {
      valEl.innerText = data.latency_ms;
      if (data.latency_ms < 60) {
        descEl.innerText = 'Ultra Low Latency (Excellent)';
        descEl.className = 'text-xs text-emerald-400 mt-1';
      } else if (data.latency_ms < 120) {
        descEl.innerText = 'Moderate Latency (Normal)';
        descEl.className = 'text-xs text-cyan-400 mt-1';
      } else {
        descEl.innerText = 'High Latency / Jitter';
        descEl.className = 'text-xs text-amber-400 mt-1';
      }
    } else {
      valEl.innerText = '--';
      descEl.innerText = 'Timeout / Unreachable';
      descEl.className = 'text-xs text-rose-400 mt-1';
    }
  } catch (e) {
    console.error('Error fetching latency:', e);
  }
}

function renderNetworkInterfaces(adapters) {
  document.getElementById('net-adapter-count').innerText = adapters.length;
  const container = document.getElementById('interfaces-container');
  container.innerHTML = adapters.map(a => `
    <div class="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1 text-xs font-mono">
      <div class="flex items-center justify-between">
        <span class="font-bold text-slate-200">${escapeHtml(a.name)}</span>
        <span class="px-1.5 py-0.2 rounded text-[10px] ${a.is_up ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-500'}">
          ${a.is_up ? 'UP' : 'DOWN'}
        </span>
      </div>
      <div class="text-slate-400">IPv4: <span class="text-slate-200">${a.ipv4}</span></div>
      <div class="text-slate-500 text-[10px]">MAC: ${a.mac}</div>
    </div>
  `).join('');
}

async function fetchNetworkConnections() {
  try {
    const res = await fetch('/api/network/connections?limit=50');
    const conns = await res.json();
    document.getElementById('net-socket-count').innerText = conns.length;

    const tbody = document.getElementById('sockets-table-body');
    if (conns.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="py-6 text-center text-slate-500">No active sockets found.</td></tr>`;
      return;
    }

    tbody.innerHTML = conns.map(c => `
      <tr class="hover:bg-slate-900/60 transition-colors">
        <td class="py-2 px-4 text-cyan-400 font-bold">${c.protocol}</td>
        <td class="py-2 px-4 text-slate-200">${c.local_address}</td>
        <td class="py-2 px-4 ${c.remote_address !== 'None' ? 'text-sky-300' : 'text-slate-500'}">${c.remote_address}</td>
        <td class="py-2 px-4">
          <span class="px-1.5 py-0.5 rounded text-[10px] ${c.status === 'ESTABLISHED' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-400'}">
            ${c.status}
          </span>
        </td>
        <td class="py-2 px-4 font-semibold text-slate-300 font-sans">${escapeHtml(c.process_name)}</td>
        <td class="py-2 px-4 text-slate-500">${c.pid || '-'}</td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Error fetching sockets:', e);
  }
}

// --- TAB 4: DIAGNOSTICS & DOCTOR ---
async function fetchHealthDiagnostics() {
  try {
    const res = await fetch('/api/diagnostics/health');
    const data = await res.json();

    document.getElementById('doctor-score-val').innerText = `${data.health_score}%`;
    document.getElementById('doctor-score-badge').innerText = data.status_text;

    const container = document.getElementById('doctor-findings-container');
    container.innerHTML = data.findings.map(f => {
      let borderClass = 'border-slate-800';
      let iconColor = 'text-cyan-400';
      let iconName = 'info';

      if (f.level === 'critical') {
        borderClass = 'border-rose-900/60 bg-rose-950/20';
        iconColor = 'text-rose-400';
        iconName = 'alert-octagon';
      } else if (f.level === 'warning') {
        borderClass = 'border-amber-900/60 bg-amber-950/20';
        iconColor = 'text-amber-400';
        iconName = 'alert-triangle';
      }

      return `
        <div class="glass-panel p-4 rounded-xl border ${borderClass} flex items-start space-x-3">
          <div class="mt-0.5 ${iconColor}">
            <i data-lucide="${iconName}" class="w-5 h-5"></i>
          </div>
          <div class="space-y-0.5">
            <h4 class="text-sm font-bold text-white">${escapeHtml(f.title)}</h4>
            <p class="text-xs text-slate-300">${escapeHtml(f.message)}</p>
          </div>
        </div>
      `;
    }).join('');

    lucide.createIcons();
  } catch (e) {
    console.error('Error fetching health diagnostics:', e);
  }
}

async function fetchCacheSummary() {
  try {
    const res = await fetch('/api/diagnostics/cache');
    const data = await res.json();
    document.getElementById('cache-size-display').innerText = `${data.size_mb} MB (${data.file_count} files)`;
  } catch (e) {
    console.error('Error fetching cache:', e);
  }
}

async function executeCacheClean() {
  const btn = document.getElementById('clean-cache-btn');
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Purging...`;
  lucide.createIcons();

  try {
    const res = await fetch('/api/diagnostics/clean', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      fetchCacheSummary();
    } else {
      showToast(data.message, 'error');
    }
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="trash-2" class="w-4 h-4"></i> Clean Temp Files`;
    lucide.createIcons();
  }
}

async function exportDiagnosticReport() {
  try {
    const res = await fetch('/api/snapshot');
    const data = await res.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `syspulse_report_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Diagnostic report downloaded successfully', 'success');
  } catch (e) {
    showToast('Failed to export diagnostic report', 'error');
  }
}

// --- Utilities ---
function showToast(msg, type = 'info') {
  const toast = document.getElementById('toast');
  const msgEl = document.getElementById('toast-message');
  msgEl.innerText = msg;

  if (type === 'success') {
    toast.className = 'fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl border font-mono text-xs shadow-2xl flex items-center space-x-2 bg-emerald-950 border-emerald-700 text-emerald-200';
  } else if (type === 'error') {
    toast.className = 'fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl border font-mono text-xs shadow-2xl flex items-center space-x-2 bg-rose-950 border-rose-700 text-rose-200';
  } else {
    toast.className = 'fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl border font-mono text-xs shadow-2xl flex items-center space-x-2 bg-slate-900 border-slate-700 text-slate-200';
  }

  toast.classList.remove('hidden');
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => {
    toast.classList.add('hidden');
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
