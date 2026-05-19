"""
Database helpers — provides both SQLAlchemy (sync) and asyncpg (async) pools.

• SQLAlchemy engine → used by Auth, Lifestyle, Symptom-log, Predictions, Lab-test
• asyncpg pool     → used by Questionnaire / PCOS assessment
"""

import ssl
import asyncpg
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

from core.config import AUTH_DATABASE_URL, DATABASE_URL


# ═══════════════════════════════════════════════════════════════════════
#  SQLAlchemy — Auth DB  (Login_Signup Neon database)
# ═══════════════════════════════════════════════════════════════════════
auth_engine = create_engine(
    AUTH_DATABASE_URL,
    poolclass=NullPool,
    pool_pre_ping=True,
)
AuthSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=auth_engine)


class AuthBase(DeclarativeBase):
    """Declarative base for Auth-related models (Login_Signup DB)."""
    pass


def get_auth_db():
    """Dependency — yields a SQLAlchemy session bound to the Auth DB."""
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
#  SQLAlchemy — Features DB  (shared Neon database)
# ═══════════════════════════════════════════════════════════════════════
features_engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"},
)
FeaturesSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=features_engine)


class FeaturesBase(DeclarativeBase):
    """Declarative base for Feature-related models (shared DB)."""
    pass


def get_features_db():
    """Dependency — yields a SQLAlchemy session bound to the Features DB."""
    db = FeaturesSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
#  Raw psycopg2-style connection (used by symptom_log, predictions, lab_test)
# ═══════════════════════════════════════════════════════════════════════
import psycopg2

def get_psycopg2_connection():
    """Returns a raw psycopg2 connection to the features/shared DB."""
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# ═══════════════════════════════════════════════════════════════════════
#  asyncpg pool  (Questionnaire / PCOS assessment)
# ═══════════════════════════════════════════════════════════════════════
_async_pool = None


async def init_async_db():
    """Create the asyncpg connection pool and ensure tables exist."""
    global _async_pool

    if _async_pool is None:
        ssl_ctx = ssl.create_default_context()
        _async_pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=1,
            max_size=10,
            ssl=ssl_ctx,
        )

    async with _async_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pcos_assessments (
                id UUID PRIMARY KEY,
                user_id UUID,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                input_data JSONB NOT NULL,
                result_data JSONB NOT NULL,
                risk_tier TEXT,
                composite_score INTEGER
            );
        """)
        await conn.execute("""
            ALTER TABLE pcos_assessments ADD COLUMN IF NOT EXISTS user_id UUID;
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pcos_assessments_created_at
            ON pcos_assessments(created_at DESC);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pcos_assessments_risk_tier
            ON pcos_assessments(risk_tier);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pcos_assessments_user_id
            ON pcos_assessments(user_id);
        """)


async def get_async_pool():
    """Return the asyncpg pool, initialising it on first call."""
    global _async_pool
    if _async_pool is None:
        await init_async_db()
    return _async_pool


async def close_async_db():
    """Shut down the asyncpg pool gracefully."""
    global _async_pool
    if _async_pool is not None:
        await _async_pool.close()
        _async_pool = None
