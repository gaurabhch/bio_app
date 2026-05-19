"""
BioCanvas — Unified FastAPI Server
===================================
Consolidates all 5 previously separate servers into a single application:

  1. Login_Signup        →  /auth/*
  2. Lifestyle_feat      →  /lifestyle/*
  3. app (1_2)           →  /symptom-log/*  +  /predictions/*
  4. lab_test            →  /lab/*
  5. questionnair_app    →  /questionnaire/*

Run with:
    cd app
    uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Core setup (loads .env, initialises config) ──────────────────────
from core.config import AUTH_DATABASE_URL          # noqa: F401  — triggers .env load
from core.database import (
    AuthBase, auth_engine,
    FeaturesBase, features_engine,
    init_async_db, close_async_db,
)

# ── Routers ──────────────────────────────────────────────────────────
from routers.auth_routes import router as auth_router
from routers.lifestyle_routes import router as lifestyle_router
from routers.lab_test_routes import router as lab_test_router
from routers.questionnaire_routes import router as questionnaire_router
from services.symptom_log_service import router as symptom_log_router
from services.prediction_service import router as prediction_router
from routers.wellness_routes import router as wellness_router


# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create SQLAlchemy tables + asyncpg pool
    AuthBase.metadata.create_all(bind=auth_engine)
    FeaturesBase.metadata.create_all(bind=features_engine)
    await init_async_db()
    yield
    # Shutdown: close asyncpg pool
    await close_async_db()


# ── Application ──────────────────────────────────────────────────────
app = FastAPI(
    title="BioCanvas API",
    description="Unified backend for BioCanvas — Auth, Questionnaire, Lifestyle, Symptom Tracking, Predictions, and Lab Test Interpretation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register all routers ─────────────────────────────────────────────
app.include_router(auth_router)             # /auth/register, /auth/me
app.include_router(lifestyle_router)        # /lifestyle/today, /lifestyle/task/{id}/complete
app.include_router(symptom_log_router)      # /symptom-log/daily, /symptom-log/today, /symptom-log/history
app.include_router(prediction_router)       # /predictions/generate, /predictions/latest
app.include_router(lab_test_router)         # /lab/interpret
app.include_router(questionnaire_router)    # /questionnaire/submit, /questionnaire/results/{id}
app.include_router(wellness_router)         # /breathing/*, /wellness/*


# ── Health / root ────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"message": "BioCanvas API is running."}


@app.get("/health", tags=["Health"])
async def health_check():
    from core.database import get_async_pool
    db_status = "ok"
    try:
        pool = await get_async_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception as e:
        db_status = f"unavailable: {str(e)[:80]}"

    return {
        "status": "ok",
        "service": "BioCanvas Unified API",
        "db": db_status,
    }
