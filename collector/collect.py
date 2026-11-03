"""라이징쇼츠 수집기. 매시간 한 번 실행합니다.

하는 일:
1. (하루 2회) 카테고리×지역별로 최근 7일 쇼츠를 검색해 추적 목록에 추가
2. (매시간) 추적 중인 쇼츠의 조회수를 다시 읽어 기록
3. (12시간마다) 채널 구독자 수 갱신
4. 떡상 점수를 계산해 site/data/*.json 으로 저장

사용: python collector/collect.py --state state/state.json.gz --out site/data [--force-discover]
"""

import argparse
import gzip
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
from youtube import QuotaExceeded, YouTube  # noqa: E402

PACIFIC = ZoneInfo("America/Los_Angeles")  # 유튜브 할당량은 태평양 시간 자정에 초기화


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def hour_of(dt):
    """스냅샷 시각은 '1970년부터 몇 시간째'를 소수 둘째 자리까지 저장합니다.
    (예약 실행이 정시보다 늦어도 실제 경과 시간으로 속도를 계산하기 위함)"""
    return round(dt.timestamp() / 3600, 2)


def duration_seconds(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return None
    days, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return days * 86400 + h * 3600 + mi * 60 + s


def load_state(path):
    if path and os.path.exists(path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    return {"videos": {}, "channels": {}, "rejected": {}, "quota": {}, "log": []}


def save_state(state, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, separators=(",", ":"))


def is_vertical(item):
    p = item.get("player") or {}
    w, h = p.get("embedWidth"), p.get("embedHeight")
    if w and h:
        return int(h) > int(w)
    return None  # 판단 불가


def make_video(item, now):
    sn, st = item["snippet"], item.get("statistics", {})
    th = sn.get("thumbnails", {})
    thumb = (th.get("high") or th.get("medium") or th.get("default") or {}).get("url")
    return {
        "t": sn.get("title", ""),
        "ch": sn.get("channelId"),
        "cn": sn.get("channelTitle", ""),
        "pub": sn.get("publishedAt"),
        "dur": duration_seconds(item.get("contentDetails", {}).get("duration")),
        "th": thumb,
        "tags": (sn.get("tags") or [])[:10],
        "lang": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage"),
        "cats": [],
        "regions": [],
        "first": iso(now),
        # 스냅샷: [시각(1970년부터 몇 시간째), 조회수, 좋아요, 댓글]
        "s": [[hour_of(now), int(st.get("viewCount", 0)), int(st.get("likeCount", 0)), int(st.get("commentCount", 0))]],
    }


def add_snapshot(v, item, now):
    st = item.get("statistics", {})
    snap = [hour_of(now), int(st.get("viewCount", 0)), int(st.get("likeCount", 0)), int(st.get("commentCount", 0))]
    if v["s"] and snap[0] - v["s"][-1][0] < 0.25:  # 15분 안에 다시 돌면 덮어씀
        v["s"][-1] = snap
    else:
        v["s"].append(snap)


def discover(yt, state, now, log):
    after = iso(now - timedelta(days=config.TRACK_DAYS))
    found = {}  # id -> set of (cat, region)
    for cat in config.CATEGORIES:
        for rkey, r in config.REGIONS.items():
            ids = yt.search_shorts(cat[r["query_key"]], r["regionCode"], r["relevanceLanguage"], after)
            for vid in ids:
                found.setdefault(vid, set()).add((cat["slug"], rkey))
    new_ids = [v for v in found if v not in state["videos"] and v not in state["rejected"]]
    kept = rejected = 0
    for item in yt.videos(new_ids, full=True):
        vid = item["id"]
        dur = duration_seconds(item.get("contentDetails", {}).get("duration"))
        vert = is_vertical(item)
        ok = dur is not None and dur <= config.MAX_SHORT_SECONDS and (vert is True or (vert is None and dur <= 60))
        if not ok:
            state["rejected"][vid] = iso(now)
            rejected += 1
            continue
        state["videos"][vid] = make_video(item, now)
        kept += 1
    # 카테고리·지역 태그는 이미 추적 중인 영상에도 덧붙임
    for vid, tags in found.items():
        v = state["videos"].get(vid)
        if not v:
            continue
        for c, r in tags:
            if c not in v["cats"]:
                v["cats"].append(c)
            if r not in v["regions"]:
                v["regions"].append(r)
    log.append(f"discover: 후보 {len(found)}개, 새 쇼츠 {kept}개, 쇼츠 아님 {rejected}개")
    return set(new_ids)


def prune(state, now):
    cutoff = now - timedelta(days=config.TRACK_DAYS)
    gone = [vid for vid, v in state["videos"].items() if v.get("pub") and parse_iso(v["pub"]) < cutoff]
    for vid in gone:
        del state["videos"][vid]
    rej_cut = now - timedelta(days=config.TRACK_DAYS + 1)
    for vid in [k for k, t in state["rejected"].items() if parse_iso(t) < rej_cut]:
        del state["rejected"][vid]
    used = {v["ch"] for v in state["videos"].values()}
    for ch in [c for c in state["channels"] if c not in used]:
        del state["channels"][ch]
    return len(gone)


def refresh_views(yt, state, now, skip):
    ids = [vid for vid in state["videos"] if vid not in skip]
    seen = set()
    for item in yt.videos(ids, full=False):
        seen.add(item["id"])
        add_snapshot(state["videos"][item["id"]], item, now)
    # 삭제·비공개된 영상은 응답에 없음 → 추적 중단
    for vid in ids:
        if vid not in seen:
            del state["videos"][vid]
    return len(seen)


def refresh_channels(yt, state, now):
    stale = now - timedelta(hours=config.CHANNEL_REFRESH_HOURS)
    need = sorted({v["ch"] for v in state["videos"].values()
                   if v["ch"] not in state["channels"] or parse_iso(state["channels"][v["ch"]]["t"]) < stale})
    for item in yt.channels(need):
        st = item.get("statistics", {})
        subs = None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0))
        state["channels"][item["id"]] = {"subs": subs, "t": iso(now)}
    return len(need)


def metrics(v, subs, now):
    snaps = v["s"]
    views = snaps[-1][1]
    age_h = max((now - parse_iso(v["pub"])).total_seconds() / 3600, 1)
    # 최근 창 안의 가장 오래된 스냅샷과 비교
    win_start = hour_of(now) - config.VELOCITY_WINDOW_HOURS
    base = snaps[0]
    for s in snaps:  # 창 시작 시각 이전의 가장 최근 스냅샷 (없으면 첫 스냅샷)
        if s[0] <= win_start:
            base = s
    if base is not snaps[-1]:
        hours = max(snaps[-1][0] - base[0], 0.5)
        velocity = (views - base[1]) / hours
        measured = True
    else:
        velocity = views / age_h  # 기록이 짧을 땐 업로드 이후 평균 속도
        measured = False
    ratio = views / subs if subs else None
    boost = 1 + math.log10(1 + ratio) if ratio is not None else 1
    score = max(velocity, 0) * min(boost, 4)
    return {"views": views, "vph": round(velocity), "measured": measured,
            "ratio": round(ratio, 2) if ratio is not None else None,
            "subs": subs, "age_h": round(age_h, 1), "score": round(score, 1)}


HANGUL = re.compile(r"[\uac00-\ud7a3]")


def is_korean(v):
    """국내 순위에는 한국어 쇼츠만: 음성 언어가 한국어이거나 제목·태그에 한글이 있으면 통과."""
    if (v.get("lang") or "").lower().startswith("ko"):
        return True
    return bool(HANGUL.search(v.get("t", "") + " ".join(v.get("tags") or [])))


LATIN = re.compile(r"[A-Za-z]")
LETTER = re.compile(r"[^\W\d_]")
NON_EN_AUDIO = ("hi", "bn", "ur", "ar", "ta", "te", "mr", "ko", "ja", "zh", "th", "ru")


def is_global(v):
    """해외 순위에는 영어권 쇼츠만: 제목 글자의 85% 이상이 로마자이고, 음성 언어가 비영어권이 아님."""
    if (v.get("lang") or "").lower().startswith(NON_EN_AUDIO):
        return False
    letters = LETTER.findall(v.get("t", ""))
    if not letters:
        return False
    return len(LATIN.findall(v.get("t", ""))) / len(letters) >= 0.85


def in_region(v, rkey):
    if rkey not in v["regions"]:
        return False
    return is_korean(v) if rkey == "kr" else is_global(v)


def card(vid, v, m, with_series):
    c = {"id": vid, "t": v["t"], "cn": v["cn"], "ch": v["ch"], "th": v["th"], "pub": v["pub"],
         "dur": v["dur"], "cats": v["cats"], **m}
    if with_series:
        c["series"] = [[s[0], s[1]] for s in v["s"]]
    return c


def build_outputs(state, now, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for vid, v in state["videos"].items():
        subs = (state["channels"].get(v["ch"]) or {}).get("subs")
        rows.append((vid, v, metrics(v, subs, now)))

    def top(filter_fn, key, n, series=True):
        sel = [r for r in rows if filter_fn(r[1])]
        sel.sort(key=lambda r: (r[2][key] if r[2][key] is not None else -1), reverse=True)
        return [card(vid, v, m, series) for vid, v, m in sel[:n]]

    written = 0
    for rkey in config.REGIONS:
        home = {"updated": iso(now), "region": rkey,
                "items": top(lambda v, rk=rkey: in_region(v, rk), "score", config.TOP_N_HOME)}
        _write(os.path.join(out_dir, f"home-{rkey}.json"), home)
        written += 1
        for cat in config.CATEGORIES:
            f = lambda v, rk=rkey, cs=cat["slug"]: in_region(v, rk) and cs in v["cats"]
            payload = {"updated": iso(now), "region": rkey, "category": cat["slug"], "name": cat["name"],
                       "by_score": top(f, "score", config.TOP_N_CATEGORY),
                       "by_ratio": top(f, "ratio", config.TOP_N_CATEGORY, series=False),
                       "by_views": top(f, "views", config.TOP_N_CATEGORY, series=False)}
            _write(os.path.join(out_dir, f"cat-{cat['slug']}-{rkey}.json"), payload)
            written += 1
        # 키워드 검색용 가벼운 목록
        idx = [{"id": vid, "t": v["t"], "cn": v["cn"], "tags": v["tags"], "cats": v["cats"],
                "th": v["th"], "views": m["views"], "vph": m["vph"], "ratio": m["ratio"], "score": m["score"]}
               for vid, v, m in rows if in_region(v, rkey)]
        idx.sort(key=lambda x: x["score"], reverse=True)
        _write(os.path.join(out_dir, f"search-{rkey}.json"), {"updated": iso(now), "items": idx})
        written += 1
    _write(os.path.join(out_dir, "meta.json"), {
        "updated": iso(now),
        "categories": [{"slug": c["slug"], "name": c["name"]} for c in config.CATEGORIES],
        "tracked": len(state["videos"]),
        "quota": state["quota"],
    })
    return written + 1


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def run(key, state_path, out_dir, force_discover=False, now=None, fetch=None):
    now = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    state = load_state(state_path)
    day = now.astimezone(PACIFIC).strftime("%Y-%m-%d")
    quota = state["quota"].get(day) or {"searches": 0, "units": 0}
    state["quota"] = {day: quota}  # 오늘 것만 보관
    yt = YouTube(key, quota, config.SEARCH_BUDGET_PER_DAY, config.UNIT_BUDGET_PER_DAY, fetch=fetch)
    log = []
    try:
        skip = set()
        if "last_discover" not in state and state["videos"]:
            # 이전 버전에서 넘어온 상태: 직전 검색을 마지막 기록 시각으로 간주 (할당량 중복 사용 방지)
            state["last_discover"] = iso(now)
        last = state.get("last_discover")
        due = last is None or (now - parse_iso(last)) >= timedelta(hours=config.DISCOVER_EVERY_HOURS)
        if force_discover or due or not state["videos"]:
            skip = discover(yt, state, now, log)
            state["last_discover"] = iso(now)
        gone = prune(state, now)
        n = refresh_views(yt, state, now, skip)
        c = refresh_channels(yt, state, now)
        log.append(f"refresh: 조회수 {n}개, 채널 {c}개, 기간 지나 제외 {gone}개")
    except QuotaExceeded as e:
        log.append(f"할당량 안전선 도달, 다음 실행에 이어서 진행: {e}")
    files = build_outputs(state, now, out_dir)
    log.append(f"할당량 사용(태평양 {day}): 검색 {quota['searches']}회, 단위 {quota['units']}")
    state["log"] = ([f"{iso(now)} " + " | ".join(log)] + state.get("log", []))[:72]
    save_state(state, state_path)
    print("\n".join(log) + f"\n출력 파일 {files}개, 추적 중 {len(state['videos'])}개")
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="state/state.json.gz")
    ap.add_argument("--out", default="site/data")
    ap.add_argument("--force-discover", action="store_true")
    a = ap.parse_args()
    key = (os.environ.get("YT_API_KEY") or "").strip()
    if not key:
        # ::error:: 줄은 GitHub 실행 요약(Annotations)에 그대로 표시됨
        print("::error::YT_API_KEY 비밀값이 비어 있습니다. 저장소 Settings > Secrets and variables > Actions에 등록하세요.")
        sys.exit(1)
    try:
        run(key, a.state, a.out, a.force_discover)
    except Exception as e:  # 원인을 요약 화면에 남기고 실패 처리
        msg = str(e).replace(key, "[KEY]").replace("\n", " ")[:600]
        print(f"::error::수집 실패 - {type(e).__name__}: {msg}")
        raise


if __name__ == "__main__":
    main()
