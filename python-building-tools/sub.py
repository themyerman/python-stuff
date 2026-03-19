"""Run a subprocess command and show output."""

import subprocess


def run_ls_var():
    """Run `ls -a /var` and return stdout/stderr."""
    result = subprocess.run(
        ["ls", "-a", "/var"],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout, result.stderr


if __name__ == "__main__":
    stdout, stderr = run_ls_var()
    print(f"stdout: {stdout}")
    print(f"stderr: {stderr}")