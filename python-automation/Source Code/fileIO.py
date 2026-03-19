"""Split an input file into pass/fail output files."""

from pathlib import Path


def split_results_file(
    input_file="inputFile.txt",
    pass_output="PassFile.txt",
    fail_output="FailFile.txt",
):
    """Write lines with third token == 'P' to pass file; others to fail file."""
    input_path = Path(input_file)
    pass_path = Path(pass_output)
    fail_path = Path(fail_output)

    with (
        input_path.open("r", encoding="utf-8") as source,
        pass_path.open("w", encoding="utf-8") as pass_file,
        fail_path.open("w", encoding="utf-8") as fail_file,
    ):
        for line in source:
            tokens = line.split()
            if len(tokens) >= 3 and tokens[2] == "P":
                pass_file.write(line)
            else:
                fail_file.write(line)


if __name__ == "__main__":
    split_results_file()
