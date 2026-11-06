# AGENTS.md

Working agreement for coding agents in this repository.

## Before changing code

- Read `dirlint/core.py` first; rules are functions on `Scanner`, each with one test in `tests/test_core.py`.
- Tests: `python -m unittest discover -s tests -v`
- Self-check after any rule/config change: `dirlint scan --root . --config dirlint.json` must exit 0.
- Keep the scanner read-only. Never add code that deletes, moves, or writes inside the scanned tree.

## Before committing

- Add or update a test for every rule change.
- Update `README.md` and `DESIGN.md` when a rule or the UI changes.

## Before pushing / releasing

- The repository's `pre-push` hook runs leakguard; install it from your local leakguard checkout if missing.
- Versioning: patch for fixes, minor for new rules; tag `vX.Y.Z` and create a GitHub release.
