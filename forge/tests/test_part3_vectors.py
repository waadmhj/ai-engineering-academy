import math

import pytest
from vectors import cosine_similarity, dot, norm, top_k


def test_dot():
    assert dot([1, 2, 3], [4, 5, 6]) == 32


def test_dot_length_mismatch():
    with pytest.raises(ValueError):
        dot([1, 2], [1, 2, 3])


def test_norm():
    assert norm([3, 4]) == pytest.approx(5.0)


def test_cosine_properties():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)
    # scale invariance
    assert cosine_similarity([1, 2, 3], [10, 20, 30]) == pytest.approx(1.0)
    assert cosine_similarity([1, 1], [1, 0]) == pytest.approx(1 / math.sqrt(2))


def test_cosine_zero_vector():
    assert cosine_similarity([0, 0], [1, 2]) == 0.0


def test_top_k_order_and_ties():
    vecs = [[0, 1], [1, 0], [1, 1], [2, 0]]
    assert top_k([1, 0], vecs, 3) == [1, 3, 2]
    assert top_k([1, 0], vecs, 0) == []
