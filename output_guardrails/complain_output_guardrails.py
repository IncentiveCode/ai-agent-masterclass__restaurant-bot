from agents import (
	Agent,
	output_guardrail,
	Runner,
	RunContextWrapper,
	GuardrailFunctionOutput,
)
from models import ComplainOutputGuardRailOutput, UserAccountContext


complain_guardrail_instructions = """
    당신은 불만 응대 에이전트의 응답을 검증하는 품질 관리자입니다.

    다음 항목을 검사하고, 하나라도 위반되면 is_safe=False를 반환하세요.

    필수 검증 항목:
    1. 공감 및 사과 여부
       - 고객의 불만에 대해 공감이나 사과 없이 바로 해결책만 제시했는가
       - 고객의 감정을 부정하거나 반박하는 표현이 있는가
       - "그럴 리가 없다", "원래 그렇다", "고객님이 잘못" 같은 표현이 있는가

    2. 책임 회피 여부
       - 불만의 원인을 고객에게 전가했는가
       - 다른 직원이나 외부 요인에만 책임을 돌렸는가
       - 변명이 사과보다 먼저 나왔는가

    3. 보상 약속 범위
       - 매니저 확인 없이 금전적 보상(환불, 할인권, 무료 제공)을 확정 약속했는가
       - 레스토랑 정책에 없는 과도한 보상을 독단적으로 약속했는가
       - "전액 환불해 드리겠습니다", "다음 방문 시 무료입니다" 같은 확정적 보상 표현이 있는가

    4. 알레르기/건강 관련 안전
       - 알레르기 관련 불만인데 고객의 건강 상태 확인을 생략했는가
       - 이물질이나 위생 문제인데 심각성을 축소했는가
       - 건강과 관련된 불만에 매니저 연결 안내를 하지 않았는가

    5. 역할 범위
       - 주문 접수, 예약 처리, 메뉴 상세 설명 등 다른 에이전트의 역할을 직접 수행했는가
       - 의학적 조언이나 법적 판단을 했는가

    6. 응대 품질
       - 감정적이거나 방어적인 어조가 있는가
       - 고객의 불만을 가볍게 취급하거나 무시하는 뉘앙스가 있는가
       - 개인정보를 불필요하게 노출했는가
       - 형식적이고 기계적인 사과만 반복했는가

    검증 결과:
    - 위 항목을 모두 통과하면 True를 반환
    - 하나라도 위반되면 위반 사유와 함께 False를 반환
"""

complain_output_guardrail_agent = Agent(
	name="complain support guardrail",
	instructions=complain_guardrail_instructions,
	output_type=ComplainOutputGuardRailOutput,
)


@output_guardrail
async def complain_output_guardrail(
	wrapper: RunContextWrapper[UserAccountContext],
	agent: Agent,
	output: str
):
	result = await Runner.run(
		complain_output_guardrail_agent,
		output,
		context=wrapper.context,
	)

	validation = result.final_output
	print('complain output guardrail : ', result.final_output)
	triggered = (
		validation.contains_off_topic
		# or validation.contains_menu_data
		# or validation.contains_order_data
		# or validation.contains_reservation_data
	)

	return GuardrailFunctionOutput(
		output_info=validation,
		tripwire_triggered=triggered,
	)