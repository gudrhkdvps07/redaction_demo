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

# === add this wrapper ===
import mimetypes

async def extract_text_from_file(file) -> dict:
    """
    UploadFile를 받아서 확장자/컨텐트타입 보고 PDF/TXT 분기.
    FastAPI 의존 줄이려고 타입힌트는 느슨하게 둠.
    """
    data = await file.read()
    name = (getattr(file, "filename", "") or "").lower()
    ctype = (getattr(file, "content_type", "") or "").lower()
    if not ctype and name:
        guessed, _ = mimetypes.guess_type(name)
        ctype = (guessed or "").lower()

    # PDF 판별
    if name.endswith(".pdf") or "pdf" in ctype:
        return extract_pdf_text(data)

    # TXT 판별(그 외에는 기본 TXT로 시도)
    if name.endswith(".txt") or ctype.startswith("text/"):
        return extract_txt_text(data)

    # 미지정이면 안전하게 TXT 시도
    try:
        return extract_txt_text(data)
    except Exception:
        raise ValueError(f"Unsupported file type: name={name}, content_type={ctype}")
