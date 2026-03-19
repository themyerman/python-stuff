"""Planet validation example."""


class CosmicException(Exception):
    """Raised when a planet name is not recognized."""


VALID_PLANETS = {
    "mercury",
    "venus",
    "earth",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
}


def hello_planet(planet_name):
    """Return a greeting for a valid planet name."""
    normalized = planet_name.lower()
    if normalized not in VALID_PLANETS:
        raise CosmicException(f"Invalid Planet - {normalized}")
    return f"Hello {normalized}"


def main():
    """Run a small demo with safe error handling."""
    for name in ("Earth", "Venus", "Barzooom"):
        try:
            print(hello_planet(name))
        except CosmicException as exc:
            print(exc)


if __name__ == "__main__":
    main()