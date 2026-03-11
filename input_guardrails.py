import streamlit as st
from agents import (
	Agent,
	RunContextWrapper,
	input_guardrail,
	Runner,
	GuardrailFunctionOutput
)
from models import UserAccountContext, InputGuardRailOutput


input_guardrail_agent = Agent(
	name="input guardrail agent",
	instructions="""
    당신은 레스토랑 에이전트의 입력을 검증하는 관련성 판별기입니다.

    이 레스토랑 봇은 다음 주제만 처리합니다:
    - 음식 주문 (메뉴 선택, 수량, 옵션, 주문 변경/취소)
    - 테이블 예약 (날짜, 시간, 인원, 좌석, 예약 변경/취소)
    - 메뉴 안내 (메뉴 구성, 재료, 알레르기, 식이 제한, 추천)
    - 레스토랑 일반 정보 (운영 시간, 위치, 연락처)

    다음과 같은 요청은 관련 없는 것으로 판단하세요:
    - 수학, 과학, 역사 등 일반 지식 질문
    - 코딩, 번역, 작문 등 레스토랑과 무관한 작업
    - 다른 식당이나 서비스에 대한 질문
    - 레스토랑 업무와 관련 없는 잡담

    판단 기준:
    - 레스토랑 운영과 직접적으로 관련된 요청 → True 반환
    - 레스토랑과 무관한 요청 → False 반환
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

	print('input guardrail : ', result.final_output)
	
	return GuardrailFunctionOutput(
		output_info=result.final_output,
		tripwire_triggered=result.final_output.is_off_topic,
	)