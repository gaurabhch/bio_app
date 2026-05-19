"""
Lifestyle routes — daily tips and task management.
Ported from features/Lifestyle_feat/lifestyle/router.py.
"""

from datetime import date
from fastapi import APIRouter, HTTPException

from services.symptom_log_repo import fetch_today_log
from services.lifestyle_service import get_lifestyle_today
from services.lifestyle_repo import mark_task_complete
from schemas.lifestyle import LifestyleTodayResponse, TaskCompleteResponse

router = APIRouter(prefix="/lifestyle", tags=["Lifestyle"])


@router.get("/today", response_model=LifestyleTodayResponse)
def lifestyle_today(user_id: str):
    today = date.today()
    symptoms = fetch_today_log(user_id=user_id, log_date=today)

    if symptoms is None:
        raise HTTPException(
            status_code=404,
            detail="No symptom log found for today. Please log your symptoms first.",
        )

    return get_lifestyle_today(user_id=user_id, today=today, symptoms=symptoms)


@router.patch("/task/{task_id}/complete", response_model=TaskCompleteResponse)
def complete_task(task_id: str):
    task = mark_task_complete(task_id=task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    return TaskCompleteResponse(
        task_id=task["id"],
        completed=task["completed"],
        message="Well done! Task completed for today. 🎉",
    )
