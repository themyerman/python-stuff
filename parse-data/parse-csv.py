"""Filter `us-500.csv` by state and optional name prefix."""

import argparse
import csv
import re
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "us-500.csv"
VALID_STATES = {
    "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA",
    "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME",
    "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM",
    "NV", "NY", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
    "UT", "VA", "VT", "WA", "WI", "WV", "WY",
}


def parse_args():
    """Parse CLI options."""
    parser = argparse.ArgumentParser(
        description="Filter CSV contacts by state and optional name regex prefix."
    )
    parser.add_argument("state", help="Two-letter US state abbreviation")
    parser.add_argument(
        "name",
        nargs="?",
        default="",
        help="Optional case-insensitive regex matched against first/last name",
    )
    parser.add_argument(
        "--file",
        default=str(DATA_FILE),
        help="CSV file path (defaults to bundled us-500.csv)",
    )
    return parser.parse_args()


def filter_rows(csv_path, state, name_pattern=""):
    """Yield matching CSV rows for the selected state and name regex."""
    normalized_state = state.upper()
    if normalized_state not in VALID_STATES:
        raise ValueError("Must enter a valid state abbreviation!")

    pattern = re.compile(name_pattern or ".*", flags=re.IGNORECASE)
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            if len(row) < 7:
                continue
            state_matches = row[6].strip().upper() == normalized_state
            name_matches = pattern.match(row[0]) or pattern.match(row[1])
            if state_matches and name_matches:
                yield row


def main():
    """Run CLI flow and print matching rows."""
    args = parse_args()
    try:
        for row in filter_rows(args.file, args.state, args.name):
            print(", ".join(row))
    except ValueError as exc:
        print(exc)
        raise SystemExit(1)


if __name__ == "__main__":
    main()