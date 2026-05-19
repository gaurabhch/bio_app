from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timedelta, timezone

from core.database import get_psycopg2_connection
from schemas.wellness import (
    BreathingPatternResponse,
    BreathingSessionCreate,
    BreathingSessionResponse,
    BreathingHistoryResponse,
    YogaPoseResponse,
    ScienceContentResponse
)

router = APIRouter(tags=["Wellness"])

# Task 2.1 — GET /breathing/patterns 
@router.get("/breathing/patterns", response_model=List[BreathingPatternResponse])
def get_breathing_patterns():
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, name, sequence, description, use_case
            FROM breathing_patterns
            WHERE is_active = TRUE
        """)
        rows = cur.fetchall()
        return [
            BreathingPatternResponse(
                id=r[0], name=r[1], sequence=r[2],
                description=r[3], use_case=r[4]
            )
            for r in rows
        ]
    finally:
        cur.close()
        conn.close()


#  Task 2.2 — POST /breathing/session
@router.post("/breathing/session", response_model=BreathingSessionResponse, status_code=201)
def log_breathing_session(payload: BreathingSessionCreate):
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM breathing_patterns WHERE id = %s", (payload.pattern_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Breathing pattern not found")      # Validate pattern exists

        cur.execute("""
            INSERT INTO breathing_sessions
                (user_id, pattern_id, cycles_completed, completed, started_at, ended_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, pattern_id, cycles_completed, total_cycles,
                        completed, started_at, ended_at
        """, (
            str(payload.user_id), payload.pattern_id, payload.cycles_completed,
            payload.completed, payload.started_at, payload.ended_at
        ))
        conn.commit()
        row = cur.fetchone()
        return BreathingSessionResponse(
            id=row[0], user_id=str(row[1]), pattern_id=row[2],
            cycles_completed=row[3], total_cycles=row[4],
            completed=row[5], started_at=row[6], ended_at=row[7]
        )
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# Task 2.3 — GET /breathing/history 
@router.get("/breathing/history", response_model=BreathingHistoryResponse)
def get_breathing_history(user_id: str):
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        # Full session history
        cur.execute("""
            SELECT id, user_id, pattern_id, cycles_completed, total_cycles,
                    completed, started_at, ended_at
            FROM breathing_sessions
            WHERE user_id = %s
            ORDER BY started_at DESC
        """, (str(user_id),))
        rows = cur.fetchall()

        sessions = [
            BreathingSessionResponse(
                id=r[0], user_id=str(r[1]), pattern_id=r[2],
                cycles_completed=r[3], total_cycles=r[4],
                completed=r[5], started_at=r[6], ended_at=r[7]
            )
            for r in rows
        ]

        # Weekly count — sessions in last 7 days
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        weekly_count = sum(1 for s in sessions if s.started_at >= week_ago)

        # Streak — consecutive days with at least one completed session
        completed_dates = sorted(
            set(s.started_at.date() for s in sessions if s.completed),
            reverse=True,
        )
        streak = 0
        expected = datetime.now(timezone.utc).date()
        for date in completed_dates:
            if date == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif date < expected:
                break

        return BreathingHistoryResponse(
            sessions=sessions,
            weekly_session_count=weekly_count,
            current_streak=streak,
        )
    finally:
        cur.close()
        conn.close()


# Task 2.4 — GET /wellness/yoga-poses
@router.get("/wellness/yoga-poses", response_model=List[YogaPoseResponse])
def get_yoga_poses():
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, name, image_url, benefit_tags, duration_seconds, instructions
            FROM yoga_poses
            WHERE is_active = TRUE
        """)
        rows = cur.fetchall()
        return [
            YogaPoseResponse(
                id=r[0], name=r[1], image_url=r[2],
                benefit_tags=r[3], duration_seconds=r[4], instructions=r[5]
            )
            for r in rows
        ]
    finally:
        cur.close()
        conn.close()


# Task 2.5 — GET /breathing/science-content
@router.get("/breathing/science-content", response_model=List[ScienceContentResponse])
def get_science_content():
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, display_order, pointer_text
            FROM science_content
            WHERE is_active = TRUE
            ORDER BY display_order ASC
        """)
        rows = cur.fetchall()
        return [
            ScienceContentResponse(id=r[0], display_order=r[1], pointer_text=r[2])
            for r in rows
        ]
    finally:
        cur.close()
        conn.close()
