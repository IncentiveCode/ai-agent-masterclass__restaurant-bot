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


class ComplainOutputGuardRailOutput(BaseModel):
	contains_off_topic: bool
	contains_menu_data: bool 
	contains_order_data: bool 
	contains_reservation_data: bool
	reason: str

class MenuOutputGuardRailOutput(BaseModel):
	contains_off_topic: bool 
	contains_complain_topic: bool
	contains_order_data: bool
	contains_reservation_data: bool
	reason: str


class OrderOutputGuardRailOutput(BaseModel):
	contains_off_topic: bool 
	contains_complain_topic: bool
	contains_menu_data: bool
	contains_reservation_data: bool
	reason: str


class ReservationOutputGuardRailOutput(BaseModel):
	contains_off_topic: bool 
	contains_complain_topic: bool
	contains_menu_data: bool 
	contains_order_data: bool
	reason: str