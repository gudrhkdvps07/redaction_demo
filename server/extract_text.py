# extract_pdf_text.py
# ------------------------------------------------------------
# 일반 PDF(텍스트 레이어 있는 PDF)에서 텍스트만 추출
# - PyMuPDF(fitz)만 사용
# - 페이지별 텍스트와 합쳐진 전체 텍스트를 반환
# ------------------------------------------------------------
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import fitz  # PyMuPDF

@dataclass
class PageText:
    page_number: int   # 1-based
    text: str          # 해당 페이지 텍스트

@dataclass
class PDFTextResult:
    full_text: str
    pages: List[PageText]

def extract_pdf_text(pdf_path: str) -> PDFTextResult:
    """
    텍스트 레이어가 존재하는 일반 PDF에서 텍스트를 추출한다.
    스캔 PDF(이미지 기반)는 빈 문자열이 나올 수 있음.
    """
    doc = fitz.open(pdf_path)
    pages: List[PageText] = []

    for i in range(len(doc)):
        page = doc[i]
        # "text" 모드는 줄바꿈/레이아웃을 어느 정도 반영
        txt = page.get_text("text") or ""
        pages.append(PageText(page_number=i + 1, text=txt))

    # 페이지 구분 표시를 넣어 전체 문자열 합치기
    full = []
    for p in pages:
        full.append(f"\n\n===== [Page {p.page_number}] =====\n{p.text}")
    full_text = "".join(full).lstrip()

    return PDFTextResult(full_text=full_text, pages=pages)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Plain PDF text extractor (no OCR).")
    ap.add_argument("pdf", help="Path to PDF file")
    ap.add_argument("--preview", type=int, default=2000, help="Number of chars to preview")
    args = ap.parse_args()

    res = extract_pdf_text(args.pdf)
    print(res.full_text[:args.preview])
    print(f"\n[INFO] pages={len(res.pages)}")
