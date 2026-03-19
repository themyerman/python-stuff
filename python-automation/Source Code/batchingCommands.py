"""Generate demo files and move each into its own folder."""

import random
import sys
from pathlib import Path


def generate_files(num_files, name_prefix, base_dir="."):
    """Create numbered text files with random content and move them to folders."""
    base = Path(base_dir)
    for i in range(num_files):
        folder = base / f"example{i}"
        folder.mkdir(exist_ok=True)
        file_name = f"{name_prefix}{i}.txt"
        file_path = base / file_name
        file_path.write_text(str(random.randint(1, 10)), encoding="utf-8")
        file_path.rename(folder / file_name)


def main():
    """CLI entrypoint."""
    if len(sys.argv) < 3:
        print("Usage: python batchingCommands.py <num_files> <name_prefix>")
        raise SystemExit(1)
    num_files = int(sys.argv[1])
    name_prefix = str(sys.argv[2])
    generate_files(num_files, name_prefix)


if __name__ == "__main__":
    main()

