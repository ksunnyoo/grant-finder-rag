"""평가 결과를 화면용 JSON으로 정리 (PRD 4-3). 새로 측정하지 않고 저장된 결과 파일만 읽는다."""

import json
import statistics
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path("data/eval")
OUT = Path("web/public/demo/eval.json")
HARD_FILE = "eval_20261109_150643.json"
RARE_FILE = "eval_20261109_150537.json"
PARA_FILE = "eval_20261109_162852.json"

LIMITS = [
    "세트당 15문항이라 1문항이 6.7%p입니다. 작은 차이는 우연과 구분되지 않습니다.",
    "필터 없는 구성은 마감된 공고까지 검색하므로 필터를 켠 구성과의 차이에는 마감 공고 제외 효과가 섞여 있습니다.",
    "어려운 질문과 희귀 단어 질문은 정확한 단어가 들어가도록 설계되어 단어 일치 방식(sparse)에 유리합니다. 의미는 같고 단어가 다른 질문(의미 같은 질문)은 15문항으로만 시험했고, 그중 비슷한 공고가 여럿인 질문 1개는 정답이 하나로 정해지지 않습니다.",
    "쉬운 질문은 제목을 거의 그대로 써서 필터를 켠 모든 구성이 만점이며 방식 간 차이를 가를 수 없습니다.",
    "범위 밖 질문 대부분은 주제가 완전히 다른 쉬운 질문이라 거절 정확도를 일반화할 수 없습니다.",
    "출처가 붙은 답변 비율은 형식만 확인하며 문장이 근거와 맞는지는 측정하지 않았습니다.",
]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metrics(result):
    return [
        {
            "name": name,
            "hitAtK": m["hit_at_k"],
            "mrr": m["mrr"],
            "precisionFilter": m["precision"]["filter"],
            "precisionDate": m["precision"]["date"],
            "precisionMulti": m["precision"]["multi"],
            "medianMs": round(m["median_ms"]),
        }
        for name, m in result["retrieval"].items()
    ]


def main():
    with_e2e = [f for f in sorted(EVAL_DIR.glob("eval_*.json")) if "e2e" in load(f)]
    e2e_file = with_e2e[-1]
    easy = load(e2e_file)
    print("쉬운 질문과 종단 평가 파일:", e2e_file.name)
    if not any("F-dense" in name for name in easy["retrieval"]):
        print("경고: 이 파일에는 dense/sparse+필터 구성이 없습니다. A 단계의 최신 실행 결과가 맞는지 확인하십시오.")

    sets = [
        {
            "id": "easy",
            "title": "쉬운 질문",
            "description": "제목을 거의 그대로 쓴 질문과 지역·업력·마감 조건 질문입니다.",
            "evaluated": "제목 질문 15개의 Hit@5·MRR, 조건 질문 27개의 정밀도",
            "hasPrecision": True,
            "metrics": metrics(easy),
        },
        {
            "id": "hard",
            "title": "어려운 질문",
            "description": "제목 없이 기관+분야, 본문에만 나오는 단어로 묻는 질문입니다.",
            "evaluated": "15문항",
            "hasPrecision": False,
            "metrics": metrics(load(EVAL_DIR / HARD_FILE)),
        },
        {
            "id": "rare",
            "title": "희귀 단어 질문",
            "description": "한 공고에만 나오는 고유명사·영문 단어 2개로 묻는 질문입니다.",
            "evaluated": "15문항",
            "hasPrecision": False,
            "metrics": metrics(load(EVAL_DIR / RARE_FILE)),
        },
        {
            "id": "paraphrase",
            "title": "의미 같은 질문",
            "description": "제목의 핵심 단어 없이 뜻만 같게 바꿔 쓴 질문입니다. 의미 검색(dense)에 유리한 설계입니다.",
            "evaluated": "15문항",
            "hasPrecision": False,
            "metrics": metrics(load(EVAL_DIR / PARA_FILE)),
        },
    ]

    rows = [r for r in easy["e2e_rows"] if "error" not in r]
    no_answer = [r for r in rows if r["type"] == "no_answer"]
    answerable = [r for r in rows if r["type"] != "no_answer"]
    answered = [r for r in answerable if not r["refused"]]
    lookup = [r for r in rows if r["type"] == "lookup"]
    e2e = {
        "refusalCorrect": sum(r["refused"] for r in no_answer),
        "nNoAnswer": len(no_answer),
        "overRefused": sum(r["refused"] for r in answerable),
        "nAnswerable": len(answerable),
        "cited": sum(r["cited"] for r in answered),
        "nAnswered": len(answered),
        "goldInSources": sum(r["gold_in_sources"] for r in lookup),
        "nLookup": len(lookup),
        "medianMs": round(statistics.median(r["latency_ms"] for r in answered)) if answered else 0,
        "rows": [
            {
                "qid": r["qid"],
                "type": r["type"],
                "question": r["question"],
                "refused": r["refused"],
                "reason": r["reason"],
                "cited": r["cited"],
                "goldInSources": r["gold_in_sources"],
                "latencyMs": r["latency_ms"],
            }
            for r in rows
        ],
    }
    payload = {
        "asOfDate": easy["as_of"],
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "sets": sets,
        "e2e": e2e,
        "limits": LIMITS,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("저장:", OUT)
    print(
        f"거절 {e2e['refusalCorrect']}/{e2e['nNoAnswer']}, 오거절 {e2e['overRefused']}/{e2e['nAnswerable']}, "
        f"출처 {e2e['cited']}/{e2e['nAnswered']}, 정답 포함 {e2e['goldInSources']}/{e2e['nLookup']}"
    )


if __name__ == "__main__":
    main()
