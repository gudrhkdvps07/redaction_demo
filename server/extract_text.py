import fitz  # PyMuPDF
from typing import Dict, Any
from server import doc_redactor, hwp_redactor, ppt_redactor, xls_extractor

def _is_pdf(name: str, ctype: str) -> bool:
    return name.endswith(".pdf") or "pdf" in ctype

def _is_doc(name: str, ctype: str) -> bool:
    return name.endswith(".doc") or "msword" in ctype

def _is_xls(name: str, ctype: str) -> bool:
    # 브라우저에 따라 application/vnd.ms-excel 등으로 올라옴
    return name.endswith(".xls") or "excel" in ctype

def _is_hwp(name: str, ctype: str) -> bool:
    return name.endswith(".hwp") or "hwp" in ctype

def _is_ppt(name: str, ctype: str) -> bool:
    return name.endswith(".ppt") or ("powerpoint" in ctype and not name.endswith("x"))

async def extract_text_from_file(file) -> Dict[str, Any]:
    data = await file.read()
    name = (getattr(file, "filename", "") or "").lower()
    ctype = (getattr(file, "content_type", "") or "").lower()

    if _is_pdf(name, ctype):
        pages, full = [], []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for i, page in enumerate(doc, start=1):
                txt = page.get_text("text") or ""
                pages.append({"page": i, "text": txt})
                full.append(f"===== [Page {i}] =====\n{txt}")
        return {"full_text": "\n".join(full), "pages": pages}

    if _is_doc(name, ctype):
        return doc_redactor.extract_text(data)

    if _is_xls(name, ctype):
        return xls_extractor.extract_text_from_xls(data)

    if _is_hwp(name, ctype):
        return hwp_redactor.extract_text(data)

    if _is_ppt(name, ctype):
        return ppt_redactor.extract_text(data)

    # TXT 등
    if ctype.startswith("text/") or name.endswith(".txt"):
        try:
            t = data.decode("utf-8", errors="ignore")
        except Exception:
            t = data.decode("cp949", errors="ignore")
        return {"full_text": t, "pages": [{"page": 1, "text": t}]}

    raise ValueError("지원하지 않는 파일 형식")
