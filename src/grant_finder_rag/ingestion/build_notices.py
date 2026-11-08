"""원본 공고(data/raw)를 정제된 Notice로 바꿔 JSONL로 저장한다 (SDD 4.1절)."""
import json
from pathlib import Path

from grant_finder_rag.contracts.models import Notice
from grant_finder_rag.ingestion.normalize import (
    clean_text,
    mask_contacts,
    normalize_category,
    parse_age_ranges,
    parse_date,
    split_tokens,
)

APPLY_METHOD_FIELDS = [
    ("aply_mthd_onli_rcpt_istc", "온라인 접수"),
    ("aply_mthd_eml_rcpt_istc", "이메일 접수"),
    ("aply_mthd_vst_rcpt_istc", "방문 접수"),
    ("aply_mthd_pssr_rcpt_istc", "우편 접수"),
    ("aply_mthd_fax_rcpt_istc", "팩스 접수"),
    ("aply_mthd_etc_istc", "기타"),
]


def _find_items(obj):
    """응답 JSON 안에서 공고 목록(리스트)을 찾는다."""
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "biz_pbanc_nm" in obj[0]:
        return obj
    if isinstance(obj, dict):
        for value in obj.values():
            found = _find_items(value)
            if found:
                return found
    return None


def load_raw_notices(raw_dir: Path) -> list[dict]:
    items = []
    for path in sorted(raw_dir.glob("page_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        items.extend(_find_items(data) or [])
    return items


def _safe_text(value) -> str | None:
    """정제 후 전화번호·이메일을 가린다."""
    text = clean_text(value)
    return mask_contacts(text) if text else None


def _apply_method(raw: dict) -> str | None:
    lines = []
    for field, label in APPLY_METHOD_FIELDS:
        text = _safe_text(raw.get(field))
        if text:
            lines.append(f"{label}: {text}")
    return "\n".join(lines) or None


def to_notice(raw: dict) -> Notice:
    return Notice(
        id=str(raw["pbanc_sn"]),
        title=clean_text(raw.get("biz_pbanc_nm")) or "",
        category=normalize_category(raw.get("supt_biz_clsfc")),
        region=clean_text(raw.get("supt_regin")),
        target=split_tokens(raw.get("aply_trgt")),
        biz_age=split_tokens(raw.get("biz_enyy")),
        age_ranges=parse_age_ranges(raw.get("biz_trgt_age")),
        start_date=parse_date(raw.get("pbanc_rcpt_bgng_dt")),
        end_date=parse_date(raw.get("pbanc_rcpt_end_dt")),
        agency=clean_text(raw.get("pbanc_ntrp_nm")) or clean_text(raw.get("sprv_inst")),
        content=_safe_text(raw.get("pbanc_ctnt")),
        target_text=_safe_text(raw.get("aply_trgt_ctnt")),
        exclusion_text=_safe_text(raw.get("aply_excl_trgt_ctnt")),
        apply_method=_apply_method(raw),
        url=clean_text(raw.get("detl_pg_url")),
        is_integrated=raw.get("intg_pbanc_yn") == "Y",
        integrated_name=clean_text(raw.get("intg_pbanc_biz_nm")),
    )


def build_notices(raw_dir: Path, out_path: Path) -> dict:
    raw_items = load_raw_notices(raw_dir)
    seen = set()
    notices = []
    for raw in raw_items:
        notice = to_notice(raw)
        if notice.id in seen:
            continue
        seen.add(notice.id)
        notices.append(notice)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for notice in notices:
            f.write(json.dumps(notice.model_dump(mode="json"), ensure_ascii=False) + "\n")

    return {
        "원본 건수": len(raw_items),
        "저장 건수": len(notices),
        "중복 제거": len(raw_items) - len(notices),
        "제목 없음": sum(1 for n in notices if not n.title),
        "접수 시작일 없음": sum(1 for n in notices if n.start_date is None),
        "마감일 없음": sum(1 for n in notices if n.end_date is None),
        "본문 없음": sum(1 for n in notices if n.content is None),
        "신청 대상 내용 없음": sum(1 for n in notices if n.target_text is None),
        "연령 범위 없음": sum(1 for n in notices if not n.age_ranges),
        "신청 방법 없음": sum(1 for n in notices if n.apply_method is None),
    }


def main() -> None:
    stats = build_notices(
        Path("data/raw/kstartup/announcements"), Path("data/clean/notices.jsonl")
    )
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
