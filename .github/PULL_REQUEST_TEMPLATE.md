<!--
This template enforces ARCHITECTURE_TENETS Tenet 5.
Fill in every section. Delete sections only if they truly don't apply,
and explain why.
-->

## Summary

<!-- 2-3 sentences: what + why. -->

## Changes

<!-- Bulleted list of files/modules touched. -->

- `path/to/file.py` — what changed and why

## Linked work

<!-- Reference a BACKLOG.md item, ADR, or issue. -->

- Closes #
- Backlog: <name of phase + item>
- ADR: (if this introduces an architectural change)

## Validation checklist (Tenet 5)

<!-- Run `bash scripts/validate.sh` locally. Paste the summary line. -->

- [ ] **1. Lint** — ruff check + format --check clean on every modified file
- [ ] **2. shared.py uniqueness** — no symbol duplicated outside shared.py
- [ ] **3. Encoding sweep** — no non-ASCII in Python source
- [ ] **4. Plugin registry** — every entry has start()/stop()
- [ ] **5. Import chain** — no circular imports
- [ ] **6. Lifecycle** — `main.py --check` passes
- [ ] **7. Docs present** — README/CHANGELOG/DECISIONS/BACKLOG/PROJECT_KNOWLEDGE
- [ ] **8. Config valid** — `kai validate-taxonomy` passes
- [ ] **9. Unit tests** — all green
- [ ] **10. Integration boot** — `main.py --boot-order` works

`scripts/validate.sh` summary:

```
Passed: __ / 10
```

## Documentation updated

- [ ] CHANGELOG.md entry added under appropriate version
- [ ] PROJECT_KNOWLEDGE.txt updated if architecture or folder map changed
- [ ] DECISIONS.md ADR added if this is a non-trivial architectural choice
- [ ] BACKLOG.md updated (phase items moved/completed/added)
- [ ] In-app Help section added/updated if user-facing behavior changed

## Screenshots / log excerpts

<!-- If UI or output changed, paste before/after. Redact any secrets. -->

## Risk + rollback plan

<!--
If this breaks production, how do you undo it?
Examples:
  - "Pure refactor. Revert is safe; no data migration involved."
  - "Adds a new column. Revert requires running migrate_down.sql."
  - "Changes default behavior. Set KAI_LEGACY_MODE=1 to restore."
-->
