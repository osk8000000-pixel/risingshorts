"""라이징쇼츠 수집 설정.

검색어는 YouTube 검색의 OR 연산자(|)를 씁니다. 결과 품질을 보며 여기만 고치면 됩니다.
"""

# 카테고리 20개. slug는 주소에 쓰이므로 바꾸지 않는 것이 좋습니다.
CATEGORIES = [
    {"slug": "mystery", "name": "미스터리·괴담", "kr": "괴담|미스터리|무서운 이야기|도시전설|공포 썰", "us": "mystery|creepy|unsolved mystery|scary story"},
    {"slug": "dog", "name": "강아지", "kr": "강아지|댕댕이|반려견", "us": "dog|puppy"},
    {"slug": "cat", "name": "고양이", "kr": "고양이|냥이|아기고양이", "us": "cat|kitten"},
    {"slug": "animals", "name": "아기동물·야생동물", "kr": "아기동물|야생동물|동물", "us": "baby animals|wildlife|animals"},
    {"slug": "parenting", "name": "육아", "kr": "육아|아기|신생아", "us": "baby|parenting|toddler"},
    {"slug": "facts", "name": "지식·잡학", "kr": "지식|상식|몰랐던 사실", "us": "facts|did you know"},
    {"slug": "ai-video", "name": "AI 영상", "kr": "AI 애니메이션|AI로 만든|AI 쇼츠|AI 영상 만들기", "us": "AI animation|AI generated|made with AI|AI short film"},
    {"slug": "cooking", "name": "요리·레시피", "kr": "레시피|요리|집밥", "us": "recipe|cooking"},
    {"slug": "mukbang", "name": "먹방·맛집", "kr": "먹방|맛집", "us": "mukbang|food review"},
    {"slug": "comedy", "name": "유머·코미디", "kr": "웃긴|개그|상황극", "us": "funny|comedy|skit"},
    {"slug": "gaming", "name": "게임", "kr": "게임 하이라이트|롤|리그오브레전드|발로란트|배그|메이플스토리|모바일게임", "us": "gaming|minecraft|roblox"},
    {"slug": "beauty", "name": "뷰티·메이크업", "kr": "메이크업|화장|뷰티", "us": "makeup|beauty"},
    {"slug": "fashion", "name": "패션", "kr": "코디|패션|옷", "us": "outfit|fashion"},
    {"slug": "fitness", "name": "운동·홈트", "kr": "홈트|운동|다이어트 운동", "us": "workout|fitness|gym"},
    {"slug": "money", "name": "재테크·경제", "kr": "재테크|경제|돈 모으기", "us": "money tips|finance|investing"},
    {"slug": "travel", "name": "여행", "kr": "여행|여행지 추천", "us": "travel|travel tips"},
    {"slug": "cars", "name": "자동차", "kr": "자동차|신차|차", "us": "cars|car"},
    {"slug": "lifehacks", "name": "생활 꿀팁·DIY", "kr": "꿀팁|살림|다이소", "us": "life hacks|DIY"},
    {"slug": "tech", "name": "테크·리뷰", "kr": "언박싱|리뷰|아이폰", "us": "tech|unboxing|gadget"},
    {"slug": "dance", "name": "음악·댄스 챌린지", "kr": "챌린지|커버댄스|댄스", "us": "dance challenge|dance|cover"},
]

REGIONS = {
    "kr": {"regionCode": "KR", "relevanceLanguage": "ko", "query_key": "kr"},
    "us": {"regionCode": "US", "relevanceLanguage": "en", "query_key": "us"},
}

# 새 쇼츠 찾기(검색) 간격. 마지막 검색 후 이 시간이 지나면 다음 실행에서 검색 (하루 2회 = 검색 80회)
# 예약 실행이 늦어져도 하루 2회를 지키도록 시각이 아니라 경과 시간으로 판단합니다.
DISCOVER_EVERY_HOURS = 11.5

# 추적 기간: 업로드 후 이 일수가 지나면 목록에서 뺍니다.
TRACK_DAYS = 7

# 예약 실행은 시간당 2번(7분, 37분) 걸려 있고, 직전 실행 후 이 시간(분)이 안 지났으면 건너뜁니다.
# GitHub 예약 실행이 가끔 빠지거나 늦어져도 매시간 갱신을 지키기 위한 예비 실행입니다.
MIN_RUN_GAP_MINUTES = 45

# 쇼츠 판별: 이 길이(초) 이하 + 세로 화면
MAX_SHORT_SECONDS = 180

# 채널 구독자 수 갱신 주기(시간)
CHANNEL_REFRESH_HOURS = 12

# 하루 할당량 안전선. 기본 할당량은 검색 100회 + 그 외 10,000단위.
# 여기를 넘기면 그날은 작업을 멈추고 다음 실행에 이어 갑니다.
SEARCH_BUDGET_PER_DAY = 90
UNIT_BUDGET_PER_DAY = 9000

# 떡상 속도 계산에 쓰는 최근 시간 창
VELOCITY_WINDOW_HOURS = 3

# 페이지에 보여 줄 순위 개수
TOP_N_CATEGORY = 50
TOP_N_HOME = 20
