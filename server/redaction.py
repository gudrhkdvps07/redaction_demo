# server/redaction.py
import io
import re
from typing import List, Tuple
import fitz  # PyMuPDF

from .schemas import Box, PatternItem
from .validators import is_valid_rrn_date_only  # 네 파일에 없으면 주석처리해도 됨

def _compile_pattern(p: PatternItem) -> re.Pattern:
    flags = 0 if p.case_sensitive else re.IGNORECASE
    pattern = p.regex
    if p.whole_word:
        pattern = rf"\b(?:{pattern})\b"
    return re.compile(pattern, flags)

def _word_spans_to_rect(words: List[tuple], spans: List[Tuple[int,int]]) -> List[fitz.Rect]:
    rects = []
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
        spans = []
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

def detect_boxes_from_patterns(pdf_bytes: bytes, patterns: List[PatternItem]) -> List[Box]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    boxes: List[Box] = []
    compiled = [(_compile_pattern(p), p.name) for p in patterns]

    for pno in range(len(doc)):
        page = doc.load_page(pno)
        for comp, pname in compiled:
            rects = _find_pattern_rects_on_page(page, comp, pname)
            for r, matched, pattern_name in rects:
                # 주민번호는 날짜 유효성으로 오탐 낮추기(없으면 제거해도 됨)
                if pattern_name == "rrn":
                    try:
                        if not is_valid_rrn_date_only(matched):
                            continue
                    except Exception:
                        pass
                boxes.append(Box(
                    page=pno, x0=float(r.x0), y0=float(r.y0), x1=float(r.x1), y1=float(r.y1),
                    matched_text=matched, pattern_name=pattern_name
                ))
    doc.close()
    return boxes

def apply_redaction(pdf_bytes: bytes, boxes: List[Box], fill: str = "black") -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for b in boxes:
        page = doc.load_page(b.page)
        rect = fitz.Rect(b.x0, b.y0, b.x1, b.y1)
        page.add_redact_annot(rect, fill=(0,0,0) if fill == "black" else (1,1,1))
    doc.apply_redactions()
    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()
