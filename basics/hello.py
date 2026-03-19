"""Python version demo."""

import platform


def get_python_version():
    """Return interpreter version as a string."""
    return platform.python_version()


def main():
    """Print Python version information."""
    print(f"this is python version {get_python_version()}")


if __name__ == "__main__":
    main()

