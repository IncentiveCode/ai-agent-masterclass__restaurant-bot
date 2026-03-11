from agents import (
	Agent,
	output_guardrail,
	Runner,
	RunContextWrapper,
	GuardrailFunctionOutput,
)
from models import OrderOutputGuardRailOutput, UserAccountContext


order_guardrail_instructions = """
    당신은 주문 에이전트의 응답을 검증하는 품질 관리자입니다.

    다음 항목을 검사하고, 하나라도 위반되면 is_safe=False를 반환하세요.

    필수 검증 항목:
    1. 주문 정확성
       - 존재하지 않는 메뉴를 확정한 응답이 있는가
       - 품절된 메뉴를 주문 가능하다고 안내했는가
       - 수량이나 옵션이 고객 요청과 다르게 확정되었는가

    2. 금액 정확성
       - 가격 정보가 포함된 경우, 계산이 명백히 틀린 부분이 있는가
       - 근거 없는 할인이나 무료 제공을 약속했는가

    3. 알레르기 안전
       - 고객의 알레르기 정보가 있음에도 관련 성분 안내를 누락했는가
       - 알레르기 유발 가능 메뉴를 안전하다고 잘못 안내했는가

    4. 역할 범위
       - 예약, 메뉴 상세 설명 등 다른 에이전트의 역할을 직접 수행했는가
       - 레스토랑 정책에 없는 환불, 보상 등을 독단적으로 약속했는가

    5. 응대 품질
       - 고객에게 무례하거나 부적절한 표현이 있는가
       - 개인정보를 불필요하게 노출하거나 요구했는가

    검증 결과:
    - 위 항목을 모두 통과하면 True를 반환
    - 하나라도 위반되면 위반 사유와 함께 False를 반환
"""

order_output_guardrail_agent = Agent(
	name="order support guardrail",
	instructions=order_guardrail_instructions,
	output_type=OrderOutputGuardRailOutput,
)


@output_guardrail
async def order_output_guardrail(
	wrapper: RunContextWrapper[UserAccountContext],
	agent: Agent,
	output: str
):
	result = await Runner.run(
		order_output_guardrail_agent,
		output,
		context=wrapper.context,
	)

	validation = result.final_output
	print('order output guardrail : ', result.final_output)
	triggered = (
		validation.contains_off_topic
		# or validation.contains_complain_data
		# or validation.contains_menu_data
		# or validation.contains_reservation_data
	)

	return GuardrailFunctionOutput(
		output_info=validation,
		tripwire_triggered=triggered,
	)