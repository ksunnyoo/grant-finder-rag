"""paraphrase 골든셋 (PRD 4-2). 제목의 핵심 단어를 쓰지 않고 뜻만 같게 바꾼 질문으로 묻는다.
질문은 사람이 공고 내용을 읽고 직접 작성했다. 지역/대상 단어는 필터가 켜지지 않도록 뺐다."""

import json
import re
from pathlib import Path

AS_OF = 20261106
SRC = Path("data/clean/notices_linked.jsonl")
OUT = Path("data/golden/golden_paraphrase.jsonl")

ITEMS = [
    ("179681", "AI 기능을 가진 온라인 서비스를 만들려는 팀에게 아이템 검증부터 시제품 제작, 해외 출시, 투자자 연결까지 함께해 주는 육성 프로그램이 있어?"),
    ("173424", "바이오 분야 회사들이 서로 필요한 기술을 가진 상대를 찾아 공동 연구로 이어 가도록 연결해 주는 서비스가 있어?"),
    ("179258", "대기업이나 관공서에 납품할 거래처를 뚫기 어려운데, 전직 임원 출신 조언자들이 연결해 주는 지원이 있어?"),
    ("179654", "제약·바이오 분야 회사가 맞춤 상담과 투자 연결, 외부 협업 기회를 받을 수 있는 회원제 사업 알려줘"),
    ("179559", "일자리가 없는 젊은 층에게 인공지능 업무 활용법을 전액 무료로 가르치는 교육 알려줘"),
    ("177072", "병원 진료 정보를 활용해 건강관리 서비스를 준비하는 사람에게 무료 교육과 일대일 전문가 상담을 해 주는 곳 알려줘"),
    ("179669", "외국인 대학생을 직원처럼 배치받아 일손 부족을 줄이고 해외 시장 개척에도 활용하려는 회사 모집 사업 알려줘"),
    ("177864", "이용자의 현재 장소를 활용하는 서비스를 운영하는 기업이 받을 수 있는 맞춤 자문 사업 알려줘"),
    ("179565", "만 19세에서 39세 사이 시민이 사업 구상을 겨루는 대회 참가자를 모집하는 지자체 사업 알려줘"),
    ("177563", "수출하는 회사가 환경·사회·지배구조에 관한 거래처 요구에 대응하도록 돕는 상담 사업 알려줘"),
    ("179552", "시장 상인을 이끄는 사람이 인공지능 도구를 실무에 쓰는 법을 익히는 강좌 알려줘"),
    ("179677", "공공과 민간이 가진 시설을 열어 개발한 제품을 현장에서 시험해 보게 하는 과제 모집 알려줘"),
    ("179663", "벤처 지위 심사를 앞두고 사전에 받아 볼 수 있는 무료 점검과 자문 사업 알려줘"),
    ("177922", "마흔 넘어 처음 사업을 시작하는 사람에게 실습 교육과 자금, 이자 부담 경감을 지원하는 사업 알려줘"),
    ("179711", "AI 대화 서비스에서 해외 소비자에게 우리 제품이 추천되도록 준비하는 방법을 알려 주는 무료 설명회 알려줘"),
]


def to_int(v):
    d = re.sub(r"\D", "", str(v or ""))
    return int(d[:8]) if len(d) >= 8 else None


def main():
    rows = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    open_ids = {str(r["id"]) for r in rows if (to_int(r.get("end_date")) or 0) >= AS_OF}
    with OUT.open("w", encoding="utf-8") as f:
        for i, (nid, q) in enumerate(ITEMS, 1):
            assert nid in open_ids, f"{nid} 마감 전 공고가 아닙니다"
            item = {
                "qid": f"P{i:03d}",
                "type": "lookup",
                "subtype": "paraphrase",
                "question": q,
                "gold_ids": [nid],
                "match_count": 1,
                "expect_refuse": False,
                "conditions": {},
            }
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"{len(ITEMS)}문항 저장: {OUT}")


main()
