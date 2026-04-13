import pytest

from src.utils.shortcode import ALPHABET, DEFAULT_LENGTH, generate_short_code


class TestGenerateShortCode:
    def test_default_length_is_seven(self):
        assert len(generate_short_code()) == DEFAULT_LENGTH == 7

    def test_custom_length_respected(self):
        assert len(generate_short_code(length=12)) == 12

    def test_only_uses_base62_alphabet(self):
        alphabet_set = set(ALPHABET)
        for _ in range(1_000):
            code = generate_short_code()
            assert set(code) <= alphabet_set

    def test_alphabet_has_62_unique_characters(self):
        assert len(ALPHABET) == 62
        assert len(set(ALPHABET)) == 62

    def test_codes_are_non_deterministic(self):
        samples = {generate_short_code() for _ in range(100)}
        assert len(samples) == 100

    def test_zero_length_rejected(self):
        with pytest.raises(ValueError):
            generate_short_code(length=0)

    def test_negative_length_rejected(self):
        with pytest.raises(ValueError):
            generate_short_code(length=-1)
