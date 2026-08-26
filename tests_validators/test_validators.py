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
