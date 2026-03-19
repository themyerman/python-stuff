# eye

Security-pattern scanner for PHP/JS-style codebases.

## What is here

- `checker.py`: command-line scanner that walks configured folders and reports matching rule violations.
- `conf.py`: rule definitions grouped by extension and severity (`high`, `medium`, `low`), plus specific-file checks.

## Notes

- Fixed option parsing issues in `checker.py` (`--verbose` handling and long-option definitions).
- Kept existing rule behavior intact while adding script-level documentation.
- Unit tests live in `tests/test_eye_conf.py` and validate config structure.
