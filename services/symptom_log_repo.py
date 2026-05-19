"""
Symptom-log repository — fetch today's log from daily_logs table.
"""

from datetime import date
from sqlalchemy import text

from core.database import FeaturesSessionLocal


def fetch_today_log(user_id: str, log_date: date) -> dict | None:
    db = FeaturesSessionLocal()
    try:
        result = db.execute(
            text("SELECT symptoms FROM daily_logs WHERE user_id = :user_id AND date = :date"),
            {"user_id": user_id, "date": log_date}
        ).fetchone()
        return result[0] if result else None
    finally:
        db.close()
