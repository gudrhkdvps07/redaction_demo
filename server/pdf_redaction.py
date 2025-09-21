import re, io, fitz, logging
from typing import List, Tuple
from .schemas import Box, PatternItem

# ==========================
# 로깅 설정
# ==========================
logger = logging.getLogger("redaction")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def _compile_pattern(p: PatternItem) -> re.Pattern:
    flags = 0 if p.case_sensitive else re.IGNORECASE
    pattern = p.regex
    if p.whole_word:
        pattern = rf"\b(?:{pattern})\b"
    logger.debug("Compiling pattern: %s -> %s", p.name, pattern)
    return re.compile(pattern, flags)


def _word_spans_to_rect(words: List[tuple], spans: List[Tuple[int, int]]) -> List[fitz.Rect]:
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
    results = []
    words = page.get_text("words")
    if not words:
        return []

    tokens = [w[4] for w in words]

    # -----------------------------
    # 카드번호 처리 (토큰 기반 재조립 + 숫자만 추출)
    # -----------------------------
    if pattern_name == "card":
        buf = ""
        spans = []
        for i, t in enumerate(tokens):
            if re.fullmatch(r"[\d\- ]+", t):  # 숫자/하이픈/공백
                if not buf:
                    start = i
                buf += t
                spans.append(i)
            else:
                if buf:
                    candidate = re.sub(r"\D", "", buf)  # 숫자만 추출
                    if comp.fullmatch(candidate):
                        rects = _word_spans_to_rect(words, [(start, spans[-1] + 1)])
                        for r in rects:
                            results.append((r, buf, pattern_name))
                            logger.debug("[CARD MATCH] page=%d matched='%s' rect=%s",
                                        page.number, buf, r)
                    buf = ""
                    spans = []
        # 마지막 버퍼 처리
        if buf:
            candidate = re.sub(r"\D", "", buf)
            if comp.fullmatch(candidate):
                rects = _word_spans_to_rect(words, [(start, spans[-1] + 1)])
                for r in rects:
                    results.append((r, buf, pattern_name))
                    logger.debug("[CARD MATCH] page=%d matched='%s' rect=%s",
                                page.number, buf, r)
        logger.debug("[RESULT] page=%d pattern=card found=%d", page.number, len(results))
        return results

    # -----------------------------
    # 일반 규칙 처리
    # -----------------------------
    joined = " ".join(tokens)
    acc = 0
    for m in comp.finditer(joined):
        matched = m.group(0)
        logger.debug("[MATCH] page=%d pattern=%s matched='%s'", page.number, pattern_name, matched)
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
    logger.debug("[RESULT] page=%d pattern=%s found=%d", page.number, pattern_name, len(results))
    return results


def detect_boxes_from_patterns(pdf_bytes: bytes, patterns: List[PatternItem]) -> List[Box]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    boxes = []
    compiled = [(_compile_pattern(p), p.name) for p in patterns]
    for pno in range(len(doc)):
        page = doc.load_page(pno)
        logger.debug("Scanning page %d...", pno)
        for comp, pname in compiled:
            rects = _find_pattern_rects_on_page(page, comp, pname)
            for r, matched, pname in rects:
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
                logger.debug("→ Box added: %s | text='%s'", pname, matched)
    doc.close()
    logger.debug("Total boxes detected: %d", len(boxes))
    return boxes


def apply_redaction(pdf_bytes: bytes, boxes: List[Box], fill="black") -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    color = (0, 0, 0) if fill == "black" else (1, 1, 1)
    by_page = {}
    for b in boxes:
        by_page.setdefault(b.page, []).append(b)

    for pno, page_boxes in by_page.items():
        page = doc.load_page(pno)
        logger.debug("Applying redactions on page %d (count=%d)", pno, len(page_boxes))
        for b in page_boxes:
            rect = fitz.Rect(b.x0, b.y0, b.x1, b.y1)
            logger.debug("  → Redact box: %s | text='%s'", rect, b.matched_text)
            page.add_redact_annot(rect, fill=color)
        page.apply_redactions()

    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()
