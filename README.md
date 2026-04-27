# kAI

Conjoint-based preference elicitation engine for quantifying engineering tenets.

The Python package is named `kai` (lowercase, per Python convention); the
project, repo, and CLI command use the styled `kAI` form. See `DECISIONS.md`
→ ADR-006 for naming rationale.

## What this does

You answer ~40 carefully-designed tradeoff questions across three formats:

1. **CBC (Choice-Based Conjoint):** "Which bundle would you ship?" — each option mixes test coverage, timeline, dependency count, etc.
2. **MaxDiff:** "Of these tenets, most/least important?"
3. **Direct ratings:** Anchor the latent scale to interpretable units.

Out the other end: a statistically-grounded profile with **part-worth utilities and confidence intervals** for every level of every attribute. The math tells you things like "1 day of timeline = 4 percentage points of test coverage" — tradeoffs you never explicitly stated.

## Why this is different from "rate these on 1–7"

A simple rating scale gives you stated importance. This system reveals **actual** importance through the pattern of choices across many bundles. The two often diverge in interesting ways.

## Status

**v0.1.4 — scaffolding.** Schema, config, module contracts, and a foundation of tests are in place. Implementation modules exist as documented stubs.

Next implementation order:
1. CBC design generation + diagnostics
2. MNL estimation
3. FastAPI elicitation layer
4. Frontend
5. MaxDiff + direct ratings
6. Ensemble estimation
7. Profile export

## Quickstart

Requires Python 3.11+.

```bash
# One-time setup: creates venv, installs deps, validates config, runs tests
bash scripts/setup.sh

# Start the API (in one terminal)
source .venv/bin/activate
uvicorn kai.elicitation.api:create_app --factory --reload

# Open the frontend (in another terminal, or just from your file browser)
open frontend/index.html
```

The API binds to `127.0.0.1:8000` only — not your local network, only your machine.
SQLite database lives at `./data/kai.db`. Nothing leaves your computer.

## Architecture

See `DECISIONS.md` for architecture decision records (the why), `CHANGELOG.md`
for version history (the what), and `BACKLOG.md` for deferred work and future
enhancements (the not-yet). Module-level docs live in each `__init__.py`.

## Engineering tenets (the ones we're modeling)

This project is built to embody them too:

1. **Scalable** — Config-driven taxonomy; adding attributes is YAML, not code.
2. **Efficient** — MNL runs in seconds.
3. **Safe** — All data local; SQLite on disk; no network calls.
4. **Organized** — Versioned, tested, documented.
5. **Priority QC** — Quality gates block bad estimates from becoming canonical.
6. **Storage-aware** — Every observation persisted with provenance.
