# server/redaction.py
import io
import re
from typing import List, Tuple, Dict
import fitz  # PyMuPDF

from .schemas import Box, PatternItem
from .validators import is_valid_rrn_date_only 

# -----------------------------
# 패턴 컴파일 / 좌표 검출 유틸
# -----------------------------
def _compile_pattern(p: PatternItem) -> re.Pattern:
    flags = 0 if p.case_sensitive else re.IGNORECASE
    pattern = p.regex
    if p.whole_word:
        pattern = rf"\b(?:{pattern})\b"
    return re.compile(pattern, flags)

def _word_spans_to_rect(words: List[tuple], spans: List[Tuple[int, int]]) -> List[fitz.Rect]:
    rects: List[fitz.Rect] = []
    for s, e in spans:
        chunk = words[s:e]
        if not chunk:
            continue
        x0 = min(w[0] for w in chunk)
        y0 = min(w[1] for w in chunk)
        x1 = max(w[2] for w in chunk)
        y1 = max(w[3] for w in chunk)
        rects.append(fitz.Rect(x0, y0, x1, y1))
    return rects

def _find_pattern_rects_on_page(page: fitz.Page, comp: re.Pattern, pattern_name: str):
    """
    페이지에서 단어 토큰을 공백으로 join하여 정규식 검색 후,
    문자 오프셋을 단어 인덱스 범위로 근사 매핑 → Rect 산출.
    """
    words = page.get_text("words")  # (x0,y0,x1,y1, text, block, line, word)
    if not words:
        return []

    tokens = [w[4] for w in words]
    joined = " ".join(tokens)

    results = []
    for m in comp.finditer(joined):
        matched = m.group(0)
        start_char, end_char = m.start(), m.end()

        # char 오프셋 -> 토큰 범위 근사 매핑
        spans: List[Tuple[int, int]] = []
        acc = 0
        start_idx = None
        end_idx = None
        for i, t in enumerate(tokens):
            if i > 0:
                acc += 1  # 공백
            token_start = acc
            token_end = acc + len(t)
            if token_end > start_char and token_start < end_char:
                if start_idx is None:
                    start_idx = i
                end_idx = i + 1
            acc += len(t)

        if start_idx is not None and end_idx is not None:
            rects = _word_spans_to_rect(words, [(start_idx, end_idx)])
            for r in rects:
                results.append((r, matched, pattern_name))
    return results

# -----------------------------
# 공개 함수: 박스 검출 / 레닥션
# -----------------------------
def detect_boxes_from_patterns(pdf_bytes: bytes, patterns: List[PatternItem]) -> List[Box]:
    """
    정규식 패턴들로 PDF 내 텍스트 좌표(Box) 검출.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    boxes: List[Box] = []
    compiled = [(_compile_pattern(p), p.name) for p in patterns]

    for pno in range(len(doc)):
        page = doc.load_page(pno)
        for comp, pname in compiled:
            rects = _find_pattern_rects_on_page(page, comp, pname)
            for r, matched, pattern_name in rects:
                # 주민번호는 날짜 유효성으로 오탐 낮춤 (선택)
                if pattern_name == "rrn":
                    try:
                        if not is_valid_rrn_date_only(matched):
                            continue
                    except Exception:
                        pass
                boxes.append(
                    Box(
                        page=pno,
                        x0=float(r.x0),
                        y0=float(r.y0),
                        x1=float(r.x1),
                        y1=float(r.y1),
                        matched_text=matched,
                        pattern_name=pattern_name,
                    )
                )
    doc.close()
    return boxes

def apply_redaction(pdf_bytes: bytes, boxes: List[Box], fill: str = "black") -> bytes:
    """
    검출된 Box 좌표에 레닥션 적용 후 PDF 바이너리 반환.
    - PyMuPDF에서는 '페이지' 단위로 apply_redactions() 호출해야 함.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # 페이지별로 박스 묶기
    by_page: Dict[int, List[Box]] = {}
    for b in boxes:
        by_page.setdefault(b.page, []).append(b)

    # 각 페이지 처리: 주석 추가 → 페이지에서 레닥션 적용
    for pno, blist in by_page.items():
        page = doc.load_page(pno)
        for b in blist:
            rect = fitz.Rect(b.x0, b.y0, b.x1, b.y1)
            page.add_redact_annot(
                rect,
                fill=(0, 0, 0) if fill == "black" else (1, 1, 1),
            )
        # 중요: 문서(doc)가 아니라 '페이지(page)'에서 적용
        page.apply_redactions()

    out = io.BytesIO()
    # 저장 최적화 옵션은 선택사항
    doc.save(out, deflate=True, garbage=4)
    doc.close()
    return out.getvalue()
