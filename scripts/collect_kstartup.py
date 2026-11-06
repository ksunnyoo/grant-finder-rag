import json
import os
import time
import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("KSTARTUP_API_KEY")
BASE = "https://apis.data.go.kr/B552735/kisedKstartupService01"
OUT = Path("data/raw/kstartup")
PER_PAGE = 1000

if not KEY:
    raise SystemExit(".env 에 KSTARTUP_API_KEY 가 없습니다")


def fetch(operation, page):
    params = {"serviceKey": KEY, "returnType": "json", "page": page, "perPage": PER_PAGE}
    r = httpx.get(BASE + "/" + operation, params=params, timeout=60)
    try:
        return r.json()
    except ValueError:
        return {"raw": r.text[:300]}


def collect(operation, folder):
    out_dir = OUT / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    page = 1
    total = 0
    while True:
        file = out_dir / ("page_%03d.json" % page)
        if file.exists():
            data = json.loads(file.read_text(encoding="utf-8"))
        else:
            data = fetch(operation, page)
            if "data" not in data:
                print("오류 응답:", str(data)[:300])
                return 0
            file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            time.sleep(1)
        total = data["totalCount"]
        print(folder, "page", page, "받은 개수", data["currentCount"], "전체", total)
        if page * PER_PAGE >= total or data["currentCount"] == 0:
            break
        page += 1
    return total


announce_total = collect("getAnnouncementInformation01", "announcements")
business_total = collect("getBusinessInformation01", "business")

manifest = {
    "collected_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "announcements_total": announce_total,
    "business_total": business_total,
}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("완료:", manifest)
