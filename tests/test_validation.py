import pytest

from core.validation import validate_filename


def test_valid_filename():
    assert validate_filename("test.txt") == "test.txt"


def test_valid_nested_path():
    assert validate_filename("logs/test.txt") == "logs/test.txt"


def test_reject_path_traversal():
    with pytest.raises(ValueError, match="path traversal tidak diizinkan"):
        validate_filename("../secret.txt")


def test_reject_nested_path_traversal():
    with pytest.raises(ValueError, match="path traversal tidak diizinkan"):
        validate_filename("logs/../secret.txt")


def test_reject_absolute_path():
    with pytest.raises(ValueError, match="absolute path tidak diizinkan"):
        validate_filename("/etc/passwd")


def test_reject_empty_filename():
    with pytest.raises(ValueError, match="filename tidak boleh kosong"):
        validate_filename("")


def test_reject_whitespace_filename():
    with pytest.raises(ValueError, match="filename tidak boleh kosong"):
        validate_filename("   ")


def test_reject_non_string_filename():
    with pytest.raises(TypeError, match="filename harus berupa string"):
        validate_filename(None)
