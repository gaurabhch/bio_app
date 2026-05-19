"""
Lifestyle repository — CRUD for DailyTask via SQLAlchemy.
"""

import uuid
from datetime import date
from sqlalchemy.orm import Session

from core.database import FeaturesSessionLocal
from models.daily_task import DailyTask


def _get_db() -> Session:
    return FeaturesSessionLocal()


def get_task_for_today(user_id: str, today: date) -> dict | None:
    db = _get_db()
    try:
        task = (
            db.query(DailyTask)
            .filter(DailyTask.user_id == user_id, DailyTask.date == today)
            .first()
        )
        if not task:
            return None
        return {"id": str(task.id), "task_description": task.task_description, "completed": task.completed}
    finally:
        db.close()


def create_task(user_id: str, today: date, task_description: str) -> dict:
    db = _get_db()
    try:
        task = DailyTask(
            id=uuid.uuid4(),
            user_id=user_id,
            date=today,
            task_description=task_description,
            completed=False,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return {"id": str(task.id), "task_description": task.task_description, "completed": task.completed}
    finally:
        db.close()


def mark_task_complete(task_id: str) -> dict | None:
    db = _get_db()
    try:
        task = db.query(DailyTask).filter(DailyTask.id == task_id).first()
        if not task:
            return None
        task.completed = True
        db.commit()
        db.refresh(task)
        return {"id": str(task.id), "task_description": task.task_description, "completed": task.completed}
    finally:
        db.close()
