"""
레스토랑 봇 테스트용 더미 데이터 및 인메모리 저장소
"""
from datetime import datetime, timedelta

# ============================================================
# 메뉴 데이터
# ============================================================
MENU_DB = {
	"김치찌개": {
		"category": "main",
		"price": 9000,
		"description": "돼지고기와 묵은지로 끓인 얼큰한 찌개",
		"ingredients": ["돼지고기", "묵은지", "두부", "대파", "고춧가루", "마늘"],
		"allergens": ["대두"],
		"dietary": [],
		"spicy_level": 3,
		"calories": 450,
		"origin": {"돼지고기": "국내산", "김치": "국내산"},
		"available": True,
		"remaining": 15,
	},
	"된장찌개": {
		"category": "main",
		"price": 8000,
		"description": "구수한 된장에 각종 채소를 넣어 끓인 찌개",
		"ingredients": ["된장", "두부", "감자", "호박", "양파", "대파", "고추"],
		"allergens": ["대두"],
		"dietary": ["vegetarian"],
		"spicy_level": 1,
		"calories": 350,
		"origin": {"된장": "국내산", "두부": "국내산"},
		"available": True,
		"remaining": 20,
	},
	"불고기": {
		"category": "main",
		"price": 15000,
		"description": "달콤한 간장 양념에 재운 소고기 불고기",
		"ingredients": ["소고기", "양파", "당근", "대파", "간장", "설탕", "참기름"],
		"allergens": ["대두", "참깨"],
		"dietary": [],
		"spicy_level": 0,
		"calories": 550,
		"origin": {"소고기": "호주산"},
		"available": True,
		"remaining": 10,
	},
	"해물파전": {
		"category": "appetizer",
		"price": 12000,
		"description": "오징어, 새우, 조개가 듬뿍 들어간 바삭한 파전",
		"ingredients": ["밀가루", "계란", "오징어", "새우", "조개", "대파"],
		"allergens": ["밀", "계란", "갑각류", "연체류"],
		"dietary": [],
		"spicy_level": 0,
		"calories": 480,
		"origin": {"오징어": "국내산", "새우": "베트남산"},
		"available": True,
		"remaining": 8,
	},
	"잡채": {
		"category": "appetizer",
		"price": 10000,
		"description": "당면과 각종 채소, 소고기를 볶아낸 잡채",
		"ingredients": ["당면", "시금치", "당근", "양파", "소고기", "간장", "참기름"],
		"allergens": ["대두", "참깨"],
		"dietary": [],
		"spicy_level": 0,
		"calories": 400,
		"origin": {"소고기": "국내산"},
		"available": True,
		"remaining": 12,
	},
	"비빔밥": {
		"category": "main",
		"price": 10000,
		"description": "갖은 나물과 고추장, 계란을 올린 비빔밥",
		"ingredients": ["밥", "시금치", "콩나물", "당근", "호박", "계란", "고추장", "참기름"],
		"allergens": ["계란", "대두", "참깨"],
		"dietary": [],
		"spicy_level": 2,
		"calories": 600,
		"origin": {"쌀": "국내산"},
		"available": True,
		"remaining": 18,
	},
	"두부샐러드": {
		"category": "appetizer",
		"price": 8000,
		"description": "부드러운 두부 위에 신선한 채소와 드레싱을 올린 샐러드",
		"ingredients": ["두부", "양상추", "토마토", "오이", "올리브유", "레몬즙"],
		"allergens": ["대두"],
		"dietary": ["vegetarian", "vegan"],
		"spicy_level": 0,
		"calories": 200,
		"origin": {"두부": "국내산"},
		"available": True,
		"remaining": 10,
	},
	"떡볶이": {
		"category": "appetizer",
		"price": 7000,
		"description": "쫄깃한 떡에 매콤달콤한 고추장 소스를 버무린 떡볶이",
		"ingredients": ["떡", "어묵", "고추장", "설탕", "대파", "삶은 계란"],
		"allergens": ["밀", "계란", "대두"],
		"dietary": [],
		"spicy_level": 3,
		"calories": 380,
		"origin": {"떡": "국내산"},
		"available": False,
		"remaining": 0,
	},
	"식혜": {
		"category": "drink",
		"price": 3000,
		"description": "달콤하고 시원한 전통 음료",
		"ingredients": ["엿기름", "쌀", "설탕", "생강"],
		"allergens": [],
		"dietary": ["vegetarian", "vegan", "gluten_free"],
		"spicy_level": 0,
		"calories": 120,
		"origin": {"쌀": "국내산"},
		"available": True,
		"remaining": 30,
	},
	"콜라": {
		"category": "drink",
		"price": 2000,
		"description": "시원한 탄산음료",
		"ingredients": ["탄산수", "설탕", "카라멜색소"],
		"allergens": [],
		"dietary": ["vegetarian", "vegan", "gluten_free"],
		"spicy_level": 0,
		"calories": 140,
		"origin": {},
		"available": True,
		"remaining": 50,
	},
	"사이다": {
		"category": "drink",
		"price": 2000,
		"description": "청량한 레몬라임 탄산음료",
		"ingredients": ["탄산수", "설탕", "레몬향"],
		"allergens": [],
		"dietary": ["vegetarian", "vegan", "gluten_free"],
		"spicy_level": 0,
		"calories": 130,
		"origin": {},
		"available": True,
		"remaining": 50,
	},
	"팥빙수": {
		"category": "dessert",
		"price": 8000,
		"description": "곱게 간 얼음 위에 팥, 떡, 과일을 올린 빙수",
		"ingredients": ["팥", "떡", "연유", "과일", "얼음"],
		"allergens": ["유제품"],
		"dietary": [],
		"spicy_level": 0,
		"calories": 350,
		"origin": {"팥": "국내산"},
		"available": True,
		"remaining": 6,
	},
	"호떡": {
		"category": "dessert",
		"price": 4000,
		"description": "바삭한 겉면 속에 흑설탕과 견과류가 가득한 호떡",
		"ingredients": ["밀가루", "흑설탕", "땅콩", "해바라기씨", "계피"],
		"allergens": ["밀", "견과류"],
		"dietary": ["vegetarian"],
		"spicy_level": 0,
		"calories": 300,
		"origin": {},
		"available": True,
		"remaining": 10,
	},
}

# 오늘의 추천 / 시즌 메뉴
SPECIAL_MENUS = {
	"today": ["불고기", "해물파전"],
	"season": ["팥빙수"],
	"chef_pick": ["김치찌개"],
}

# ============================================================
# 좌석 데이터
# ============================================================
SEATING_OPTIONS = {
	"홀": {"capacity_min": 1, "capacity_max": 4, "total": 10, "description": "오픈된 일반 좌석"},
	"창가": {"capacity_min": 1, "capacity_max": 2, "total": 4, "description": "창가 2인석"},
	"룸": {"capacity_min": 4, "capacity_max": 10, "total": 3, "description": "프라이빗 룸"},
	"야외": {"capacity_min": 1, "capacity_max": 6, "total": 5, "description": "테라스 야외 좌석"},
}

# ============================================================
# 인메모리 저장소 (주문 & 예약)
# ============================================================
orders_store: dict = {}
_order_counter = 1000

reservations_store: dict = {}
_reservation_counter = 5000

waitlist_store: list = []

# 테스트용 기존 예약 데이터 생성
_tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
reservations_store["RSV-5001"] = {
	"reservation_id": "RSV-5001",
	"date": _tomorrow,
	"time": "18:30",
	"party_size": 4,
	"customer_name": "김철수",
	"phone": "010-1234-5678",
	"seating_preference": "창가",
	"special_requests": "생일 케이크 준비 부탁드립니다",
	"status": "confirmed",
	"created_at": datetime.now().isoformat(),
}

# 이미 예약된 시간대 (예약 가능 여부 시뮬레이션용)
booked_slots: dict = {
	_tomorrow: ["12:00", "12:30", "18:00", "18:30", "19:00"],
}


def get_next_order_id() -> str:
	global _order_counter
	_order_counter += 1
	return f"ORD-{_order_counter}"


def get_next_reservation_id() -> str:
	global _reservation_counter
	_reservation_counter += 1
	return f"RSV-{_reservation_counter}"