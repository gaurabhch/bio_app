"""
Lifestyle tip provider — uses Groq LLM to generate personalised tips and a daily task.
"""

import os
import json
from groq import Groq

from schemas.lifestyle import TipCard
from core.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


def generate_tips_and_task(symptoms: dict) -> tuple[list[TipCard], str]:

    logged_lines = [
        f"- {key.replace('_', ' ').title()}: {value}"
        for key, value in symptoms.items()
        if value not in (None, "", [])
    ]
    symptom_summary = "\n".join(logged_lines) if logged_lines else "- No specific symptoms logged."

    prompt = f"""You are a compassionate women's health assistant inside an app called Biocanvas.
The app helps women track PCOS and pregnancy-related symptoms daily.

A user has logged the following symptoms today:
{symptom_summary}

Based ONLY on these symptoms, return a JSON object in this exact structure:
{{
  "tips": [
    {{"icon": "<single emoji>", "headline": "<max 5 words>", "description": "<1-2 warm, practical sentences>"}},
    {{"icon": "<single emoji>", "headline": "<max 5 words>", "description": "<1-2 warm, practical sentences>"}},
    {{"icon": "<single emoji>", "headline": "<max 5 words>", "description": "<1-2 warm, practical sentences>"}}
  ],
  "task": "<one specific, achievable action the user can complete today — max 20 words>"
}}

Rules:
- Tips must be directly personalised to the symptoms above — not generic.
- Cover different dimensions across the 3 tips (nutrition, movement, mental wellbeing).
- Task must be concrete: not "rest more" but "lie down for 20 minutes after lunch".
- Tone: warm, non-clinical, encouraging. No scary medical language.
- Return ONLY raw JSON. No markdown fences, no extra text.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.7,
    )

    data = json.loads(response.choices[0].message.content.strip())
    tips = [TipCard(**tip) for tip in data["tips"]]
    task_description: str = data["task"]

    return tips, task_description
