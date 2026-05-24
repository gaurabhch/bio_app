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
    name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    dob: Optional[str] = None

@router.post("/register")
async def register(request: TokenRequest, db: Session = Depends(get_auth_db)):
    try:
        decoded = firebase_auth.verify_id_token(request.token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    existing = db.query(User).filter(User.firebase_uid == decoded["uid"]).first()
    if existing:
        if request.email and existing.email != request.email:
            existing.email = request.email
            db.commit()
            db.refresh(existing)
        return {"message": "Already registered", "email": existing.email}

    try:
        dob_value = date.fromisoformat(request.dob) if request.dob else None
    except ValueError:
        raise HTTPException(status_code=400, detail="dob must be in YYYY-MM-DD format")

    email_value = request.email or decoded.get("email")

    new_user = User(
        firebase_uid=decoded["uid"],
        email=email_value,
        name=request.name,
        mobile=request.mobile,
        dob=dob_value
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
