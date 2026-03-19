"""Error handling demonstration."""

import traceback


def divide(a, b):
    """Divide numbers and propagate errors for caller handling."""
    return a / b


def main():
    """Demonstrate catching and logging a division error."""
    try:
        divide(10, 0)
    except ZeroDivisionError:
        traceback.print_exc()
    print("Program proceeds!")


if __name__ == "__main__":
    main()