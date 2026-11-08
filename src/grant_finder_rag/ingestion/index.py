"""검색 문서를 Qdrant에 색인한다 (CLI 전용, SDD 4.3~4.4절)."""
import json
import os
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from grant_finder_rag.contracts.models import Notice
from grant_finder_rag.embedding.bm25_sparse import Bm25SparseEncoder
from grant_finder_rag.embedding.ollama_embedder import OllamaEmbedder
from grant_finder_rag.storage.qdrant_store import QdrantStore

BATCH = 64


def select_for_index(notices: list[Notice], from_date: date) -> list[Notice]:
    """접수 시작일(없으면 마감일)이 from_date 이후인 공고만 고른다. 둘 다 없으면 제외."""
    selected = []
    for n in notices:
        reference = n.start_date or n.end_date
        if reference is not None and reference >= from_date:
            selected.append(n)
    return selected


def _date_int(value: date | None) -> int | None:
    return int(value.strftime("%Y%m%d")) if value else None


def to_payload(n: Notice, text: str) -> dict:
    ages = sorted({age for lo, hi in n.age_ranges for age in range(lo, hi + 1)})
    return {
        "notice_id": n.id,
        "title": n.title,
        "category": n.category,
        "region": n.region,
        "target": n.target,
        "biz_age": n.biz_age,
        "ages": ages,
        "start_date": n.start_date.isoformat() if n.start_date else None,
        "end_date": n.end_date.isoformat() if n.end_date else None,
        "start_date_int": _date_int(n.start_date),
        "end_date_int": _date_int(n.end_date),
        "agency": n.agency,
        "url": n.url,
        "linked_business": n.linked_business,
        "text": text,
    }


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    load_dotenv()
    from_date = date.fromisoformat(os.getenv("INDEX_FROM_DATE", "2025-01-01"))
    notices = [Notice(**row) for row in _read_jsonl(Path("data/clean/notices_linked.jsonl"))]
    text_by_id = {d["notice_id"]: d["text"] for d in _read_jsonl(Path("data/clean/search_docs.jsonl"))}

    selected = select_for_index(notices, from_date)
    texts = [text_by_id[n.id] for n in selected]
    print(f"색인 기준일: {from_date} / 대상 {len(selected)}건 (전체 {len(notices)}건)")

    started = time.time()
    sparse_encoder = Bm25SparseEncoder()
    sparse_vectors = sparse_encoder.fit_transform(texts)
    sparse_encoder.save(Path("data/index/bm25.json"))
    print(f"BM25 단어 사전 {len(sparse_encoder.vocab)}개 생성 ({time.time() - started:.0f}초)")

    embedder = OllamaEmbedder(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_EMBED_MODEL", "bge-m3"),
    )
    store = QdrantStore()
    store.recreate()
    started = time.time()
    for i in range(0, len(selected), BATCH):
        chunk = selected[i : i + BATCH]
        dense = embedder.embed(texts[i : i + BATCH])
        store.upsert(
            ids=[int(n.id) for n in chunk],
            dense=dense,
            sparse=sparse_vectors[i : i + BATCH],
            payloads=[to_payload(n, texts[i + j]) for j, n in enumerate(chunk)],
        )
        done = i + len(chunk)
        print(f"{done}/{len(selected)} ({time.time() - started:.0f}초)", flush=True)

    print(f"색인 완료: Qdrant {store.count()}건, 소요 {time.time() - started:.0f}초")
    store.close()


if __name__ == "__main__":
    main()
