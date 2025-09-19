import fitz  # PyMuPDF

def extract_pdf_text(data: bytes) -> dict:
    """PDF 바이트에서 페이지별 텍스트 추출"""
    pages = []
    full = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for i, page in enumerate(doc, start=1):
            txt = page.get_text("text") or ""
            pages.append({"page": i, "text": txt})
            full.append(f"===== [Page {i}] =====\n{txt}")
    return {"full_text": "\n".join(full), "pages": pages}


async def extract_text_from_file(file) -> dict:
    """
    UploadFile 받아서 PDF만 처리
    """
    data = await file.read()
    name = (getattr(file, "filename", "") or "").lower()

    if not name.endswith(".pdf"):
        raise ValueError("PDF 파일만 지원합니다.")

    return extract_pdf_text(data)
