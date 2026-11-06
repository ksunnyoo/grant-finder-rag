import os
import httpx
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("KSTARTUP_API_KEY")
BASE = "https://apis.data.go.kr/B552735/kisedKstartupService01"
ANN = "getAnnouncementInformation01"
BIZ = "getBusinessInformation01"

if not KEY:
    raise SystemExit(".env 에 KSTARTUP_API_KEY 가 없습니다")


def call(operation, params):
    params = dict(params)
    params["serviceKey"] = KEY
    params["returnType"] = "json"
    r = httpx.get(BASE + "/" + operation, params=params, timeout=30)
    try:
        return r.json()
    except ValueError:
        print("   JSON이 아닌 응답:", r.text[:200])
        return None


print("1) 전체 공고 수")
d = call(ANN, {"page": 1, "perPage": 1})
if d:
    print("   totalCount =", d.get("totalCount"))

print("2) 모집 중 공고 수 (필터 이름 두 가지 시험)")
for name in ["Rcrt_prgs_yn", "rcrt_prgs_yn"]:
    d = call(ANN, {"page": 1, "perPage": 1, name: "Y"})
    if d:
        print("  ", name, "-> totalCount =", d.get("totalCount"))

print("3) 한 번에 가져올 수 있는 최대 개수")
for n in [100, 500, 1000]:
    d = call(ANN, {"page": 1, "perPage": n})
    if d:
        print("  ", "perPage", n, "-> currentCount =", d.get("currentCount"))

print("4) 모집 중 공고 100건의 본문 길이")
d = call(ANN, {"page": 1, "perPage": 100, "Rcrt_prgs_yn": "Y"})
if d and d.get("data"):
    items = d["data"]
    for field in ["pbanc_ctnt", "aply_trgt_ctnt"]:
        lens = [len(x.get(field) or "") for x in items]
        print("  ", field, "최소", min(lens), "평균", sum(lens) // len(lens), "최대", max(lens), "빈값", lens.count(0))
    print("   응답 필드 이름:", sorted(items[0].keys()))
    print("   날짜 예:", items[0].get("pbanc_rcpt_bgng_dt"), items[0].get("pbanc_rcpt_end_dt"))

print("5) 사업 소개 (통합공고 지원사업 정보)")
d = call(BIZ, {"page": 1, "perPage": 100})
if d and d.get("data"):
    items = d["data"]
    print("   totalCount =", d.get("totalCount"))
    print("   응답 필드 이름:", sorted(items[0].keys()))
    for field in ["biz_supt_ctnt", "supt_biz_intrd_info"]:
        lens = [len(x.get(field) or "") for x in items]
        print("  ", field, "최소", min(lens), "평균", sum(lens) // len(lens), "최대", max(lens))
