import streamlit as st
from agents import (
	RunContextWrapper,
	handoff
)
from models import UserAccountContext, HandoffData
from agents.extensions import handoff_filters


def handle_handoff(
	wrapper: RunContextWrapper[UserAccountContext],
	input_data: HandoffData,
):
	# st.caption(f"[ {input_data.to_agent_name}로 handoff ]")
	pass


def make_handoff(agent):
	return handoff(
		agent=agent,
		on_handoff=handle_handoff,
		input_type=HandoffData,
		input_filter=handoff_filters.remove_all_tools,
	)