"""
Firebase Admin SDK initialisation and token verification.
"""

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import HTTPException

from core.config import FIREBASE_SERVICE_ACCOUNT_PATH

# Initialise only once — guards against reload issues in dev
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)


def verify_firebase_token(token: str) -> dict:
    """
    Verifies a Firebase ID token sent from the frontend.
    Returns the decoded token payload (uid, email, etc.) on success.
    Raises HTTP 401 on failure.
    """
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid token. Please sign in again.")
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication failed. Please sign in again.")
