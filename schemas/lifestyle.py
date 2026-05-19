"""
Pydantic schemas for the Lifestyle feature.
"""

from pydantic import BaseModel
from uuid import UUID


class TipCard(BaseModel):
    icon: str
    headline: str
    description: str


class TaskCardResponse(BaseModel):
    task_id: UUID
    task_description: str
    completed: bool


class LifestyleTodayResponse(BaseModel):
    tips: list[TipCard]
    task: TaskCardResponse


class TaskCompleteResponse(BaseModel):
    task_id: UUID
    completed: bool
    message: str
