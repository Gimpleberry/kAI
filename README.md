# kAI

> Conjoint-based preference elicitation engine for engineering tenets.
> For: solo use by the project owner, on a single Windows dev machine.
> Last updated: v0.2.0 (2026-04-26).

---

## 1. What is this?

kAI is a local-only tool that quantifies your engineering preferences through
conjoint analysis. You answer ~40 carefully-designed tradeoff questions, and
the math returns part-worth utilities with confidence intervals — telling you
things like "1 day of timeline is worth 4 percentage points of test coverage
to you" that no rating scale can.

The Python package is `kai` (lowercase, per Python convention). The project,
repo, and CLI command use the styled `kAI`.

---

## 2. Quick start

Two terminals, one URL:

```bash
# Terminal 1 — start the API
cd /c/dev/kAI
source .venv/Scripts/activate     # Windows (Git Bash)
python main.py
```

```bash
# Terminal 2 — open the frontend (once it exists)
open frontend/index.html          # macOS
start frontend/index.html         # Windows
```

Bookmark: `http://127.0.0.1:8000` once the API is running.

---

## 3. URL / endpoint reference

| What I want to do | Where to go |
|---|---|
| Take a questionnaire | `http://127.0.0.1:8000/` |
| View the latest profile | `http://127.0.0.1:8000/profile` |
| API health check | `http://127.0.0.1:8000/health` |
| API docs (auto-generated) | `http://127.0.0.1:8000/docs` |
| Diagnostics dashboard | `http://127.0.0.1:8000/diagnostics` |

(Endpoints marked TBD are planned in the BACKLOG.md phases.)

---

## 4. First-time setup

Only runs once per machine. Requires Python 3.12 (not 3.13 or 3.14 — see
`DECISIONS.md` → ADR-007).

```bash
# 1. Clone or extract the repo to a NON-CLOUD-SYNCED folder
cd /c/dev/kAI

# 2. Run the setup script — creates venv, installs deps, hooks, runs tests
bash scripts/setup.sh

# 3. Smoke test — confirm config and CLI are wired up
source .venv/Scripts/activate
kai validate-taxonomy
```

Expected smoke-test output:

```
✓ Taxonomy v1.0 valid
  Attributes: 8
  Tenets: 7
  Estimable parameters: 16
```

---

## 5. What's where? (folder map)

```
kAI/
├── main.py                    Entry point — boots all plugins
├── plugins.py                 Feature registry — one line per plugin
├── pyproject.toml             Pinned deps + project metadata
├── README.md                  This file
├── PROJECT_KNOWLEDGE.txt      Current-state architecture reference
├── BACKLOG.md                 Phase-ordered future work
├── CHANGELOG.md               Versioned change history
├── DECISIONS.md               Architecture decision records (ADRs)
│
├── config/                    Static configuration (committed)
│   ├── taxonomy.yaml          Central definition of attributes × levels
│   └── design_params.yaml     Experimental design parameters
│
├── src/kai/                   The Python package
│   ├── shared.py              Single source of truth (Tenet 1)
│   ├── plugin_base.py         Plugin protocol
│   ├── cli.py                 `kai` CLI commands
│   ├── taxonomy/              Schema + loader
│   ├── design/                CBC + MaxDiff design generation
│   ├── estimation/            MNL + ensemble math
│   ├── diagnostics/           Quality gates and consistency checks
│   ├── storage/               SQLite persistence layer
│   ├── elicitation/           FastAPI server (loads last)
│   └── profile/               Profile generation + export
│
├── tests/unit/                Unit tests (sandbox-only, never prod data)
├── scripts/                   Operational scripts
│   ├── setup.sh               First-time install
│   ├── validate.sh            10-item Tenet-5 validation suite
│   ├── pre-commit             Git hook blocking data leaks
│   └── install_hooks.sh       Installs the pre-commit hook
├── frontend/                  Browser UI (TBD)
├── analysis/                  Jupyter notebooks (TBD; gitignored output)
├── data/                      Runtime data — GITIGNORED, NEVER COMMIT
└── .github/                   PR + issue templates, CI workflows
```

What's NOT in the project folder, and why:

| Lives elsewhere | Why |
|---|---|
| `data/kai.db` | Personal preference data — local only (ADR-003) |
| `.venv/` | Build artifact — gitignored, recreated by setup.sh |
| `.env` | Per-user overrides — gitignored, copy from `.env.example` |

---

## 6. Plugin / feature commands

Manual one-off commands grouped by feature.

### Validate config

```bash
kai validate-taxonomy
```
Loads `config/taxonomy.yaml`, runs schema validation, reports attribute/tenet
counts and estimable parameter count. Writes nothing.

### Run all plugin lifecycle checks

```bash
python main.py --check
```
Verifies every plugin in `plugins.py` implements `start()` and `stop()`.
Writes nothing.

### Show boot order

```bash
python main.py --boot-order
```
Prints registry in boot order, then in shutdown order. Useful when adding
a new plugin and deciding where it goes.

### Run the full validation suite (10-item Tenet-5 checklist)

```bash
bash scripts/validate.sh           # full
bash scripts/validate.sh fast      # skip integration boot
```
Runs lint, tests, plugin checks, config validation, encoding sweep. Returns
0 if all pass, 1 if any fail. Run before every commit.

---

## 7. Diagnostics — "is everything working?"

Run these top-to-bottom. Each should pass.

```bash
# 1. venv exists and Python is 3.12
python --version
# Expected: Python 3.12.x

# 2. Imports work
python -c "import kai, plugins; print('OK')"
# Expected: OK

# 3. Config loads
kai validate-taxonomy
# Expected: ✓ Taxonomy v1.0 valid

# 4. Plugin registry is sound
python main.py --check
# Expected: ✓ N plugins valid

# 5. Unit tests pass
pytest tests/unit -q
# Expected: all green

# 6. Full validation suite
bash scripts/validate.sh
# Expected: Passed: 10 Failed: 0
```

---

## 8. Common issues / troubleshooting

### "Python was not found; run without arguments to install from the Microsoft Store"

Cause: the script is calling `python3` but Windows resolves it to a Microsoft
Store stub. Use `py -3.12` directly, or run `bash scripts/setup.sh` which
detects this case and uses the Python launcher.

### "fatal: pathspec '.gitattributes' did not match any files"

Cause: file saved as `gitattributes` (no leading dot) — Windows often strips
leading dots. Rename in Git Bash:
```bash
mv gitattributes .gitattributes
```

### "ERROR: not a git repository. Run 'git init' first."

Cause: `scripts/install_hooks.sh` ran outside a git repo. Run `git init` first.

### "ConfigError: Required config key 'KAI_DB_URL' is not set"

Cause: missing or unreadable `.env` file, and no `KAI_DB_URL` in your shell.
Fix: `cp .env.example .env` from the repo root.

### Tests fail with "Tenet 1 violation: shared.py symbols are redefined elsewhere"

Cause: a module redefines a name that lives in `src/kai/shared.py`. Fix by
deleting the local definition and importing from `kai.shared`.

### "✗ COMMIT BLOCKED: personal data files detected"

Working as intended — the pre-commit hook caught a `.db`, `.env`, or `data/`
file in your staging area. Read the hook output for which file and how to
remove it from staging.

---

## 9. Security reminders

| ✅ Already done | ⏳ Still TODO | 🚫 Never do these |
|---|---|---|
| API binds to 127.0.0.1 only | Add CORS allowlist with explicit origins | Bind API to 0.0.0.0 |
| Pre-commit hook blocks .db / .env | Add CI secret-scan (gitleaks) on PR | Commit a `.env` file |
| `.gitignore` blocks data dirs | Set up branch protection on main | Put credentials in source |
| All config via env / .env | Encrypt the project drive (BitLocker) | Run kAI from OneDrive/iCloud |
| No external network calls at runtime | Add `git ls-files` audit step | `git revert` a leaked secret (rotate AND filter-repo) |

---

## 10. When things really break

Numbered escalation ladder — try in order. Last resort is destructive.

1. `git status` — confirm what you've changed since the last good state.
2. `bash scripts/validate.sh` — see what's failing.
3. `python main.py --check` — narrow to plugin lifecycle issues.
4. `git stash` — set aside uncommitted changes, see if HEAD is healthy.
5. `git reset --hard HEAD` — discard uncommitted changes (you stashed first, right?).
6. `rm -rf .venv && bash scripts/setup.sh` — rebuild the environment from scratch.

---

## 11. Glossary

| Term | Meaning |
|---|---|
| ADR | Architecture Decision Record — entry in `DECISIONS.md` |
| Attribute | One engineering dimension you trade off (e.g., "test coverage") |
| BIBD | Balanced Incomplete Block Design — used for MaxDiff task generation |
| CBC | Choice-Based Conjoint — pick best bundle from N options |
| D-efficiency | A measure of how well a design supports estimation; ≥ 0.85 is the gate |
| Determinism contract | Same `(taxonomy, params, seed)` ⇒ byte-identical design (ADR-005) |
| Effects coding | Encoding K levels as K-1 dummies; standard for MNL |
| Level | One discrete value an attribute can take (e.g., "60%", "80%", "95%") |
| MaxDiff | Best-Worst Scaling — pick most + least important from a set of items |
| MNL | Multinomial Logit — the primary estimator |
| Part-worth | Estimated utility of a single attribute level |
| Plugin | A self-contained feature module with start()/stop() lifecycle |
| Quality gate | A pass/fail check that blocks bad outputs from becoming canonical |
| Tenet | One of the six core architectural principles (see `ARCHITECTURE_TENETS`) |
| WAL mode | SQLite Write-Ahead Logging — enables concurrent reads |

---

## 12. Restart cheat sheet

If everything's broken and you just need to get back to a known-good state:

```bash
# 1. Save any uncommitted work
cd /c/dev/kAI
git stash

# 2. Get to clean main
git checkout main
git pull

# 3. Nuke the venv
rm -rf .venv

# 4. Fresh install
bash scripts/setup.sh

# 5. Verify
bash scripts/validate.sh

# 6. (If you stashed in step 1)
git stash pop
```

---

## 13. Footer

> When you ask Claude to add a feature, mention which plugin it belongs to.
> Save your future self an iteration.
