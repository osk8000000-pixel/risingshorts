"""돈챙김 API 탐색: 응답 구조만 출력(키는 출력하지 않음)."""
import json, os, urllib.parse, urllib.request

def get(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return getattr(e, "code", 0), str(getattr(e, "read", lambda: b"")() or e)[:400]

def show(name, url, key):
    st, body = get(url)
    body = body.replace(key, "[KEY]") if key else body
    print(f"=== {name}: HTTP {st}")
    try:
        d = json.loads(body)
        print(json.dumps(d, ensure_ascii=False)[:2500])
    except Exception:
        print(body[:800])

fk = os.environ.get("FINLIFE_API_KEY", "").strip()
for kind in ("depositProductsSearch", "savingProductsSearch"):
    show(kind, f"https://finlife.fss.or.kr/finlifeapi/{kind}.json?auth={fk}&topFinGrpNo=020000&pageNo=1", fk)

dk = os.environ.get("DATA_GO_KR_KEY", "").strip()
q = urllib.parse.quote(dk, safe="")
show("gov24 serviceList", f"https://api.odcloud.kr/api/gov24/v3/serviceList?page=1&perPage=3&serviceKey={q}", dk)
show("gov24 serviceDetail", f"https://api.odcloud.kr/api/gov24/v3/serviceDetail?page=1&perPage=2&serviceKey={q}", dk)
show("gov24 supportConditions", f"https://api.odcloud.kr/api/gov24/v3/supportConditions?page=1&perPage=1&serviceKey={q}", dk)
