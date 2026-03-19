# eye-of-sauron

Security-pattern scanner for PHP/JS-style codebases.

## What is here

- `checker.py`: command-line scanner that walks configured folders and reports matching rule violations.
- `conf.py`: rule definitions grouped by extension and severity (`high`, `medium`, `low`), plus specific-file checks.

## CLI usage

- `python3 checker.py -t /path/to/repo -f application,assets -s high,medium`
- `python3 checker.py -t /path/to/repo --format json --fail-on medium`
- `python3 checker.py -t /path/to/repo --max-findings 50 --exclude-dirs .git,node_modules`

## Notes

- `checker.py` is now a Python 3 scanner with `argparse`, structured findings, and text/JSON output modes.
- Regex rules are compiled once at startup with validation errors surfaced before scan completion.
- Path filtering uses path-part matching instead of substring checks and supports explicit exclude directories.
- Exit codes:
  - `0`: no findings at/above `--fail-on`
  - `1`: findings at/above `--fail-on`
  - `2`: config/runtime errors (invalid regex, unreadable files, etc.)
- Unit tests live in `tests/test_eye_conf.py` and `tests/test_checker.py`.
