"""
Auth routes — register, login, profile.
Ported from Login_Signup/routes/auth_routes.py.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from firebase_admin import auth as firebase_auth

from core.database import get_auth_db
from models.user import User
from auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()


class TokenRequest(BaseModel):
    token: str
    name:   Optional[str] = None
    mobile: Optional[str] = None
    dob:    Optional[str] = None


@router.post("/register")
async def register(request: TokenRequest, db: Session = Depends(get_auth_db)):
    try:
        decoded = firebase_auth.verify_id_token(request.token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # If user already exists, just return them (idempotent)
    existing = db.query(User).filter(User.firebase_uid == decoded["uid"]).first()
    if existing:
        return {"message": "Already registered", "email": existing.email}

    # Create new row in Neon DB
    new_user = User(
        firebase_uid=decoded["uid"],
        email=decoded.get("email"),
        name=request.name,
        mobile=request.mobile,
        dob=date.fromisoformat(request.dob) if request.dob else None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "email": new_user.email}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the currently authenticated user's details.
    The frontend sends the Firebase ID token in the Authorization header.
    """
    return {
        "id":           current_user.id,
        "firebase_uid": current_user.firebase_uid,
        "email":        current_user.email,
        "message":      "Token is valid."
    }
