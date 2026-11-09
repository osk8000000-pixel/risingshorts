"""DART 오픈API 시험: 최근 증권신고서(지분증권) 목록과 한 종목의 주요정보를 받아 형태를 확인한다.
키 값은 출력하지 않는다."""
import json, os, urllib.parse, urllib.request
from datetime import date, timedelta

KEY = os.environ["DART_API_KEY"].strip()
BASE = "https://opendart.fss.or.kr/api"

def get(path, **q):
    q["crtfc_key"] = KEY
    with urllib.request.urlopen(f"{BASE}/{path}?{urllib.parse.urlencode(q)}", timeout=30) as r:
        return json.loads(r.read().decode())

end = date.today(); start = end - timedelta(days=60)
lst = get("list.json", bgn_de=start.strftime("%Y%m%d"), end_de=end.strftime("%Y%m%d"),
          pblntf_detail_ty="C001", page_count=100)
out = {"list_status": lst.get("status"), "list_message": lst.get("message"), "total": lst.get("total_count")}
items = lst.get("list", [])
out["sample_titles"] = [(i["corp_name"], i["report_nm"], i["rcept_dt"], i.get("corp_cls")) for i in items[:25]]
# 지분증권 주요정보: 신규상장 공모로 보이는 것 하나
pick = next((i for i in items if "증권신고서(지분증권)" in i["report_nm"]), None)
if pick:
    d = get("estkRs.json", corp_code=pick["corp_code"], bgn_de=start.strftime("%Y%m%d"), end_de=end.strftime("%Y%m%d"))
    out["estk_corp"] = pick["corp_name"]
    out["estk_status"] = d.get("status"); out["estk_message"] = d.get("message")
    out["estk_groups"] = {g.get("title"): g.get("list", [])[:2] for g in d.get("group", [])}
print(json.dumps(out, ensure_ascii=False, indent=1)[:60000])
with open(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"), "a") as f:
    f.write("```json\n" + json.dumps(out, ensure_ascii=False, indent=1)[:60000] + "\n```\n")
