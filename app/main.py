from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging

from app.config import APP_NAME, APP_VERSION, APP_DESCRIPTION, HOST, PORT
from app.routes import health, scan, scrape

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

_LANDING_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>DataSnoop</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f172a; color: #e2e8f0;
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      padding: 2rem;
    }
    .wrap { max-width: 800px; width: 100%; }

    /* ── Hero ── */
    .hero { display: flex; align-items: center; gap: 1.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
    .logo-svg { flex-shrink: 0; filter: drop-shadow(0 4px 24px rgba(99,102,241,.5)); }
    .hero-text h1 {
      font-size: 3rem; font-weight: 900; line-height: 1;
      background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .hero-text .sub { color: #94a3b8; font-size: 1rem; margin-top: .4rem; }
    .tagline { color: #cbd5e1; font-size: 1.05rem; line-height: 1.7; margin-bottom: 2rem; }

    /* ── Cards ── */
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: .9rem; margin-bottom: 2rem; }
    .card { background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 1.3rem; transition: border-color .2s; }
    .card:hover { border-color: #6366f1; }
    .icon { font-size: 1.7rem; margin-bottom: .6rem; }
    .card h3 { font-size: .9rem; font-weight: 700; color: #f1f5f9; margin-bottom: .35rem; }
    .card p { font-size: .8rem; color: #94a3b8; line-height: 1.55; }

    /* ── Buttons ── */
    .actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-bottom: 2rem; }
    .btn { padding: .6rem 1.4rem; border-radius: 9px; font-weight: 700; font-size: .875rem; text-decoration: none; transition: opacity .15s, transform .1s; display: inline-block; }
    .btn:hover { opacity: .85; transform: translateY(-1px); }
    .primary { background: linear-gradient(135deg, #6366f1, #a855f7); color: #fff; box-shadow: 0 4px 14px rgba(99,102,241,.35); }
    .secondary { background: #1e293b; border: 1px solid #475569; color: #e2e8f0; }

    /* ── Endpoints table ── */
    .ep-box { background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 1.4rem; }
    .ep-box h2 { font-size: .75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 1rem; }
    .ep { display: flex; align-items: flex-start; gap: .8rem; padding: .55rem 0; border-bottom: 1px solid #0f172a; }
    .ep:last-child { border-bottom: none; }
    .badge { font-size: .65rem; font-weight: 800; padding: .2rem .55rem; border-radius: 5px; white-space: nowrap; margin-top: 3px; }
    .get  { background: #064e3b; color: #34d399; }
    .post { background: #172554; color: #60a5fa; }
    .path { font-family: "Courier New", monospace; font-size: .85rem; color: #c084fc; }
    .desc { font-size: .78rem; color: #94a3b8; margin-top: 2px; }

    /* ── Datasets grid ── */
    .ds-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px,1fr)); gap: .6rem; margin-top: .75rem; }
    .ds-chip {
      background: #0f172a; border: 1px solid #334155; border-radius: 8px;
      padding: .5rem .75rem; text-decoration: none; color: #94a3b8;
      font-size: .78rem; transition: all .15s; text-align: center;
    }
    .ds-chip:hover { border-color: #6366f1; color: #c084fc; }
    .ds-chip strong { display: block; color: #e2e8f0; font-size: .82rem; margin-bottom: 2px; }
  </style>
</head>
<body>
<div class="wrap">

  <!-- Hero -->
  <div class="hero">
    <svg class="logo-svg" width="90" height="90" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <!-- Left ear -->
      <ellipse cx="25" cy="36" rx="13" ry="22" fill="#c8956c" transform="rotate(-15 25 36)"/>
      <!-- Right ear -->
      <ellipse cx="75" cy="36" rx="13" ry="22" fill="#c8956c" transform="rotate(15 75 36)"/>
      <!-- Head -->
      <ellipse cx="50" cy="60" rx="32" ry="28" fill="#e8b88a"/>
      <!-- White eye patches -->
      <ellipse cx="38" cy="53" rx="9" ry="9" fill="white"/>
      <ellipse cx="62" cy="53" rx="9" ry="9" fill="white"/>
      <!-- Pupils -->
      <circle cx="39" cy="54" r="5" fill="#1a1a2e"/>
      <circle cx="63" cy="54" r="5" fill="#1a1a2e"/>
      <!-- Eye shine -->
      <circle cx="41" cy="52" r="2" fill="white"/>
      <circle cx="65" cy="52" r="2" fill="white"/>
      <!-- Nose -->
      <ellipse cx="50" cy="68" rx="7" ry="5" fill="#3d1a0e"/>
      <!-- Smile -->
      <path d="M43 73 Q50 80 57 73" stroke="#3d1a0e" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      <!-- Magnifying glass handle -->
      <line x1="76" y1="30" x2="90" y2="16" stroke="#6366f1" stroke-width="5" stroke-linecap="round"/>
      <!-- Magnifying glass ring -->
      <circle cx="68" cy="37" r="14" fill="none" stroke="#6366f1" stroke-width="4.5"/>
      <!-- Magnifying glass tinted lens -->
      <circle cx="68" cy="37" r="10" fill="rgba(99,102,241,0.18)"/>
      <!-- Lens reflection -->
      <path d="M62 32 Q65 29 70 30" stroke="rgba(255,255,255,0.55)" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>
    <div class="hero-text">
      <h1>DataSnoop</h1>
      <div class="sub">Your friendly data detective 🕵️</div>
    </div>
  </div>

  <p class="tagline">
    Drop in a CSV <em>or</em> pick a live dataset — DataSnoop checks for missing values, outliers,
    and quality issues, then explains exactly what it found in plain English. No data science degree required.
  </p>

  <!-- Feature cards -->
  <div class="cards">
    <div class="card">
      <div class="icon">⚡</div>
      <h3>Try the demo</h3>
      <p>See DataSnoop in action right now — zero setup, zero uploads. Just click and go.</p>
    </div>
    <div class="card">
      <div class="icon">📁</div>
      <h3>Upload your CSV</h3>
      <p>Drag and drop any CSV file. Get back a full health score, column breakdown, and recommendations.</p>
    </div>
    <div class="card">
      <div class="icon">🌐</div>
      <h3>Fetch live data</h3>
      <p>Pull from 9 built-in live datasets — crypto, countries, SpaceX, nutrition, and more.</p>
    </div>
    <div class="card">
      <div class="icon">💬</div>
      <h3>Plain English results</h3>
      <p>No jargon. DataSnoop tells you what it found and what to do about it in simple terms.</p>
    </div>
  </div>

  <!-- Action buttons -->
  <div class="actions">
    <a href="/docs"             class="btn primary">Open API Docs</a>
    <a href="/api/v1/demo"      class="btn secondary">⚡ Try Demo</a>
    <a href="/api/v1/datasets"  class="btn secondary">🌐 All Datasets</a>
    <a href="/health"           class="btn secondary">Health Check</a>
  </div>

  <!-- Endpoint reference -->
  <div class="ep-box">
    <h2>Endpoints at a glance</h2>
    <div class="ep">
      <span class="badge get">GET</span>
      <div><div class="path">/api/v1/demo</div><div class="desc">Run analysis on the built-in sample — zero setup</div></div>
    </div>
    <div class="ep">
      <span class="badge post">POST</span>
      <div><div class="path">/api/v1/scan/file</div><div class="desc">Upload your own CSV for a full analysis</div></div>
    </div>
    <div class="ep">
      <span class="badge get">GET</span>
      <div><div class="path">/api/v1/datasets</div><div class="desc">List all 9 built-in live datasets</div></div>
    </div>
    <div class="ep">
      <span class="badge get">GET</span>
      <div><div class="path">/api/v1/scrape/{dataset_id}</div><div class="desc">Fetch &amp; analyze a live dataset</div></div>
    </div>
    <div class="ep">
      <span class="badge get">GET</span>
      <div><div class="path">/health</div><div class="desc">Check the service is up and running</div></div>
    </div>

    <!-- Quick-access dataset links -->
    <h2 style="margin-top:1.2rem;">Live datasets — click to analyze now</h2>
    <div class="ds-grid">
      <a href="/api/v1/scrape/crypto"    class="ds-chip"><strong>💰 Crypto</strong>Top 100 coins</a>
      <a href="/api/v1/scrape/countries" class="ds-chip"><strong>🌍 Countries</strong>World data</a>
      <a href="/api/v1/scrape/spacex"    class="ds-chip"><strong>🚀 SpaceX</strong>All launches</a>
      <a href="/api/v1/scrape/products"  class="ds-chip"><strong>🛒 Products</strong>100 items</a>
      <a href="/api/v1/scrape/nutrition" class="ds-chip"><strong>🍎 Nutrition</strong>Fruit facts</a>
      <a href="/api/v1/scrape/quotes"    class="ds-chip"><strong>💬 Quotes</strong>Famous quotes</a>
      <a href="/api/v1/scrape/people"    class="ds-chip"><strong>👤 People</strong>User profiles</a>
      <a href="/api/v1/scrape/posts"     class="ds-chip"><strong>📝 Posts</strong>Blog posts</a>
      <a href="/api/v1/scrape/todos"     class="ds-chip"><strong>✅ Todos</strong>Task list</a>
    </div>
  </div>

</div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    return _LANDING_PAGE
