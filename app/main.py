from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from app.config import APP_NAME, APP_VERSION, APP_DESCRIPTION, HOST, PORT
from app.routes import health, scan, scrape, clean

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.info(f"Docs: http://{HOST}:{PORT}/docs")
    yield
    logger.info(f"Shutting down {APP_NAME}")


app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(scan.router, tags=["Scan"])
app.include_router(scrape.router, tags=["Scrape"])
app.include_router(clean.router, tags=["Clean"])

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>DataSnoop 🔍</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 2rem 1rem; }
    .page { max-width: 860px; margin: 0 auto; }

    /* Hero */
    .hero { display: flex; align-items: center; gap: 1.25rem; margin-bottom: .5rem; flex-wrap: wrap; }
    .hero h1 { font-size: 2.6rem; font-weight: 900; background: linear-gradient(135deg,#6366f1,#a855f7,#ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero-sub { color: #94a3b8; font-size: .95rem; margin-top: .2rem; }
    .tagline { color: #94a3b8; line-height: 1.7; margin-bottom: 2rem; font-size: .95rem; }

    /* Panels */
    .panel { background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 1.4rem; margin-bottom: 1rem; }
    .panel h2 { font-size: .95rem; font-weight: 700; margin-bottom: 1rem; color: #f1f5f9; }

    /* Buttons */
    .btn { display: inline-block; padding: .6rem 1.4rem; border-radius: 8px; font-weight: 700; font-size: .875rem; cursor: pointer; border: none; transition: opacity .15s, transform .1s; text-decoration: none; }
    .btn:hover { opacity: .85; transform: translateY(-1px); }
    .btn:active { transform: translateY(0); }
    .btn-primary { background: linear-gradient(135deg,#6366f1,#a855f7); color: #fff; }
    .btn-ghost { background: #0f172a; border: 1px solid #475569; color: #e2e8f0; }

    /* Dataset chips */
    .chips { display: flex; flex-wrap: wrap; gap: .5rem; }
    .chip { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: .45rem .9rem; cursor: pointer; font-size: .82rem; color: #94a3b8; transition: all .15s; }
    .chip:hover { border-color: #6366f1; color: #c084fc; }
    .chip strong { display: block; color: #e2e8f0; font-size: .85rem; }

    /* Upload zone */
    .upload-zone { border: 2px dashed #334155; border-radius: 10px; padding: 2rem; text-align: center; cursor: pointer; transition: border-color .2s; }
    .upload-zone:hover, .upload-zone.drag { border-color: #6366f1; background: rgba(99,102,241,.05); }
    .upload-zone p { color: #94a3b8; font-size: .875rem; margin-top: .5rem; }
    #file-input { display: none; }

    /* Loading */
    .loading { text-align: center; padding: 2rem; color: #94a3b8; }
    .spinner { width: 36px; height: 36px; border: 3px solid #334155; border-top-color: #6366f1; border-radius: 50%; animation: spin .8s linear infinite; margin: 0 auto 1rem; }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Results */
    #results { display: none; }
    .result-header { display: flex; align-items: flex-start; gap: 1.25rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .score-ring { width: 90px; height: 90px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; flex-shrink: 0; border: 4px solid; }
    .score-ring .score-num { font-size: 1.6rem; font-weight: 900; line-height: 1; }
    .score-ring .score-label { font-size: .65rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; margin-top: 2px; }
    .result-title { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; margin-bottom: .4rem; word-break: break-all; }
    .result-summary { font-size: .875rem; color: #94a3b8; line-height: 1.6; }

    /* Stats row */
    .stats { display: flex; flex-wrap: wrap; gap: .75rem; margin-bottom: 1.25rem; }
    .stat { background: #0f172a; border-radius: 10px; padding: .75rem 1rem; flex: 1; min-width: 90px; text-align: center; }
    .stat .stat-val { font-size: 1.25rem; font-weight: 800; color: #f1f5f9; }
    .stat .stat-key { font-size: .7rem; color: #64748b; text-transform: uppercase; letter-spacing: .05em; margin-top: 2px; }

    /* Recommendations */
    .rec { background: #0f172a; border-left: 3px solid #6366f1; border-radius: 0 8px 8px 0; padding: .75rem 1rem; margin-bottom: .5rem; font-size: .875rem; line-height: 1.55; color: #cbd5e1; }

    /* Column cards */
    .col-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: .75rem; }
    .col-card { background: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 1rem; }
    .col-card .col-name { font-weight: 700; color: #f1f5f9; font-size: .9rem; margin-bottom: .2rem; word-break: break-all; }
    .col-card .col-type { font-size: .7rem; color: #6366f1; text-transform: uppercase; letter-spacing: .06em; margin-bottom: .6rem; }
    .null-track { background: #1e293b; border-radius: 4px; height: 5px; margin-bottom: .6rem; }
    .null-fill { height: 5px; border-radius: 4px; background: #ef4444; }
    .col-meta { display: flex; flex-wrap: wrap; gap: .35rem; }
    .tag { font-size: .7rem; padding: .15rem .45rem; border-radius: 4px; background: #1e293b; color: #94a3b8; }
    .tag.bad { background: rgba(239,68,68,.15); color: #f87171; }
    .col-samples { font-size: .72rem; color: #475569; margin-top: .5rem; }

    .section-title { font-size: .8rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .07em; margin-bottom: .75rem; }

    /* Suggestions */
    .suggestion-card { background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 1rem; display: flex; align-items: center; gap: 1rem; margin-bottom: .75rem; }
    .suggestion-icon { flex-shrink: 0; font-size: 1.5rem; }
    .suggestion-body { flex-grow: 1; }
    .suggestion-title { font-weight: 700; color: #f1f5f9; font-size: .9rem; margin-bottom: .2rem; }
    .suggestion-desc { font-size: .85rem; color: #94a3b8; line-height: 1.5; }
    .suggestion-actions { flex-shrink: 0; display: flex; gap: .5rem; }

    .mb { margin-bottom: 1.25rem; }
    .gap { margin-bottom: 1rem; }
    .link { color: #818cf8; font-size: .82rem; text-decoration: none; }
    .link:hover { text-decoration: underline; }
  </style>
</head>
<body>
<div class="page">

  <!-- Hero -->
  <div class="hero">
    <svg width="72" height="72" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style="filter:drop-shadow(0 4px 16px rgba(99,102,241,.5));flex-shrink:0">
      <ellipse cx="25" cy="36" rx="13" ry="22" fill="#c8956c" transform="rotate(-15 25 36)"/>
      <ellipse cx="75" cy="36" rx="13" ry="22" fill="#c8956c" transform="rotate(15 75 36)"/>
      <ellipse cx="50" cy="60" rx="32" ry="28" fill="#e8b88a"/>
      <ellipse cx="38" cy="53" rx="9" ry="9" fill="white"/>
      <ellipse cx="62" cy="53" rx="9" ry="9" fill="white"/>
      <circle cx="39" cy="54" r="5" fill="#1a1a2e"/>
      <circle cx="63" cy="54" r="5" fill="#1a1a2e"/>
      <circle cx="41" cy="52" r="2" fill="white"/>
      <circle cx="65" cy="52" r="2" fill="white"/>
      <ellipse cx="50" cy="68" rx="7" ry="5" fill="#3d1a0e"/>
      <path d="M43 73 Q50 80 57 73" stroke="#3d1a0e" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      <line x1="76" y1="30" x2="90" y2="16" stroke="#6366f1" stroke-width="5" stroke-linecap="round"/>
      <circle cx="68" cy="37" r="14" fill="none" stroke="#6366f1" stroke-width="4.5"/>
      <circle cx="68" cy="37" r="10" fill="rgba(99,102,241,0.18)"/>
      <path d="M62 32 Q65 29 70 30" stroke="rgba(255,255,255,0.55)" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>
    <div>
      <h1>DataSnoop</h1>
      <div class="hero-sub">Your friendly data detective 🕵️</div>
    </div>
  </div>
  <p class="tagline">Drop in a CSV or pick a live dataset — DataSnoop checks for missing values, outliers, and quality issues, then explains what it found in plain English.</p>

  <!-- Quick demo -->
  <div class="panel gap">
    <h2>⚡ Quick demo — see it in action</h2>
    <button class="btn btn-primary" onclick="runDemo()">Analyze sample data</button>
    <span style="color:#475569;font-size:.82rem;margin-left:.75rem;">No file needed — runs on built-in employee data</span>
  </div>

  <!-- Upload -->
  <div class="panel gap">
    <h2>📁 Upload your own CSV</h2>
    <div class="upload-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="1.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
      <p>Click to choose a file, or drag and drop it here</p>
      <p style="margin-top:.3rem;font-size:.75rem;color:#334155;">CSV files only · max 500 MB</p>
    </div>
    <input type="file" id="file-input" accept=".csv" onchange="uploadFile(this.files[0])"/>
  </div>

  <!-- Live datasets -->
  <div class="panel gap">
    <h2>🌐 Fetch live data from the web</h2>
    <div class="chips">
      <div class="chip" onclick="scrape('crypto','Top 100 Cryptocurrencies')"><strong>💰 Crypto</strong>Live prices</div>
      <div class="chip" onclick="scrape('countries','World Countries')"><strong>🌍 Countries</strong>World data</div>
      <div class="chip" onclick="scrape('spacex','SpaceX Launches')"><strong>🚀 SpaceX</strong>All launches</div>
      <div class="chip" onclick="scrape('products','Product Catalog')"><strong>🛒 Products</strong>100 items</div>
      <div class="chip" onclick="scrape('nutrition','Fruit Nutrition')"><strong>🍎 Nutrition</strong>Fruit facts</div>
      <div class="chip" onclick="scrape('quotes','Famous Quotes')"><strong>💬 Quotes</strong>100 quotes</div>
      <div class="chip" onclick="scrape('people','User Profiles')"><strong>👤 People</strong>Fake users</div>
      <div class="chip" onclick="scrape('posts','Blog Posts')"><strong>📝 Posts</strong>100 posts</div>
      <div class="chip" onclick="scrape('todos','Task List')"><strong>✅ Todos</strong>200 tasks</div>
    </div>
  </div>

  <!-- Results panel -->
  <div id="results">
    <div class="panel">
      <div id="results-inner"><div class="loading"><div class="spinner"></div>Analyzing…</div></div>
    </div>
    <p style="text-align:center;margin-top:.5rem;"><a href="/docs" class="link">View full API docs →</a></p>
  </div>

</div>

<script>
  // ── helpers ──────────────────────────────────────────────────────────────────
  function healthColor(score) {
    if (score >= 85) return '#22c55e';
    if (score >= 65) return '#eab308';
    if (score >= 40) return '#f97316';
    return '#ef4444';
  }

  function getIconForIssue(issueType) {
    if (issueType.includes('Missing')) return '💧';
    if (issueType.includes('Outlier')) return '⚡️';
    if (issueType.includes('Inconsistent')) return '🎭';
    return '🔧';
  }

  function showLoading(msg) {
    const el = document.getElementById('results');
    el.style.display = 'block';
    document.getElementById('results-inner').innerHTML =
      `<div class="loading"><div class="spinner"></div>${msg}</div>`;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function showError(msg) {
    document.getElementById('results-inner').innerHTML =
      `<div class="loading" style="color:#f87171;">❌ ${msg}</div>`;
  }

  // ── render ───────────────────────────────────────────────────────────────────
  function renderResults(data) {
    window.currentScanData = data; // Store data globally for actions

    const color = healthColor(data.health_score);

    const statsHtml = [
      { val: data.total_rows.toLocaleString(), key: 'Rows' },
      { val: data.total_columns, key: 'Columns' },
      { val: data.null_percentage + '%', key: 'Missing' },
      { val: data.outlier_count, key: 'Outliers' },
      { val: (data.anomaly_score * 100).toFixed(1) + '%', key: 'Anomalies (ML)' },
    ].map(s => `<div class="stat"><div class="stat-val">${s.val}</div><div class="stat-key">${s.key}</div></div>`).join('');

    const recsHtml = data.recommendations.map(r => `<div class="rec">${r}</div>`).join('');

    const colsHtml = data.columns.map(col => {
      const nullW = Math.min(100, col.null_percentage);
      const tags = [
        `<span class="tag">${col.null_percentage}% missing</span>`,
        `<span class="tag">${col.unique_values} unique</span>`,
        col.mean_value !== null && col.mean_value !== undefined
          ? `<span class="tag">avg ${col.mean_value}</span>` : '',
        col.outlier_count
          ? `<span class="tag bad">⚠ ${col.outlier_count} outlier${col.outlier_count>1?'s':''}</span>` : '',
      ].filter(Boolean).join('');
      const samples = col.sample_values.slice(0, 3).join(', ');
      return `<div class="col-card">
        <div class="col-name">${col.name}</div>
        <div class="col-type">${col.data_type}</div>
        <div class="null-track"><div class="null-fill" style="width:${nullW}%"></div></div>
        <div class="col-meta">${tags}</div>
        ${samples ? `<div class="col-samples">e.g. ${samples}</div>` : ''}
      </div>`;
    }).join('');

    const suggestionsHtml = data.suggestions.map(s => {
      const actionsHtml = s.suggested_actions.map(action =>
        `<button class="btn btn-ghost" onclick='applyFix(this, ${JSON.stringify(action)})'>
          ${action.description}
        </button>`
      ).join('');

      return `<div class="suggestion-card">
        <div class="suggestion-icon">${getIconForIssue(s.issue_type)}</div>
        <div class="suggestion-body">
          <div class="suggestion-title">${s.issue_type} in <code>${s.column}</code></div>
          <div class="suggestion-desc">${s.description}</div>
        </div>
        <div class="suggestion-actions">${actionsHtml}</div>
      </div>`;
    }).join('');

    const sourceHtml = data.source_url
      ? `<p style="font-size:.78rem;color:#475569;margin-top:.3rem;">Source: ${data.source_url}</p>` : '';

    document.getElementById('results-inner').innerHTML = `
      <div class="result-header">
        <div class="score-ring" style="border-color:${color};color:${color}">
          <span class="score-num">${data.health_score}</span>
          <span class="score-label">${data.overall_health}</span>
        </div>
        <div>
          <div class="result-title">${data.dataset_name}</div>
          <div class="result-summary">${data.summary}</div>
          ${sourceHtml}
        </div>
      </div>

      <div class="section-title mb">Key numbers</div>
      <div class="stats mb">${statsHtml}</div>

      <div class="section-title mb">What DataSnoop found</div>
      <div class="mb">${recsHtml}</div>

      ${suggestionsHtml ? `
        <div class="section-title mb">Actionable Suggestions</div>
        <div class="mb">${suggestionsHtml}</div>
      ` : ''}

      <div class="section-title mb">Column breakdown</div>
      <div class="col-grid">${colsHtml}</div>
    `;
  }

  // ── actions ──────────────────────────────────────────────────────────────────
  async function runDemo() {
    showLoading('Analyzing sample employee data…');
    try {
      const r = await fetch('/api/v1/demo');
      if (!r.ok) throw new Error(await r.text());
      renderResults(await r.json());
    } catch(e) { showError('Could not run demo: ' + e.message); }
  }

  async function scrape(id, name) {
    showLoading('Fetching ' + name + ' from the web…');
    try {
      const r = await fetch('/api/v1/scrape/' + id);
      if (!r.ok) throw new Error(await r.text());
      renderResults(await r.json());
    } catch(e) { showError('Could not fetch ' + name + ': ' + e.message); }
  }

  async function applyFix(btn, action) {
  const sessionId = window.currentScanData?.file_id;
  if (!sessionId) {
    showError("Cannot apply fix: no session found. Please re-upload the file.");
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Applying...';

  try {
    // Step 1: apply the cleaning action, update session in memory
    const response = await fetch('/api/v1/clean', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, actions: [action] })
    });

    if (!response.ok) throw new Error((await response.json()).detail);

    btn.textContent = '✅ Applied';

    // Step 2: show a download button so the user can grab the file when ready
    const existingDownload = document.getElementById('download-btn');
    if (!existingDownload) {
      const dlBtn = document.createElement('a');
      dlBtn.id = 'download-btn';
      dlBtn.className = 'btn btn-primary';
      dlBtn.style.marginTop = '1rem';
      dlBtn.style.display = 'inline-block';
      dlBtn.textContent = '⬇️ Download cleaned CSV';
      dlBtn.href = `/api/v1/download/${sessionId}`;
      dlBtn.download = `cleaned_${sessionId.substring(0, 8)}.csv`;
      document.getElementById('results-inner').prepend(dlBtn);
    }

  } catch (e) {
    btn.textContent = '❌ Failed';
    alert('Failed to apply fix: ' + e.message);
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = action.description;
    }, 2000);
  }
}

  async function uploadFile(file) {
    if (!file) return;
    showLoading('Analyzing ' + file.name + '…');
    const form = new FormData();
    form.append('file', file);
    try {
      const r = await fetch('/api/v1/scan/file', { method: 'POST', body: form });
      if (!r.ok) throw new Error((await r.json()).detail || await r.text());
      renderResults(await r.json());
    } catch(e) { showError('Could not read file: ' + e.message); }
  }

  // drag and drop
  const zone = document.getElementById('drop-zone');
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('drag');
    const f = e.dataTransfer.files[0];
    if (f) uploadFile(f);
  });
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    return _PAGE
