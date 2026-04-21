# CI/CD Pipeline

> File: `.github/workflows/ci.yml`  
> Platform: GitHub Actions  
> CD: Streamlit Cloud (auto-deploy on push to master)

## Overview

Automated quality gates on every PR and push to master. The CI pipeline validates code quality, import integrity, pipeline functionality, secret hygiene, and dependency compatibility. CD is handled by Streamlit Cloud which auto-deploys from the master branch.

---

## CI Pipeline Architecture

```
Pull Request → master
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions CI                              │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐               │
│  │   Lint   │  │ Import Check │  │ Smoke Test │  (parallel)    │
│  │ (flake8) │  │  (all modules)│  │ (pipeline) │               │
│  └──────────┘  └──────────────┘  └────────────┘               │
│  ┌──────────────┐  ┌─────────────┐                            │
│  │ Secret Scan  │  │  Dep Check  │  (parallel)                │
│  │ (patterns)   │  │ (pip install)│                            │
│  └──────────────┘  └─────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼ (all pass)
   Merge to master
        │
        ▼
┌─────────────────────┐
│  Streamlit Cloud CD │
│  Auto-deploy on     │
│  push to master     │
└─────────────────────┘
```

## Trigger Configuration

```yaml
on:
  pull_request:
    branches: [master]    # Runs on PR creation/update
  push:
    branches: [master]    # Runs after merge

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true   # Cancels stale runs on same branch
```

**Concurrency:** If you push new commits to a PR while CI is running, the in-progress run is cancelled and restarted. Saves GitHub Actions minutes.

---

## CI Jobs (5 Parallel Checks)

### 1. Lint (flake8)

**Matrix:** Python 3.10, 3.11

**What it checks:**
| Pass | Rule Set | Scope |
|------|----------|-------|
| Critical (blocking) | E9, F63, F7, F82 | Syntax errors, undefined names, import failures |
| Warnings (non-blocking) | Everything else (max-line=120) | Style, whitespace, naming |

**Scanned directories:** `app/`, `utils/`, `simulator/`, `ai/`, `pipeline/`

**Ignored warnings:** E501 (line length handled by max-line), W503, E302, E303, W291-293, E266, E265, E741, E711, E712, W504

**Why two passes:**
- First pass is the gate — fails the job if there are real errors
- Second pass runs with `|| true` — informational only, never blocks merge

### 2. Import Check

**What it does:** Installs all dependencies, then imports every public function/class from every module.

**Verifies:**
```python
# utils
from utils.theme import COLORS, apply_theme, metric_card, section_header
from utils.charts import gauge_chart, time_series_chart, bar_chart, funnel_chart
from utils.kpi_calculator import get_flight_kpis, get_passenger_kpis
from utils.lineage import get_lineage_for_stream, get_sankey_data

# simulator
from simulator.airport_generator import generate_all_events, write_events_to_json
from simulator.config import AIRPORT_CONFIG
from simulator.failure_injector import inject_schema_drift, inject_sensor_outage

# ai
from ai.claude_client import ClaudeClient
from ai.context_builder import build_ai_context, format_context_for_prompt
from ai.prompts import SYSTEM_PROMPT

# pipeline
from pipeline.orchestrator import run_pipeline
from pipeline.bronze_ingestion import ingest_to_bronze
from pipeline.silver_transformation import transform_to_silver
from pipeline.gold_aggregation import aggregate_to_gold
from pipeline.quality_rules import validate_record
```

**Why:** Catches circular imports, missing modules, renamed functions, broken `__init__.py` exports. The `ANTHROPIC_API_KEY=test-key-not-real` env var prevents `ClaudeClient.__init__()` from failing on API validation.

### 3. Smoke Test (Data Pipeline)

**End-to-end functional test in 3 steps:**

| Step | What It Does | Validates |
|------|-------------|-----------|
| Generate data | `generate_all_events(hours=1)` | Simulator produces events for all 6 streams |
| Run pipeline | `run_pipeline()` | Bronze→Silver→Gold completes without crash |
| Verify outputs | Check `data/silver/*.parquet` | All Silver files exist with >0 rows |

**Why 1 hour (not 24):** Faster CI run (~3s vs ~10s for generation). Still covers all streams and peak-hour logic.

### 4. Secret Scan

**Two checks:**

| Check | Method | Fails If |
|-------|--------|----------|
| .env gitignored | `grep "^\.env$" .gitignore` | .env not in .gitignore |
| Pattern scan | grep across all source files | Finds: Anthropic key prefixes, AWS key prefixes (`AKIA...`), GitHub token prefixes (`ghp_...`, `gho_...`) |

**Scanned file types:** `*.py`, `*.yml`, `*.yaml`, `*.toml`, `*.json`, `*.md`

**Excluded:** `.env.example`, `.github/workflows/ci.yml` (contains pattern strings themselves)

### 5. Dependency Check

**Matrix:** Python 3.10, 3.11

**What it does:**
1. `pip install -r requirements.txt` — Verifies all packages install without conflicts
2. Imports key packages and prints versions — Confirms packages are importable

**Verifies:** streamlit, plotly, pandas, duckdb, pyarrow, anthropic, faker

---

## CD Process (Streamlit Cloud)

### Deployment Configuration

| Setting | Value |
|---------|-------|
| Platform | Streamlit Cloud (community tier) |
| Repository | varnika-98/AeroOps-POC |
| Branch | master |
| Main file path | `app/Command_Center.py` |
| Python version | 3.12 |
| Dependencies | `requirements.txt` (auto-installed) |

### Deployment Flow

```
Developer workflow:
1. Create feature branch (e.g., add-docs)
2. Make changes, commit, push
3. Open PR to master
4. CI runs automatically (5 checks)
5. All checks pass → Merge PR
6. Push to master triggers Streamlit Cloud redeploy
7. App live at https://<app-name>.streamlit.app (~30-60s)
```

### Streamlit Cloud Behavior

| Event | Action |
|-------|--------|
| Push to master | Auto-redeploy (cold start ~30s) |
| requirements.txt change | Full dependency reinstall |
| App idle (no visitors) | Sleeps after ~7 days |
| First visit after sleep | Cold start (~60s spin-up) |
| Runtime error | Shows error page, previous version NOT preserved |

### Environment Variables (Streamlit Cloud Secrets)

```toml
# Configured in Streamlit Cloud dashboard → App settings → Secrets
ANTHROPIC_API_KEY = "your-anthropic-key-here"
```

Accessible in app via `os.getenv("ANTHROPIC_API_KEY")` or `st.secrets["ANTHROPIC_API_KEY"]`.

---

## Git Workflow Rules

| Rule | Enforcement |
|------|-------------|
| Never commit to master directly | Branch protection (PR required) |
| Always use feature branches | Convention (e.g., `add-docs`, `fix-chat-ux`) |
| CI must pass before merge | Required status checks |
| "commit" = stage + commit | Developer convention |
| "push" = stage + commit + push | Developer convention |
| Check code integrity before commit | Local: imports resolve, syntax OK, no broken refs |
| No CI locally | CI runs on GitHub only (on merge) |

---

## Caching Strategy

```yaml
- name: Cache pip
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: pip-${{ hashFiles('requirements.txt') }}
```

**Effect:** If `requirements.txt` hasn't changed, pip downloads are cached. Saves ~30s per job.

---

## Interview Pitch

"The CI/CD pipeline implements defense-in-depth — 5 parallel checks validate different quality dimensions: syntax correctness (flake8), module integration (import check), functional correctness (smoke test), security hygiene (secret scan), and environment compatibility (dep check across Python 3.10/3.11). CD is zero-config via Streamlit Cloud — push to master auto-deploys in 30 seconds. The concurrency group ensures stale CI runs are cancelled when new commits arrive, saving GitHub Actions minutes."

## Interview Q&A

1. **Q: Why 5 separate jobs instead of one monolithic script?**
   A: Parallel execution — all 5 run simultaneously, so total CI time equals the slowest job (~90s) rather than sum of all (~5 min). Independent failures are also easier to diagnose: "Import Check failed" immediately tells you what's wrong without reading unrelated lint output.

2. **Q: Why test on Python 3.10 and 3.11 but deploy on 3.12?**
   A: Ensures backward compatibility — if a contributor uses an older Python, the code still works. 3.12 deployment takes advantage of performance improvements. The code avoids 3.12+-only features (like `type` statements) for compatibility.

3. **Q: Why is the smoke test only 1 hour of data?**
   A: CI speed — 1 hour generates ~2,500 events vs ~60,000 for 24 hours. Both exercise the same code paths (all 6 streams, peak-hour logic, validation rules). The smoke test validates "does it work?" not "does it scale?" Performance testing would be a separate concern.

4. **Q: What does the secret scan NOT catch?**
   A: It uses pattern matching — it catches known API key formats but not arbitrary passwords, database URLs, or custom tokens. For comprehensive secret scanning, you'd add GitHub's built-in secret scanning (enabled at repo level) or tools like `trufflehog` / `gitleaks` that check git history.

5. **Q: Why no unit tests in CI?**
   A: The POC prioritizes functional validation (smoke test) over unit tests. The smoke test IS an integration test — it runs the full pipeline end-to-end. Unit tests would be valuable for quality_rules validation logic and KPI calculations, but the import check + smoke test cover the critical path for a POC.

6. **Q: How does Streamlit Cloud handle rollbacks?**
   A: It doesn't — there's no built-in rollback. If a broken commit reaches master, the app shows an error page. To rollback: `git revert <commit>` → push to master → auto-redeploy. This is why CI gates are critical — they prevent broken code from reaching master.

7. **Q: Why `cancel-in-progress: true`?**
   A: If you push 3 commits rapidly to a PR, only the latest commit's CI run matters. Without cancellation, all 3 run to completion, wasting 3× the compute. With it, the first two are cancelled immediately when the third starts.
