"""String utilities module."""


def slugify(text: str) -> str:
    """Convert arbitrary text into a URL-safe slug.

    Args:
        text: The input string to convert.

    Returns:
        A lowercase, hyphen-separated slug.
    """
    return "-".join(
        word.lower() for word in text.split() if word.isalnum()
    )
