"""Tuple examples with a tiny helper function."""


def build_tuple(*args):
    """Return all positional arguments as a tuple."""
    return args


def main():
    """Run tuple slicing demos."""
    tup = build_tuple(1, 2, 3, 4, 5)
    print(tup)
    print(tup[0])
    print(tup[2:4])


if __name__ == "__main__":
    main()
