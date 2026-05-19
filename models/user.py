"""
User model — mapped to the Auth (Login_Signup) Neon database.
"""

import uuid
from sqlalchemy import Column, String, DateTime, Date
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from core.database import AuthBase


class User(AuthBase):
    __tablename__ = "users"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firebase_uid = Column(String, unique=True, nullable=False, index=True)
    email        = Column(String, unique=True, nullable=False)
    name         = Column(String, nullable=True)
    mobile       = Column(String, nullable=True)
    dob          = Column(Date,   nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at   = Column(DateTime, nullable=True, default=None)
