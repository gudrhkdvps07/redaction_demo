from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import re

from ..redac_rules import RULES
from ..normalize import normalize_text
from ..extract_text import extract_text_from_file

router = APIRouter(prefix="/v1/text", tags=["text"])

# ---------- 데이터 모델 ----------
class MatchRequest(BaseModel):
    text: str
    rules: Optional[List[str]] = None
    options: Optional[Dict[str, Any]] = None
    normalize: bool = True 

class MatchItem(BaseModel):
    rule: str
    value: str
    valid: bool
    index: int
    end: int
    context: str

class MatchResponse(BaseModel):
    counts: Dict[str, int]
    items: List[MatchItem]

# ---------- 헬퍼 ----------
def _ctx(text: str, start: int, end: int, window: int = 25) -> str:
    return text[max(0, start - window): start] + "【" + text[start:end] + "】" + text[end: end + window]

def _overlaps(a, b) -> bool:
    return a[0] < b[1] and b[0] < a[1]

def _mask_ranges_same_length(s: str, spans, mask_char: str = "R") -> str:
    if not spans: return s
    arr = list(s)
    L = len(arr)
    for st, ed in spans:
        st = max(0, min(st, L)); ed = max(0, min(ed, L))
        for i in range(st, ed):
            if arr[i].isdigit() or arr[i] in "- ":
                arr[i] = mask_char
    return "".join(arr)

# ---------- API ----------
@router.get("/rules")
async def list_rules():
    return list(RULES.keys())

@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    """PDF/TXT에서 텍스트 추출"""
    try:
        return await extract_text_from_file(file)
    except Exception as e:
        raise HTTPException(status_code=415, detail=str(e))

@router.post("/match", response_model=MatchResponse)
async def match(req: MatchRequest):
    # 1) 항상 정규화 (요청 토글 무시)
    original_text = normalize_text(req.text)
    working_text = original_text
    options = req.options or {}

    # 2) 우선순위
    default_order = ["rrn", "email", "phone_mobile", "phone_city", "bizno", "card"]
    selected = req.rules if req.rules else list(RULES.keys())
    ordered_rules = [r for r in default_order if r in selected]

    results: List[Dict[str, Any]] = []

    # 3) RRN 먼저 탐지 → 마스킹
    rrn_spans = []
    if "rrn" in ordered_rules:
        regex = RULES["rrn"]["regex"]
        validator = RULES["rrn"]["validator"]
        for m in regex.finditer(working_text):
            value = m.group(); start, end = m.start(), m.end()
            valid = validator(value, options)  # Always checksum inside validator
            results.append({"rule": "rrn","value": value,"valid": valid,
                            "index": start,"end": end,"context": _ctx(original_text, start, end)})
            rrn_spans.append((start, end))
        working_text = _mask_ranges_same_length(working_text, rrn_spans, "R")

    # 4) 나머지 규칙 (카드는 마지막, 특수 필터 적용)
    for rid in ordered_rules:
        if rid == "rrn": continue
        regex = RULES[rid]["regex"]
        validator = RULES[rid]["validator"]

        for m in regex.finditer(working_text):
            value = m.group(); start, end = m.start(), m.end()

            if rid == "card":
                # 같은 라인에 RRN이 있으면 카드 스킵
                line_start = working_text.rfind("\n", 0, start) + 1
                line_end = working_text.find("\n", end); line_end = len(working_text) if line_end == -1 else line_end
                line = working_text[line_start:line_end]
                if RULES["rrn"]["regex"].search(line): continue
                # 좌우 이웃이 숫자면 스킵
                left = working_text[start - 1] if start > 0 else " "
                right = working_text[end] if end < len(working_text) else " "
                if left.isdigit() or right.isdigit(): continue
                # RRN 형태 자체는 방어
                if re.fullmatch(r"\d{6}[-\s]?\d{7}", value): continue

            valid = validator(value, options)
            results.append({"rule": rid,"value": value,"valid": valid,
                            "index": start,"end": end,"context": _ctx(original_text, start, end)})

    # 5) 후처리: 겹침 제거
    rrn_spans_final = [(r["index"], r["end"]) for r in results if r["rule"] == "rrn"]
    if rrn_spans_final:
        results = [r for r in results if not (r["rule"]=="card" and any(_overlaps((r["index"], r["end"]), s) for s in rrn_spans_final))]
    mobile_spans = [(r["index"], r["end"]) for r in results if r["rule"] == "phone_mobile"]
    if mobile_spans:
        results = [r for r in results if not (r["rule"]=="phone_city" and any(_overlaps((r["index"], r["end"]), s) for s in mobile_spans))]

    # 6) 카운트
    counts = {rid: 0 for rid in RULES}
    for r in results: counts[r["rule"]] += 1
    return {"counts": counts, "items": results}