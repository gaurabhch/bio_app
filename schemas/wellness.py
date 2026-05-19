from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class BreathingPatternResponse(BaseModel):
    id: int
    name: str
    sequence: List[Any]
    description: str
    use_case: str


class BreathingSessionCreate(BaseModel):
    user_id: str
    pattern_id: int
    cycles_completed: int
    completed: bool
    started_at: datetime
    ended_at: Optional[datetime] = None


class BreathingSessionResponse(BaseModel):
    id: int
    user_id: str
    pattern_id: int
    cycles_completed: int
    total_cycles: int
    completed: bool
    started_at: datetime
    ended_at: Optional[datetime]


class BreathingHistoryResponse(BaseModel):
    sessions: List[BreathingSessionResponse]
    weekly_session_count: int
    current_streak: int


class YogaPoseResponse(BaseModel):
    id: int
    name: str
    image_url: Optional[str]
    benefit_tags: List[str]
    duration_seconds: int
    instructions: str


class ScienceContentResponse(BaseModel):
    id: int
    display_order: int
    pointer_text: str
