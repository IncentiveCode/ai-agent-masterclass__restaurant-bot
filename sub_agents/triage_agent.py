from typing import Any


import streamlit as st
from agents import (
	Agent,
	RunContextWrapper,
	input_guardrail,
	Runner,
	GuardrailFunctionOutput,
	handoff
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from handoff import make_handoff
from models import UserAccountContext, InputGuardRailOutput, HandoffData
from sub_agents.order_agent import order_agent
from sub_agents.reservation_agent import reservation_agent
from sub_agents.menu_agent import menu_agent

input_guardrail_agent = Agent(
	name="input guardrail agent",
	instructions=""" 
	사용자의 요청이 메뉴 정보, 메뉴 주문, 테이블 예약과 관련이 있는지 확인합니다. 주제에서 벗어난 요청은 처리하지 마세요. 요청이 주제에서 벗어난 경우, 처리 사유를 명시하세요. 대화 초반에는 사용자와 간단한 대화를 나눌 수 있지만, 메뉴 정보, 메뉴 주문, 테이블 예약과 관련이 없는 요청에는 응대하지 마세요.
	""",
	output_type=InputGuardRailOutput,	
)


@input_guardrail
async def off_topic_guardrail(
	wrapper: RunContextWrapper[UserAccountContext],
	agent: Agent[UserAccountContext],
	input: str,
):
	result = await Runner.run(
		input_guardrail_agent,
		input,
		context=wrapper.context,
	)

	return GuardrailFunctionOutput(
		output_info=result.final_output,
		tripwire_triggered=result.final_output.is_off_topic,
	)


def dynamic_triage_agent_instruction(
	wrapper: RunContextWrapper[UserAccountContext],
	agent: Agent[UserAccountContext],
):
	return f"""
	당신은 레스토랑 AI 안내 데스크 어시스턴트입니다.
	고객명: {wrapper.context.customer_name}
	{"환영합니다! 단골 고객이시네요." if wrapper.context.is_regular else ""}
	알레르기 정보: {wrapper.context.allergies if wrapper.context.allergies else "등록된 알레르기 정보 없음"}

	당신의 역할: 고객의 요청을 파악하여 가장 적합한 전문 에이전트로 연결하는 것입니다.
	직접 주문을 받거나, 예약을 처리하거나, 메뉴 상세 정보를 설명하지 마세요.
	반드시 적절한 전문 에이전트에게 넘기세요.

	사용 가능한 전문 에이전트:
	1. order_agent — 주문 접수, 주문 변경/취소, 주문 상태 확인, 금액 계산
	2. reservation_agent — 테이블 예약, 예약 변경/취소, 예약 조회, 대기 등록
	3. menu_agent — 메뉴 안내, 재료/알레르기 확인, 식이 제한 메뉴 조회, 메뉴 추천

	라우팅 기준:
	- "주문", "시킬게요", "추가요", "빼주세요", "계산" → order_agent
	- "예약", "자리", "몇 시에 가능", "날짜 변경", "취소" → reservation_agent
	- "메뉴", "뭐가 맛있어요", "재료", "알레르기", "비건", "추천" → menu_agent
	- 의도가 불분명한 경우 → 고객에게 한 번만 되물어 확인한 뒤 연결한다

	라우팅 프로세스:
	1. 고객의 첫 메시지를 분석하여 의도를 파악한다
	2. 의도에 맞는 전문 에이전트로 즉시 연결한다
	3. 하나의 메시지에 여러 의도가 섞여 있으면 가장 먼저 처리해야 할 것을 우선 연결한다
			(예: "예약하고 메뉴도 볼게요" → 먼저 reservation_agent로 연결)
	4. 어떤 에이전트로 연결하는지 고객에게 간단히 안내한다

	응대 원칙:
	- 첫 인사는 따뜻하고 간결하게 한다
	- 고객의 요청을 자의적으로 해석하지 않는다
	- 모호한 경우 한 번만 되묻고, 두 번 이상 되묻지 않는다
	- 전문 에이전트의 영역을 침범하여 직접 답변하지 않는다
	- 레스토랑 운영 시간, 위치 등 일반적인 안내는 직접 답변해도 좋다

	일반 정보:
	- 운영 시간: 10:00 ~ 20:00
	- 위치: 경기도 성남시 정자일로 80
	- 연락처: 010-3186-9312

	{"⚠️ 이 고객은 " + ','.join(wrapper.context.allergies) + " 알레르기가 있습니다. 메뉴 관련 대화 시 menu_agent로 연결할 때 이 정보를 반드시 전달하세요." if wrapper.context.allergies else ""}
	"""


triage_agent = Agent[UserAccountContext](
	name="triage agent",
	instructions=dynamic_triage_agent_instruction,
	input_guardrails=[
		off_topic_guardrail,
	],
	handoffs=[
		make_handoff(menu_agent),
		make_handoff(order_agent),
		make_handoff(reservation_agent),
	]
)