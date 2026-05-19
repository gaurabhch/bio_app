"""
Lab test interpreter — compare user values against reference ranges.
Ported from features/lab_test/interpreter.py.
"""

import re
from services.lab_test.repository import get_pcos_tests, get_pregnancy_tests

ALIAS_MAP = {
    "lh": "Luteinizing Hormone (LH)",
    "fsh": "Follicle-Stimulating Hormone (FSH)",
    "amh": "Anti-Müllerian Hormone (AMH)",
    "beta-hcg": "Human Chorionic Gonadotropin (hCG)",
    "hcg": "Human Chorionic Gonadotropin (hCG)",
    "dheas": "DHEA-S",
    "dhea-s": "DHEA-S",
    "hpl": "Human Placental Lactogen (hPL)",
    "total testosterone": "Total Testosterone",
    "free testosterone": "Free Testosterone",
    "lh:fsh ratio": "LH:FSH Ratio",
    "lh/fsh ratio": "LH:FSH Ratio",
    "fasting insulin": "Fasting Insulin",
    "progesterone": "Progesterone",
    "estrogen": "Estrogen",
    "prolactin": "Prolactin",
    "androstenedione": "Androstenedione",
}

def normalize_name(raw_name: str) -> str:
    cleaned = raw_name.lower().strip()
    cleaned = re.sub(r"[^a-z0-9:\-/\s]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return ALIAS_MAP.get(cleaned, raw_name.strip())

def parse_threshold(threshold: str):
    if not threshold:
        return None, None
    threshold = threshold.strip()
    match = re.match(r"([<>]=?|=)\s*([\d.]+)", threshold)
    if match:
        return match.group(1), float(match.group(2))
    range_match = re.match(r"([\d.]+)\s*-\s*([\d.]+)", threshold)
    if range_match:
        return "range", (float(range_match.group(1)), float(range_match.group(2)))
    return None, None

def compare_value(user_value: str, threshold: str) -> str:
    qualitative_markers = ["rising", "increasing", "decreasing", "falling", "present", "absent"]
    if any(q in user_value.lower() for q in qualitative_markers):
        return "CHECK"
    try:
        numeric = float(re.sub(r"[^\d.]", "", user_value))
    except ValueError:
        return "UNIT_MISMATCH"
    operator, parsed = parse_threshold(threshold)
    if operator is None:
        return "UNIT_MISMATCH"
    if operator == "range":
        low, high = parsed
        if numeric < low:
            return "LOW"
        if numeric > high:
            return "HIGH"
        return "NORMAL"
    if operator == ">" and numeric > parsed:
        return "HIGH"
    if operator == ">=" and numeric >= parsed:
        return "HIGH"
    if operator == "<" and numeric < parsed:
        return "LOW"
    if operator == "<=" and numeric <= parsed:
        return "LOW"
    return "NORMAL"

def fuzzy_match(normalized: str, db_rows: list, name_key: str) -> dict | None:
    normalized_lower = normalized.lower()
    for row in db_rows:
        if row[name_key].lower() in normalized_lower or normalized_lower in row[name_key].lower():
            return row
    return None

def interpret(extracted_tests: list[dict]) -> list[dict]:
    pcos_rows = get_pcos_tests()
    pregnancy_rows = get_pregnancy_tests()

    pcos_index = {row["test_name"].lower(): row for row in pcos_rows}
    pregnancy_index = {row["hormone_name"].lower(): row for row in pregnancy_rows}

    results = []

    for test in extracted_tests:
        raw_name = test.get("test_name", "")
        user_value = str(test.get("value", "")).strip()
        unit = test.get("unit", "")

        normalized = normalize_name(raw_name)
        normalized_lower = normalized.lower()

        db_row = pcos_index.get(normalized_lower)
        row_type = "pcos"

        if not db_row:
            db_row = pregnancy_index.get(normalized_lower)
            row_type = "pregnancy"

        if not db_row:
            db_row = fuzzy_match(normalized, pcos_rows, "test_name")
            row_type = "pcos"

        if not db_row:
            db_row = fuzzy_match(normalized, pregnancy_rows, "hormone_name")
            row_type = "pregnancy"

        if not db_row:
            results.append({
                "test_name": raw_name,
                "user_value": user_value,
                "unit": unit,
                "normal_range": None,
                "flag": "NOT_FOUND",
                "condition": None,
                "abnormal_reason": None,
            })
            continue

        if row_type == "pcos":
            threshold = db_row.get("flag_threshold")
            normal_range = db_row.get("normal_range")
            condition = db_row.get("flag_condition", "PCOS")
            abnormal_reason = db_row.get("abnormal_reason")
            display_name = db_row.get("test_name")
        else:
            threshold = db_row.get("flag_value")
            normal_range = None
            condition = db_row.get("flag_condition", "Pregnancy")
            abnormal_reason = db_row.get("reason_for_change")
            display_name = db_row.get("hormone_name")

        flag = compare_value(user_value, threshold) if threshold else "NORMAL"

        show_reason = flag not in ("NORMAL", "NOT_FOUND")

        results.append({
            "test_name": display_name,
            "user_value": user_value,
            "unit": unit,
            "normal_range": normal_range,
            "flag": flag,
            "condition": condition,
            "abnormal_reason": abnormal_reason if show_reason else None,
        })

    return results
