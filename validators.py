"""Input validation helpers — fully typed, documented, and tested."""


def is_valid_email(email: str) -> bool:
    """Check whether an email has a basic valid shape (local@domain.tld).

    This is a shape check, not full RFC 5322 validation.

    Args:
        email: The email string to check.

    Returns:
        True if the email has local@domain.tld shape.
    """
    if not email or "@" not in email:
        return False
    local, _, domain = email.rpartition("@")
    return bool(local) and "." in domain and not domain.startswith(".")


def clamp(value: float, low: float, high: float) -> float:
    """Restrict a value to the inclusive range [low, high].

    Args:
        value: The value to clamp.
        low:   Lower bound.
        high:  Upper bound.

    Returns:
        value if within bounds, otherwise the nearest bound.
    """
    if high < low:
        raise ValueError("high must be >= low")
    return max(low, min(value, high))


def is_valid_port(value: int) -> bool:
    """Check whether a value is a valid TCP/UDP port (1-65535).

    Args:
        value: The port number to validate.

    Returns:
        True if the value is an int in [1, 65535].
    """
    return isinstance(value, int) and 1 <= value <= 65535


def is_valid_hex_color(value: str) -> bool:
    """Check whether a string is a 6-digit hex color like #A1B2C3.

    Args:
        value: The string to check.

    Returns:
        True if the value matches the #RRGGBB pattern.
    """
    if not value or len(value) != 7 or value[0] != "#":
        return False
    return all(c in "0123456789abcdefABCDEF" for c in value[1:])


def is_even(value: int) -> bool:
    """Check whether an integer is even.

    Args:
        value: The integer to check.

    Returns:
        True if value is divisible by 2.
    """
    return value % 2 == 0
