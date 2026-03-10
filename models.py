from pydantic import BaseModel
from typing import Optional

class UserAccountContext(BaseModel):
	customer_id: int
	customer_name: str
	party_size: int
	is_regular: bool
	allergies: Optional[list[str]] = []


class InputGuardRailOutput(BaseModel):
	is_off_topic: bool 
	reason: str


class HandoffData(BaseModel):
	to_agent_name: str
	issue_type: str
	issue_description: str
	reason: str