"""Dictionary examples."""


def build_dictionary_map():
    """Return a dictionary with vowel/consonant groups."""
    return {
        "vowels": "aeiou",
        "consonants": "bcdfghjklmnpqrstvwxyz",
    }


def build_menu():
    """Return a sample menu dictionary."""
    return {"coffee": 10, "tea": 5, "cookie": 2, "chips": 5}


def main():
    """Print dictionary operations demo."""
    dictionary_map = build_dictionary_map()
    print(dictionary_map.get("vowels"))

    menu = build_menu()
    print(menu.get("coffee"))
    print(menu.keys())
    print(menu.values())
    for key, value in menu.items():
        print(key, value)


if __name__ == "__main__":
    main()