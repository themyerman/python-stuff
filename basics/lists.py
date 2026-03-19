"""List-comprehension and loop examples."""


def get_squares(max_value=20):
    """Return squares from 0 to max_value - 1."""
    return [x * x for x in range(max_value)]


def get_squares_loop(max_value=20):
    """Same as get_squares, but written with an explicit loop."""
    new_list = []
    for x in range(max_value):
        new_list.append(x * x)
    return new_list


def main():
    """Print sample square lists."""
    print(get_squares_loop(50))
    print(get_squares(50))


if __name__ == "__main__":
    main()