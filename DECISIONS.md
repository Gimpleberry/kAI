# Architecture Decisions

This document records the *why* behind architectural choices. Different from
`CHANGELOG.md` (which records *what* changed). Read this when you're about to
make a change and want to understand if there's a reason the current design
exists.

Format: each decision is dated and structured as Context → Decision → Consequences.

---

## ADR-001: Local-only hosting (no cloud, no Docker for v1)

**Date:** 2026-04-26
**Status:** Accepted

### Context
kAI handles personal preference data. Cloud hosting would
introduce a network attack surface, third-party dependencies, and recurring
costs (~$5/mo) for a single-user tool that runs on a laptop just fine.

### Decision
Run via `uvicorn` bound to `127.0.0.1:8000` only. SQLite database on local
disk. No Docker. No reverse proxy. No external network calls during normal
operation.

### Consequences
- ✓ Tenet #3 (safe) satisfied by construction — there is no remote attack surface
- ✓ Zero hosting costs
- ✓ Works offline
- ✗ Cannot use the tool from a different device without setting up dev environment there
- ✗ No automatic backups (must be done manually or via the planned CLI command)

### Reversibility
Easy. The FastAPI app is portable — wrapping it in a Dockerfile and pointing
at a hosted Postgres is a few hours of work if circumstances change.

---

## ADR-002: MNL estimation only, no Hierarchical Bayes

**Date:** 2026-04-26
**Status:** Accepted

### Context
HB shines when pooling information across many respondents to get individual
estimates from sparse data. With a single respondent (the project owner) and
80 CBC observations, MNL with bootstrap CIs delivers ≥90% of the value at
~1% of the implementation complexity.

### Decision
Implement MNL via scipy.optimize as the only estimator. Drop PyMC dependency.
Bootstrap CIs replace Bayesian posteriors.

### Consequences
- ✓ Faster (seconds, not minutes per estimation)
- ✓ Fewer dependencies (no PyMC, no arviz, no compiler-heavy install)
- ✓ Simpler diagnostic story (optimizer convergence vs. R-hat/ESS/divergences)
- ✗ Cannot natively support multiple respondents if scope ever expands
- ✗ Bootstrap CIs are frequentist; loses some Bayesian niceties (full posterior, prior incorporation)

### Reversibility
Medium. The `EstimatedProfile` data contract is method-agnostic — adding an
HB estimator later is a sibling file in `estimation/`, not a refactor.

---

## ADR-003: Code on GitHub, data local-only

**Date:** 2026-04-26
**Status:** Accepted

### Context
The repository contains both engineering artifacts (taxonomy, code, designs)
and personal preference data (responses, profiles). These have fundamentally
different sharing properties:
- Code is reproducible, shareable, has no privacy implications
- Data is personal, sensitive, and reproducing it requires the human re-answering

### Decision
- Code → GitHub (private or public, owner's choice)
- Data → local disk only, gitignored, never committed
- Specifically: `data/`, `*.db`, `*.sqlite`, `*.sqlite3`, `.env` are all in `.gitignore`
- Database default location: `./data/kai.db` (inside repo, gitignored)

### Consequences
- ✓ Cannot accidentally commit personal data
- ✓ Repo can be made public without privacy review
- ✓ Cloning the repo on a new machine gives a clean, working system (no data inheritance)
- ✓ Backups of personal data are explicit and intentional, not coupled to git operations
- ✗ Re-creating preference history requires either a backup or re-running the questionnaire

### Enforcement
- `.gitignore` patterns prevent accidental staging
- `pre-commit` hook (in `scripts/`) double-checks no `.db` files are being committed
- `scripts/setup.sh` creates `data/` directory on first run
- `.github/workflows/secret-scan.yml` runs gitleaks on every PR (added v0.2.0)

### Related
- ADR-004 (DB location)
- ADR-005 (Design reproducibility)

---

## ADR-004: SQLite file lives at ./data/kai.db inside the repo

**Date:** 2026-04-26
**Status:** Accepted

### Context
Single-user, single-machine deployment. The DB could live in user-data dirs
(`~/.local/share/...`) or inside the repo. The XDG-standard location is
better for multi-user / cross-machine setups; in-repo is better for "everything
in one place" mental model.

### Decision
Default to `./data/kai.db` inside the repo, with `data/` gitignored.
Path is overridable via `KAI_DB_URL` env var.

### Consequences
- ✓ Simple mental model: backup = tar the project directory
- ✓ Easy to delete/reset: remove the file
- ✓ Works for the single-machine case without configuration
- ✗ If repo is moved/cloned, data does not follow (this is acceptable — see ADR-003)

---

## ADR-005: CBC designs are reproducible from seed, not stored verbatim

**Date:** 2026-04-26
**Status:** Accepted

### Context
A CBC design is a specific set of choice tasks shown to the respondent.
Designs can be stored as full data, OR regenerated deterministically given
a seed and parameters.

### Decision
Store only the seed + design parameters in the `sessions` table. Regenerate
the design on demand using `generate_cbc_design(taxonomy, n_tasks, n_alts, seed=...)`.

### Consequences
- ✓ Smaller storage footprint
- ✓ If DB is corrupted but seed is recoverable (e.g., from logs), design is reconstructable
- ✓ Design generator becomes a pure function, easier to test
- ✗ Changes to the design generator algorithm break old sessions (mitigation: version the generator alongside taxonomy)

### Caveats
The taxonomy referenced by the seed must be identical. If taxonomy changes
between session creation and re-generation, regeneration will produce a
different design. Therefore: `taxonomy_version` is also stored on the session
row, and regeneration verifies version match.

---

## ADR-006: Project naming convention — kAI for branding, kai for Python

**Date:** 2026-04-26
**Status:** Accepted

### Context
The project owner wants the styled name "kAI" for branding. Python has rules
about package names: lowercase preferred, no special characters, hyphens
allowed in install names but not in import statements. Forcing the styled
name into Python would mean either non-conventional imports (`from kAI ...`)
that confuse tooling or workarounds that complicate the layout.

### Decision
Layered naming, each layer using the form most appropriate for its context:

| Layer | Name | Where it appears |
|---|---|---|
| Project / repo / folder | `kAI` | GitHub repo name, top-level folder, branding |
| Python package | `kai` | `from kai.taxonomy import ...`, `src/kai/` |
| PyPI / installable name | `kai` | `pyproject.toml` `name = "kai"` |
| CLI command | `kai` | `kai validate-taxonomy` |
| Env var prefix | `KAI_` | `KAI_DB_URL`, `KAI_HOST` |

This pattern matches established projects: "FastAPI" → `fastapi`,
"scikit-learn" → `sklearn`, "PyYAML" → `yaml`, "BeautifulSoup" → `bs4`.

### Consequences
- ✓ Branding visible everywhere humans look (folder, repo, CLI prompt, README headings)
- ✓ Python code follows convention — IDE autocomplete works, linters happy, no import surprises
- ✓ Env vars in standard SCREAMING_SNAKE_CASE
- ✗ Two forms of the name to remember (kAI for prose, kai for code) — but this is the same situation every Python project with a styled name handles

### Reversibility
Hard. Renaming a Python package after code is written requires updating every
import statement. Locking this in at scaffolding time is intentional.

---

## ADR-007: Python 3.12.x specifically (not >=3.11 unbounded)

**Date:** 2026-04-26
**Status:** Accepted

### Context
Initial scaffolding declared `requires-python = ">=3.11"`. In practice, when
the user attempted setup on a fresh Windows install they had Python 3.14.4,
which has no pre-built wheels for several pinned scientific dependencies
(numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, etc.). pip would have either
failed or attempted to compile from source — requiring a full C++ toolchain
on Windows.

### Decision
Pin to Python 3.12.x specifically: `requires-python = ">=3.12,<3.13"`.

The setup script searches for Python in this priority order:
1. `py -3.12` (Windows Python launcher)
2. `python3.12` (Linux/macOS explicit)
3. `python3` if and only if it reports Python 3.12.x
4. `python` if and only if it reports Python 3.12.x

### Consequences
- ✓ Reproducibility: same Python version + same pinned deps = identical numerical results
- ✓ Setup works on any platform with Python 3.12 installed, regardless of whether 3.13 or 3.14 is also present
- ✓ When we eventually upgrade Python, it's a deliberate decision documented in a future ADR — not silent breakage
- ✗ Users with only 3.13 or 3.14 installed must install 3.12 alongside (one-time friction)
- ✗ Have to remember to bump this when 3.12 reaches end-of-life (October 2028)

### Why 3.12 specifically (not 3.11 or 3.13)
- 3.11: Older. Eventually we'd have to upgrade anyway.
- 3.12: Current LTS-style stable. All pinned scientific libraries publish wheels.
  Supported until October 2028.
- 3.13: Released October 2024. Several scientific libraries took 3-6 months to
  publish wheels. As of mid-2025 most are caught up but some still lag.
- 3.14: Released October 2025. Same lag problem as 3.13 was at launch.

### Reversibility
Easy in principle (change one number in `pyproject.toml`), but should be
treated as a non-trivial change because:
- All pinned dependency versions need re-validation against the new Python
- All tests must pass on the new version
- The CI matrix (when we have one) must be updated
- A new ADR must document the upgrade decision

### Related
- `pyproject.toml` (`requires-python` field)
- `scripts/setup.sh` (Python detection logic)

---

## ADR-008: Adopt the ARCHITECTURE_TENETS plugin pattern

**Date:** 2026-04-26
**Status:** Accepted

### Context
The user uploaded ARCHITECTURE_TENETS.txt as project knowledge. Reviewing
kAI against it surfaced a meaningful divergence: kAI was structured as a
"library + FastAPI app" with no central plugin registry, no shared.py
module, no main.py lifecycle orchestrator. Tenet 1 mandates all three.

The choice was: keep diverging (justified for some project shapes) or
realign (mandatory if cross-project consistency matters to the owner).
The owner explicitly chose the strict plugin pattern.

### Decision
Adopt the full plugin pattern from ARCHITECTURE_TENETS Tenet 1:

1. **`src/kai/shared.py`** is the single source of truth for cross-cutting
   paths, constants, error types, and config-loading entry points.
   Mechanically enforced by `tests/unit/test_shared_uniqueness.py`, which
   scans every Python file in src/ and tests/ and fails CI if any name
   in `shared.__all__` is redefined elsewhere.

2. **`plugins.py`** at the repo root is the feature registry. One line per
   plugin, in boot order. Adding a feature = create a `<feature>/plugin.py`
   module + one line in the registry.

3. **`main.py`** at the repo root is the lifecycle entry point. It imports
   `REGISTRY` from `plugins.py` and calls `start()` on each in order, then
   blocks until shutdown signal, then calls `stop()` in reverse order.

4. **Each feature module exposes a `Plugin` class** with `start()` and
   `stop()` methods. Plugin protocol defined in `src/kai/plugin_base.py`.

5. **Boot order is documented** in `plugins.py`: storage-creating plugins
   load before consumers, FastAPI server loads last.

### Consequences
- ✓ Architectural consistency with the owner's other projects (PokeBS pattern)
- ✓ Adding new features is mechanical: create module, add line, no other
  files touched
- ✓ Disabling a feature is one comment-out
- ✓ Boot order is explicit and reviewable rather than implicit and tangled
- ✓ Mechanically enforceable: shared.py uniqueness test, plugin protocol test
- ✗ More files for the same functionality (plugin shells around each module)
- ✗ Plugin lifecycle methods are mostly nominal at this stage — they exist
  for the protocol's sake even when there's nothing meaningful to start/stop

### Why we accepted the cost
The "more files for the same functionality" cost is paid once at scaffolding
time. The "easier to add features later" benefit compounds with every new
feature. For a project that will accumulate plugins over phases (CBC, MaxDiff,
ratings, profile export, frontend, analysis tools, etc.), the trade favors
the pattern.

### Reversibility
Medium. Removing plugins.py and merging shared.py back into individual
modules is mechanical but touches every file. The plugin pattern is sticky
once code starts depending on the cached singletons it provides (e.g.,
`get_taxonomy()`).

### Adapted Tenet 5 validation checklist
The tenet document's 10-item checklist references plugin concepts directly.
We adopted them as written:
- Item 4 (plugin registry check): enforced by
  `tests/unit/test_plugins_registry.py`
- Item 6 (lifecycle check): enforced by `python main.py --check`
- All 10 items runnable as one command via `bash scripts/validate.sh`

### Related
- `plugins.py`, `main.py`, `src/kai/shared.py`, `src/kai/plugin_base.py`
- All `src/kai/*/plugin.py` files
- `scripts/validate.sh`
- `tests/unit/test_shared_uniqueness.py`
- `tests/unit/test_plugins_registry.py`

---

## ADR-009: Action safety — automation prepares, human commits

**Date:** 2026-04-26
**Status:** Accepted

### Context
The updated ARCHITECTURE_TENETS document expanded Tenet 3's action-safety
section with a clearer formulation: "the script never makes a decision
that's expensive to undo." kAI's current code surface has no irreversible
actions, but several future surfaces could acquire them silently:

- Profile export could write to Claude memory or auto-commit a profile to git
- Frontend could be wired to "share to Slack" or similar publishing flows
- A CLI `kai apply-profile` command could mutate user-visible state elsewhere
- Future scraping integrations (none planned) would qualify

Encoding the principle as an ADR before any of those exist prevents
violation by accretion.

### Decision
Adopt the "automation prepares, human commits" pattern as a project
invariant. Concretely:

1. **Automation is allowed to:** read, compute, validate, log, write to
   the local DB, generate files locally, prepare drafts, open browsers
   to a pre-filled state.

2. **Automation is NOT allowed to:** click "send" / "publish" / "buy" /
   "deploy" / "purchase" / "place order" / anything that mutates state
   visible outside the local machine, without an explicit per-action
   confirmation by a human.

3. **Where the line is enforced:** any code that performs an
   irreversible-by-design action (defined as: an action whose undo
   requires manual intervention by an external system) MUST:
   - Validate the intent matches expected positive keywords AND does
     NOT match dangerous negative keywords
   - Surface ambiguous cases as errors (raise `ActionSafetyError`),
     not silent skips
   - Log the attempt at INFO with the masked target
   - Implement a circuit breaker: after N consecutive anomalies, stop
     and surface

4. **The reverse principle:** actions that are CHEAP to undo (write a
   log line, send a notification to yourself, refresh a cache) can be
   fully automated. Reserve human attention for actions that matter.

### Consequences
- ✓ The architecture explicitly carves out a "no irreversible actions"
  contract. Future code that violates it has to be a deliberate ADR.
- ✓ `ActionSafetyError` is now in `shared.py` for any future code
  needing to raise it.
- ✗ Some convenience features become harder to implement. That's the
  point. We're trading speed-of-implementation for reduced blast radius.

### Currently in scope (audit)
At v0.2.1, kAI has zero irreversible-action surfaces. Future surfaces
that would require this ADR's enforcement, when added, are noted in
BACKLOG.md as relevant.

### Reversibility
Easy to relax (allowlist a specific action surface), hard to reinstate
once relaxed without auditing every relaxation. So: don't relax it.

---

## ADR-010: Structured logging conventions

**Date:** 2026-04-26
**Status:** Accepted

### Context
The updated tenets added an "Observability & debug modes" section
specifying:
  - No `print()` for anything that ships
  - Per-component log prefixes (`[api]`, `[bestbuy]`, etc.)
  - Five-level log discipline (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - Log rotation at a size limit
  - Mask secrets inside the helper that does the logging
  - Tripwire log entries for "events that should never happen"

### Decision
1. **No `print()` in shipping code.** Use `logging.getLogger("kai.<module>")`
   exclusively. The lint rule (manual for now, automated in a future ADR)
   is: any `print(` call in `src/kai/` is a bug.

2. **Logger naming convention.** `kai.<package>.<module>` — e.g.,
   `kai.elicitation.api`, `kai.estimation.mnl`. This makes
   `grep '\[kai\.estimation' kai.log` isolate one subsystem.

3. **Log rotation.** Plugins use `setup_rotating_logger()` from
   `kai.shared` to get an automatically-rotating file handler at
   `data/logs/<n>.log`. Default 5 MB × 3 backups; configurable per
   call.

4. **Secret masking.** Anywhere a config value, token, ID, or URL with
   embedded credentials might end up in a log line, callers wrap it
   with `mask_secret()` from `kai.shared`. The masking lives inside
   the helper, not in callers' control flow — but callers must reach
   for it. A future tooling enhancement is to add a custom log filter
   that auto-masks values matching secret patterns.

5. **Tripwire convention.** Events that should never happen get logged
   at WARNING (or higher) with the prefix `TRIPWIRE: ` and enough
   context to investigate. Examples: CORS-rejected request from
   unexpected origin, schema_version mismatch on boot, circuit-breaker
   trip, paths that are "supposed to be unreachable."

### Consequences
- ✓ Logs become diagnosable rather than ornamental
- ✓ Secrets stay out of logs by default
- ✓ Disk-fill is no longer a failure mode
- ✗ Slightly more boilerplate per module — `setup_rotating_logger()`
  call in each `Plugin.start()`. Acceptable.

### Migration
Existing modules in v0.2.0 use `logging.getLogger(...)` correctly but
do NOT yet call `setup_rotating_logger`. Each plugin's `start()` will
adopt it as that plugin gains real logic to log. Until then, the basic
logger format from `main._setup_logging()` is sufficient.

### Reversibility
Easy.

---

## ADR-011: Versioning scheme and release tags

**Date:** 2026-04-26
**Status:** Accepted

### Context
The updated tenets added a "Patch rollout process" section specifying
a versioning scheme (`major.minor[.patch]`) and a multi-tag taxonomy
applied to each release. We've been using major.minor informally
already; this ADR codifies it.

### Decision

**Format:** `major.minor[.patch]`, leading "v" in git tags only
(`v0.2.1`, not `0.2.1` in pyproject.toml).

**Bump rules:**
- **MAJOR** — architecture change other plugins must adapt to; storage
  schema change with no backward-compat shim; removal of a public
  API/symbol; breaking change. Triggers full re-validation.
- **MINOR** — new feature/plugin/page; additive API; security hardening
  that changes behavior; refactor that changes file layout.
- **PATCH** — bug fix with no observable behavior change; doc-only
  changes; minor tuning (intervals, retry counts); removing a
  no-longer-working dep.

**Tags** (one or more per release, declared in CHANGELOG):
`Major | Feature | Fix | Security | Refactor | Performance |
Architecture | Scalability`

**Release process:**
1. Bump version in `pyproject.toml` and `src/kai/__init__.py`
2. Add CHANGELOG.md entry with version + date + tags + changes
3. Merge to main
4. Tag: `git tag -a v0.2.1 -m "description"` then `git push --tags`
5. (Optional) Create a GitHub Release pulling release notes from the
   changelog entry

### Tag retroactive assignment for existing versions
- v0.1.0 — Architecture, Feature (initial scaffold)
- v0.1.1 — Refactor (CBC ratio + scope cut)
- v0.1.2 — Security, Architecture (storage policy, pre-commit hook)
- v0.1.3 — Architecture (design reproducibility, BACKLOG)
- v0.1.4 — Refactor (rename to kAI)
- v0.1.5 — Architecture (Python 3.12 pin, cross-platform setup)
- v0.2.0 — Architecture, Feature (tenet alignment pass)
- v0.2.1 — Feature, Architecture (resilience helpers, action safety, rollout process)

### Consequences
- ✓ Future-you can scan CHANGELOG and know at a glance whether an
  upgrade is risky (Major) or trivial (Patch).
- ✓ The CI matrix can react to tags — e.g., Major releases trigger
  the full validation matrix on multiple OSs.
- ✗ One more thing to remember at release time. Mitigated by
  `scripts/rollout.sh` step 10 reminding you.

### Reversibility
Trivial. The tags are advisory metadata.
