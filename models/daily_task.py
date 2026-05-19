"""
DailyTask model — mapped to the Features (shared) Neon database.
"""

import uuid
from datetime import date
from sqlalchemy import Column, Boolean, Date, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.database import FeaturesBase


class DailyTask(FeaturesBase):
    __tablename__ = "daily_tasks"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), nullable=False, index=True)
    date             = Column(Date, nullable=False)
    task_description = Column(Text, nullable=False)
    completed        = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_task_date"),
    )
