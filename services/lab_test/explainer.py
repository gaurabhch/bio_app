"""
Lab test explainer — uses Groq LLM to generate patient-friendly explanations.
Ported from features/lab_test/explainer.py.
"""

import json
from groq import Groq

from core.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = (
    "You are a warm health companion in a women's health app. "
    "For each flagged test result, write one short paragraph explaining "
    "what this result means, what symptoms it might explain, and what the user should do next. "
    "Never diagnose. Never recommend specific medication. "
    "Always end each explanation with: consult your doctor for a full assessment. "
    "Use the medical_context provided. Write in plain, warm language."
)

EXPLANATION_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "test_name": {"type": "string"},
                    "explanation": {"type": "string"}
                },
                "required": ["test_name", "explanation"],
                "additionalProperties": False
            }
        }
    },
    "required": ["items"],
    "additionalProperties": False
}

def explain_flagged_results(flagged_results: list[dict]) -> dict[str, str]:
    if not flagged_results:
        return {}

    payload = []
    for r in flagged_results:
        payload.append({
            "test_name": r["test_name"],
            "user_value": r["user_value"],
            "unit": r["unit"],
            "flag": r["flag"],
            "normal_range": r.get("normal_range"),
            "condition": r["condition"],
            "medical_context": r.get("abnormal_reason"),
        })

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, indent=2)}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "lab_explanations",
                "strict": True,
                "schema": EXPLANATION_SCHEMA
            }
        }
    )

    text = response.choices[0].message.content or "{}"
    parsed = json.loads(text)

    return {
        item["test_name"]: item["explanation"]
        for item in parsed.get("items", [])
    }
