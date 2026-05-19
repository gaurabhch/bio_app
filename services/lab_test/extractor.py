"""
Lab value extractor — uses Groq LLM to extract test results from PDF text.
Ported from features/lab_test/extractor.py.
"""

import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

model = ChatGroq(model="openai/gpt-oss-120b")

EXTRACTION_PROMPT = (
    "Extract every lab test from this report. Return only a JSON array.\n"
    "Each object must have exactly three keys: test_name, value, unit.\n"
    "Do not explain. Do not interpret. Only extract.\n\n"
)


def extract_lab_values(raw_text: str) -> list[dict]:
    response = model.invoke([HumanMessage(content=EXTRACTION_PROMPT + raw_text)])
    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())
