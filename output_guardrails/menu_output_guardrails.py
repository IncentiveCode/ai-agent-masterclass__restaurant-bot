from agents import (
	Agent,
	output_guardrail,
	Runner,
	RunContextWrapper,
	GuardrailFunctionOutput,
)
from models import MenuOutputGuardRailOutput, UserAccountContext


menu_guardrail_instructions = """
    당신은 메뉴 안내 에이전트의 응답을 검증하는 품질 관리자입니다.

    다음 항목을 검사하고, 하나라도 위반되면 is_safe=False를 반환하세요.

    필수 검증 항목:
    1. 메뉴 정보 정확성
       - 실제 메뉴에 존재하지 않는 항목을 소개했는가
       - 가격 정보가 실제와 다르게 안내되었는가
       - 재료나 조리 방법이 사실과 다르게 설명되었는가

    2. 알레르기 안전 (최우선)
       - 알레르기 유발 성분을 누락하거나 축소하여 안내했는가
       - 알레르기 성분이 포함된 메뉴를 안전하다고 잘못 안내했는가
       - 교차 오염 가능성에 대한 안내를 빠뜨렸는가
       - 확실하지 않은 성분을 단정적으로 "없다"고 안내했는가

    3. 식이 제한 정확성
       - 비건/채식/할랄 등 식이 분류가 잘못 안내되었는가
       - 해당 식이 제한에 맞지 않는 메뉴를 적합하다고 추천했는가

    4. 역할 범위
       - 주문 접수나 예약 처리를 직접 수행했는가
       - 메뉴에 대한 근거 없는 건강 효능이나 의학적 조언을 했는가

    5. 응대 품질
       - 고객에게 무례하거나 부적절한 표현이 있는가
       - 특정 메뉴를 과장되게 홍보하거나 허위 정보를 포함했는가

    검증 결과:
    - 위 항목을 모두 통과하면 True를 반환
    - 하나라도 위반되면 위반 사유와 함께 False를 반환
"""

menu_output_guardrail_agent = Agent(
	name="menu support guardrail",
	instructions=menu_guardrail_instructions,
	output_type=MenuOutputGuardRailOutput,
)


@output_guardrail
async def menu_output_guardrail(
	wrapper: RunContextWrapper[UserAccountContext],
	agent: Agent,
	output: str
):
	result = await Runner.run(
		menu_output_guardrail_agent,
		output,
		context=wrapper.context,
	)

	validation = result.final_output
	print('menu output guardrail : ', result.final_output)
	triggered = (
		validation.contains_off_topic
		# or validation.contains_complain_data
		# or validation.contains_order_data
		# or validation.contains_reservation_data
	)

	return GuardrailFunctionOutput(
		output_info=validation,
		tripwire_triggered=triggered,
	)