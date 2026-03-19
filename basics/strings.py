"""Common string operation examples."""


def demo_string_ops():
    """Print examples of common string methods and slicing."""
    text = "When Johnny comes marching home hurrah hurrah"
    print(text.upper())
    print(text.lower())
    print(text.startswith("When"))
    print(text.replace("Johnny", "Tommy"))
    print(len(text))
    print(text[0])
    print(text[12:])
    print(text[5:9])
    print(list(text))
    print(":".join(list(text)))
    print(text.split("comes"))
    print(text.zfill(60))

    print("There are %d letters in the alphabet" % 26)
    letters = 26
    print(f"There are {letters} letters in the alphabet")
    planets = 8
    planet_name = "mars"
    print(f"There are {planets} planets. We are going to {planet_name}.")


if __name__ == "__main__":
    demo_string_ops()
