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
