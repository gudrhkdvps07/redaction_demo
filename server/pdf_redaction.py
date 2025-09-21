# pdf_redaction.py
import re
import io
import fitz
from typing import List, Tuple, Optional
from .schemas import Box, PatternItem
from .redac_rules import RULES  # validator 사용


# --------------------------
# 내부 유틸
# --------------------------
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


def _search_exact_bbox(page: fitz.Page, text: str, hint_rect: Optional[fitz.Rect] = None) -> Optional[fitz.Rect]:
    try:
        hits = page.search_for(text)  # List[Rect]
    except Exception:
        hits = []
    if not hits:
        return None
    if hint_rect is None:
        return hits[0]

    best, best_iou = None, -1.0
    for r in hits:
        inter = fitz.Rect(
            max(hint_rect.x0, r.x0),
            max(hint_rect.y0, r.y0),
            min(hint_rect.x1, r.x1),
            min(hint_rect.y1, r.y1),
        )
        if inter.x1 <= inter.x0 or inter.y1 <= inter.y0:
            iou = 0.0
        else:
            inter_a = (inter.x1 - inter.x0) * (inter.y1 - inter.y0)
            union_a = (hint_rect.get_area() + r.get_area() - inter_a) or 1.0
            iou = inter_a / union_a
        if iou > best_iou:
            best, best_iou = r, iou
    return best or hits[0]


def _find_pattern_rects_on_page(page: fitz.Page, comp: re.Pattern, pattern_name: str):
    results = []
    words = page.get_text("words")
    if not words:
        return []

    tokens = [w[4] for w in words]

    # -----------------------------
    # 카드번호 처리
    # -----------------------------
    if pattern_name == "card":
        buf = ""
        spans: List[int] = []
        start_idx: Optional[int] = None

        for i, t in enumerate(tokens):
            if re.fullmatch(r"[\d\- ]+", t):
                if start_idx is None:
                    start_idx = i
                buf += t
                spans.append(i)
            else:
                if buf:
                    candidate = re.sub(r"\D", "", buf)
                    if comp.fullmatch(candidate):
                        rects = _word_spans_to_rect(words, [(start_idx, spans[-1] + 1)])
                        for r in rects:
                            results.append((r, buf, pattern_name))
                    buf = ""
                    spans = []
                    start_idx = None

        if buf:
            candidate = re.sub(r"\D", "", buf)
            if comp.fullmatch(candidate):
                rects = _word_spans_to_rect(words, [(start_idx, spans[-1] + 1)])
                for r in rects:
                    results.append((r, buf, pattern_name))

        return results

    # -----------------------------
    # 일반 규칙 처리 (이메일은 search_for 사용)
    # -----------------------------
    joined = " ".join(tokens)
    acc = 0
    for m in comp.finditer(joined):
        matched = m.group(0)
        start_char, end_char = m.start(), m.end()
        start_idx = end_idx = None

        acc = 0
        for i, t in enumerate(tokens):
            if i > 0:
                acc += 1
            token_start, token_end = acc, acc + len(t)
            if token_end > start_char and token_start < end_char:
                if start_idx is None:
                    start_idx = i
                end_idx = i + 1
            acc += len(t)
        if start_idx is None or end_idx is None:
            continue

        if pattern_name == "email":
            hint_rects = _word_spans_to_rect(words, [(start_idx, end_idx)])
            hint = hint_rects[0] if hint_rects else None
            exact = _search_exact_bbox(page, matched, hint)
            if exact:
                results.append((exact, matched, pattern_name))
                continue
            for r in hint_rects:
                results.append((r, matched, pattern_name))
            continue

        rects = _word_spans_to_rect(words, [(start_idx, end_idx)])
        for r in rects:
            results.append((r, matched, pattern_name))

    return results


# --------------------------
# 공개 함수
# --------------------------
def detect_boxes_from_patterns(pdf_bytes: bytes, patterns: List[PatternItem]) -> List[Box]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    boxes: List[Box] = []

    compiled = [(_compile_pattern(p), p.name) for p in patterns]

    for pno in range(len(doc)):
        page = doc.load_page(pno)
        for comp, pname in compiled:
            rects = _find_pattern_rects_on_page(page, comp, pname)

            validator = None
            rule = RULES.get(pname)
            if rule:
                validator = rule.get("validator")

            for r, matched, _pname in rects:
                is_ok = True
                if callable(validator):
                    try:
                        is_ok = bool(validator(matched))
                    except Exception:
                        is_ok = False

                if not is_ok:
                    continue

                boxes.append(
                    Box(
                        page=pno,
                        x0=float(r.x0),
                        y0=float(r.y0),
                        x1=float(r.x1),
                        y1=float(r.y1),
                        matched_text=matched,
                        pattern_name=pname,
                    )
                )

    doc.close()
    return boxes


def apply_redaction(pdf_bytes: bytes, boxes: List[Box], fill="black") -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    color = (0, 0, 0) if fill == "black" else (1, 1, 1)
    by_page = {}
    for b in boxes:
        by_page.setdefault(b.page, []).append(b)

    for pno, page_boxes in by_page.items():
        page = doc.load_page(pno)
        for b in page_boxes:
            rect = fitz.Rect(b.x0, b.y0, b.x1, b.y1)
            page.add_redact_annot(rect, fill=color)
        page.apply_redactions()

    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()
