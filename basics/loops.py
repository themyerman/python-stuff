"""Examples of for/while loop patterns."""


def for_loop_values():
    """Return values from a standard for loop."""
    return list(range(1, 10))


def while_loop_values(limit=10):
    """Return values from a basic while loop."""
    values = []
    i = 0
    while i < limit:
        values.append(i)
        i += 1
    return values


def break_at_five():
    """Return sequence that stops when the counter reaches five."""
    values = []
    i = 0
    while i < 10:
        i += 1
        values.append(i)
        if i == 5:
            break
    return values


def odd_numbers_under_ten():
    """Return odd numbers from 1..9 using continue."""
    values = []
    i = 0
    while i < 10:
        i += 1
        if i % 2 == 0:
            continue
        values.append(i)
    return values


def main():
    """Print all loop demos."""
    print(*for_loop_values(), sep="\n")
    print(*while_loop_values(), sep="\n")
    print(*break_at_five(), sep="\n")
    print(*odd_numbers_under_ten(), sep="\n")


if __name__ == "__main__":
    main()