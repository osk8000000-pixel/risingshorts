"""가짜 유튜브 API로 수집기를 3일치 돌려 보는 테스트. 실행: python tests/test_collect.py"""

import json
import os
import random
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "collector"))
import collect  # noqa: E402
import config  # noqa: E402

random.seed(7)
START = datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc)


class FakeYouTube:
    """영상 600개짜리 가짜 세계. 일부는 작은 채널의 떡상 영상, 일부는 가로 영상·긴 영상."""

    def __init__(self):
        self.now = START
        self.calls = {"search": 0, "videos": 0, "channels": 0}
        self.videos = {}
        for i in range(600):
            vid = f"v{i:04d}"
            kind = random.random()
            self.videos[vid] = {
                "pub": START - timedelta(hours=random.randint(1, 160)),
                "dur": random.choice([25, 45, 58, 90, 170]) if kind > 0.15 else random.choice([200, 600]),
                "vertical": kind > 0.25,
                "ch": f"c{i % 120:03d}",
                "rate": random.choice([50, 200, 1000]) * (40 if i % 97 == 0 else 1),  # 시간당 조회수
                "deleted_at": START + timedelta(hours=30) if i == 5 else None,
            }
        self.subs = {f"c{j:03d}": random.choice([800, 5000, 80000, 2_000_000]) for j in range(120)}

    def views(self, v):
        hours = max((self.now - v["pub"]).total_seconds() / 3600, 0)
        return int(v["rate"] * hours)

    def __call__(self, endpoint, params):
        self.calls[endpoint] += 1
        assert params["key"] == "TEST"
        if endpoint == "search":
            after = datetime.strptime(params["publishedAfter"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            pool = [k for k, v in self.videos.items() if after < v["pub"] <= self.now and v["dur"] < 240]
            random.shuffle(pool)
            return {"items": [{"id": {"videoId": k}} for k in pool[:50]]}
        if endpoint == "videos":
            items = []
            for vid in params["id"].split(","):
                v = self.videos[vid]
                if v["deleted_at"] and self.now >= v["deleted_at"]:
                    continue
                st = {"viewCount": str(self.views(v)), "likeCount": "10", "commentCount": "2"}
                it = {"id": vid, "statistics": st}
                if "snippet" in params["part"]:
                    it["snippet"] = {"title": f"테스트 영상 {vid}", "channelId": v["ch"], "channelTitle": f"채널 {v['ch']}",
                                     "publishedAt": v["pub"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                                     "thumbnails": {"high": {"url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}}}
                    it["contentDetails"] = {"duration": f"PT{v['dur'] // 60}M{v['dur'] % 60}S"}
                    it["player"] = {"embedWidth": "360" if v["vertical"] else "640",
                                    "embedHeight": "640" if v["vertical"] else "360"}
                items.append(it)
            return {"items": items}
        if endpoint == "channels":
            return {"items": [{"id": c, "statistics": {"subscriberCount": str(self.subs[c])}} for c in params["id"].split(",")]}
        raise AssertionError(endpoint)


def main():
    tmp = tempfile.mkdtemp()
    state_path = os.path.join(tmp, "state.json.gz")
    out = os.path.join(tmp, "data")
    fake = FakeYouTube()
    try:
        for h in range(72):  # 3일, 매시간
            fake.now = START + timedelta(hours=h)
            state = collect.run("TEST", state_path, out, now=fake.now, fetch=fake)
        # 1) 쇼츠 판별: 가로·긴 영상은 추적 목록에 없어야 함
        for vid in state["videos"]:
            v = fake.videos[vid]
            assert v["vertical"] and v["dur"] <= config.MAX_SHORT_SECONDS, vid
        # 2) 7일 지난 영상 제외
        cutoff = fake.now - timedelta(days=config.TRACK_DAYS)
        assert all(collect.parse_iso(v["pub"]) >= cutoff for v in state["videos"].values())
        # 3) 삭제된 영상 제외
        assert "v0005" not in state["videos"]
        # 4) 할당량: 하루 검색 80회 이하
        assert state["quota"][list(state["quota"])[0]]["searches"] <= 80
        # 5) 랭킹 파일과 떡상 영상 상위 노출
        home = json.load(open(os.path.join(out, "home-kr.json"), encoding="utf-8"))
        assert home["items"], "홈 순위가 비어 있음"
        top_rates = [fake.videos[c["id"]]["rate"] for c in home["items"][:5]]
        print("홈 상위 5개 실제 시간당 조회수:", top_rates)
        first = home["items"][0]
        print("1위:", first["t"], "| 시간당", first["vph"], "| 구독자 대비", first["ratio"], "| 측정값 사용:", first["measured"])
        assert first["measured"], "3일 뒤에는 실제 측정 속도를 써야 함"
        files = sorted(f for f in os.listdir(out) if f.endswith(".json"))
        assert len(files) == 2 * (len(config.CATEGORIES) + 2) + 1, len(files)
        detail = json.load(open(os.path.join(out, "v", first["id"] + ".json"), encoding="utf-8"))
        assert detail["ranks"][0]["rank"] == 1 and detail["series"], "상세 파일에 순위·추이가 있어야 함"
        print("상세 파일", len(os.listdir(os.path.join(out, "v"))), "개, 1위 배지:", detail["ranks"][:3])
        size = os.path.getsize(state_path)
        print(f"추적 영상 {len(state['videos'])}개, 상태 파일 {size / 1024:.0f}KB, 출력 파일 {len(files)}개")
        print("API 호출 수(3일):", fake.calls)
        print("최근 로그:", state["log"][0])
        # 6) 예비 실행: 직전 실행 10분 뒤에 다시 돌면 API를 부르지 않고 건너뜀
        before = dict(fake.calls)
        fake.now = fake.now + timedelta(minutes=10)
        again = collect.run("TEST", state_path, out, now=fake.now, fetch=fake)
        assert fake.calls == before, "예비 실행이 API를 호출함"
        assert again["log"][0] == state["log"][0]
        print("모든 테스트 통과")
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
