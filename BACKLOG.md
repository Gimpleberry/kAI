# Backlog

Future-state plan. Phase-ordered: each phase finishes before the next starts.
Doing them out of order causes rework (per ARCHITECTURE_TENETS Tenet 4).

When picking up an item:
1. Move the entry into the `[Unreleased]` section of CHANGELOG.md when work begins
2. If it requires an architectural choice, write a new ADR in DECISIONS.md first
3. **Delete** the entry from this file once shipped — git history is the record

---

## Phase 0 — Foundation (DONE)

Architectural scaffolding, naming, dependencies, validation infrastructure.
All items complete; kept here briefly for navigation.

- [x] Project rename (preference-engine → kAI) — v0.1.4
- [x] Python 3.12.x version pin — v0.1.5 / ADR-007
- [x] Storage policy (code → GitHub, data → local) — v0.1.2 / ADR-003
- [x] Design reproducibility (store seed only) — v0.1.3 / ADR-005
- [x] shared.py + plugin registry pattern — v0.2.0 / ADR-008
- [x] 10-item validate.sh + .github/ infrastructure — v0.2.0

**Phase 0 exit criterion:** `bash scripts/validate.sh` returns Passed: 10 / 10
on a fresh clone.

---

## Phase 1 — CBC core

Goal: a working, tested CBC design generator and MNL estimator on synthetic
data. By the end of this phase, we can hand-run estimation against fake
respondents and verify the math is correct.

### 1.1 CBC design generator (balanced overlap method)

**WHAT:** Implement `kai.design.cbc_generator.generate_cbc_design()` returning
a `CBCDesign` with deterministic output for `(taxonomy, params, seed)`.

**WHY:** Foundation for everything downstream. No design ⇒ no questionnaire
⇒ no responses ⇒ no estimation. Also enforces ADR-005's determinism contract.

**OPEN QUESTIONS:**
- Pure Python or pyDOE3 for the level-balanced sampling?
- Tolerance for "near-balanced" vs strict equal-frequency on tasks that
  don't divide evenly?

### 1.2 Design diagnostics (D-efficiency, level balance)

**WHAT:** Implement `kai.design.design_diagnostics.diagnose_cbc_design()`
returning a `DesignReport` with D-efficiency, level frequencies, dominated
alternative count, pass/fail vs gates.

**WHY:** Quality gate before any human sees the questionnaire. Bad designs
waste your time and corrupt estimation.

### 1.3 Determinism test

**WHAT:** Test that asserts byte-identical output for the same inputs across
runs. Run multiple seeds; pickle each design and compare hashes.

**WHY:** ADR-005 contract. If this test ever fails, the seed-storage policy
is broken and old sessions can't be reproduced.

### 1.4 MNL estimator (MLE + bootstrap CIs)

**WHAT:** Implement `kai.estimation.mnl.estimate_mnl()` returning a fully
populated `EstimatedProfile` with point estimates, 95% CIs via bootstrap,
log-likelihood, and convergence flag.

**WHY:** This is THE math. Everything else is plumbing.

### 1.5 Synthetic recovery test

**WHAT:** Generate fake CBC choices from known part-worths, run estimation,
verify recovered values are within 2 × SE of true values.

**WHY:** The single highest-value test in the codebase. If this passes, the
math is correct. If it fails, something fundamental is broken.

**Phase 1 exit criterion:** Synthetic recovery test passes for at least 3
different parameter regimes (low, mid, high signal-to-noise).

---

## Phase 2 — Storage layer

Goal: real SQLAlchemy implementations replacing the stubs, with migrations
and the repository pattern wired up.

### 2.1 SQLAlchemy engine + session factory

**WHAT:** Implement `StoragePlugin.start()` to create the engine, run
`Base.metadata.create_all()`, insert/check `schema_meta` row.

**WHY:** Plugin currently logs and does nothing. Real persistence depends on this.

### 2.2 Repository implementations

**WHAT:** Replace `NotImplementedError` in `SessionRepository`,
`ObservationRepository`, `ProfileRepository` with real CRUD.

### 2.3 Alembic migrations bootstrapped

**WHAT:** Initialize Alembic, create the v1 baseline migration matching the
current ORM models.

**WHY:** Future schema changes need a migration path. Setting this up before
the schema evolves prevents painful retrofitting.

**Phase 2 exit criterion:** Round-trip test: create session, insert
observations, save profile, reload, compare equals — passes.

---

## Phase 3 — Elicitation API

Goal: FastAPI server exposing endpoints the (future) frontend will hit.

### 3.1 FastAPI app factory + lifecycle integration

**WHAT:** Implement `create_app()`, integrate uvicorn into
`ElicitationPlugin.start()`/`stop()`.

### 3.2 Session endpoints

**WHAT:** POST /sessions, GET /sessions/{id}, GET /sessions/{id}/next-task,
POST /sessions/{id}/responses.

### 3.3 Estimation + profile endpoints

**WHAT:** POST /sessions/{id}/estimate, GET /sessions/{id}/profile,
GET /sessions/{id}/diagnostics.

### 3.4 Health + introspection

**WHAT:** GET /health, GET /docs (FastAPI auto-generated).

**Phase 3 exit criterion:** Can create a session, fetch a task, submit a
response, trigger estimation, and retrieve a profile, all via curl.

---

## Phase 4 — Frontend

Goal: a working browser UI to actually run the questionnaire.

### 4.1 Skeleton + question rendering

**WHAT:** Single-page HTML+JS app that hits the API, renders CBC tasks,
captures choices.

**WHY:** Without this, the only way to use kAI is curl. Not viable.

### 4.2 In-app Help section (per Tenet 4)

**WHAT:** /help page with FAQ, diagnostic commands, file reference. Ships
WITH this feature, not as a follow-up.

### 4.3 Profile review page

**WHAT:** Visual rendering of part-worths, importances, archetype, with
copy-to-clipboard for the Claude preferences string.

**Phase 4 exit criterion:** End-to-end flow — open localhost, answer
questions, see profile — works for one human (you).

---

## Phase 5 — Hybrid signals (MaxDiff + ratings)

Goal: bring the second and third question formats online, validate that
the ensemble is more robust than CBC alone.

### 5.1 MaxDiff design generation (BIBD)
### 5.2 MaxDiff estimator (rank-ordered logit)
### 5.3 Direct rating UI flow + calibration math
### 5.4 Ensemble estimator (weighted combination)
### 5.5 Stated-vs-revealed gap detection (ported from v0 prototype)

**Phase 5 exit criterion:** Ensemble profile has tighter CIs than CBC-alone
profile on the same synthetic respondent.

---

## Phase 6 — Profile export + history

Goal: profiles are persistent, comparable across sessions, and exportable
in formats useful outside kAI.

### 6.1 Profile generator (archetype, summary, tradeoff examples)
### 6.2 Multi-format exporters (text, markdown, JSON, claude_prefs)
### 6.3 Profile differ (compare two profile versions)
### 6.4 Profile evolution view (trend charts in /diagnostics)

**Phase 6 exit criterion:** Re-running the questionnaire produces a profile
that can be diffed against the previous one, showing what changed.

---

## Phase 7 — Polish, analysis tooling, optional enhancements

These are deliberately last because they're easy to do prematurely. Skip
to whichever subset is actually useful.

- Adaptive question selection (deferred — see ADR-005 mention)
- Hierarchical Bayes estimation (deferred indefinitely — see ADR-002)
- Jupyter notebooks for design exploration / model validation
- CLI: `kai estimate`, `kai export`, `kai diff`, `kai diagnose`, `kai backup`
- Backup/snapshot rotation in `data/backups/`
- Branch protection + CI matrix expansion (3.13 once wheels exist)

---

## Cross-cutting / not-phase-aligned

These cut across phases or apply project-wide.

### Claude Project setup

**Status:** Deferred to user
**WHAT:** Create `.claudeproject/` directory at repo root with
PROJECT_OVERVIEW, CURRENT_STATE, upload_manifest, sync.sh.
**WHY:** Stops re-establishing context every conversation.
**OPEN QUESTIONS:** Owner will set up independently.

### Observation: phase ordering matters

The phases above are not arbitrary. Specifically:
- Phase 1 before Phase 2: estimation math is meaningless without working
  designs to estimate from.
- Phase 2 before Phase 3: the API needs persistence underneath it.
- Phase 3 before Phase 4: the frontend hits the API; building UI without
  the backend leads to mock-driven design that doesn't survive integration.
- Phase 4 before Phase 5: humans need to actually try the basic CBC flow
  before we add complexity. If CBC alone doesn't feel right, MaxDiff won't fix it.
- Phase 5 before Phase 6: ensemble estimation defines what "the profile" is,
  and export is downstream of that.
