import fitz  # PyMuPDF
from server import doc_redactor, hwp_redactor, ppt_redactor

def extract_pdf_text(data: bytes) -> dict:
    pages, full = [], []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for i, page in enumerate(doc, start=1):
            txt = page.get_text("text") or ""
            pages.append({"page": i, "text": txt})
            full.append(f"===== [Page {i}] =====\n{txt}")
    return {"full_text": "\n".join(full), "pages": pages}

async def extract_text_from_file(file) -> dict:
    data = await file.read()
    name = (getattr(file, "filename", "") or "").lower()
    ctype = (getattr(file, "content_type", "") or "").lower()

    if name.endswith(".pdf") or ctype == "application/pdf":
        return extract_pdf_text(data)
    if name.endswith(".txt") or ctype.startswith("text/"):
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = data.decode("cp949", errors="ignore")
        return {"full_text": text, "pages": [{"page": 1, "text": text}]}
    if name.endswith(".doc"):
        return doc_redactor.extract_text(data)
    if name.endswith(".hwp"):
        return hwp_redactor.extract_text(data)
    if name.endswith(".ppt"):
        return ppt_redactor.extract_text(data)

    raise ValueError("지원하지 않는 파일 형식")
