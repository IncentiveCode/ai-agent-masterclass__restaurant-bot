import dotenv

from handoff import make_handoff
dotenv.load_dotenv()

from openai import OpenAI
import asyncio, json
import streamlit as st
from agents import Runner, SQLiteSession, InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from models import UserAccountContext
from sub_agents.complain_agent import complain_agent
from sub_agents.menu_agent import menu_agent
from sub_agents.order_agent import order_agent
from sub_agents.reservation_agent import reservation_agent
from sub_agents.triage_agent import triage_agent

client = OpenAI()

# handoff setting
complain_agent.handoffs = [
	make_handoff(menu_agent),
	make_handoff(order_agent),
	make_handoff(reservation_agent),
	make_handoff(triage_agent),
],
menu_agent.handoffs = [
	make_handoff(complain_agent),
	make_handoff(menu_agent),
	make_handoff(reservation_agent),
	make_handoff(triage_agent),
],
order_agent.handoffs = [
	make_handoff(complain_agent),
	make_handoff(order_agent),
	make_handoff(reservation_agent),
	make_handoff(triage_agent),
]
reservation_agent.handoffs = [
	make_handoff(complain_agent),
	make_handoff(menu_agent),
	make_handoff(order_agent),
	make_handoff(triage_agent),
]

user_account_ctx = UserAccountContext(
	customer_id=1,
	customer_name="incentive",
	party_size=6,
	is_regular=False,
	allergies=[]
)

user_account_ctx2 = UserAccountContext(
	customer_id=2,
	customer_name="인센티브",
	party_size=2,
	is_regular=True,
	allergies=['대두', '참깨']
)


if "session" not in st.session_state:
	st.session_state["session"] = SQLiteSession(
		"chat_history",
		"customer-support-memory.db",
	)

session = st.session_state["session"]


if "agent" not in st.session_state:
	st.session_state["agent"] = triage_agent
if "dp_agent" not in st.session_state:
	st.session_state["dp_agent"] = triage_agent.name

async def display_history():
	messages = await session.get_items()
	dp_agent = st.session_state["dp_agent"]
	
	for message in messages:
		if "role" in message:
			role = message["role"]
			with st.chat_message(role):
				if role == "user":
					st.write(message["content"])
				else:
					if "type" in message:
						type = message["type"]
						if type == "message":
							st.write(
								f"{dp_agent} : {message["content"][0]["text"]}".replace("$", "\\$")
							)

		elif "type" in message and message["type"] == "function_call_output":
			if "assistant" in message["output"]:
				print(message)
				data = json.loads(message["output"]);
				dp_agent = data["assistant"]
				st.caption(f"[ {dp_agent}로 handoff ]")

asyncio.run(display_history())


async def run_agent(message):
	with st.chat_message("ai"):
		current_agent = st.session_state["agent"].name
		response = ""
		text_placeholder = st.empty()
		st.session_state["text_placeholder"] = text_placeholder
	
		try:
			stream = Runner.run_streamed(
				st.session_state["agent"],
				message,
				session=session,
				context=user_account_ctx2,
			)

			async for event in stream.stream_events():
				if event.type == "raw_response_event":
					if event.data.type == "response.output_text.delta":
						response += event.data.delta
						text_placeholder.write(
							f"{current_agent} : {response}".replace("$", "\\$")
						)

				elif event.type == "agent_updated_stream_event":
					new_agent = event.new_agent.name

					if current_agent != new_agent:
						st.session_state["agent"] = event.new_agent
						current_agent = new_agent

						# st.caption(f"[ {new_agent}로 handoff ]")

						response = ""
						text_placeholder = st.empty()
						st.session_state["text_placeholder"] = text_placeholder
						
		except InputGuardrailTripwireTriggered:
			text_placeholder = st.empty()
			text_placeholder.write("요청하신 정보에 대해서는 도움을 드릴 수 없습니다.")
			st.session_state["text_placeholder"] = text_placeholder

		except OutputGuardrailTripwireTriggered:
			text_placeholder = st.empty()
			text_placeholder.write("이 요청에 대한 답변을 드릴 수 없습니다.")
			st.session_state["text_placeholder"] = text_placeholder


message = st.chat_input(
	"AI assistant 에게 질문하세요.",
)

if message:
	with st.chat_message("human"):
		st.write(message)
	asyncio.run(run_agent(message))


with st.sidebar:
	reset = st.button("메모리 초기화")
	if reset:
		asyncio.run(session.clear_session())
	st.write(asyncio.run(session.get_items()))