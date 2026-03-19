"""Set operation examples."""


def set_operations(a, b, c):
    """Return common set operation results."""
    return {
        "intersection": a.intersection(b),
        "union": a.union(b),
        "a_minus_b": a.difference(b),
        "b_minus_a": b.difference(a),
        "c_in_a": c.issubset(a),
        "c_in_b": c.issubset(b),
        "a_in_c": a.issubset(c),
    }


def main():
    """Print a set-operations demo."""
    a = {1, 2, 3}
    b = {2, 3, 5}
    c = {2, 3}
    results = set_operations(a, b, c)
    print(f"intersection of a and b is {results['intersection']}")
    print(f"union of a and b is {results['union']}")
    print(f"set difference between a and b is {results['a_minus_b']}")
    print(f"set difference between b and a is {results['b_minus_a']}")
    print(f"is c subset of a {results['c_in_a']}")
    print(f"is c subset of b {results['c_in_b']}")
    print(f"is a subset of c {results['a_in_c']}")


if __name__ == "__main__":
    main()