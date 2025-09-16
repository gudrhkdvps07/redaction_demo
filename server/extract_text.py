from __future__ import annotations
from typing import Dict, Any
import fitz  # PyMuPDF

def extract_pdf_text(file_bytes: bytes) -> Dict[str, Any]:
    pages = []; full_parts = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            pages.append({"page": i, "text": text})
            full_parts.append(f"\n\n===== [Page {i}] =====\n{text}")
    return {"full_text": "".join(full_parts).lstrip(), "pages": pages}

def extract_txt_text(file_bytes: bytes, encoding: str = "utf-8") -> Dict[str, Any]:
    text = file_bytes.decode(encoding, errors="ignore")
    return {"full_text": text, "pages": [{"page": 1, "text": text}]}
