"""
Prediction service — symptom prediction based on historical cycle data.
Ported from features/app (1_2)/prediction.py.
"""

import json
import os
import re
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import date, timedelta
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from core.database import get_psycopg2_connection

router = APIRouter(prefix="/predictions", tags=["Predictions"])


class GenerateRequest(BaseModel):
    user_id: str
    last_period_date: date


def fetch_logs(user_id: str, last_period_date: date):
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        # Look at PREVIOUS cycles only (before current cycle started)
        window_start = last_period_date - timedelta(days=90)
        window_end = last_period_date - timedelta(days=1)

        cur.execute(
            """SELECT date, symptoms FROM daily_logs
               WHERE user_id = %s AND date BETWEEN %s AND %s
               ORDER BY date ASC""",
            (user_id, window_start, window_end)
        )
        rows = cur.fetchall()
        return [{"date": row[0], "symptoms": row[1]} for row in rows]
    finally:
        cur.close()
        conn.close()


def group_by_cycle_day(logs: list, cycle_length: int = 28) -> dict:
    """
    Groups logs by cycle day using modular arithmetic.
    This correctly maps Jan/Feb/Mar cycle days to the same slot (e.g. all cycle day 1s align).
    """
    grouped = {}
    for entry in logs:
        log_date = entry["date"]
        symptoms = entry["symptoms"]

        # Calculate cycle day using modular arithmetic relative to a fixed epoch
        days_since_epoch = (log_date - date(2000, 1, 1)).days
        cycle_day = (days_since_epoch % cycle_length) + 1

        if cycle_day not in grouped:
            grouped[cycle_day] = []
        grouped[cycle_day].append(symptoms)

    return grouped


def detect_patterns(grouped, current_cycle_day, cycle_length=28):
    raw_predictions = []

    for cycle_day, symptom_list in grouped.items():

        # ─────────────────────────────────────────────
        # WINDOW FIX: handle wrap-around past day 28
        # e.g. current_cycle_day=26, cycle_day=1 means
        # day 1 of NEXT cycle = 28-26+1 = 3 days away
        # ─────────────────────────────────────────────
        if cycle_day > current_cycle_day:
            days_until = cycle_day - current_cycle_day
        else:
            # cycle_day has wrapped to next cycle
            days_until = (cycle_length - current_cycle_day) + cycle_day

        if not (1 <= days_until <= 7):
            continue

        total = len(symptom_list)
        field_counts = {}
        for symptoms in symptom_list:
            for key, val in symptoms.items():
                if isinstance(val, list):
                    for item in val:
                        k = f"{key}:{item}"
                        field_counts[k] = field_counts.get(k, 0) + 1
                else:
                    k = f"{key}:{val}"
                    field_counts[k] = field_counts.get(k, 0) + 1

        for symptom_key, count in field_counts.items():
            frequency = count / total

            # ─────────────────────────────────────────
            # CONFIDENCE LOGIC — this is where it lives
            # frequency >= 0.6 → LIKELY   (seen in 60%+ of past cycles)
            # frequency >= 0.4 → POSSIBLE (seen in 40-59% of past cycles)
            # below 0.4        → ignored
            # ─────────────────────────────────────────
            if frequency >= 0.6:
                confidence = "LIKELY"
            elif frequency >= 0.4:
                confidence = "POSSIBLE"
            else:
                continue  # skip low-frequency symptoms

            raw_predictions.append({
                "symptom": symptom_key,
                "predicted_cycle_day": cycle_day,
                "frequency": round(frequency, 2),
                "days_until": days_until,
                "confidence": confidence
            })

    return raw_predictions

def rewrite_with_llm(raw_predictions):
    if not raw_predictions:
        return []

    client = ChatGroq(
        api_key=os.environ.get("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile"
    )

    system_prompt = (
        "You are a warm health companion in a women's health app. "
        "Rewrite each prediction in one warm friendly sentence. "
        "Never suggest diagnoses or medications. "
        "Return only a valid JSON array of objects with keys: symptom, human_message. "
        "No trailing commas. No markdown. No extra text."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(raw_predictions))
    ]

    response = client.invoke(messages)
    raw_text = response.content.strip()

    # Strip markdown fences if present
    raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
    raw_text = re.sub(r'\s*```$', '', raw_text)

    # Remove trailing commas before } or ]
    raw_text = re.sub(r',\s*([\]}])', r'\1', raw_text)

    try:
        llm_output = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if match:
            cleaned = re.sub(r',\s*([\]}])', r'\1', match.group())
            try:
                llm_output = json.loads(cleaned)
            except json.JSONDecodeError:
                llm_output = []
        else:
            llm_output = []

    llm_map = {item["symptom"]: item["human_message"] for item in llm_output}
    for pred in raw_predictions:
        pred["human_message"] = llm_map.get(pred["symptom"], "")

    return raw_predictions


def save_predictions(user_id: str, predicted_for_date: date, predictions: list, cycles_analysed: int):
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO symptom_predictions (user_id, predicted_for_date, predictions, cycles_analysed)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, predicted_for_date)
            DO UPDATE SET predictions = EXCLUDED.predictions,
                          cycles_analysed = EXCLUDED.cycles_analysed,
                          generated_at = NOW()
            """,
            (user_id, predicted_for_date, json.dumps(predictions), cycles_analysed)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def fetch_descriptions(raw_predictions: list) -> list:
    """
    Queries PGVector table using symptom_name as a metadata filter.
    Attaches the pre-written description to each detected prediction.
    """
    if not raw_predictions:
        return raw_predictions

    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        # Extract all detected symptom keys
        symptom_keys = [pred["symptom"] for pred in raw_predictions]

        # Metadata filter: WHERE symptom_name IN (detected symptoms)
        cur.execute(
            """
            SELECT symptom_name, description
            FROM symptom_descriptions
            WHERE symptom_name = ANY(%s)
            """,
            (symptom_keys,)
        )
        rows = cur.fetchall()

        # Build a lookup map: symptom_name → description
        description_map = {row[0]: row[1] for row in rows}

        # Attach description to each prediction
        for pred in raw_predictions:
            pred["human_message"] = description_map.get(
                pred["symptom"],
                "Our research team is preparing a description for this symptom."  # fallback
            )

        return raw_predictions
    finally:
        cur.close()
        conn.close()


@router.post("/generate")
def generate_predictions(payload: GenerateRequest):
    current_cycle_day = (date.today() - payload.last_period_date).days + 1

    logs = fetch_logs(payload.user_id, payload.last_period_date)
    if not logs:
        return {"predictions": [], "message": "No logs found in previous cycles."}

    grouped = group_by_cycle_day(logs)
    raw = detect_patterns(grouped, current_cycle_day)
    final = fetch_descriptions(raw)
    # final = rewrite_with_llm(raw)

    save_predictions(
        user_id=str(payload.user_id),
        predicted_for_date=date.today(),
        predictions=final,
        cycles_analysed=len(set(
            (entry["date"] - date(2000, 1, 1)).days // 28 for entry in logs
        ))
    )
    return {"predictions": final, "current_cycle_day": current_cycle_day}


@router.get("/latest")
def get_latest_predictions(user_id: str):
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, user_id, predicted_for_date, predictions, cycles_analysed, generated_at
            FROM symptom_predictions
            WHERE user_id = %s
            ORDER BY generated_at DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return {"prediction": None}
        return {
            "prediction": {
                "id": str(row[0]),
                "user_id": str(row[1]),
                "predicted_for_date": str(row[2]),
                "predictions": row[3],
                "cycles_analysed": row[4],
                "generated_at": str(row[5])
            }
        }
    finally:
        cur.close()
        conn.close()
