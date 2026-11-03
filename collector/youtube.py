"""YouTube Data API v3 호출과 할당량 기록. 표준 라이브러리만 씁니다."""

import json
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3/"


class QuotaExceeded(Exception):
    pass


class YouTube:
    def __init__(self, key, quota, search_budget, unit_budget, fetch=None):
        self.key = key
        self.quota = quota  # {"searches": n, "units": n} 오늘 사용량, 바깥에서 저장
        self.search_budget = search_budget
        self.unit_budget = unit_budget
        self._fetch = fetch or self._http

    def _http(self, endpoint, params):
        url = API + endpoint + "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 403 and "quota" in body.lower():
                raise QuotaExceeded(body[:300])
            raise RuntimeError(f"YouTube API {endpoint} {e.code}: {body[:300]}")

    def _call(self, endpoint, params, is_search=False):
        if is_search:
            if self.quota["searches"] >= self.search_budget:
                raise QuotaExceeded("search budget reached")
        elif self.quota["units"] >= self.unit_budget:
            raise QuotaExceeded("unit budget reached")
        data = self._fetch(endpoint, {**params, "key": self.key})
        if is_search:
            self.quota["searches"] += 1
        else:
            self.quota["units"] += 1
        return data

    def search_shorts(self, q, region_code, language, published_after):
        data = self._call("search", {
            "part": "id",
            "type": "video",
            "q": q,
            "order": "viewCount",
            "videoDuration": "short",  # 4분 미만
            "publishedAfter": published_after,
            "regionCode": region_code,
            "relevanceLanguage": language,
            "safeSearch": "moderate",
            "maxResults": 50,
        }, is_search=True)
        return [it["id"]["videoId"] for it in data.get("items", []) if it.get("id", {}).get("videoId")]

    def videos(self, ids, full):
        """ids를 50개씩 묶어 조회. full이면 제목·길이·화면 비율까지."""
        part = "snippet,contentDetails,statistics,player" if full else "statistics"
        out = []
        for i in range(0, len(ids), 50):
            params = {"part": part, "id": ",".join(ids[i:i + 50]), "maxResults": 50}
            if full:
                params["maxHeight"] = 640  # 응답의 embedWidth/embedHeight로 세로 여부 판단
            out.extend(self._call("videos", params).get("items", []))
        return out

    def channels(self, ids):
        out = []
        for i in range(0, len(ids), 50):
            out.extend(self._call("channels", {"part": "statistics", "id": ",".join(ids[i:i + 50]), "maxResults": 50}).get("items", []))
        return out
