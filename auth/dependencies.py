"""
Auth dependencies for protected routes.
"""

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_auth_db
from models.user import User
from auth.firebase import verify_firebase_token

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_auth_db)
) -> User:
    """
    Dependency for all protected routes.

    Flow:
      1. Extract Bearer token from the Authorization header
      2. Verify it against Firebase — gets uid + email back
      3. Look up the user row in Neon by firebase_uid
      4. If no row exists (first login ever), create one automatically
      5. Return the User ORM object to the route handler
    """
    token   = credentials.credentials
    decoded = verify_firebase_token(token)          # raises 401 if invalid

    uid   = decoded["uid"]
    email = decoded.get("email", "")

    # Try to find existing user in Neon
    user = db.query(User).filter(User.firebase_uid == uid).first()

    # First-time login — create the user row automatically
    if not user:
        user = User(firebase_uid=uid, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


async def get_active_user(
    current_user=Depends(get_current_user),
    db=Depends(get_auth_db)
):
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    return current_user
