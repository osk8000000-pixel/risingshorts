"""돈챙김 API 탐색 2: 필드 목록, 신청기한 표본, 분야 분포."""
import collections, json, os, urllib.parse, urllib.request

dk = os.environ.get("DATA_GO_KR_KEY", "").strip()
q = urllib.parse.quote(dk, safe="")
def get(ep, page, per):
    url = f"https://api.odcloud.kr/api/gov24/v3/{ep}?page={page}&perPage={per}&serviceKey={q}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())
d = get("serviceList", 1, 1000)
print("total", d.get("totalCount"))
rows = d["data"]
print("LIST KEYS", list(rows[0].keys()))
c = collections.Counter(r.get("서비스분야") for r in rows); print("분야", c.most_common())
c = collections.Counter(r.get("사용자구분") for r in rows); print("사용자", c.most_common())
c = collections.Counter(r.get("지원유형") for r in rows); print("지원유형", c.most_common(12))
c = collections.Counter(r.get("소관기관유형") for r in rows); print("기관유형", c.most_common())
dl = collections.Counter(r.get("신청기한") for r in rows); print("신청기한 top", dl.most_common(25))
rows.sort(key=lambda r: -(r.get("조회수") or 0))
for r in rows[:15]:
    print("TOP", r.get("조회수"), r.get("서비스명"), "|", r.get("소관기관명"), "|", (r.get("신청기한") or "")[:40])
dd = get("serviceDetail", 1, 1)["data"][0]; print("DETAIL KEYS", list(dd.keys()))
try:
    with urllib.request.urlopen("https://infuser.odcloud.kr/oas/docs?namespace=15113968/v1", timeout=30) as r:
        s = r.read().decode()
    import re
    i = s.find("JA0101"); print("DOC", s[i-200:i+6000].replace(dk, "")[:6000])
except Exception as e:
    print("doc fail", e)
