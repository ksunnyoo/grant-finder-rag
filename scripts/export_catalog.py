"""공개 사이트 '공고 찾기'용 공고 목록 저장 (SDD 8.3.1). 백엔드 서버를 끈 상태에서 실행한다.

만드는 파일
- web/public/demo/catalog.json: 마감 전 공고의 메타데이터와 짧은 발췌(최대 160자). 브라우저에서 조건으로 거른다.
- web/src/catalog_checks.json: 파이썬 필터(build_filter) 결과를 정답으로 둔 검증 사례.
  화면 쪽 거르기(catalog.ts)가 같은 결과를 내는지 vitest가 비교한다.
"""

import json
import os
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from grant_finder_rag.bootstrap import build_retriever
from grant_finder_rag.contracts.models import SearchFilters
from grant_finder_rag.retrieval.query_analyzer import (
    BIZ_AGE_OPTIONS,
    CATEGORIES,
    REGIONS,
    TARGETS,
)
from grant_finder_rag.service import make_snippet
from grant_finder_rag.storage.qdrant_store import REGION_EXPANSION, build_filter

OUT = Path("web/public/demo/catalog.json")
CHECKS = Path("web/src/catalog_checks.json")

# 화면에서 쓰는 조건 이름(camelCase)과 같은 모양으로 적는다.
CASES: list[dict] = [
    {},
    {"region": ["서울"]},
    {"region": ["전남"]},
    {"region": ["광주"]},
    {"bizAge": ["예비창업자"]},
    {"bizAge": ["예비창업자"], "region": ["서울"]},
    {"bizAge": ["3년미만"]},
    {"target": ["1인 창조기업"]},
    {"target": ["대학생"]},
    {"target": ["대학생"], "age": 24},
    {"age": 25},
    {"age": 45},
    {"category": ["사업화"]},
    {"category": ["창업교육"], "region": ["부산"]},
    {"category": ["정책자금", "융자·보증"]},
    {"endFrom": "2026-11-20"},
    {"endFrom": "2026-10-01"},
    {"endTo": "2026-11-30"},
    {"endFrom": "2026-11-15", "endTo": "2026-12-15"},
    {"region": ["서울"], "bizAge": ["예비창업자"], "target": ["일반인"], "age": 30},
]


def to_ranges(ages: list[int]) -> list[list[int]]:
    ranges: list[list[int]] = []
    for a in sorted(set(ages)):
        if ranges and a == ranges[-1][1] + 1:
            ranges[-1][1] = a
        else:
            ranges.append([a, a])
    return ranges


def to_filters(case: dict, as_of: date) -> SearchFilters:
    return SearchFilters(
        as_of_date=as_of,
        region=case.get("region", []),
        target=case.get("target", []),
        biz_age=case.get("bizAge", []),
        age=case.get("age"),
        category=case.get("category", []),
        include_closed=case.get("includeClosed", False),
        end_from=date.fromisoformat(case["endFrom"]) if case.get("endFrom") else None,
        end_to=date.fromisoformat(case["endTo"]) if case.get("endTo") else None,
    )


def scroll_all(store, flt=None) -> list[dict]:
    rows, offset = [], None
    while True:
        points, offset = store.client.scroll(
            store.collection,
            scroll_filter=flt,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        rows += [p.payload for p in points]
        if offset is None:
            return rows


def main() -> None:
    load_dotenv()
    as_of = date.fromisoformat(os.getenv("AS_OF_DATE") or "2026-11-06")
    _, store = build_retriever(with_reranker=False)
    try:
        # 공개 사이트에는 마감 전 공고만 담는다. 조건이 없을 때의 기본 필터(마감 전)와 같다.
        payloads = scroll_all(store, build_filter(to_filters({}, as_of)))
        items = [
            {
                "id": p["notice_id"],
                "title": p["title"],
                "agency": p.get("agency"),
                "category": p.get("category"),
                "region": p.get("region"),
                "target": p.get("target") or [],
                "bizAge": p.get("biz_age") or [],
                "ages": to_ranges(p.get("ages") or []),
                "startDate": p.get("start_date"),
                "endDate": p.get("end_date"),
                "url": p.get("url"),
                "snippet": make_snippet(p.get("text", ""), 160),
            }
            for p in payloads
        ]
        items.sort(key=lambda i: i["id"])
        checks = []
        for case in CASES:
            flt = build_filter(to_filters(case, as_of))
            ids = sorted(p["notice_id"] for p in scroll_all(store, flt))
            checks.append({"filter": case, "expectedIds": ids})
            print(f"{json.dumps(case, ensure_ascii=False):<90} -> {len(ids)}건")
    finally:
        store.close()

    catalog = {
        "asOfDate": str(as_of),
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "meta": {
            "asOfDate": str(as_of),
            "regions": list(REGIONS),
            "targets": list(TARGETS),
            "categories": list(CATEGORIES),
            "bizAges": list(BIZ_AGE_OPTIONS),
        },
        "regionExpansion": REGION_EXPANSION,
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    CHECKS.write_text(
        json.dumps({"asOfDate": str(as_of), "cases": checks}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"저장: {OUT} ({len(items)}건, {OUT.stat().st_size // 1024}KB), {CHECKS}")


if __name__ == "__main__":
    main()
