# kAI - Session handoff

This document is meta-information about the working state of recent
Claude conversations about kAI. Read this at the start of any new
conversation to catch up fast.

Distinct from `PROJECT_KNOWLEDGE.txt` (current-state architecture),
`DECISIONS.md` (rationale for past architectural choices), and
`BACKLOG.md` (forward-looking work plan). This doc is short-lived: it
gets rewritten at the end of each significant session. Old content
moves out, new state moves in.

**Last updated:** 2026-04-27, end of Phase 1.1 + 1.2 session.

---

## Where we are

**Repo:** https://github.com/Gimpleberry/kAI (public, branch protection active)
**Local:** `C:\dev\kAI\kAI\` (note doubled folder - see PROJECT_KNOWLEDGE Section 2)
**HEAD:** Phase 1.2 squash merge (#2) on `main`
**Latest tag:** `v0.2.1`
**Validation:** 10/10 passing on `bash scripts/validate.sh`
**Tests:** 91 passing (was 41 at start of session)

## What just got done (this session)

Today shipped Phase 1.1 (CBC generator) and Phase 1.2 (design
diagnostics) as two separate PRs, each through a full rollout with
branch protection and CI. Three local-vs-CI gate gaps were caught and
captured during the rollouts.

### PR #1 - Phase 1.1: CBC balanced-overlap generator + determinism tests

- `kai.design.cbc_generator.generate_cbc_design()` - level-balanced
  independent shuffles, single seeded numpy RNG, byte-identical output
  verified across processes and across `PYTHONHASHSEED` values.
- `tests/unit/test_cbc_generator.py` - 27 tests covering output
  contract, level balance (perfect when divisible, near-balanced
  otherwise with deterministic alphabetical-first remainder),
  determinism (closes BACKLOG 1.3), validation, production-config smoke.
- Caught 9 files of pre-existing ruff format drift; fixed in same PR.
- Caught Windows cp1252 encoding failure on unicode characters in
  `cli.py` and `main.py` `print`/`logger` calls; replaced with ASCII.
- BACKLOG: closed 1.1 + 1.3.

### PR #2 - Phase 1.2: design diagnostics + 1.1.5 surfaced

- `kai.design.design_diagnostics.diagnose_cbc_design()` - computes
  D-efficiency, level balance, max imbalance, duplicate-alternative
  count; checks against shared.py quality gates; returns DesignReport.
- D-efficiency uses standard MNL relative formulation under uniform
  priors: `det(I)^(1/p) / N` where `I = sum_t X_t' M X_t` with M the
  J x J within-task centering matrix. Catches task-degenerate designs
  (an attribute constant across all alts in a task contributes zero
  info). Effects coding: deviation/sum-to-zero, alphabetically-first
  level as reference.
- Numerical stability via `numpy.linalg.slogdet`; singular info matrix
  reports d_efficiency=0.0 with descriptive failed_gates msg.
- Hand-verifiable: orthogonal 2x2 design hits exactly 1.0; singular
  design hits exactly 0.0.
- `kai.shared.QUALITY_GATE_MAX_LEVEL_IMBALANCE = 0.15` promoted from
  literal in design_params.yaml to cross-module constant per Tenet 1.
- `DesignReport.n_dominated_alternatives` renamed to
  `n_duplicate_alternatives` - strict dominance requires preference-
  direction metadata not currently in the schema; we count duplicates
  within a task (computable, real pathology). Real dominance detection
  captured in BACKLOG.
- `tests/unit/test_design_diagnostics.py` - 23 tests covering output
  contract, level balance, D-efficiency (orthogonal + singular cases),
  duplicate detection, gate logic, default-thresholds-from-shared
  (Tenet 1), production-config sentinel.
- BACKLOG: closed 1.2.

### Big finding from PR #2

Production D-efficiency lands at **0.38** on the real
`config/taxonomy.yaml` at 20 tasks x 4 alts. The 0.85 quality gate is
calibrated against full Sawtooth balanced overlap (which uses swap-
based D-eff optimization on top of level balancing). Calibration over
20 seeds shows our generator is statistically indistinguishable from
pure random sampling.

**Decision (signed off):** ship 1.2 with a deliberate sentinel test
asserting the gate failure, capture the fix as new BACKLOG item 1.1.5,
preferred over weakening the 0.85 gate. Estimation still works at
D-eff 0.38 (wider CIs, not wrong answers), so the intermediate state
is survivable. PROJECT_KNOWLEDGE.txt Section 9 documents this as
ITEM 3 in the Known Issues register.

### Tooling/QC follow-ups captured during rollouts

Three local-vs-CI gate gaps surfaced when validate.sh passed 10/10
locally but CI rejected the PRs. All captured in BACKLOG:

1. **validate.sh item #1**: should also run `ruff format --check`.
   Caught twice in two PRs - this is the next thing to fix.
2. **validate.sh item #3**: encoding sweep extended during this
   session to catch non-ASCII in output-context strings (print/echo/
   logger calls). DONE - test confirms PASS in latest gate run.
3. **Codebase-wide ASCII sweep of docstring/comment unicode** (~100
   em-dashes/arrows). Latent, not active. Cheap insurance for a
   future doc-cleanup PR.

## What's next

Two reasonable choices for next session, in priority order:

### Option A - Quick toolchain PR (~15 min)

Add `ruff format --check` to validate.sh item #1. Closes the BACKLOG
gap that bit us in both PRs today. After this, the local gate matches
CI exactly. Small, focused, removes a recurring papercut before it
bites a third time.

### Option B - Phase 1.1.5: within-task overlap minimization

Real algorithmic work. Extend `cbc_generator.generate_cbc_design()`
for `method="balanced_overlap"` to perform swap-based D-efficiency
optimization on top of the level-balanced sampling. Target: production
D-eff >= 0.85. When the target is met, the sentinel test in
`test_design_diagnostics.py`
(`test_production_design_intentionally_fails_d_eff_gate`) flips its
assertion to expect `passes_gates=True`.

**Recommended order: A then B.** A unblocks the gate parity issue
that would otherwise bite during B's rollout. B is the real feature
work and shouldn't start tired.

After 1.1.5, Phase 1 continues with:
- **1.4: MNL estimator** - `estimate_mnl()` returning a fully populated
  `EstimatedProfile` with bootstrap CIs. THE math.
- **1.5: Synthetic recovery test** - generate fake choices from known
  part-worths, verify recovery within 2 x SE. Highest-value test in
  the codebase.

Phase 1 exit criterion: synthetic recovery passes for 3 different
SNR regimes.

See `BACKLOG.md` for the full phased breakdown.

## How to start the next session

When you start a new conversation about kAI:

1. Open the conversation in the same Claude project (project knowledge
   auto-loads).
2. Tell me: "Ready to start [Option A or B]" - or just describe what
   you want to do.
3. I'll have access to `PROJECT_KNOWLEDGE.txt`, this handoff doc, and
   `ARCHITECTURE_TENETS.txt`.
4. First action depends on which option:
   - **Option A**: read `scripts/validate.sh`, propose the diff.
   - **Option B**: read `cbc_generator.py` (the shipped code, not the
     stub), confirm the algorithm sketch from BACKLOG 1.1.5, then
     implement.

## kAI-specific operational notes

These are quirks of the kAI environment that future Claude needs to
know to be efficient:

- **Doubled folder**: project root is `C:\dev\kAI\kAI\` not
  `C:\dev\kAI\`. Every command should use the inner path.
- **Windows + Git Bash**: shell is MINGW64 with auto-link rewriting
  (URLs in pasted output get mangled with `[text](http://text)` form;
  it's display-only).
- **Python**: `py -3.12` launcher is reliable; venv at
  `.venv/Scripts/python.exe` (Windows path).
- **Activate venv first**: a fresh terminal loses the venv. If
  `ruff: command not found`, run `source .venv/Scripts/activate`.
- **Validation gate**: never push without `bash scripts/validate.sh`
  returning 10/10. NOTE: validate.sh item #1 currently only runs
  `ruff check`, not `ruff format --check`. Until that gap is fixed
  (Option A above), CI may still reject what locally looks clean.
  Run `ruff format src tests` before pushing as a safety belt.
- **Branch protection**: `main` cannot be force-pushed. Bug fixes
  that need history rewrites require temporarily relaxing protection.
- **CRLF warnings**: harmless. `.gitattributes` is configured to
  normalize line endings on commit.
- **One-off scripts**: any apply_*.sh helpers should NOT be committed
  to the repo. They're tooling debris. After running, `rm` them.
- **Two-test-commit history quirk**: commits b8d522b (test commit)
  + 797e193 (revert) between v0.2.1 and PR #1 are intentional
  artifacts of branch-protection verification. Documented in
  PROJECT_KNOWLEDGE.txt Section 9 ITEM 2. Don't try to clean them up.

## Operational reminders for the operator (Keef)

- Future commits: just `git push` (upstream is set per branch).
- Tag releases: `git tag -a vX.Y.Z -m "..."` then `git push --tags`.
  Phase 1.1 + 1.2 are NOT yet tagged - typically tag at meaningful
  release boundaries. Recommended: tag v0.3.0 once 1.1.5 lands, since
  1.1.5 closes the gate and Phase 1 reaches a coherent intermediate
  state ("designs that earn their quality gate"). Or tag v0.3.0 now
  if you'd rather mark today's work explicitly.
- Watch the PR Checks tab on every push. CI runs three workflows:
  ci.yml, lint.yml, secret-scan.yml.
- The pre-commit hook is local-only - it runs on `git commit`, not
  on push. The CI workflows are the second line of defense.

## Useful URLs

- Repo: https://github.com/Gimpleberry/kAI
- Actions: https://github.com/Gimpleberry/kAI/actions
- Branch rules: https://github.com/Gimpleberry/kAI/settings/rules
- Security: https://github.com/Gimpleberry/kAI/settings/security_analysis
- Phase 1.1 PR (#1): https://github.com/Gimpleberry/kAI/pull/1
- Phase 1.2 PR (#2): https://github.com/Gimpleberry/kAI/pull/2

---

*Update this doc at the end of every significant session. Old content
moves out, new state moves in.*
