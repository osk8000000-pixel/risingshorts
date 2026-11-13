"""돈챙김 지원금 수집기: 행정안전부 '대한민국 공공서비스(혜택) 정보'(gov24 v3) 전체를 받아 정리한다.

출력: money/data/services.json (사이트에 쓸 서비스 목록), money/data/meta.json
DATA_GO_KR_KEY 환경변수가 필요하다. 키 값은 출력하지 않는다.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
BASE = "https://api.odcloud.kr/api/gov24/v3"
PER = 1000
PAGE_LIMIT = 1500        # 개별 페이지를 만들 서비스 수(인기순 + 마감 예정은 따로 모두 포함)

TARGETS = [  # (주소, 이름, 찾는 낱말)
    ("youth", "청년", ["청년", "대학생", "사회초년"]),
    ("senior", "어르신", ["어르신", "노인", "65세", "고령"]),
    ("baby", "임신·출산·육아", ["임신", "출산", "임산부", "영유아", "아동", "육아", "보육", "산모", "신생아"]),
    ("job", "취업·구직", ["구직", "취업", "실업", "일자리", "근로자", "직업훈련"]),
    ("house", "주거·전월세", ["주거", "전세", "월세", "임대", "주택", "청약"]),
    ("lowincome", "저소득·생계", ["기초생활", "저소득", "차상위", "긴급복지", "생계"]),
    ("disabled", "장애인", ["장애인", "장애"]),
    ("business", "소상공인·자영업", ["소상공인", "자영업", "창업"]),
    ("farmer", "농어업인", ["농업인", "어업인", "농가", "어가", "귀농", "임업"]),
    ("single", "한부모·다자녀", ["한부모", "다자녀", "조손"]),
]
SIDO = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남",
        "전북", "경북", "경남", "제주"]
SIDO_FULL = {"전남광주통합특별시": "전남·광주", "광주광역시": "전남·광주", "전라남도": "전남·광주", "충청북도": "충북", "충청남도": "충남", "전라북도": "전북", "전북특별자치도": "전북",
             "경상북도": "경북", "경상남도": "경남", "강원특별자치도": "강원", "강원도": "강원", "제주특별자치도": "제주",
             "세종특별자치시": "세종"}


class ApiError(Exception):
    pass


def get(ep, page, key):
    q = urllib.parse.quote(key, safe="")
    url = f"{BASE}/{ep}?page={page}&perPage={PER}&serviceKey={q}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.loads(r.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt == 3:
                raise ApiError(f"{ep} {page}쪽 실패: {str(e).replace(key, '[KEY]')[:200]}")
            time.sleep(5 * (attempt + 1))


def fetch_all(ep, key):
    first = get(ep, 1, key)
    rows = list(first.get("data", []))
    pages = (int(first.get("totalCount") or 0) + PER - 1) // PER
    for p in range(2, pages + 1):
        rows += get(ep, p, key).get("data", [])
        time.sleep(0.3)
    return rows


# ---------- 신청기한 ----------
D1 = re.compile(r"(20\d\d)\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})")


def parse_deadline(s):
    """'2026.05.04~2026.05.20' → (시작, 끝). 연도가 붙은 날짜만 믿는다."""
    ds = []
    for y, m, d in D1.findall(s or ""):
        try:
            ds.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    if not ds:
        return None, None
    return min(ds).isoformat(), max(ds).isoformat()


def clean(s, n=None):
    s = re.sub(r"\r\n?", "\n", (s or "").strip())
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s[:n] if n else s


def region_of(org, org_type):
    if org_type != "시군구":
        return "전국"
    for full, short in SIDO_FULL.items():
        if org.startswith(full):
            return short
    for s in SIDO:
        if org.startswith(s):
            return s
    return "기타"


def targets_of(text):
    return [slug for slug, _, words in TARGETS if any(w in text for w in words)]


def build(key, today):
    lst = fetch_all("serviceList", key)
    det = {d["서비스ID"]: d for d in fetch_all("serviceDetail", key)}
    cond = {c["서비스ID"]: c for c in fetch_all("supportConditions", key)}
    t = today.isoformat()
    items = []
    for r in lst:
        users = (r.get("사용자구분") or "").split("||")
        if users == ["법인/시설/단체"]:
            continue  # 개인이 받을 수 없는 것만 뺀다
        sid = r["서비스ID"]
        d = det.get(sid, {})
        c = cond.get(sid, {})
        dl_raw = clean(r.get("신청기한"), 300)
        start, end = parse_deadline(dl_raw)
        text = " ".join([r.get("서비스명") or "", r.get("지원대상") or "", r.get("서비스목적요약") or ""])
        age_min, age_max = c.get("JA0110"), c.get("JA0111")
        items.append({
            "id": sid,
            "name": clean(r.get("서비스명"), 120),
            "summary": clean(r.get("서비스목적요약"), 400),
            "field": r.get("서비스분야") or "기타",
            "users": users,
            "kind": r.get("지원유형") or "",
            "org": r.get("소관기관명") or "",
            "org_type": r.get("소관기관유형") or "",
            "region": region_of(r.get("소관기관명") or "", r.get("소관기관유형") or ""),
            "dept": r.get("부서명") or "",
            "target": clean(r.get("지원대상"), 1500),
            "criteria": clean(r.get("선정기준"), 1500),
            "benefit": clean(r.get("지원내용"), 1500),
            "how": clean(r.get("신청방법"), 800),
            "deadline": dl_raw,
            "dl_start": start,
            "dl_end": end,
            "open_now": bool(end and start and start <= t <= end) or (bool(end) and not start and t <= end),
            "docs": clean(d.get("구비서류"), 800),
            "contact": clean(d.get("문의처") or r.get("전화문의"), 300),
            "reception": clean(r.get("접수기관") or d.get("접수기관명"), 200),
            "online_url": (d.get("온라인신청사이트URL") or "").strip(),
            "gov_url": r.get("상세조회URL") or "",
            "views": int(r.get("조회수") or 0),
            "updated": (r.get("수정일시") or "")[:8],
            "age_min": age_min, "age_max": age_max,
            "male": c.get("JA0101") == "Y", "female": c.get("JA0102") == "Y",
            "targets": targets_of(text),
        })
    items.sort(key=lambda x: -x["views"])
    for i, it in enumerate(items):
        it["rank"] = i + 1
        # 개별 페이지: 인기 상위 + 지금 접수 중이거나 앞으로 열리는 것
        it["page"] = i < PAGE_LIMIT or it["open_now"] or bool(it["dl_start"] and it["dl_start"] > t)
    return items, len(lst)


def main():
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        print("::error::DATA_GO_KR_KEY 가 없습니다")
        sys.exit(1)
    out = sys.argv[1] if len(sys.argv) > 1 else "money/data"
    os.makedirs(out, exist_ok=True)
    now = datetime.now(KST)
    try:
        items, total = build(key, now.date())
    except ApiError as e:
        print(f"::error::{e}")
        sys.exit(1)
    if len(items) < 1000:
        print(f"::error::서비스가 너무 적음({len(items)}) — 저장하지 않음")
        sys.exit(1)
    with open(os.path.join(out, "services.json"), "w", encoding="utf-8") as f:
        json.dump({"updated": now.isoformat(timespec="minutes"), "items": items}, f, ensure_ascii=False, separators=(",", ":"))
    meta = {"updated": now.isoformat(timespec="minutes"), "api_total": total, "items": len(items),
            "pages": sum(1 for i in items if i["page"]), "open_now": sum(1 for i in items if i["open_now"]),
            "with_dates": sum(1 for i in items if i["dl_end"])}
    with open(os.path.join(out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
