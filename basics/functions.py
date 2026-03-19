"""Function defaults demo."""


def add(a, b=10):
    """Return the sum of a and b."""
    return a + b


def main():
    """Print sample calls."""
    print(add(2, 5))
    print(add(2))


if __name__ == "__main__":
    main()