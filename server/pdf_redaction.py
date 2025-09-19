import re, io, fitz
from typing import List, Tuple
from .schemas import Box, PatternItem

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
        if not chunk: continue
        x0 = min(w[0] for w in chunk); y0 = min(w[1] for w in chunk)
        x1 = max(w[2] for w in chunk); y1 = max(w[3] for w in chunk)
        rects.append(fitz.Rect(x0, y0, x1, y1))
    return rects

def normalize_dash(s: str) -> str:
    """유니코드 dash 문자를 일반 하이픈(-)으로 통일"""
    return (
        s.replace("‐", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )

def _find_pattern_rects_on_page(page: fitz.Page, comp: re.Pattern, pattern_name: str):
    results = []

    # -----------------------------
    # 카드번호 처리 (토큰 기반)
    # -----------------------------
    if pattern_name == "card":
        words = page.get_text("words")  # (x0, y0, x1, y1, text, block, line, word)
        if not words:
            return []

        for w in words:
            token = normalize_dash(w[4])
            if comp.fullmatch(token):
                r = fitz.Rect(w[0], w[1], w[2], w[3])
                results.append((r, token, pattern_name))
        return results

    # -----------------------------
    # 일반 규칙 처리
    # -----------------------------
    words = page.get_text("words")
    if not words:
        return []

    tokens = [w[4] for w in words]
    joined = " ".join(tokens)

    acc = 0
    for m in comp.finditer(joined):
        matched = m.group(0)
        start_char, end_char = m.start(), m.end()
        start_idx = end_idx = None
        for i, t in enumerate(tokens):
            if i > 0:
                acc += 1  # 공백
            token_start, token_end = acc, acc + len(t)
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
    boxes = []
    compiled = [(_compile_pattern(p), p.name) for p in patterns]
    for pno in range(len(doc)):
        page = doc.load_page(pno)
        for comp, pname in compiled:
            rects = _find_pattern_rects_on_page(page, comp, pname)
            for r, matched, pname in rects:
                boxes.append(Box(
                    page=pno, x0=float(r.x0), y0=float(r.y0),
                    x1=float(r.x1), y1=float(r.y1),
                    matched_text=matched, pattern_name=pname
                ))
    doc.close()
    return boxes

def apply_redaction(pdf_bytes: bytes, boxes: List[Box], fill="black") -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    color = (0,0,0) if fill=="black" else (1,1,1)
    by_page = {}
    for b in boxes: by_page.setdefault(b.page, []).append(b)

    for pno, page_boxes in by_page.items():
        page = doc.load_page(pno)
        for b in page_boxes:
            rect = fitz.Rect(b.x0,b.y0,b.x1,b.y1)
            page.add_redact_annot(rect, fill=color)
        page.apply_redactions()
    out = io.BytesIO(); doc.save(out); doc.close()
    return out.getvalue()
