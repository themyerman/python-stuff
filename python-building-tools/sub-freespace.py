"""Check free disk space for root filesystem."""

import subprocess


def get_free_space():
    """Return free space text from `df -h /` output."""
    result = subprocess.run(
        ["df", "-h", "/"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("An error occurred retrieving free space.")
    lines = result.stdout.strip().splitlines()
    if len(lines) < 2:
        raise RuntimeError("Unexpected output from df command.")
    # Header is first line; second line has data where 4th column is available space.
    return lines[1].split()[3]


if __name__ == "__main__":
    try:
        print("The free space is:", get_free_space())
    except RuntimeError as exc:
        print(exc)