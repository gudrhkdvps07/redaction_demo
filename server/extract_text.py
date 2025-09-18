import fitz  # PyMuPDF
import mimetypes

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

def extract_txt_text(data: bytes, encoding: str | None = None) -> dict:
    """TXT 바이트에서 텍스트 디코드"""
    if encoding:
        text = data.decode(encoding, errors="ignore")
    else:
        # 간단 전략: UTF-8 우선
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="ignore")
    return {"full_text": text, "pages": [{"page": 1, "text": text}]}

# === FastAPI 업로드 파일 래퍼 ===
async def extract_text_from_file(file) -> dict:
    """
    UploadFile 받아서 PDF/TXT 자동 분기
    """
    data = await file.read()
    name = (getattr(file, "filename", "") or "").lower()
    ctype = (getattr(file, "content_type", "") or "").lower()
    if not ctype and name:
        guessed, _ = mimetypes.guess_type(name)
        ctype = (guessed or "").lower()

    if name.endswith(".pdf") or "pdf" in ctype:
        return extract_pdf_text(data)
    if name.endswith(".txt") or ctype.startswith("text/"):
        return extract_txt_text(data)

    # 확실치 않으면 TXT 시도
    try:
        return extract_txt_text(data)
    except Exception as e:
        raise ValueError(f"Unsupported file type: name={name}, content_type={ctype}") from e
