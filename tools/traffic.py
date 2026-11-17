"""Cloudflare 존별 최근 방문 통계(읽기 전용). 토큰은 출력하지 않는다."""
import json, os, urllib.request
from datetime import date, timedelta
T = os.environ["CF_TOKEN"]; A = os.environ["CF_ACCOUNT"]
def api(path, data=None):
    req = urllib.request.Request("https://api.cloudflare.com/client/v4" + path, data=json.dumps(data).encode() if data else None,
                                 headers={"Authorization": "Bearer " + T, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: return {"http": e.code, "body": e.read().decode()[:300]}
z = api(f"/zones?account.id={A}&per_page=50")
print("zones:", z.get("http") or [(x["name"], x["id"][:6]) for x in z.get("result", [])])
end = date.today(); start = end - timedelta(days=13)
for x in z.get("result", []) or []:
    q = {"query": """query($z:String!,$s:Date!,$e:Date!){viewer{zones(filter:{zoneTag:$z}){httpRequests1dGroups(limit:20,filter:{date_geq:$s,date_leq:$e},orderBy:[date_ASC]){dimensions{date} uniq{uniques} sum{pageViews requests}}}}}""",
         "variables": {"z": x["id"], "s": start.isoformat(), "e": end.isoformat()}}
    r = api("/graphql", q)
    try:
        rows = r["data"]["viewer"]["zones"][0]["httpRequests1dGroups"]
        print(x["name"], json.dumps([(g["dimensions"]["date"][5:], g["uniq"]["uniques"], g["sum"]["pageViews"]) for g in rows]))
    except Exception:
        print(x["name"], "ERR", json.dumps(r)[:300])
