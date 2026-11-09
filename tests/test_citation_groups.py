from grant_finder_rag.generation.answer import extract_citations


def test_single_citation_still_works():
    text, cited = extract_citations("가 [1] 나 [1] 다 [2]", {"1", "2"})
    assert cited == ["1", "2"]
    assert "[1]" in text


def test_grouped_citation_is_split_and_validated():
    text, cited = extract_citations("가 [1, 2, 9] 나", {"1", "2"})
    assert text == "가 [1][2] 나"
    assert cited == ["1", "2"]


def test_grouped_citation_without_valid_id_is_removed():
    text, cited = extract_citations("가 [8, 9] 나", {"1"})
    assert cited == []
    assert "[" not in text
