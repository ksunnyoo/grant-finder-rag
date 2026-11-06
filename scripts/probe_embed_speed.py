import json
import time
from pathlib import Path

import httpx

path = Path("data/raw/kstartup/announcements/page_001.json")
raw = json.loads(path.read_text(encoding="utf-8"))


def find_items(obj):
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "biz_pbanc_nm" in obj[0]:
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            found = find_items(v)
            if found:
                return found
    return None


items = find_items(raw)[:64]
texts = []
for it in items:
    parts = [it.get("biz_pbanc_nm"), it.get("pbanc_ctnt"), it.get("aply_trgt_ctnt")]
    texts.append("\n".join(p for p in parts if p)[:2000])
avg_chars = sum(len(t) for t in texts) / len(texts)
print("문서 수:", len(texts), "평균 글자 수:", round(avg_chars))

start = time.time()
for i in range(0, len(texts), 16):
    r = httpx.post(
        "http://localhost:11434/api/embed",
        json={"model": "bge-m3", "input": texts[i : i + 16]},
        timeout=300,
    )
    r.raise_for_status()
    dim = len(r.json()["embeddings"][0])
elapsed = time.time() - start
per_doc = elapsed / len(texts)
print("차원:", dim)
print("총 시간(초):", round(elapsed, 1), "문서당(초):", round(per_doc, 3))
print("7,369건 예상(분):", round(per_doc * 7369 / 60, 1))
print("3,530건 예상(분):", round(per_doc * 3530 / 60, 1))
