"""
Lifestyle service — orchestrates tips + task generation.
"""

from datetime import date

from services.lifestyle_repo import get_task_for_today, create_task
from services.tip_provider import generate_tips_and_task
from schemas.lifestyle import TaskCardResponse, LifestyleTodayResponse


def get_lifestyle_today(
    user_id: str,
    today: date,
    symptoms: dict,
) -> LifestyleTodayResponse:

    existing_task = get_task_for_today(user_id, today)
    tips, generated_task_text = generate_tips_and_task(symptoms)

    if existing_task is None:
        existing_task = create_task(user_id, today, generated_task_text)

    task_card = TaskCardResponse(
        task_id=existing_task["id"],
        task_description=existing_task["task_description"],
        completed=existing_task["completed"],
    )

    return LifestyleTodayResponse(tips=tips, task=task_card)
