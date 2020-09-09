from typing import Iterator

letters = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
]


def alphabetic_slot_name_generator(number: int) -> str:
    if number == 0:
        return "A"
    result = []
    while number > 0:
        result.append(letters[int(number % len(letters))])
        number //= len(letters)
    return "".join(result[::-1])


def alphabetic_slot_name_iterator() -> Iterator[str]:
    i = 0
    while True:
        yield alphabetic_slot_name_generator(i)
        i += 1
