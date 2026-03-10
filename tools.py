"""
레스토랑 봇 도구 함수 구현
OpenAI Agents SDK 의 @function_tool 데코레이터를 사용합니다.
"""
import json
from datetime import datetime
from agents import function_tool, AgentHooks, Agent, Tool, RunContextWrapper
from data import (
    MENU_DB,
    SPECIAL_MENUS,
    SEATING_OPTIONS,
    orders_store,
    reservations_store,
    waitlist_store,
    booked_slots,
    get_next_order_id,
    get_next_reservation_id,
)

import streamlit as st
from models import UserAccountContext
from pydantic import BaseModel


class OrderItem(BaseModel):
	menu_name: str
	quantity: int = 1
	options: str = ""


class OrderChange(BaseModel):
	action: str
	menu_name: str
	quantity: int = 1
	options: str = ""


# ============================================================
# order_agent 도구 함수
# ============================================================

# 1. 메뉴 목록 조회 (주문 가능한 항목 확인용)
@function_tool
def get_available_menu(category: str = "") -> str:
	"""
	현재 주문 가능한 메뉴 목록을 조회한다.
	category: 카테고리 필터 (appetizer, main, dessert, drink). 빈 문자열이면 전체 조회.
	"""
	results = []
	for name, info in MENU_DB.items():
		if not info["available"]:
			continue
		if category and info["category"] != category:
			continue
		results.append({
			"메뉴명": name,
			"카테고리": info["category"],
			"가격": f"{info['price']:,}원",
			"설명": info["description"],
		})

	if not results:
		return "해당 카테고리에 주문 가능한 메뉴가 없습니다."
	return json.dumps(results, ensure_ascii=False, indent=2)


# 2. 메뉴 가격 조회
@function_tool
def get_menu_price(menu_name: str) -> str:
	"""
	특정 메뉴의 가격을 조회한다.
	menu_name: 메뉴명
	"""
	if menu_name not in MENU_DB:
			return f"'{menu_name}' 메뉴를 찾을 수 없습니다."
	price = MENU_DB[menu_name]["price"]
	return f"{menu_name}: {price:,}원"


# 3. 품절 여부 확인
@function_tool
def check_availability(menu_name: str) -> str:
	"""
	특정 메뉴의 품절 여부를 확인한다.
	menu_name: 메뉴명
	"""
	if menu_name not in MENU_DB:
		return f"'{menu_name}' 메뉴를 찾을 수 없습니다."
	info = MENU_DB[menu_name]
	if not info["available"]:
		return f"'{menu_name}'은(는) 현재 품절입니다."
	return f"'{menu_name}' 주문 가능합니다. (남은 수량: {info['remaining']})"


# 4. 주문 접수
@function_tool
def place_order(items: list[OrderItem]) -> str:
	"""
	주문을 접수한다.
	items: 주문 항목 리스트. 예: [{"menu_name": "김치찌개", "quantity": 2, "options": "덜 맵게"}]
	"""
	order_id = get_next_order_id()
	order_items = []
	total = 0
	errors = []

	for item in items:
		name = item.menu_name
		qty = item.quantity
		options = item.options

		if name not in MENU_DB:
			errors.append(f"'{name}' 메뉴를 찾을 수 없습니다.")
			continue
		if not MENU_DB[name]["available"]:
			errors.append(f"'{name}'은(는) 현재 품절입니다.")
			continue
		if qty > MENU_DB[name]["remaining"]:
			errors.append(f"'{name}' 재고 부족 (남은 수량: {MENU_DB[name]['remaining']})")
			continue

		subtotal = MENU_DB[name]["price"] * qty
		total += subtotal
		order_items.append({
			"menu_name": name,
			"quantity": qty,
			"options": options,
			"subtotal": subtotal,
		})

	if errors and not order_items:
		return "주문 실패:\n" + "\n".join(f"- {e}" for e in errors)

	order = {
		"order_id": order_id,
		"items": order_items,
		"total": total,
		"status": "접수됨",
		"estimated_minutes": len(order_items) * 10 + 5,
		"created_at": datetime.now().isoformat(),
	}
	orders_store[order_id] = order

	# 재고 차감
	for oi in order_items:
		MENU_DB[oi["menu_name"]]["remaining"] -= oi["quantity"]

	result = {
		"주문번호": order_id,
		"주문항목": [
			f"{oi['menu_name']} x{oi['quantity']}" + (f" ({oi['options']})" if oi['options'] else "")
			for oi in order_items
		],
		"총액": f"{total:,}원",
		"예상소요시간": f"약 {order['estimated_minutes']}분",
		"상태": "접수됨",
	}
	if errors:
		result["주의"] = errors

	return json.dumps(result, ensure_ascii=False, indent=2)


# 5. 주문 내역 조회
@function_tool
def get_order_status(order_id: str) -> str:
	"""
	접수된 주문의 현재 상태를 조회한다.
	order_id: 주문 번호
	"""
	if order_id not in orders_store:
		return f"주문번호 '{order_id}'를 찾을 수 없습니다."

	order = orders_store[order_id]
	result = {
		"주문번호": order["order_id"],
		"상태": order["status"],
		"주문항목": [
			f"{oi['menu_name']} x{oi['quantity']}" for oi in order["items"]
		],
		"총액": f"{order['total']:,}원",
		"주문시각": order["created_at"],
	}
	return json.dumps(result, ensure_ascii=False, indent=2)


# 6. 주문 수정
@function_tool
def modify_order(order_id: str, changes: list[OrderChange]) -> str:
	"""
	접수된 주문을 수정한다.
	order_id: 주문 번호
	changes: 변경 사항 리스트.
						예: [{"action": "add", "menu_name": "콜라", "quantity": 1},
								{"action": "remove", "menu_name": "사이다"}]
	"""
	if order_id not in orders_store:
			return f"주문번호 '{order_id}'를 찾을 수 없습니다."

	order = orders_store[order_id]
	if order["status"] == "취소됨":
			return "이미 취소된 주문은 수정할 수 없습니다."

	messages = []

	for change in changes:
		action = change.action
		name = change.menu_name
		qty = change.quantity

		if action == "add":
			if name not in MENU_DB:
				messages.append(f"'{name}' 메뉴를 찾을 수 없습니다.")
				continue
			if not MENU_DB[name]["available"]:
				messages.append(f"'{name}'은(는) 품절입니다.")
				continue
			subtotal = MENU_DB[name]["price"] * qty
			order["items"].append({
				"menu_name": name,
				"quantity": qty,
				"options": change.options,
				"subtotal": subtotal,
			})
			order["total"] += subtotal
			MENU_DB[name]["remaining"] -= qty
			messages.append(f"'{name}' x{qty} 추가 완료")

		elif action == "remove":
			found = False
			for i, oi in enumerate(order["items"]):
				if oi["menu_name"] == name:
					order["total"] -= oi["subtotal"]
					MENU_DB[name]["remaining"] += oi["quantity"]
					order["items"].pop(i)
					messages.append(f"'{name}' 제거 완료")
					found = True
					break
			if not found:
				messages.append(f"주문 내역에 '{name}'이(가) 없습니다.")

	result = {
		"주문번호": order_id,
		"변경내역": messages,
		"현재주문": [f"{oi['menu_name']} x{oi['quantity']}" for oi in order["items"]],
		"총액": f"{order['total']:,}원",
	}
	return json.dumps(result, ensure_ascii=False, indent=2)


# 7. 주문 취소
@function_tool
def cancel_order(order_id: str, reason: str = "") -> str:
	"""
	접수된 주문을 취소한다.
	order_id: 주문 번호
	reason: 취소 사유 (선택)
	"""
	if order_id not in orders_store:
		return f"주문번호 '{order_id}'를 찾을 수 없습니다."

	order = orders_store[order_id]
	if order["status"] == "취소됨":
		return "이미 취소된 주문입니다."

	# 재고 복구
	for oi in order["items"]:
		MENU_DB[oi["menu_name"]]["remaining"] += oi["quantity"]

	order["status"] = "취소됨"
	order["cancel_reason"] = reason

	return json.dumps({
		"주문번호": order_id,
		"상태": "취소됨",
		"취소사유": reason or "사유 없음",
	}, ensure_ascii=False, indent=2)


# 8. 총 금액 계산
@function_tool
def calculate_total(order_id: str) -> str:
	"""
	주문의 총 금액을 계산한다.
	order_id: 주문 번호
	"""
	if order_id not in orders_store:
		return f"주문번호 '{order_id}'를 찾을 수 없습니다."

	order = orders_store[order_id]
	breakdown = []
	for oi in order["items"]:
		unit_price = MENU_DB[oi["menu_name"]]["price"]
		breakdown.append({
			"메뉴": oi["menu_name"],
			"단가": f"{unit_price:,}원",
			"수량": oi["quantity"],
			"소계": f"{oi['subtotal']:,}원",
		})

	result = {
		"주문번호": order_id,
		"항목별금액": breakdown,
		"총액": f"{order['total']:,}원",
	}
	return json.dumps(result, ensure_ascii=False, indent=2)



# ============================================================
# reservation_agent 도구 함수
# ============================================================

# 1. 예약 가능 시간 조회
@function_tool
def check_available_slots(date: str, party_size: int) -> str:
	"""
	특정 날짜에 예약 가능한 시간대를 조회한다.
	date: 날짜 (YYYY-MM-DD)
	party_size: 인원수
	"""
	all_slots = [
		"11:30", "12:00", "12:30", "13:00", "13:30",
		"17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
	]
	booked = booked_slots.get(date, [])
	available = [s for s in all_slots if s not in booked]

	# 인원수에 맞는 좌석 유형 필터
	suitable_seats = []
	for seat_type, info in SEATING_OPTIONS.items():
		if info["capacity_min"] <= party_size <= info["capacity_max"]:
			suitable_seats.append(f"{seat_type} ({info['description']})")

	if not available:
		return f"{date}에는 예약 가능한 시간대가 없습니다. 대기 등록을 원하시면 말씀해주세요."

	result = {
		"날짜": date,
		"인원": f"{party_size}명",
		"예약가능시간": available,
		"이용가능좌석": suitable_seats if suitable_seats else ["해당 인원에 맞는 좌석이 없습니다. 문의 바랍니다."],
	}
	return json.dumps(result, ensure_ascii=False, indent=2)


# 2. 예약 접수
@function_tool
def make_reservation(
	date: str,
	time: str,
	party_size: int,
	customer_name: str,
	phone: str,
	seating_preference: str = "",
	special_requests: str = "",
) -> str:
	"""
	테이블 예약을 접수한다.
	date: 날짜 (YYYY-MM-DD)
	time: 시간 (HH:MM)
	party_size: 인원수
	customer_name: 예약자명
	phone: 연락처
	seating_preference: 좌석 선호 (창가, 룸, 야외 등)
	special_requests: 특별 요청 (생일, 하이체어 등)
	"""
	booked = booked_slots.get(date, [])
	if time in booked:
		return f"{date} {time}은(는) 이미 예약이 마감되었습니다. 다른 시간을 확인해주세요."

	reservation_id = get_next_reservation_id()
	reservation = {
		"reservation_id": reservation_id,
		"date": date,
		"time": time,
		"party_size": party_size,
		"customer_name": customer_name,
		"phone": phone,
		"seating_preference": seating_preference,
		"special_requests": special_requests,
		"status": "confirmed",
		"created_at": datetime.now().isoformat(),
	}
	reservations_store[reservation_id] = reservation

	# 해당 시간대를 예약 완료로 표시
	if date not in booked_slots:
		booked_slots[date] = []
	booked_slots[date].append(time)

	result = {
		"예약번호": reservation_id,
		"날짜": date,
		"시간": time,
		"인원": f"{party_size}명",
		"예약자": customer_name,
		"연락처": phone,
		"좌석": seating_preference or "지정 없음",
		"특별요청": special_requests or "없음",
		"상태": "예약 확정",
	}
	return json.dumps(result, ensure_ascii=False, indent=2)


# 3. 예약 조회
@function_tool
def get_reservation(reservation_id: str = "", phone: str = "") -> str:
	"""
	기존 예약 정보를 조회한다.
	reservation_id 또는 phone 중 하나로 조회 가능.
	"""
	found = None

	if reservation_id and reservation_id in reservations_store:
		found = reservations_store[reservation_id]
	elif phone:
		for r in reservations_store.values():
			if r["phone"] == phone:
				found = r
				break

	if not found:
		return "해당하는 예약 정보를 찾을 수 없습니다."

	result = {
		"예약번호": found["reservation_id"],
		"날짜": found["date"],
		"시간": found["time"],
		"인원": f"{found['party_size']}명",
		"예약자": found["customer_name"],
		"좌석": found.get("seating_preference", "지정 없음"),
		"특별요청": found.get("special_requests", "없음"),
		"상태": found["status"],
	}
	return json.dumps(result, ensure_ascii=False, indent=2)


# 4. 예약 변경
@function_tool
def modify_reservation(
	reservation_id: str,
	new_date: str = "",
	new_time: str = "",
	new_party_size: int = 0,
	new_seating_preference: str = "",
) -> str:
	"""
	기존 예약을 변경한다.
	reservation_id: 예약 번호
	변경할 항목만 전달하면 된다.
	"""
	if reservation_id not in reservations_store:
		return f"예약번호 '{reservation_id}'를 찾을 수 없습니다."

	r = reservations_store[reservation_id]
	if r["status"] == "cancelled":
		return "이미 취소된 예약은 변경할 수 없습니다."

	changes = []

	if new_date:
		# 기존 날짜 슬롯 해제
		old_date = r["date"]
		old_time = r["time"]
		if old_date in booked_slots and old_time in booked_slots[old_date]:
				booked_slots[old_date].remove(old_time)
		r["date"] = new_date
		changes.append(f"날짜: {new_date}")

	if new_time:
		target_date = new_date if new_date else r["date"]
		booked = booked_slots.get(target_date, [])
		if new_time in booked:
			return f"{target_date} {new_time}은(는) 이미 예약이 마감되었습니다."
		# 기존 시간 슬롯 해제 (날짜 변경이 없었을 때만)
		if not new_date and r["date"] in booked_slots and r["time"] in booked_slots[r["date"]]:
			booked_slots[r["date"]].remove(r["time"])
		r["time"] = new_time
		if target_date not in booked_slots:
			booked_slots[target_date] = []
		booked_slots[target_date].append(new_time)
		changes.append(f"시간: {new_time}")

	if new_party_size > 0:
		r["party_size"] = new_party_size
		changes.append(f"인원: {new_party_size}명")

	if new_seating_preference:
		r["seating_preference"] = new_seating_preference
		changes.append(f"좌석: {new_seating_preference}")

	if not changes:
		return "변경할 항목이 없습니다."

	result = {
		"예약번호": reservation_id,
		"변경내역": changes,
		"현재예약": {
			"날짜": r["date"],
			"시간": r["time"],
			"인원": f"{r['party_size']}명",
			"좌석": r.get("seating_preference", "지정 없음"),
		},
	}
	return json.dumps(result, ensure_ascii=False, indent=2)


# 5. 예약 취소
@function_tool
def cancel_reservation(reservation_id: str, reason: str = "") -> str:
	"""
	예약을 취소한다.
	reservation_id: 예약 번호
	reason: 취소 사유 (선택)
	"""
	if reservation_id not in reservations_store:
		return f"예약번호 '{reservation_id}'를 찾을 수 없습니다."

	r = reservations_store[reservation_id]
	if r["status"] == "cancelled":
		return "이미 취소된 예약입니다."

	# 슬롯 해제
	if r["date"] in booked_slots and r["time"] in booked_slots[r["date"]]:
		booked_slots[r["date"]].remove(r["time"])

	r["status"] = "cancelled"
	r["cancel_reason"] = reason

	return json.dumps({
		"예약번호": reservation_id,
		"상태": "취소 완료",
		"취소사유": reason or "사유 없음",
	}, ensure_ascii=False, indent=2)


# 6. 좌석 유형 조회
@function_tool
def get_seating_options() -> str:
	"""
	레스토랑에서 제공하는 좌석 유형과 각 유형별 수용 가능 인원을 조회한다.
	"""
	results = []
	for seat_type, info in SEATING_OPTIONS.items():
		results.append({
			"좌석유형": seat_type,
			"설명": info["description"],
			"수용인원": f"{info['capacity_min']}~{info['capacity_max']}명",
			"총좌석수": f"{info['total']}석",
		})
	return json.dumps(results, ensure_ascii=False, indent=2)


# 7. 대기 등록
@function_tool
def add_to_waitlist(
	date: str,
	time: str,
	party_size: int,
	customer_name: str,
	phone: str,
) -> str:
	"""
	원하는 시간대가 만석일 때 대기 명단에 등록한다.
	"""
	entry = {
		"waitlist_number": len(waitlist_store) + 1,
		"date": date,
		"time": time,
		"party_size": party_size,
		"customer_name": customer_name,
		"phone": phone,
		"registered_at": datetime.now().isoformat(),
	}
	waitlist_store.append(entry)

	return json.dumps({
		"대기번호": entry["waitlist_number"],
		"날짜": date,
		"시간": time,
		"인원": f"{party_size}명",
		"안내": "자리가 나는 대로 연락드리겠습니다.",
	}, ensure_ascii=False, indent=2)


# ============================================================
# menu_agent 도구 함수
# ============================================================

# 1. 전체 메뉴 조회
@function_tool
def get_full_menu(category: str = "") -> str:
	"""
	전체 메뉴 목록을 조회한다.
	category: 카테고리 필터 (appetizer, main, dessert, drink). 빈 문자열이면 전체 조회.
	"""
	results = []
	for name, info in MENU_DB.items():
		if category and info["category"] != category:
			continue
		results.append({
			"메뉴명": name,
			"카테고리": info["category"],
			"가격": f"{info['price']:,}원",
			"설명": info["description"],
			"맵기": f"{'🌶️' * info['spicy_level']}" if info["spicy_level"] > 0 else "안 매움",
			"품절여부": "품절" if not info["available"] else "주문가능",
		})
	return json.dumps(results, ensure_ascii=False, indent=2)


# 2. 메뉴 상세 정보 조회
@function_tool
def get_menu_detail(menu_name: str) -> str:
	"""
	특정 메뉴의 상세 정보를 조회한다.
	menu_name: 메뉴명
	"""
	if menu_name not in MENU_DB:
		return f"'{menu_name}' 메뉴를 찾을 수 없습니다."

	info = MENU_DB[menu_name]
	result = {
		"메뉴명": menu_name,
		"카테고리": info["category"],
		"가격": f"{info['price']:,}원",
		"설명": info["description"],
		"재료": info["ingredients"],
		"조리방법": "전통 방식으로 정성껏 조리합니다",
		"칼로리": f"{info['calories']}kcal",
		"맵기": f"{info['spicy_level']}/5" + (f" {'🌶️' * info['spicy_level']}" if info["spicy_level"] > 0 else ""),
		"알레르기성분": info["allergens"] if info["allergens"] else "없음",
		"품절여부": "품절" if not info["available"] else "주문가능",
	}
	return json.dumps(result, ensure_ascii=False, indent=2)


# 3. 알레르기 성분 확인
@function_tool
def check_allergens(menu_name: str) -> str:
	"""
	특정 메뉴에 포함된 알레르기 유발 성분을 확인한다.
	menu_name: 메뉴명
	"""
	if menu_name not in MENU_DB:
		return f"'{menu_name}' 메뉴를 찾을 수 없습니다."

	info = MENU_DB[menu_name]
	result = {
		"메뉴명": menu_name,
		"알레르기유발성분": info["allergens"] if info["allergens"] else "해당 없음",
		"주요재료": info["ingredients"],
		"안내": "교차 오염 가능성이 있으므로 심한 알레르기가 있으신 분은 직원에게 문의해주세요.",
	}
	return json.dumps(result, ensure_ascii=False, indent=2)


# 4. 알레르기 기반 안전 메뉴 필터링
@function_tool
def get_safe_menu(allergies: list[str], category: str = "") -> str:
	"""
	특정 알레르기를 피할 수 있는 안전한 메뉴 목록을 조회한다.
	allergies: 알레르기 리스트 (예: ["견과류", "유제품"])
	category: 카테고리 필터 (선택)
	"""
	results = []
	for name, info in MENU_DB.items():
		if category and info["category"] != category:
			continue
		# 알레르기 성분이 겹치지 않는 메뉴만 필터
		has_allergen = any(a in info["allergens"] for a in allergies)
		if not has_allergen:
			results.append({
				"메뉴명": name,
				"카테고리": info["category"],
				"가격": f"{info['price']:,}원",
				"설명": info["description"],
				"알레르기성분": info["allergens"] if info["allergens"] else "없음",
				"품절여부": "품절" if not info["available"] else "주문가능",
			})

	if not results:
		return f"해당 알레르기({', '.join(allergies)})를 모두 피할 수 있는 메뉴가 없습니다."
	return json.dumps(results, ensure_ascii=False, indent=2)


# 5. 식이 제한별 메뉴 조회
@function_tool
def get_dietary_menu(dietary_type: str) -> str:
	"""
	식이 제한 유형에 맞는 메뉴를 조회한다.
	dietary_type: 식이 유형 (vegetarian, vegan, halal, gluten_free 등)
	"""
	results = []
	for name, info in MENU_DB.items():
		if dietary_type in info.get("dietary", []):
			results.append({
				"메뉴명": name,
				"카테고리": info["category"],
				"가격": f"{info['price']:,}원",
				"설명": info["description"],
				"품절여부": "품절" if not info["available"] else "주문가능",
			})

	if not results:
		return f"'{dietary_type}' 유형에 해당하는 메뉴가 없습니다."
	return json.dumps(results, ensure_ascii=False, indent=2)


# 6. 메뉴 추천
@function_tool
def recommend_menu(
	preferences: str = "",
	allergies: list[str] = [],
	party_size: int = 0,
) -> str:
	"""
	고객 상황에 맞는 메뉴를 추천한다.
	preferences: 선호 사항 (예: "매운 음식 좋아함", "가벼운 식사")
	allergies: 알레르기 정보
	party_size: 인원수 (단체 메뉴 추천용)
	"""
	safe_menus = []
	for name, info in MENU_DB.items():
		if not info["available"]:
			continue
		if allergies and any(a in info["allergens"] for a in allergies):
			continue
		safe_menus.append((name, info))

	recommendations = []

	if "매운" in preferences or "매콤" in preferences or "얼큰" in preferences:
		for name, info in safe_menus:
			if info["spicy_level"] >= 2:
				recommendations.append(name)
	elif "가벼운" in preferences or "다이어트" in preferences:
		for name, info in safe_menus:
			if info["calories"] <= 350:
				recommendations.append(name)
	else:
		# 기본 추천: 셰프 추천 + 오늘의 메뉴
		for name in SPECIAL_MENUS["chef_pick"] + SPECIAL_MENUS["today"]:
			if any(n == name for n, _ in safe_menus):
				recommendations.append(name)

	if party_size >= 4:
		for name, info in safe_menus:
			if name in ["해물파전", "잡채", "불고기"] and name not in recommendations:
				recommendations.append(name)

	if not recommendations:
		recommendations = [name for name, _ in safe_menus[:3]]

	result = {
		"추천메뉴": [
			{
				"메뉴명": name,
				"가격": f"{MENU_DB[name]['price']:,}원",
				"설명": MENU_DB[name]["description"],
			}
			for name in recommendations
		],
		"추천사유": preferences if preferences else "셰프 추천 및 오늘의 메뉴 기반",
	}
	return json.dumps(result, ensure_ascii=False, indent=2)


# 7. 오늘의 메뉴 / 시즌 메뉴 조회
@function_tool
def get_special_menu() -> str:
	"""
	오늘의 추천 메뉴, 시즌 한정 메뉴, 셰프 추천 메뉴를 조회한다.
	"""
	result = {}
	for label, key in [("오늘의추천", "today"), ("시즌메뉴", "season"), ("셰프추천", "chef_pick")]:
		menus = []
		for name in SPECIAL_MENUS[key]:
			if name in MENU_DB:
				menus.append({
					"메뉴명": name,
					"가격": f"{MENU_DB[name]['price']:,}원",
					"설명": MENU_DB[name]["description"],
				})
		result[label] = menus
	return json.dumps(result, ensure_ascii=False, indent=2)


# 8. 재료 원산지 조회
@function_tool
def get_ingredient_origin(menu_name: str) -> str:
	"""
	특정 메뉴에 사용된 주요 재료의 원산지 정보를 조회한다.
	menu_name: 메뉴명
	"""
	if menu_name not in MENU_DB:
		return f"'{menu_name}' 메뉴를 찾을 수 없습니다."

	info = MENU_DB[menu_name]
	origin = info.get("origin", {})
	if not origin:
		return f"'{menu_name}'의 원산지 정보가 등록되어 있지 않습니다."

	result = {
		"메뉴명": menu_name,
		"원산지정보": {k: v for k, v in origin.items()},
	}
	return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================
# 에이전트별 도구 모음 (편의용 export)
# ============================================================

ORDER_TOOLS = [
	get_available_menu,
	get_menu_price,
	check_availability,
	place_order,
	get_order_status,
	modify_order,
	cancel_order,
	calculate_total,
]

RESERVATION_TOOLS = [
	check_available_slots,
	make_reservation,
	get_reservation,
	modify_reservation,
	cancel_reservation,
	get_seating_options,
	add_to_waitlist,
]

MENU_TOOLS = [
	get_full_menu,
	get_menu_detail,
	check_allergens,
	get_safe_menu,
	get_dietary_menu,
	recommend_menu,
	get_special_menu,
	get_ingredient_origin,
]


#class AgentToolUsageLoggingHooks(AgentHooks):
#
#	async def on_tool_start(
#		self,
#		context: RunContextWrapper[UserAccountContext],
#		agent: Agent[UserAccountContext],
#		tool: Tool,
#	):
#		with st.sidebar:
#			st.write(f"🔧 **{agent.name}** starting tool: `{tool.name}`")
#
#	async def on_tool_end(
#		self,
#		context: RunContextWrapper[UserAccountContext],
#		agent: Agent[UserAccountContext],
#		tool: Tool,
#		result: str,
#	):
#		with st.sidebar:
#			st.write(f"🔧 **{agent.name}** used tool: `{tool.name}`")
#			st.code(result)
#
#	async def on_handoff(
#		self,
#		context: RunContextWrapper[UserAccountContext],
#		agent: Agent[UserAccountContext],
#		source: Agent[UserAccountContext],
#	):
#		with st.sidebar:
#			st.write(f"🔄 Handoff: **{source.name}** → **{agent.name}**")
#
#	async def on_start(
#		self,
#		context: RunContextWrapper[UserAccountContext],
#		agent: Agent[UserAccountContext],
#	):
#		with st.sidebar:
#			st.write(f"🚀 **{agent.name}** activated")
#
#	async def on_end(
#		self,
#		context: RunContextWrapper[UserAccountContext],
#		agent: Agent[UserAccountContext],
#		output,
#	):
#		with st.sidebar:
#			st.write(f"🏁 **{agent.name}** completed")