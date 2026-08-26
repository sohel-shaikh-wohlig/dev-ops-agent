"""Tests for math_utils.ops."""
from math_utils.ops import add, multiply


def test_add_positive():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, -2) == -3


def test_add_zero():
    assert add(0, 0) == 0


def test_add_floats():
    assert add(1.5, 2.5) == 4.0


def test_multiply_positive():
    assert multiply(2, 3) == 6


def test_multiply_negative():
    assert multiply(-2, 3) == -6


def test_multiply_zero():
    assert multiply(5, 0) == 0


def test_multiply_floats():
    assert multiply(1.5, 2.0) == 3.0


def test_types_are_numeric():
    assert isinstance(add(1, 2), (int, float))
    assert isinstance(multiply(1, 2), (int, float))


def test_subtract_positive():
    assert subtract(5, 3) == 2


def test_subtract_negative_result():
    assert subtract(3, 5) == -2


def test_subtract_zero():
    assert subtract(4, 0) == 4


def test_subtract_exists_and_works():
    """Direct coverage for math_utils.ops.subtract."""
    from math_utils.ops import subtract
    assert subtract(10, 4) == 6
