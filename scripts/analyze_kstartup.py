import json
import re
import datetime
from collections import Counter
from pathlib import Path

ROOT = Path("data/raw/kstartup")


def load(folder):
    items = []
    for f in sorted((ROOT / folder).glob("page_*.json")):
        items += json.loads(f.read_text(encoding="utf-8"))["data"]
    return items


def norm(s):
    return re.sub(r"[^0-9A-Za-z가-힣]", "", s or "")


ann = load("announcements")
biz = load("business")
print("공고", len(ann), "건 / 사업소개", len(biz), "건")

ids = [x["pbanc_sn"] for x in ann]
print("중복 pbanc_sn:", len(ids) - len(set(ids)))

today = datetime.date.today().strftime("%Y%m%d")
years = Counter((x.get("pbanc_rcpt_bgng_dt") or "없음")[:4] for x in ann)
print("접수 시작 연도별:", sorted(years.items()))

open_flag = sum(1 for x in ann if x.get("rcrt_prgs_yn") == "Y")
open_date = sum(1 for x in ann if (x.get("pbanc_rcpt_end_dt") or "") >= today)
recent = sum(1 for x in ann if (x.get("pbanc_rcpt_bgng_dt") or "") >= "20250101")
print("rcrt_prgs_yn=Y:", open_flag, "/ 마감일이 오늘 이후:", open_date)
print("2025-01-01 이후 접수 시작:", recent)

bad = sum(1 for x in ann if len(x.get("pbanc_rcpt_end_dt") or "") != 8)
print("마감일 형식이 8자리가 아닌 건:", bad)

print("지역 상위:", Counter(x.get("supt_regin") for x in ann).most_common(8))
print("분야:", Counter(x.get("supt_biz_clsfc") for x in ann).most_common(12))
print("통합공고 여부:", Counter(x.get("intg_pbanc_yn") for x in ann))

for f in ["pbanc_ctnt", "aply_trgt", "aply_trgt_ctnt", "biz_enyy", "biz_trgt_age", "supt_regin", "pbanc_rcpt_end_dt"]:
    empty = sum(1 for x in ann if not x.get(f))
    print("빈값", f, empty, "(%d%%)" % (empty * 100 // len(ann)))

biz_names = set(norm(x.get("supt_biz_titl_nm")) for x in biz)
integrated = [x for x in ann if x.get("intg_pbanc_yn") == "Y"]
linked = sum(1 for x in integrated if norm(x.get("intg_pbanc_biz_nm")) in biz_names)
print("통합공고", len(integrated), "건 중 사업소개와 이름이 일치:", linked)
