import pytest
from chunking import chunk_text

WORDS = [f"w{i}" for i in range(10)]
TEXT = " ".join(WORDS)


def test_basic_windows_with_overlap():
    assert chunk_text(TEXT, size=4, overlap=1) == ["w0 w1 w2 w3", "w3 w4 w5 w6", "w6 w7 w8 w9"]


def test_last_window_contains_final_word_without_redundant_tail():
    chunks = chunk_text(TEXT, size=4, overlap=2)
    assert chunks[-1].split()[-1] == "w9"
    assert chunks == ["w0 w1 w2 w3", "w2 w3 w4 w5", "w4 w5 w6 w7", "w6 w7 w8 w9"]


def test_short_text_is_one_chunk():
    assert chunk_text("a b c", size=10, overlap=3) == ["a b c"]


def test_empty_text():
    assert chunk_text("", size=5, overlap=1) == []


def test_no_overlap():
    assert chunk_text(TEXT, size=5, overlap=0) == ["w0 w1 w2 w3 w4", "w5 w6 w7 w8 w9"]


@pytest.mark.parametrize("size,overlap", [(0, 0), (5, -1), (5, 5), (5, 7)])
def test_invalid_arguments(size, overlap):
    with pytest.raises(ValueError):
        chunk_text(TEXT, size=size, overlap=overlap)
