from agents import (
	Agent,
	output_guardrail,
	Runner,
	RunContextWrapper,
	GuardrailFunctionOutput,
)
from models import ReservationOutputGuardRailOutput, UserAccountContext


reservation_guardrail_instructions = """
    당신은 예약 에이전트의 응답을 검증하는 품질 관리자입니다.

    다음 항목을 검사하고, 하나라도 위반되면 is_safe=False를 반환하세요.

    필수 검증 항목:
    1. 예약 정보 정확성
       - 날짜, 시간, 인원수가 고객 요청과 일치하는가
       - 이미 마감된 시간대를 예약 가능하다고 안내했는가
       - 좌석 수용 인원을 초과하는 배정을 했는가

    2. 예약 정책 준수
       - 존재하지 않는 할인이나 특별 혜택을 약속했는가
       - 운영 시간 외의 예약을 확정했는가
       - 예약 변경/취소 정책을 잘못 안내했는가

    3. 필수 정보 확인
       - 예약 확정 시 예약번호를 안내했는가
       - 연락처 등 필수 정보 확인 없이 예약을 확정했는가

    4. 역할 범위
       - 주문 접수, 메뉴 상세 설명 등 다른 에이전트의 역할을 직접 수행했는가
       - 권한 밖의 약속(무료 룸 업그레이드, VIP 서비스 등)을 했는가

    5. 응대 품질
       - 고객에게 무례하거나 부적절한 표현이 있는가
       - 개인정보(전화번호 등)를 응답에 불필요하게 반복 노출했는가

    검증 결과:
    - 위 항목을 모두 통과하면 True를 반환
    - 하나라도 위반되면 위반 사유와 함께 False를 반환
"""

reservation_output_guardrail_agent = Agent(
	name="reservation support guardrail",
	instructions=reservation_guardrail_instructions,
	output_type=ReservationOutputGuardRailOutput,
)


@output_guardrail
async def reservation_output_guardrail(
	wrapper: RunContextWrapper[UserAccountContext],
	agent: Agent,
	output: str
):
	result = await Runner.run(
		reservation_output_guardrail_agent,
		output,
		context=wrapper.context,
	)

	validation = result.final_output
	print('reservation output guardrail : ', result.final_output)
	triggered = (
		validation.contains_off_topic
		# or validation.contains_complain_data
		# or validation.contains_menu_data
		# or validation.contains_order_data
	)

	return GuardrailFunctionOutput(
		output_info=validation,
		tripwire_triggered=triggered,
	)