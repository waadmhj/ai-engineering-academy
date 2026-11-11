from text import STOPWORDS, normalize, tokenize


def test_normalize_whitespace_and_case():
    assert normalize("  Hello\t\nWORLD  ") == "hello world"


def test_normalize_unicode_nfkc():
    # full-width letters and the "ﬁ" ligature normalise to ASCII
    assert normalize("ＡＩ ﬁne") == "ai fine"


def test_tokenize_drops_punctuation_and_stopwords():
    assert tokenize("What is the dot-product, really?") == ["dot", "product", "really"]


def test_tokenize_keeps_internal_apostrophes_and_numbers():
    assert tokenize("Bayes' theorem isn't hard; GPT-4 has 2 parts") == ["bayes", "theorem", "isn't", "hard", "gpt", "4", "2", "parts"]


def test_tokenize_empty():
    assert tokenize("   ") == []


def test_stopwords_are_removed():
    assert not set(tokenize("the a an of to and")) & STOPWORDS
