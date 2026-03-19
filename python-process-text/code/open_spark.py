"""Read and preview the Spark course description text."""

from pathlib import Path


def read_preview(file_path, length=200):
    """Return first `length` characters from a text file."""
    return Path(file_path).read_text(encoding="utf-8")[:length]


def main():
    """Print a preview from local source text."""
    source = Path(__file__).resolve().parent / "Spark-Course-Description.txt"
    print("Data read from file :", read_preview(source))


if __name__ == "__main__":
    main()