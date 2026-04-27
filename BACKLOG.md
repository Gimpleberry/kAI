# Backlog

Deferred work, future enhancements, and ideas worth remembering.
Distinct from `CHANGELOG.md` (what happened) and `DECISIONS.md` (why we chose what we chose).

When picking something up from here:
1. Move the entry to an `[Unreleased]` section in CHANGELOG when work begins
2. If it requires an architectural choice, write a new ADR in DECISIONS first
3. Move to CHANGELOG proper once shipped

---

## Claude Project setup

**Status:** Deferred — to be set up by user when convenient
**Priority:** Medium
**Why deferred:** User will set up the Claude Project independently and move
the design conversation into it for reference.

### Suggested when ready

Create a `.claudeproject/` directory at the repo root containing:

- **`PROJECT_OVERVIEW.md`** — orientation doc Claude reads at the start of every
  conversation. What the project is, the engineering tenets, the architecture,
  and where things live. Prevents the "re-establish context" tax on every chat.
- **`CURRENT_STATE.md`** — living "what's done, what's in progress, what's next"
  document. Updated at the end of each working session.
- **`upload_manifest.txt`** — explicit list of files to upload to the Claude Project
  as project knowledge.
- **`sync.sh`** — script that copies manifest files to a staging directory you
  can drag into the Project all at once.

### Initial upload candidates for the Claude Project

Files that orient future conversations fast:
- `README.md`
- `DECISIONS.md`
- `CHANGELOG.md`
- `BACKLOG.md`
- `config/taxonomy.yaml`
- `pyproject.toml`

Plus a personal `PROJECT_OVERVIEW.md` written by the user explaining what
they want to learn from running this system (the "why this matters to me"
context that documentation alone doesn't capture).

### Files explicitly NOT to upload

- Anything under `data/` (personal preference data — see ADR-003)
- `.env`
- Generated profile exports
- Session JSON dumps
- Anything matching the pre-commit hook's forbidden patterns

---

## Adaptive question selection

**Status:** Deferred to v2
**Priority:** Low
**Why deferred:** Fixed design generation is sufficient for v1. Adaptive
selection (re-estimate after each response, pick most-informative next task)
adds significant complexity and is most valuable when minimizing respondent
burden — not a primary concern for a single motivated user.

Pre-stubbed at `src/kai/elicitation/adaptive.py`.

---

## Hierarchical Bayes estimation

**Status:** Deferred indefinitely
**Priority:** None for current scope
**Why deferred:** See ADR-002. HB's value is multi-respondent pooling, which
doesn't apply to single-user setup. Bootstrap CIs on MNL deliver ~90% of HB's
value at ~1% of the implementation complexity.

Would only revisit if scope expanded to multi-respondent.

---

## CLI command suite

**Status:** Partially scaffolded
**Priority:** Medium — implement alongside relevant features

Planned commands beyond the existing `validate-taxonomy`:
- `kai init` — set up DB and config
- `kai estimate <session_id>` — re-run estimation on existing session
- `kai export <session_id>` — export profile in chosen format
- `kai diff <id1> <id2>` — compare two profiles
- `kai diagnose <session_id>` — run all diagnostics
- `kai backup` — snapshot the DB to `data/backups/` with rotation

---

## Notebooks for analysis

**Status:** Directory exists, no notebooks yet
**Priority:** Low — create as needed

Planned notebooks for `analysis/`:
- `01_design_exploration.ipynb` — visualize CBC design balance, D-efficiency
- `02_model_validation.ipynb` — synthetic respondent validation, recovery testing
- `03_profile_evolution.ipynb` — track how preferences change as you add sessions

Notebook outputs are gitignored — clear before committing.
