"""Tests for text_utils.format — all functions fully covered."""
from text_utils.format import (
    capitalize_words,
    count_vowels,
    is_palindrome,
    reverse_string,
    truncate,
)


# --- capitalize_words ---
def test_capitalize_words_basic():
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_single_word():
    assert capitalize_words("python") == "Python"


def test_capitalize_words_empty():
    assert capitalize_words("") == ""


def test_capitalize_words_multiple_spaces():
    assert capitalize_words("a  b") == "A B"


def test_capitalize_words_already_caps():
    assert capitalize_words("HELLO") == "Hello"


# --- reverse_string ---
def test_reverse_basic():
    assert reverse_string("abc") == "cba"


def test_reverse_empty():
    assert reverse_string("") == ""


def test_reverse_palindrome():
    assert reverse_string("aba") == "aba"


# --- count_vowels ---
def test_count_vowels_mixed_case():
    assert count_vowels("AeIoU") == 5


def test_count_vowels_none():
    assert count_vowels("rhythm") == 0


def test_count_vowels_empty():
    assert count_vowels("") == 0


# --- is_palindrome ---
def test_palindrome_true():
    assert is_palindrome("Racecar") is True


def test_palindrome_with_punctuation():
    assert is_palindrome("A man, a plan, a canal: Panama!") is True


def test_palindrome_false():
    assert is_palindrome("hello") is False


def test_palindrome_empty():
    assert is_palindrome("") is True


# --- truncate ---
def test_truncate_no_cut_needed():
    assert truncate("short", 10) == "short"


def test_truncate_cuts_with_suffix():
    assert truncate("a long sentence here", 10) == "a long..."


def test_truncate_exact_length():
    assert truncate("exactly10!", 10) == "exactly10!"


def test_truncate_custom_suffix():
    assert truncate("abcdef", 4, suffix="~") == "abc~"


def test_truncate_returns_str():
    assert isinstance(truncate("x", 5), str)
