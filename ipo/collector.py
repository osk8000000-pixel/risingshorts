"""공모주데이 수집기: 금융감독원 DART 오픈API로 신규상장 공모주 일정을 모은다.

- list.json  : 최근 발행공시(증권신고서·투자설명서·발행실적보고서·철회신고서) 목록
- estkRs.json: 증권신고서(지분증권) 주요정보 — 청약기일, 납입기일, 공모가, 주식 수, 인수인(주관사)

출력: ipo/data/ipos.json (종목 목록), ipo/data/meta.json
DART_API_KEY 환경변수가 필요하다. 키 값은 절대 출력하지 않는다.
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
BASE = "https://opendart.fss.or.kr/api"
LOOKBACK_DAYS = 150          # 이 기간 안에 공시가 있는 종목만 추적
KEEP_DAYS_AFTER_REFUND = 120  # 환불일 뒤 이만큼 지나면 목록에서 뺌(상장 후 성적표는 따로 보관)
DART_VIEW = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="


class DartError(Exception):
    pass


def get(path, key, **q):
    q["crtfc_key"] = key
    url = f"{BASE}/{path}?{urllib.parse.urlencode(q)}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                d = json.loads(r.read().decode())
            st = d.get("status")
            if st in ("000", "013"):   # 013 = 조회된 데이터 없음
                return d
            if st == "020":            # 요청 제한 초과
                raise DartError("DART 요청 한도 초과")
            raise DartError(f"DART {path} 오류 {st}: {d.get('message')}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                raise DartError(f"DART 연결 실패: {e}")
            time.sleep(3)


# ---------- 파싱 ----------
DATE_RE = re.compile(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일")


def parse_dates(s):
    """'2026년 12월 07일 ~ 2026년 12월 08일' -> ['2026-12-07', '2026-12-08']"""
    return [f"{y}-{int(m):02d}-{int(d):02d}" for y, m, d in DATE_RE.findall(s or "")]


def num(s):
    s = re.sub(r"[^\d.]", "", s or "")
    if not s:
        return None
    return float(s) if "." in s else int(s)


def kind_of(report_nm):
    r = report_nm
    if "철회" in r:
        return "withdraw"
    if "증권발행실적보고서" in r:
        return "result"
    if "투자설명서" in r:
        return "prospectus"
    if "증권신고서(지분증권)" in r:
        if "발행조건확정" in r:
            return "final"
        if "정정" in r or "기재정정" in r:
            return "amend"
        return "filing"
    return None


# ---------- 수집 ----------
def fetch_filings(key, today):
    """최근 발행공시 전부 (여러 쪽)."""
    start = (today - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    out, page = [], 1
    while True:
        d = get("list.json", key, bgn_de=start, end_de=end, pblntf_ty="C", page_no=page, page_count=100)
        out += d.get("list", [])
        if page >= int(d.get("total_page") or 1):
            break
        page += 1
        time.sleep(0.2)
    return out


def latest_group(groups, title):
    rows = groups.get(title) or []
    if not rows:
        return []
    last = max(r.get("rcept_no", "") for r in rows)
    return [r for r in rows if r.get("rcept_no") == last]


def build(key, today=None):
    today = today or datetime.now(KST).date()
    filings = fetch_filings(key, today)
    by_corp = {}
    for f in filings:
        k = kind_of(f.get("report_nm", ""))
        if not k:
            continue
        # 비상장 회사(E)의 공모만 = 신규상장 공모주. 상장사 유상증자는 뺀다.
        if f.get("corp_cls") != "E":
            continue
        by_corp.setdefault(f["corp_code"], {"name": f["corp_name"], "filings": []})["filings"].append(
            {"kind": k, "title": f["report_nm"].strip(), "date": f["rcept_dt"], "rcept_no": f["rcept_no"]})

    items, errors = [], []
    bgn = (today - timedelta(days=LOOKBACK_DAYS + 60)).strftime("%Y%m%d")
    for corp_code, c in by_corp.items():
        fl = sorted(c["filings"], key=lambda x: x["rcept_no"])
        kinds = {x["kind"] for x in fl}
        if not kinds & {"filing", "amend", "final", "prospectus"}:
            continue
        try:
            d = get("estkRs.json", key, corp_code=corp_code, bgn_de=bgn, end_de=today.strftime("%Y%m%d"))
        except DartError as e:
            errors.append(f"{c['name']}: {e}")
            continue
        time.sleep(0.15)
        groups = {g.get("title"): g.get("list", []) for g in d.get("group", [])}
        gen = latest_group(groups, "일반사항")
        kinds_rows = latest_group(groups, "증권의종류")
        under = latest_group(groups, "인수인정보")
        if not gen:
            continue
        g0 = gen[0]
        sub = parse_dates(g0.get("sbd"))
        pay = parse_dates(g0.get("pymd"))
        common = next((r for r in kinds_rows if "보통" in (r.get("stksen") or "")), kinds_rows[0] if kinds_rows else {})
        uw, seen = [], set()
        for r in under:
            n = (r.get("actnmn") or "").strip()
            if n and n not in seen and n != "-":
                seen.add(n)
                uw.append({"name": n, "role": (r.get("actsen") or "").strip(), "shares": num(r.get("udtcnt"))})
        last_filing = max((x for x in fl if x["kind"] in ("filing", "amend", "final")), key=lambda x: x["rcept_no"], default=None)
        withdrawn = any(x["kind"] == "withdraw" and (not last_filing or x["rcept_no"] > last_filing["rcept_no"]) for x in fl)
        price_confirmed = "final" in kinds or "prospectus" in kinds
        item = {
            "corp_code": corp_code,
            "name": c["name"],
            "spac": "기업인수목적" in c["name"] or "스팩" in c["name"],
            "sub_start": sub[0] if sub else None,
            "sub_end": sub[-1] if sub else None,
            "refund": pay[0] if pay else None,
            "price": num(common.get("slprc")),
            "price_confirmed": price_confirmed,
            "shares": num(common.get("stkcnt")),
            "amount": num(common.get("slta")),
            "face": num(common.get("fv")),
            "method": (common.get("slmthn") or "").strip(),
            "underwriters": uw,
            "withdrawn": withdrawn,
            "has_result": "result" in kinds,
            "filings": [{"kind": x["kind"], "title": x["title"], "date": x["date"],
                         "url": DART_VIEW + x["rcept_no"]} for x in fl],
            "source_rcept": g0.get("rcept_no"),
        }
        item["status"] = status_of(item, today)
        if item["refund"] and date.fromisoformat(item["refund"]) < today - timedelta(days=KEEP_DAYS_AFTER_REFUND):
            continue
        items.append(item)
    items.sort(key=lambda x: (x["sub_start"] or "9999", x["name"]))
    return items, errors, len(filings)


def status_of(it, today):
    if it["withdrawn"]:
        return "withdrawn"
    s, e, r = it["sub_start"], it["sub_end"], it["refund"]
    if not s:
        return "unknown"
    t = today.isoformat()
    if t < s:
        return "upcoming"
    if s <= t <= (e or s):
        return "subscribing"
    if r and t <= r:
        return "refund"
    return "done"


def main():
    key = os.environ.get("DART_API_KEY", "").strip()
    if not key:
        print("::error::DART_API_KEY 가 없습니다")
        sys.exit(1)
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "ipo/data"
    os.makedirs(out_dir, exist_ok=True)
    now = datetime.now(KST)
    try:
        items, errors, nfil = build(key, now.date())
    except DartError as e:
        print(f"::error::{str(e).replace(key, '[KEY]')}")
        sys.exit(1)
    with open(os.path.join(out_dir, "ipos.json"), "w", encoding="utf-8") as f:
        json.dump({"updated": now.isoformat(timespec="minutes"), "items": items}, f, ensure_ascii=False, indent=1)
    meta = {"updated": now.isoformat(timespec="minutes"), "filings_seen": nfil, "items": len(items),
            "by_status": {s: sum(1 for i in items if i["status"] == s) for s in
                          ("upcoming", "subscribing", "refund", "done", "withdrawn", "unknown")},
            "errors": errors[:20]}
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    for e in errors[:5]:
        print(f"::warning::{e}")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
