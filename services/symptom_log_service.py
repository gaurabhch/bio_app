"""
Symptom log service — save / retrieve daily symptom logs.
Ported from features/app (1_2)/symptoms_log.py.
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date

from core.database import get_psycopg2_connection

router = APIRouter(prefix="/symptom-log", tags=["Symptom Log"])


class DailyLogRequest(BaseModel):
    user_id: str
    date: date
    symptoms: dict


@router.post("/daily")
def save_daily_log(payload: DailyLogRequest):
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO daily_logs (user_id, date, symptoms)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, date)
            DO UPDATE SET symptoms = EXCLUDED.symptoms, updated_at = NOW()
            """,
            (str(payload.user_id), payload.date, json.dumps(payload.symptoms))
        )
        conn.commit()
        return {"status": "saved", "date": str(payload.date)}
    finally:
        cur.close()
        conn.close()


@router.get("/today")
def get_today_log(user_id: str, date: date):
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, user_id, date, symptoms, created_at, updated_at FROM daily_logs WHERE user_id = %s AND date = %s",
            (user_id, date)
        )
        row = cur.fetchone()
        if not row:
            return {"log": None}
        return {
            "log": {
                "id": str(row[0]),
                "user_id": str(row[1]),
                "date": str(row[2]),
                "symptoms": row[3],
                "created_at": str(row[4]),
                "updated_at": str(row[5])
            }
        }
    finally:
        cur.close()
        conn.close()


@router.get("/history")
def get_history(user_id: str):
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, user_id, date, symptoms, created_at, updated_at
            FROM daily_logs
            WHERE user_id = %s
            ORDER BY date DESC
            """,
            (user_id,)
        )
        rows = cur.fetchall()
        return {
            "logs": [
                {
                    "id": str(r[0]),
                    "user_id": str(r[1]),
                    "date": str(r[2]),
                    "symptoms": r[3],
                    "created_at": str(r[4]),
                    "updated_at": str(r[5])
                }
                for r in rows
            ]
        }
    finally:
        cur.close()
        conn.close()
