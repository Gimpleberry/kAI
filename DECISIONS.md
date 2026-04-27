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

We had two choices:
1. Loosen the pinned dependencies to "latest" so pip could find compatible versions
2. Tighten the Python version requirement to one that has wheels for our pins

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
