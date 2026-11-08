from datetime import date

from grant_finder_rag.ingestion.build_notices import to_notice


def test_to_notice_full():
    raw = {
        "pbanc_sn": 123,
        "biz_pbanc_nm": "⌈서울⌋ 창업 &amp; 지원",
        "supt_biz_clsfc": "시설ㆍ공간ㆍ보육",
        "supt_regin": "서울",
        "aply_trgt": "일반인,대학생",
        "biz_enyy": "예비창업자,1년미만",
        "biz_trgt_age": "만 20세 이상 ~ 만 39세 이하",
        "pbanc_rcpt_bgng_dt": "20261101",
        "pbanc_rcpt_end_dt": "20261130",
        "pbanc_ctnt": "문의 02-123-4567",
        "aply_mthd_onli_rcpt_istc": "K-Startup 접수",
        "intg_pbanc_yn": "Y",
        "intg_pbanc_biz_nm": "통합사업",
        "pbanc_ntrp_nm": "기관",
        "detl_pg_url": "https://example.com",
    }
    n = to_notice(raw)
    assert n.id == "123"
    assert n.title == "⌈서울⌋ 창업 & 지원"
    assert n.category == "시설·공간·보육"
    assert n.target == ["일반인", "대학생"]
    assert n.biz_age == ["예비창업자", "1년미만"]
    assert n.age_ranges == [(20, 39)]
    assert n.end_date == date(2026, 11, 30)
    assert n.content == "문의 [전화번호]"
    assert n.apply_method == "[온라인] K-Startup 접수"
    assert n.is_integrated is True


def test_to_notice_missing_fields():
    n = to_notice({"pbanc_sn": 1, "biz_pbanc_nm": "a"})
    assert n.start_date is None
    assert n.end_date is None
    assert n.target == []
    assert n.age_ranges == []
    assert n.content is None
    assert n.apply_method is None
    assert n.is_integrated is False
