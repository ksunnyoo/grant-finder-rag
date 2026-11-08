from datetime import date

from grant_finder_rag.ingestion.normalize import (
    clean_text,
    mask_contacts,
    normalize_category,
    parse_age_ranges,
    parse_date,
    split_tokens,
)


def test_parse_date_yyyymmdd():
    assert parse_date("20261105") == date(2026, 11, 5)


def test_parse_date_with_time():
    assert parse_date("2012-11-29 00:00:00") == date(2012, 11, 29)


def test_parse_date_missing_or_bad():
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("abc") is None
    assert parse_date("00000000") is None


def test_clean_text_unescape():
    assert clean_text("기술개발(R&amp;D)") == "기술개발(R&D)"


def test_clean_text_newlines_and_empty():
    assert clean_text("a\r\nb\n\n\n\nc ") == "a\nb\n\nc"
    assert clean_text("   ") is None
    assert clean_text(None) is None


def test_mask_contacts():
    assert mask_contacts("문의 02-123-4567, a@b.com") == "문의 [전화번호], [이메일]"


def test_normalize_category():
    assert normalize_category("시설ㆍ공간ㆍ보육") == "시설·공간·보육"
    assert normalize_category("기술개발(R&amp;D)") == "기술개발(R&D)"


def test_split_tokens():
    assert split_tokens("예비창업자,1년미만") == ["예비창업자", "1년미만"]
    assert split_tokens(None) == []


def test_parse_age_ranges():
    value = "만 20세 미만,만 20세 이상 ~ 만 39세 이하,만 40세 이상"
    assert parse_age_ranges(value) == [(0, 19), (20, 39), (40, 120)]
    assert parse_age_ranges("만 20세 미만,만 40세 이상") == [(0, 19), (40, 120)]
    assert parse_age_ranges(None) == []


def test_clean_text_double_escaped():
    assert clean_text("A&amp;amp;B") == "A&B"


def test_clean_text_many_levels_escaped():
    assert clean_text("a?x=1&amp;amp;amp;amp;amp;b=2") == "a?x=1&b=2"
