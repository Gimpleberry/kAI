# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Tooling
- Tooling: validate.sh item #1 now runs `ruff format --check` in addition
  to `ruff check`, matching .github/workflows/lint.yml exactly. Closes the
  local-vs-CI gate parity gap caught during Phase 1.1 and 1.2 rollouts.
  New `tests/unit/test_validate_script_lint_parity.py` regression-guards
  the invariant going forward. Tags: Tooling, QC.


**Tags:** Feature

Phase 1.2 ships: design diagnostics. Closes BACKLOG 1.2. Surfaces a new
follow-up captured as BACKLOG 1.1.5.

### Added (code)

- `kai.design.design_diagnostics.diagnose_cbc_design()` - computes
  D-efficiency, per-attribute level balance, max level imbalance, and
  duplicate-alternative count; checks against shared.py quality gates
  and returns a `DesignReport`.
- D-efficiency uses the standard MNL relative formulation under uniform
  priors: `det(I)^(1/p) / N` where `I = sum_t X_t' M X_t` and M is the
  J x J within-task centering matrix. Catches task-degenerate designs
  (an attribute constant across all alts in a task contributes zero
  information from that task).
- Effects coding: deviation/sum-to-zero, alphabetically-first level as
  reference. Numerical stability via `numpy.linalg.slogdet`; singular
  information matrices report d_efficiency=0.0 with descriptive message.
- `kai.shared.QUALITY_GATE_MAX_LEVEL_IMBALANCE = 0.15` - promoted from
  literal in design_params.yaml to cross-module constant per Tenet 1.
- `tests/unit/test_design_diagnostics.py` - 25+ tests covering output
  contract, level balance, D-efficiency (hand-verifiable orthogonal
  case = exactly 1.0; singular = 0.0), duplicate detection, gate logic,
  Tenet 1 enforcement of defaults, and a production-config sentinel.

### Changed (code)

- `DesignReport.n_dominated_alternatives` renamed to
  `n_duplicate_alternatives`. Strict dominance requires preference-
  direction metadata not currently in the taxonomy schema; we count
  duplicate alternatives within a task instead, which is well-defined
  and a real pathology. Real dominance detection captured in BACKLOG.

### Decisions

- **Production D-efficiency lands at ~0.38**, well below the 0.85 gate.
  Calibration over 20 seeds shows our generator is statistically
  indistinguishable from pure random sampling. The 0.85 gate is
  calibrated against full Sawtooth balanced overlap (swap-based D-eff
  optimization on top of level balancing). Captured as new BACKLOG
  item 1.1.5; preferred over weakening the gate. Estimation still works
  at D-eff 0.38 (wider CIs, not wrong answers), so the intermediate
  state is survivable.
- **Sentinel test for 1.1.5**:
  `test_production_design_intentionally_fails_d_eff_gate` asserts the
  current failure with a docstring explaining the path forward. When
  1.1.5 ships, the assertion flips.

### Verified

- D-efficiency matches hand-computed value (1.0 exactly) on orthogonal
  2-attribute 2-level case.
- Singular designs correctly report d_efficiency=0.0 and fail gates.
- Production calibration: our generator vs pure random vs random-with-
  no-duplicates over 20 seeds each gave 0.384 / 0.371 / 0.372 mean
  D-eff respectively (statistically indistinguishable).

### Closes (BACKLOG)

- 1.2 Design diagnostics (D-efficiency, level balance)

### New BACKLOG item

- 1.1.5 Within-task overlap minimization (swap-based D-efficiency
  optimization). Target: production D-eff >= 0.85. Highest priority
  remaining Phase 1 work; should land before 1.4 (MNL estimator).



## [0.2.1] — 2026-04-26 — Resilience + observability foundations

**Tags:** Feature, Architecture

Incorporates the new sections from the updated ARCHITECTURE_TENETS document:
high-leverage helpers and architectural decisions that affect future code,
plus deferred items captured cleanly in BACKLOG.

### Added (code)
- `shared.batch_with_isolation()` + `BatchResult` + `SkipItem` — per-item
  exception isolation pattern. One bad item never aborts a batch loop.
  Counts (total/ok/failed/skipped) become the audit trail. Tests in
  `tests/unit/test_shared_helpers.py`.
- `shared.mask_secret()` — masks values for safe logging. Returns
  `<unset>` / `<masked>` / `****<tail>` based on input length. Built-in
  short-value protection prevents leaks via single-char tails.
- `shared.setup_rotating_logger()` — configures a logger with rotating
  file handler at `data/logs/<n>.log` plus optional stderr. Idempotent;
  safe to call multiple times.
- `shared.ActionSafetyError` — raised when an irreversible-action guard
  rejects an attempted action. No callers yet (kAI has no irreversible
  actions at v0.2.1) — encoded ahead of need per ADR-009.
- `shared.LOGS_DIR`, `shared.DEFAULT_LOG_MAX_BYTES`,
  `shared.DEFAULT_LOG_BACKUP_COUNT` — log rotation defaults.
- `tests/unit/test_main_lifecycle.py` — verifies graceful shutdown
  contract: stop() runs in reverse boot order, partial-start failures
  only stop the started subset, individual stop() failures don't
  prevent later stops.
- `scripts/rollout.sh` — interactive 11-step rollout workflow per the
  new "Patch Rollout Process" section. Walks PLAN → BRANCH → IMPLEMENT
  → SELF-REVIEW → VALIDATE → UPDATE DOCS → COMMIT → PUSH → PR → MERGE
  → POST-VALIDATE. Honors `--hotfix` (skip PLAN/BRANCH/PR steps but
  enforces all QC) and `--dry-run` (show steps without prompting).

### Added (docs)
- ADR-009: Action safety — automation prepares, human commits.
- ADR-010: Structured logging conventions.
- ADR-011: Versioning scheme + multi-tag taxonomy. Retroactive tags
  applied to all prior versions.
- PROJECT_KNOWLEDGE.txt: new section 9 "Known Issues & Technical Debt
  Register" (currently empty by design — distinct from BACKLOG).
- BACKLOG.md: new "Forward-looking tenet patterns" section capturing
  9 patterns deliberately deferred (circuit breakers, adaptive
  scheduling, resource pooling, multi-signal verification,
  per-feature debug CLIs, tripwire conventions, auto-mask filter,
  action-safety guard utilities, post-mortem habit).

### Changed (docs)
- PROJECT_KNOWLEDGE.txt section 7 (Changelog summary) now includes
  multi-tag annotations per ADR-011.
- PROJECT_KNOWLEDGE.txt section 6 (Architecture rules) updated with
  pointers to ADRs 009-011 and the new shared.py helpers.

### Why split this from v0.2.0
v0.2.0 was the "tenet alignment pass" against the original tenet
document. The owner uploaded an updated version of the tenets shortly
after, with new sections on resilience, observability, and patch
rollout. Rather than re-version v0.2.0, this is captured as a patch
release that incorporates only the items that affect future code or
encode principles likely to be violated otherwise. Forward-looking
patterns (circuit breakers, etc.) live in BACKLOG and are built when
the triggering feature is added.

### Migration notes
- New helpers in `shared.py` are additive — existing code continues
  to work unchanged. Use them in new code.
- The rollout script supersedes the informal "git add / commit / push"
  flow for any meaningful change. Existing scripts/setup.sh and
  scripts/validate.sh remain the same.
- `scripts/rollout.sh` requires the venv to exist (it calls
  `bash scripts/validate.sh` internally).


## [0.2.0] — 2026-04-26 — Tenet alignment pass

This release reorganizes the project to fully comply with the
ARCHITECTURE_TENETS document the owner uploaded as project knowledge.
Minor version bump because it's a meaningful architectural realignment,
even though no business logic changed.

### Added
- ADR-008: documents the decision to adopt the strict plugin pattern.
- `src/kai/shared.py` — single source of truth for paths, constants,
  error types, config loading. All other modules import from here.
- `src/kai/plugin_base.py` — Plugin protocol contract.
- `plugins.py` at repo root — feature registry, one line per plugin, in
  boot order.
- `main.py` at repo root — lifecycle entry point. Boots plugins in registry
  order, runs until SIGINT/SIGTERM, shuts down in reverse order.
- Per-feature plugin modules: `kai.storage.plugin`, `kai.taxonomy.plugin`,
  `kai.design.plugin`, `kai.estimation.plugin`, `kai.profile.plugin`,
  `kai.elicitation.plugin`. Each exposes a `Plugin` class with
  `start()`/`stop()`.
- `tests/unit/test_shared_uniqueness.py` — mechanically enforces Tenet 1's
  rule that nothing redefines what shared.py owns. Scans every Python file
  in src/ and tests/, fails CI if any `shared.__all__` name appears outside
  shared.py.
- `tests/unit/test_plugins_registry.py` — enforces plugin protocol
  conformance for every entry in `plugins.REGISTRY`.
- `scripts/validate.sh` — the 10-item Tenet-5 validation checklist as
  runnable code. Single command runs lint, uniqueness check, encoding sweep,
  plugin checks, import chain, lifecycle, doc presence, config validation,
  unit tests, integration boot. Returns exit 0 only if all pass.
- `.github/PULL_REQUEST_TEMPLATE.md` — every PR re-affirms the 10-item
  validation checklist plus risk + rollback plan.
- `.github/ISSUE_TEMPLATE/bug_report.md` and `feature_request.md` — issue
  templates. Feature template mirrors BACKLOG.md format so promotion is
  zero-rewrite.
- `.github/ISSUE_TEMPLATE/config.yml` — disables blank issues, surfaces
  links to DECISIONS and BACKLOG.
- `.github/workflows/ci.yml` — runs unit tests + validate-taxonomy + lifecycle
  check on Ubuntu and Windows for every push/PR.
- `.github/workflows/lint.yml` — ruff check + ruff format on every push/PR.
- `.github/workflows/secret-scan.yml` — gitleaks blocks accidental secret
  commits at PR time. Combined with the existing local pre-commit hook,
  secrets must bypass two layers to leak.
- `PROJECT_KNOWLEDGE.txt` — current-state architecture reference. Distinct
  from README (operator's manual) and DECISIONS (why we chose what we chose).

### Changed
- `README.md` rewritten following the 13-section operator's-manual
  pattern from ARCHITECTURE_TENETS.
- `BACKLOG.md` restructured to phase-ordered (Phase 0 done, Phases 1–7
  upcoming), with explicit phase entry/exit criteria and rationale for
  the ordering.
- `src/kai/taxonomy/loader.py` and `src/kai/design/cbc_generator.py` now
  import paths and version constants from `kai.shared` instead of
  redefining them locally.

### Architectural decisions documented
- **Strict plugin pattern adopted (ADR-008).** Owner's choice between
  full strict, hybrid, and skip; owner chose strict to preserve
  cross-project consistency.

### Migration notes (for future-you reading this)
- This is the first release where `python main.py` is the canonical way
  to start the application. The earlier `uvicorn` direct-invocation pattern
  still works for development with --reload but is no longer the default.
- The validation script is the new pre-push gate. Run it before every
  commit to avoid CI failures.
- If you add a new module, you also add a `plugin.py` next to it and one
  line in `plugins.py`. There are now no exceptions to this rule.


## [0.1.5] — 2026-04-26 — Cross-platform setup, Python version pin

### Added
- ADR-007: Python 3.12.x version pin (rationale + reversibility notes).
- `setup.sh` now detects platform (Windows Git Bash vs Linux/macOS) and uses
  the correct venv paths and Python launcher for each.
- `setup.sh` now searches for Python 3.12 in priority order: `py -3.12` →
  `python3.12` → `python3` → `python`, verifying version match before use.

### Changed
- **Python version requirement tightened from `>=3.11` to `>=3.12,<3.13`.**
  Discovered when a user with Python 3.14.4 attempted setup: our pinned
  scientific dependencies (numpy 2.1.3, scipy 1.14.1, pandas 2.2.3) lack
  pre-built wheels for 3.13/3.14, which would force source compilation
  (requires C++ toolchain on Windows). Pinning to 3.12 means everyone gets
  identical numerical behavior. See ADR-007.
- ruff `target-version` and mypy `python_version` updated to 3.12 to match.
- Setup script error messages on missing Python now show install commands
  for Windows (winget), macOS (brew), and Linux (apt).

### Caught at setup stage
- Setup attempt on a Windows machine with Python 3.14 surfaced this issue
  before any business logic was written. Tenet #5 working as intended again.


## [0.1.4] — 2026-04-26 — Renamed to kAI

### Changed
- **Project renamed from "preference-engine" to "kAI"** following standard
  Python naming convention: project/repo/CLI use the styled `kAI`, while the
  Python package is `kai` (lowercase, no special characters). See ADR-006.
- Python package: `preference_engine` → `kai`
- Installable name: `preference-engine` → `kai`
- CLI command: `prefeng` → `kai`
- Env var prefix: `PREFENG_` → `KAI_`
- Default DB filename: `preference_engine.db` → `kai.db`
- All imports updated across source and tests.

### Added
- ADR-006: Project naming convention (kAI for branding, kai for Python).

## [0.1.3] — 2026-04-26 — Design reproducibility + backlog discipline

### Added
- `BACKLOG.md` — deferred-work register. Distinct from CHANGELOG (what happened)
  and DECISIONS (why we chose what we chose). First entries: Claude Project setup,
  adaptive question selection, HB estimation, CLI suite, analysis notebooks.
- `GENERATOR_VERSION` constant in `design/cbc_generator.py` for tracking algorithm
  changes that would break design regeneration.
- Determinism contract explicitly documented in CBC generator docstring.

### Changed
- **Session ORM model:** removed `cbc_design_json` and `maxdiff_design_json` columns.
  Replaced with `design_params` (JSON snapshot of design params used) and
  `generator_version` (string). Implements ADR-005's "store seed, regenerate design"
  policy. Designs are now reproducible from `(taxonomy_version, design_seed,
  design_params, generator_version)`.
- Smaller row size, cleaner separation between configuration and data, and design
  correctness becomes verifiable rather than trusted.

### Deferred (now tracked in BACKLOG.md)
- Setting up `.claudeproject/` directory structure — user will handle independently.

## [0.1.2] — 2026-04-26 — Storage policy formalized

### Added
- `DECISIONS.md` — architecture decision log documenting the *why* behind choices.
  Initial entries: ADR-001 (local hosting), ADR-002 (MNL only), ADR-003 (code/data split),
  ADR-004 (DB location), ADR-005 (design reproducibility).
- `scripts/pre-commit` — git pre-commit hook actively blocking accidental commit of
  `.db`, `.sqlite`, `.env`, `data/`, `backups/`, profile exports, session JSON.
- `scripts/install_hooks.sh` — one-command hook installer.
- Hardened `.gitignore` with explicit data-leak prevention patterns.

### Changed
- `setup.sh` now installs git hooks automatically if run inside a git repo.

### Decisions documented
- **Code → GitHub, data → local-only.** The code/data split is now both
  documented (ADR-003) and enforced (gitignore + pre-commit hook).
- **Single-machine deployment.** DB stays at `./data/kai.db`,
  no XDG-dir indirection.

## [0.1.1] — 2026-04-26 — Scope refinement

### Changed
- **Bumped CBC alternatives from 3 to 4 per task.** Original 3-alt config gave 3.8:1 obs:params ratio for MNL; 4-alt gives exactly 5:1, the standard threshold for stable estimation. Caught at scaffolding stage before any business logic was written.
- **Confirmed single-user, MNL-only scope.** Removed HB estimator stub and the `[hb]` PyMC dependency group from `pyproject.toml`. HB's main value is multi-respondent pooling; with one respondent we have neither the data nor the need.
- **Confirmed local-only hosting.** No Docker, no cloud — just `uvicorn` on localhost. API binds to `127.0.0.1` only (not `0.0.0.0`), so it's not even reachable from other devices on the local network.

### Removed
- `estimation/hb.py` (deferred indefinitely)
- `[project.optional-dependencies.hb]` group from pyproject.toml

## [0.1.0] — 2026-04-26 — Scaffolding

### Added
- Project skeleton with directory structure for taxonomy, design, elicitation, estimation, diagnostics, storage, profile, frontend, tests, analysis.
- Pinned dependencies in `pyproject.toml` for reproducibility (FastAPI, SQLAlchemy, NumPy, scipy, statsmodels, pyDOE3, Typer).
- Optional `[dev]` extra for tests and linting (pytest, ruff, mypy).
- `config/taxonomy.yaml` — central taxonomy with 8 attributes × 3 levels each, mapped to 7 tenets.
- `config/design_params.yaml` — separable experimental design parameters.
- Pydantic schema (`taxonomy/schema.py`) enforcing taxonomy structural rules with cross-reference validation.
- YAML loader (`taxonomy/loader.py`) as single entry point for taxonomy access.
- Unit tests for taxonomy schema and loader, covering happy paths and validation failures.
- SQLAlchemy 2.0 typed ORM models for sessions, observations, and profiles.
- Module-level docstrings for every package describing intent, contracts, and implementation plans.
- Stub implementations (`NotImplementedError`) for: CBC design generation, MaxDiff design, MNL estimation, MaxDiff estimation, rating calibration, ensemble estimation, repository layer, FastAPI app, session orchestration, profile generation/export/diff, and CLI.
- `.env.example`, `.gitignore`, README, this changelog.

### Decisions
- **Estimation order:** MNL first.
- **Storage:** SQLite via SQLAlchemy 2.0; clean upgrade path to Postgres if needed.
- **Hosting:** Local-only via uvicorn for v1; design keeps Docker viable as future addition.
- **Design method:** Balanced overlap CBC for v1; orthogonal arrays available as alternative.
- **Profile persistence:** JSON snapshot column rather than relational decomposition (read-mostly access pattern).
- **Ensemble approach:** CBC carries primary signal weight; MaxDiff cross-validates tenet rankings; ratings anchor interpretable scale.
