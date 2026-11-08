"""정제 전후 품질 리포트 (PRD 1-4)."""
import json
import random
import re
from pathlib import Path

from grant_finder_rag.ingestion.build_notices import load_raw_notices
from grant_finder_rag.ingestion.normalize import parse_date

PHONE = re.compile(r"0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
SKIP_FIELDS = {"prch_cnpl_no", "biz_prch_dprt_nm"}


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _values(row: dict) -> list[str]:
    return [str(v) for k, v in row.items() if k not in SKIP_FIELDS and v is not None]


def _has(row: dict, pattern: re.Pattern) -> bool:
    return any(pattern.search(v) for v in _values(row))


def _has_text(row: dict, text: str) -> bool:
    return any(text in v for v in _values(row))


def main() -> None:
    raw = load_raw_notices(Path("data/raw/kstartup/announcements"))
    clean = read_jsonl(Path("data/clean/notices_linked.jsonl"))
    docs = read_jsonl(Path("data/clean/search_docs.jsonl"))

    table = [
        ("공고 건수", len(raw), len(clean)),
        (
            "접수 시작일 없음/형식 이상",
            sum(1 for r in raw if parse_date(r.get("pbanc_rcpt_bgng_dt")) is None),
            sum(1 for c in clean if c["start_date"] is None),
        ),
        (
            "마감일 없음/형식 이상",
            sum(1 for r in raw if parse_date(r.get("pbanc_rcpt_end_dt")) is None),
            sum(1 for c in clean if c["end_date"] is None),
        ),
        (
            "본문 빈값",
            sum(1 for r in raw if not str(r.get("pbanc_ctnt") or "").strip()),
            sum(1 for c in clean if c["content"] is None),
        ),
        (
            "HTML 엔티티(&amp;) 포함",
            sum(1 for r in raw if _has_text(r, "&amp;")),
            sum(1 for c in clean if _has_text(c, "&amp;")),
        ),
        (
            "전화번호 형태 포함",
            sum(1 for r in raw if _has(r, PHONE)),
            sum(1 for c in clean if _has(c, PHONE)),
        ),
        (
            "이메일 형태 포함",
            sum(1 for r in raw if _has(r, EMAIL)),
            sum(1 for c in clean if _has(c, EMAIL)),
        ),
        (
            "분야에 'ㆍ' 포함",
            sum(1 for r in raw if "ㆍ" in str(r.get("supt_biz_clsfc") or "")),
            sum(1 for c in clean if "ㆍ" in (c["category"] or "")),
        ),
    ]
    print(f"{'항목':<28}{'정제 전':>10}{'정제 후':>10}")
    for name, before, after in table:
        print(f"{name:<28}{before:>10}{after:>10}")

    extra = {
        "신청 대상 내용 없음": sum(1 for c in clean if c["target_text"] is None),
        "제외 대상 내용 없음": sum(1 for c in clean if c["exclusion_text"] is None),
        "신청 방법 없음": sum(1 for c in clean if c["apply_method"] is None),
        "연령 범위 없음": sum(1 for c in clean if not c["age_ranges"]),
        "사업 소개 연결": sum(1 for c in clean if c["linked_business"]),
        "검색 문서 수": len(docs),
        "100자 미만 문서": sum(1 for d in docs if len(d["text"]) < 100),
    }
    print("\n[정제 후 추가 지표]")
    for name, value in extra.items():
        print(f"{name}: {value}")

    report = {name: {"before": b, "after": a} for name, b, a in table}
    report["extra"] = extra
    Path("data/clean/quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    raw_by_id = {str(r["pbanc_sn"]): r for r in raw}
    clean_by_id = {c["id"]: c for c in clean}
    random.seed(7)
    print("\n[샘플 10건: 원본 -> 정제]")
    for notice_id in random.sample(sorted(clean_by_id), 10):
        r, c = raw_by_id[notice_id], clean_by_id[notice_id]
        print(f"- {notice_id} {c['title'][:30]}")
        print(f"  접수 {r.get('pbanc_rcpt_bgng_dt')}~{r.get('pbanc_rcpt_end_dt')}"
              f" -> {c['start_date']}~{c['end_date']}")
        print(f"  분야 {r.get('supt_biz_clsfc')} -> {c['category']}")
        print(f"  지역 {r.get('supt_regin')} -> {c['region']}")


if __name__ == "__main__":
    main()
