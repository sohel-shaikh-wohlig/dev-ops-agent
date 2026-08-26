"""Tests for string_utils.slugify."""
from fresh_flow_dir.string_utils import slugify


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_strips_punctuation_words():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_empty():
    assert slugify("") == ""


def test_slugify_multiple_spaces():
    assert slugify("a  b   c") == "a-b-c"


def test_slugify_returns_str():
    assert isinstance(slugify("x"), str)
