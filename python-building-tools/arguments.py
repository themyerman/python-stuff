"""Show how command-line arguments are exposed in Python."""

import sys


def describe_arguments(arguments):
    """Print a safe summary for argv-like input."""
    print("Items in the list 'arguments'")
    print("-----------------------------")
    print(f"arguments: \t\t\t{arguments}")
    print(f"arguments[0] script name:\t{arguments[0] if arguments else ''}")
    print(f"arguments[1] first arg:\t\t{arguments[1] if len(arguments) > 1 else '<missing>'}")
    print(f"arguments[2] second arg:\t{arguments[2] if len(arguments) > 2 else '<missing>'}")
    print(f"arguments[1:] all but [0]:\t{arguments[1:]}")


if __name__ == "__main__":
    describe_arguments(sys.argv)