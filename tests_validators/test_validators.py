"""Tests for validators.is_valid_email and validators.clamp."""
from validators import is_valid_email, clamp


# --- is_valid_email ---
def test_email_valid():
    assert is_valid_email("user@example.com") is True


def test_email_missing_at():
    assert is_valid_email("user.example.com") is False


def test_email_empty():
    assert is_valid_email("") is False


def test_email_no_tld_dot():
    assert is_valid_email("user@localhost") is False


def test_email_domain_starting_dot():
    assert is_valid_email("user@.com") is False


# --- clamp ---
def test_clamp_within_range():
    assert clamp(5, 0, 10) == 5


def test_clamp_below_range():
    assert clamp(-3, 0, 10) == 0


def test_clamp_above_range():
    assert clamp(15, 0, 10) == 10


def test_clamp_at_bounds():
    assert clamp(0, 0, 10) == 0
    assert clamp(10, 0, 10) == 10


def test_clamp_inverted_range_raises():
    import pytest
    with pytest.raises(ValueError):
        clamp(5, 10, 0)


# --- is_valid_port ---
def test_port_valid():
    assert is_valid_port(8080) is True


def test_port_boundaries():
    assert is_valid_port(1) is True
    assert is_valid_port(65535) is True


def test_port_zero_invalid():
    assert is_valid_port(0) is False


def test_port_negative_invalid():
    assert is_valid_port(-1) is False


def test_port_too_large_invalid():
    assert is_valid_port(65536) is False


# --- is_valid_port (second pass) ---
def test_port_valid_tcp():
    assert is_valid_port(443) is True


def test_port_string_invalid():
    assert is_valid_port("80") is False  # type: ignore[arg-type]


def test_port_float_invalid():
    assert is_valid_port(80.5) is False  # type: ignore[arg-type]


# --- is_valid_hex_color ---
def test_hex_color_valid():
    assert is_valid_hex_color("#A1B2C3") is True


def test_hex_color_lowercase_valid():
    assert is_valid_hex_color("#a1b2c3") is True


def test_hex_color_missing_hash():
    assert is_valid_hex_color("A1B2C3") is False


def test_hex_color_wrong_length():
    assert is_valid_hex_color("#FFF") is False


def test_hex_color_invalid_chars():
    assert is_valid_hex_color("#GGHHII") is False


def test_port_type_error_message():
    """is_valid_port returns False (not raises) for non-ints."""
    assert is_valid_port(None) is False


# --- hex color edge cases ---
def test_hex_color_all_digits():
    assert is_valid_hex_color("#123456") is True


def test_hex_color_empty_string():
    assert is_valid_hex_color("") is False


def test_clamp_returns_float():
    """clamp returns a numeric type for float inputs."""
    assert isinstance(clamp(1.5, 0, 2), float)
