import pytest

from guardrailbench.transforms import TRANSFORMS, apply_span, long_padding

MARKER = "pwned-marker 42 sat"


def test_keys():
    assert set(TRANSFORMS) == {"base64", "rot13", "leet", "homoglyph", "zero_width", "unicode_tags"}


@pytest.mark.parametrize("name", sorted(TRANSFORMS))
def test_transform_keeps_marker_substring(name):
    text = "before text. " + MARKER + " after text."
    new_text, new_span = apply_span(text, MARKER, name)
    assert new_span in new_text
    assert MARKER not in new_text
    assert new_text == text.replace(MARKER, new_span, 1)


def test_apply_span_missing_raises():
    with pytest.raises(ValueError):
        apply_span("hello", "nope", "rot13")


def test_fixed_tables():
    assert TRANSFORMS["leet"]("aeiost") == "431057"
    assert TRANSFORMS["zero_width"]("abc") == "a​b​c"
    assert TRANSFORMS["unicode_tags"]("A é") == "\U000e0041\U000e0020é"
    assert TRANSFORMS["homoglyph"]("aeopcxi") == "аеорсхі"


def test_long_padding_keeps_marker_and_is_benign_filler():
    text = "hello " + MARKER
    a = long_padding(text, MARKER, 1)
    assert MARKER in a and a.endswith(text)
    assert len(a) >= 24_000
    assert a == long_padding(text, MARKER, 1)
    assert a != long_padding(text, MARKER, 2)
    low = a[: -len(text)].lower()
    for w in ("ignore", "instruction", "assistant", "system", "pwned", "marker"):
        assert w not in low
    with pytest.raises(ValueError):
        long_padding("x", MARKER, 1)
