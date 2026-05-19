"""
PDF reader — extract text from uploaded PDF lab reports.
Ported from features/lab_test/pdf_reader.py.
"""

import pdfplumber


def extract_text_from_pdf(file_bytes: bytes) -> str:
    import io
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "".join(pages).strip()
