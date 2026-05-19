"""
Lab test interpretation route — upload PDF, extract, interpret, explain.
Ported from features/lab_test/main.py.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.lab_test.pdf_reader import extract_text_from_pdf
from services.lab_test.extractor import extract_lab_values
from services.lab_test.interpreter import interpret
from services.lab_test.explainer import explain_flagged_results

router = APIRouter(prefix="/lab", tags=["Lab Test"])


@router.post("/interpret")
async def lab_interpret(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()

    raw_text = extract_text_from_pdf(file_bytes)

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from the uploaded PDF.")

    extracted_tests = extract_lab_values(raw_text)

    all_results = interpret(extracted_tests)

    flagged = [
        r for r in all_results
        if r["flag"] not in ("NORMAL", "NOT_FOUND")
    ]

    explanations = explain_flagged_results(flagged)

    for result in all_results:
        result["explanation"] = explanations.get(result["test_name"])

    return {"results": all_results}
