# parse-data

CSV parsing utilities and example data.

## What is here

- `parse-csv.py`: CLI utility that filters rows by US state and optional name regex.
- `data/us-500.csv`: sample dataset used by the parser.

## Notes

- The parser now uses structured argument parsing and explicit validation for state abbreviations.
- Core filtering logic is testable via `filter_rows(...)`.
- Unit tests live in `tests/test_parse_data.py`.
