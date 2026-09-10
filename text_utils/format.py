"""Text formatting utilities.

Fully typed, documented, and tested. Every function is pure with no
side effects, so coverage is straightforward.
"""


def capitalize_words(text: str) -> str:
    """Capitalize the first letter of every word in the text.

    Args:
        text: The input string.

    Returns:
        The text with each word's first letter capitalized.
    """
    return " ".join(word.capitalize() for word in text.split())


def reverse_string(text: str) -> str:
    """Return the reversed input string.

    Args:
        text: The string to reverse.

    Returns:
        The reversed string.
    """
    return text[::-1]


def count_vowels(text: str) -> int:
    """Count the vowels (a, e, i, o, u) in the text, case-insensitive.

    Args:
        text: The string to analyze.

    Returns:
        The number of vowels found.
    """
    return sum(1 for ch in text.lower() if ch in "aeiou")


def is_palindrome(text: str) -> bool:
    """Check whether the text reads the same forwards and backwards.

    Comparison is case-insensitive; non-alphanumeric characters are ignored.

    Args:
        text: The string to check.

    Returns:
        True if the cleaned text is a palindrome.
    """
    cleaned = "".join(ch.lower() for ch in text if ch.isalnum())
    return cleaned == cleaned[::-1]


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length characters, appending a suffix if cut.

    Args:
        text: The string to truncate.
        max_length: Maximum total length of the result (including suffix).
        suffix: Appended to truncated text. Defaults to "...".

    Returns:
        The original text if short enough, else a truncated version.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix
