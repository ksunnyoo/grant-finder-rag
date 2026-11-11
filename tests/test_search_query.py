import pytest

from grant_finder_rag.retrieval.query_analyzer import search_query


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("바이오 지원사업 알려줘", "바이오 지원사업"),
        ("바이오 지원사업 알려줘요", "바이오 지원사업"),
        ("바이오 지원사업 알려주세요.", "바이오 지원사업"),
        ("환경 지원사업 좀 알려줘?", "환경 지원사업"),
        ("로봇 지원사업 찾아줘", "로봇 지원사업"),
        ("로봇 지원사업 추천해줘", "로봇 지원사업"),
        ("자동차 수리 지원사업 알려줘", "자동차 수리 지원사업"),
    ],
)
def test_짧은_주제_질문은_요청_어미를_뗀다(question, expected):
    assert search_query(question) == expected


@pytest.mark.parametrize(
    "question",
    [
        "서울 예비창업자가 신청할 수 있는 사업 알려줘",  # 긴 문장
        "바이오 지원사업",  # 어미가 없으면 그대로
        "알려줘",  # 어미만 있으면 그대로
        "  ",  # 빈 질문
    ],
)
def test_그_밖의_질문은_바꾸지_않는다(question):
    assert search_query(question) == question.strip()


def test_조건이_있는_질문은_바꾸지_않는다():
    assert search_query("다음 달 마감되는 사업 알려줘", has_conditions=True) == "다음 달 마감되는 사업 알려줘"
    assert search_query("다음 달 마감되는 사업 알려줘") == "다음 달 마감되는 사업"
