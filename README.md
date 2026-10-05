# World Monitor — AI-Assisted Security Assessment Platform (Basic Model)

**SIH26163 — Security Assessment of the World Monitor Application**

> This is a **basic / minimal working model** of the full platform described in the
> project spec. It implements a real, end-to-end pipeline — GitHub repo analysis →
> endpoint discovery → application map → test planning → authorized runtime testing →
> evidence collection → LLM-assisted analysis → validation → CVSS scoring →
> remediation → report — using real tool integrations (GitHub API, httpx, NetworkX,
> Anthropic API), but with reduced scope/depth compared to a production build (see
> "What's simplified" below).

---

## 1. Problem Statement

Perform an **authorized, repository-aware** security assessment of the World Monitor
application: understand its code and API structure, build an application map,
generate context-aware security tests, execute them safely, collect evidence, use an
LLM to reason over that evidence, validate findings, trace them back to source code,
and produce a professional security report with remediation guidance.

## 2. Core Principle

> We do not blindly scan an application. We first understand its code and API
> structure, build an application map, perform context-aware security testing,
> collect evidence, use AI to interpret and correlate the evidence, validate
> vulnerabilities, trace them back to the relevant code, and provide actionable
> remediation and a professional security report.

The LLM is used **only** as a reasoning/correlation layer over evidence that
deterministic tools already collected. It never performs HTTP testing itself, and it
never invents evidence — if the evidence is insufficient it must say
`INCONCLUSIVE — MORE VALIDATION REQUIRED`.

## 3. Architecture

```
WORLD MONITOR
      │
      ├───────────────┐
      ▼               ▼
 SOURCE CODE      AUTHORIZED APP/API
      │               │
      ▼               ▼
 REPOSITORY        RUNTIME
  ANALYZER         TESTING (httpx)
 (GitHub API)          │
      │               │
      ▼               ▼
 APPLICATION       TEST
    MAP            RESULTS
   (NetworkX)         │
      └───────┬───────┘
              ▼
        EVIDENCE ENGINE
              ↓
         LLM ANALYSIS (Anthropic API)
              ↓
      VALIDATION + CVSS v3.1
              ↓
        CONTROLLED PoC
              ↓
      CODE LOCATION + FIX
              ↓
       SECURITY REPORT (Markdown)
```

## 4. Technology Choices

| Layer | Technology | Why |
|---|---|---|
| Backend API | FastAPI + Pydantic | Async-friendly, auto docs at `/docs`, strong typing |
| Database | SQLite (swap to PostgreSQL via `DATABASE_URL`) | Zero-setup for a basic model; schema is Postgres-compatible |
| Repo access | GitHub REST API (git trees + blobs) | No local clone required; works with any public/token-accessible repo |
| Static analysis | Custom regex/AST-lite route extractor + OpenAPI parser | Deterministic, line-traceable endpoint discovery |
| Application graph | NetworkX | Standard Python graph library, easy to serialize to JSON for the UI |
| Runtime testing | `httpx` | Full control over method/headers/auth per test case, sync client is simple to reason about for safety gating |
| LLM | Groq API (default, `llama-3.3-70b-versatile`) or Anthropic API | Used only for evidence reasoning/correlation, not test execution. Provider is switchable via `LLM_PROVIDER` |
| Frontend | React + Vite + Tailwind | Fast iteration, utility CSS matches a dense security-dashboard UI |

## 5. What's Simplified vs. the Full Spec

This is explicitly a **basic model**, built to demonstrate the real pipeline working
end-to-end rather than every feature in the full spec. Differences from the full
spec:

- **No Semgrep / Trivy / Schemathesis / ts-morph / Buf integrations.** The spec calls
  for these; this basic model replaces them with an equivalent deterministic
  mechanism (regex/pattern-based route + auth-hint extraction, and a rule-based test
  planner) so the "deterministic tools feed the LLM, not the other way around"
  principle still holds. Swapping in Semgrep/Trivy/Schemathesis is a drop-in
  extension point — see "Extending this basic model" below.
- **Endpoint discovery is pattern-based, not a full TypeScript AST.** It will miss
  dynamically constructed routes (e.g. `app[method](base + '/x', ...)`).
- **SQLite instead of PostgreSQL** by default (switch with one env var).
- **Frontend→API linkage in the application map is heuristic** (string-matching
  `fetch()`/`axios()` calls against known endpoint paths), not a full call-graph
  analysis.
- **No authentication/session management UI** — the platform itself has no login;
  it's a single-tenant local tool for the hackathon demo.
- Not independently executed/tested in the environment this was built in (no network
  access to `pip install`), though every file was syntax-checked. Run
  `pytest` locally before your demo.

## 6. Safety Model

This platform is built to test **only** systems you are explicitly authorized to
test:

- **Target allowlisting**: `SafeHttpxRunner` refuses to send a single request to any
  host not in `ALLOWED_TARGET_HOSTS`. This is enforced in code, not just
  configuration — a `ScopeViolationError` is raised before any HTTP call is made.
- **No destructive test cases**: the test planner never generates payloads that
  write, update, or delete real data. SQLi/XSS probes are detection-only (e.g. a
  single quote to look for a leaked DB error string), never actual exploitation.
- **Rate limiting** (`REQUEST_RATE_LIMIT_PER_SEC`) and a **hard request cap per
  assessment** (`MAX_REQUESTS_PER_ASSESSMENT`).
- **PASS/FAIL/POTENTIAL_FINDING/ERROR classification is conservative** — a failed
  test is never automatically treated as a confirmed vulnerability. Only evidence
  that passes both the deterministic classifier **and** LLM review (with
  medium/high confidence) is marked `validated`.
- Use the bundled `backend/tests/mock_target_app.py` (an intentionally flawed local
  FastAPI app) to demo the pipeline safely without touching a real system.

## 7. Repository Layout

```
wm-security-platform/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entrypoint
│   │   ├── config.py                # env-driven settings
│   │   ├── database.py / models.py / schemas.py
│   │   ├── analyzers/
│   │   │   ├── repository_analyzer.py   # GitHub API file retrieval
│   │   │   ├── endpoint_extractor.py    # regex-based route discovery
│   │   │   └── openapi_analyzer.py      # OpenAPI spec parsing
│   │   ├── mapping/application_mapper.py  # NetworkX graph builder
│   │   ├── testing/
│   │   │   ├── test_planner.py          # rule-based test case generation
│   │   │   └── httpx_runner.py          # scope-safe test execution
│   │   ├── evidence/evidence_engine.py
│   │   ├── ai/analyzer.py + prompts.py  # Anthropic API reasoning layer
│   │   ├── validation/validator.py
│   │   ├── scoring/cvss.py              # CVSS v3.1 base score formula
│   │   ├── reports/report_generator.py
│   │   └── api/                         # FastAPI routers
│   ├── tests/
│   │   ├── mock_target_app.py       # safe local demo target
│   │   └── test_*.py                # pytest unit tests
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── pages/  (Dashboard, ApplicationMap, Endpoints, Findings, TestResults, Report, ...)
    │   ├── services/api.js
    │   └── App.jsx
    ├── package.json
    └── vite.config.js / tailwind.config.js
```

## 8. Setup & Running Locally

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set GITHUB_TOKEN (optional but recommended), LLM_API_KEY, TARGET_BASE_URL
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

### Safe local demo target (recommended for your first run)

```bash
cd backend
uvicorn tests.mock_target_app:app --port 8080
```

This spins up a tiny intentionally-flawed app (missing auth on `/api/admin/stats`,
an IDOR on `/api/users/{id}`, and a DB-error leak on `/api/search`) so you can see
real findings without touching anything else.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## 9. Running an Assessment (Demo Script)

1. **New Assessment** → enter a GitHub repo URL (e.g. the World Monitor repo) and the
   authorized target base URL (`http://localhost:8080` for the mock target).
2. **Dashboard → "1. Analyze Repository"** — pulls relevant files via the GitHub API
   and extracts endpoints.
3. **Dashboard → "2. Build Application Map"** — builds and renders the
   File → Endpoint → Handler graph.
4. **Dashboard → "3. Plan + Run Tests"** — generates endpoint-specific test cases and
   executes them against the authorized target only.
5. **Findings tab** — review potential/validated findings, each with evidence, code
   location, CVSS score, and remediation.
6. **Test Results tab** — inspect every individual request/response pair.
7. **Report tab** — generate and download the full Markdown report.

## 10. Testing the Platform Itself

```bash
cd backend
pytest
```

Covers the endpoint extractor (route/auth-hint detection), the CVSS v3.1 scorer
(validated against the well-known reference vector `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`
→ 9.8), and the validator's state-machine logic.

## 11. Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | Raises GitHub API rate limit; required for private repos |
| `DATABASE_URL` | SQLite by default; set a `postgresql://...` URL for production |
| `LLM_PROVIDER` | `groq` (default) or `anthropic` — selects which API the evidence-analysis layer calls |
| `GROQ_API_KEY`, `GROQ_MODEL` | Used when `LLM_PROVIDER=groq`. Get a key at [console.groq.com/keys](https://console.groq.com/keys) |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Used when `LLM_PROVIDER=anthropic` |
| `ALLOWED_TARGET_HOSTS` | **Safety-critical** — comma-separated hostnames the test runner may contact |
| `TARGET_BASE_URL` | Default authorized target |
| `MAX_REQUESTS_PER_ASSESSMENT`, `REQUEST_RATE_LIMIT_PER_SEC` | Safety throttles |

Never commit a real `.env` file — only `.env.example` is checked in.

## 12. Extending This Basic Model Toward the Full Spec

- Swap `endpoint_extractor.py`'s regex pass for `ts-morph`-driven AST analysis of the
  actual TypeScript/JS source for more accurate call-graph-aware discovery.
- Add `semgrep_analyzer.py` and `trivy_analyzer.py` modules that run as subprocesses
  and feed their JSON output into the same `Evidence` records the httpx runner
  produces today — the evidence/validation/report layers are already
  source-agnostic.
- Replace the rule-based `httpx_runner` payloads with `schemathesis`-generated cases
  for schema-driven fuzzing, still routed through the same `SafeHttpxRunner` scope
  checks.
- Move from SQLite to PostgreSQL by changing `DATABASE_URL`; the SQLAlchemy models
  are already Postgres-compatible.
- Add a proper graph-visualization library (e.g. `react-force-graph`) to the
  Application Map page in place of the current grouped-list view.

## 13. Limitations

- Endpoint discovery can miss dynamically constructed routes.
- Runtime testing is intentionally conservative/non-destructive; some vulnerability
  classes (stored XSS requiring a rendered DOM, complex business-logic flaws,
  race conditions) need manual follow-up beyond this pipeline.
- LLM analysis quality depends on the quality/completeness of the evidence passed to
  it; it is explicitly instructed to return `inconclusive` rather than guess.
- This was built and syntax-validated without network/package access in the
  authoring environment — install dependencies and run `pytest` + a manual pass
  against the mock target before relying on it for a live demo.

## 14. Authorized-Use Disclaimer

This platform must only be pointed at applications, repositories, and endpoints you
own or are explicitly authorized to test. `ALLOWED_TARGET_HOSTS` is a safety control,
not a substitute for proper authorization — set it only to hosts you have permission
to assess, and never to third-party production systems.
