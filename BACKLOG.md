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

### 1.1.5 Within-task overlap minimization (swap-based D-efficiency)

**WHAT:** Extend `kai.design.cbc_generator.generate_cbc_design()` for
`method="balanced_overlap"` to perform swap-based D-efficiency optimization
on top of the level-balanced sampling 1.1 already does.

Algorithm sketch: starting from the 1.1 level-balanced design, iterate up
to N times. In each iteration: pick a random pair of alternatives (within
the same task or across tasks), try swapping a single attribute's level
between them, accept the swap iff D-efficiency improves AND the swap
doesn't break level balance per attribute. Stop when no improving swap
is found in M consecutive attempts.

Must remain deterministic given the same seed.

**WHY:** Phase 1.2 calibration showed our 1.1 generator produces D-eff
~0.38 at production scale, statistically indistinguishable from pure
random sampling. The 0.85 quality gate is calibrated against full
Sawtooth-style balanced overlap which includes this swap step. Until
1.1.5 ships, the production design fails its own quality gate.

**TARGET:** Production D-eff >= 0.85 on `config/taxonomy.yaml` at
20 tasks x 4 alts. When the target is met, the sentinel test in
`tests/unit/test_design_diagnostics.py`
(`test_production_design_intentionally_fails_d_eff_gate`) flips its
assertion to expect `passes_gates=True`.

**PRIORITY:** Highest remaining Phase 1 work. Should ship before 1.4
(MNL estimator) so we estimate against a design that earns its quality
gate.

**OPEN QUESTIONS:**
- Greedy vs simulated annealing? Greedy is simpler and likely sufficient
  at our scale; SA only matters if greedy gets stuck in local minima.
  Default greedy unless calibration shows otherwise.
- Iteration cap: probably 1000-10000 swaps; tune based on D-eff
  stability across seeds.

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

## Forward-looking tenet patterns (build when triggered)

These patterns from ARCHITECTURE_TENETS are accepted in principle but
deliberately NOT implemented yet — premature implementation is itself
an anti-pattern. Each entry says WHEN to revisit.

### Circuit breaker pattern

**Source:** ARCHITECTURE_TENETS "Resilience & fault isolation"
**Trigger:** First feature that calls an external service repeatedly
(e.g., a future scraping plugin, a webhook delivery, a third-party
estimation library that can fail).
**Pattern:** After N consecutive failures, stop hammering for a
backoff window. Resume automatically when the window expires.
**Implementation:** Will live in `kai/shared.py` as a `CircuitBreaker`
context manager when first needed.

### Adaptive scheduling

**Source:** ARCHITECTURE_TENETS "Resilience & fault isolation"
**Trigger:** First feature that polls something on a schedule.
kAI is currently event-driven (questionnaire responses, manual estimation
triggers); no polling exists.
**Pattern:** Hot/normal/dead windows with different check frequencies.
Same code, different schedule.

### Resource pooling

**Source:** ARCHITECTURE_TENETS "Resilience & fault isolation"
**Trigger:** Profiling shows that creating-and-tearing-down per call
is a measurable bottleneck. SQLAlchemy's connection pool already
handles DB connections; we don't have other resources to pool.
**Pattern:** Reuse expensive resources across operations.

### Multi-signal verification

**Source:** ARCHITECTURE_TENETS "Resilience & fault isolation" /
"The false-positive lesson"
**Trigger:** First feature that parses noisy external sources (HTML
scrapes, vendor APIs that lie). kAI is currently a closed system —
all inputs come from the user via our own UI.
**Pattern:** Source-of-truth hierarchy; structured data first, fall
back to less reliable signals only when authoritative one is absent;
when in doubt, default to the safer answer.

### Per-feature debug CLI

**Source:** ARCHITECTURE_TENETS "Observability & debug modes"
**Trigger:** Each feature's first failure-prone code path. Add a
`python -m kai.<feature> debug` entry that prints raw inputs and
outputs of the most failure-prone functions.
**Pattern:** ~30 minutes per module to add; saves hours per incident
later.

### Tripwire log entries for reachability invariants

**Source:** ARCHITECTURE_TENETS "Observability & debug modes"
**Trigger:** Per-feature, as branches that should never be reached
get added.
**Convention:** Log at WARNING with prefix `TRIPWIRE: ` per ADR-010.
Investigate every occurrence; the entry is a debug breadcrumb, not
a metric.

### Auto-mask filter for log lines

**Source:** ARCHITECTURE_TENETS "Observability & debug modes"
**Trigger:** Repeated bugs where a developer forgot to wrap a value
with `mask_secret()` and it leaked into a log file.
**Pattern:** A `logging.Filter` subclass that scans log records for
patterns matching secret formats and replaces them in-place. Belt
and suspenders on top of explicit `mask_secret()` calls.

### Action-safety guard utilities

**Source:** ARCHITECTURE_TENETS "Action Safety" / ADR-009
**Trigger:** First feature that performs an irreversible action.
At v0.2.1 there is no such feature — kAI's only writes are to the
local SQLite. When the first irreversible-action surface is added
(profile export to Claude memory, share-to-Slack, etc.):
  - Add `validate_action_intent(target, expected_keywords,
    forbidden_keywords)` to shared.py
  - Wire the function-failure circuit breaker
  - Add tests that synthetic forbidden inputs raise ActionSafetyError

### Remove-and-explain pattern enforcement

**Source:** ARCHITECTURE_TENETS "Observability & debug modes"
**Trigger:** Code review convention; not infrastructure.
**Pattern:** When removing code because an approach didn't work, leave
a commented-out block with a one-line WHY. After 12+ months of stability,
the commented block can be deleted in a refactor.
**Adoption:** Already documented in `scripts/rollout.sh` step 3 reminder.
No enforcement automation needed unless we accumulate violations.

### Post-mortem / guardrails-as-code habit

**Source:** ARCHITECTURE_TENETS "Observability & debug modes"
**Trigger:** First incident or near-miss.
**Convention:** After any significant incident, write down:
  - What happened
  - Immediate cause
  - Contributing factor
  - What guardrail (in CODE, not in README) prevents recurrence
**Storage:** A new `INCIDENTS.md` file at repo root, formatted like
DECISIONS.md (one entry per incident). Guardrails go into `shared.py`
or relevant module.

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

### validate.sh: extend item #3 to catch non-ASCII in string literals

**WHAT:** Item #3 currently checks for non-ASCII in Python source but
appears to miss characters embedded inside string literals (`"\u2713"`,
`"✓"`, etc.). Extend to scan string contents.

**WHY:** Caught during Phase 1.1 rollout — `cli.py` shipped with a
literal ✓ that broke `kai validate-taxonomy` on Windows cp1252 consoles.
Local Linux dev never saw it.

### Sweep remaining non-ASCII chars from docstrings and comments

**WHAT:** ~100 em-dashes and a handful of arrows or inequalities remain
in docstrings and inline comments across the codebase. Replace with
ASCII equivalents (regular hyphens, `->`, `>=`).

**WHY:** Conform to Tenet 5 / validate.sh item #3 in spirit. Currently
latent - these chars never reach a console encoder because they live
in source-only `__doc__` attributes and comments. But they're a
tripwire: any future code path that prints a docstring or includes
one in an error message would fail on Windows cp1252.

**WHY NOT NOW:** Cleaning during Phase 1.1 rollout would have
scope-crept the PR with 100+ unrelated single-char edits. Captured
here for a focused doc-cleanup PR.

### Patch-script template: include shared.py in pre-delivery sandbox

**WHAT:** Patch scripts that generate Python files for the kAI tree
(typically new test files under `tests/unit/`) MUST include a
representative `src/kai/shared.py` (or at minimum that file's `__all__`
set) in the pre-delivery sandbox. The sandbox MUST run
`tests/unit/test_shared_uniqueness.py` against the patched state
before declaring success.

**WHY:** During the validate.sh / CI lint parity rollout, a generated
test file locally redefined `REPO_ROOT` (already exported by
`kai.shared`). The pre-delivery sandbox missed it because the sandbox
had no `kai.shared` module to detect the duplication. The Tenet 1
violation only surfaced when the operator ran `bash scripts/validate.sh`,
requiring a second fix-up patch in the same branch before commit.

The sandbox-fidelity principle: invariant-defining tests
(`test_shared_uniqueness.py`, `test_plugins_registry.py`) must run
against the patched state in the patch's own QC, not just on the
operator's machine. A patch that lands a Tenet 1 violation in the
operator's working tree is a QC failure even when downstream
validation catches it.

**PRIORITY:** Apply on the next patch script that generates Python
files for the kAI tree. Codify in any future `PATCH_SCRIPT_TEMPLATE.md`.

### Patch-script template: ruff format newly-generated Python files

**WHAT:** Any patch script that creates new Python files MUST run
`ruff format` on those files as a final edit step (before the
self-verification block). The script's own pre-delivery QC should
verify `ruff format --check` passes against the patched state.

**WHY:** The validate.sh parity rollout required the operator to run
`ruff format` manually on a generated test file because the heredoc-
written code was not born conformant. Friction is small (one extra
command), but recurring across any patch that touches Python. Baking
formatting into the patch script means generated code is always landed
already-formatted, and the operator's pre-validate `ruff format --check`
becomes purely a tree-wide drift check rather than a patch-output check.

**PRIORITY:** Apply on the next patch script that creates Python files.
Trivially small to add (one `ruff format <new_file>` invocation as a
final patch step).

### Generalize parity-test pattern as more CI workflows mirror locally

**WHAT:** `tests/unit/test_validate_script_lint_parity.py` asserts that
`scripts/validate.sh` and `.github/workflows/lint.yml` stay in sync on
the ruff invocations. Currently lint is the only CI workflow with a
local mirror. As more workflows acquire local mirrors (e.g., a future
type-check workflow mirrored in `validate.sh`), each pair should grow
its own parametrized `tests/unit/test_<workflow>_local_parity.py`.

**WHY:** The local validation gate must be a strict superset of CI's
enforcement, or a clean local 10/10 does not imply a clean CI run. The
parity-test pattern generalizes naturally; one parity test per
(local check, CI workflow) pair scales until 3-5 pairs exist.

**OPEN QUESTIONS:**
- At what point (3+ workflows? 5+?) does a single meta-test that walks
  all `.github/workflows/*.yml` and asserts each step has a local
  equivalent become preferable to one parity test per pair? Defer until
  at least a second parity test actually exists. YAGNI.

**PRIORITY:** Triggered by the addition of a second CI workflow with a
local mirror, NOT by clock time. Today this entry is just a reminder of
the pattern; no work to do until then.

