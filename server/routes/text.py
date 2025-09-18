from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import re

from ..redac_rules import RULES
from ..normalize import normalize_text
from ..extract_text import extract_text_from_file

router = APIRouter(tags=["text"])

# ---------- 데이터 모델 ----------
class MatchRequest(BaseModel):
    text: str
    rules: Optional[List[str]] = None

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
            if arr[i].isdigit() or arr[i] in "- /":  #구분자도 모두 가리기
                arr[i] = mask_char
    return "".join(arr)

# 기본적으로 모두 가리는걸로 설정
DEFAULT_ORDER = ["rrn", "email", "phone_mobile", "phone_city", "bizno", "card"]

# ---------- API ----------
@router.get("/rules")
async def list_rules():
    # 존재하는 RULES만 우선순위대로 반환
    return [r for r in DEFAULT_ORDER if r in RULES]

@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    #PDF/TXT에서 텍스트 추출
    try:
        return await extract_text_from_file(file)
    except Exception as e:
        raise HTTPException(status_code=415, detail=str(e))

@router.post("/match", response_model=MatchResponse)
async def match(req: MatchRequest):
    original_text = normalize_text(req.text)
    working_text = original_text

    # 우선순위 적용
    selected = req.rules or list(RULES.keys())
    selected = [r for r in selected if r in RULES]   # 존재 검증
    ordered_rules = [r for r in DEFAULT_ORDER if r in selected]

    results: List[Dict[str, Any]] = []

    #  RRN 먼저 탐지 → 마스킹
    rrn_spans = []
    if "rrn" in ordered_rules:
        regex = RULES["rrn"]["regex"]
        validator = RULES["rrn"]["validator"]
        for m in regex.finditer(working_text):
            value = m.group(); start, end = m.start(), m.end()
            valid = validator(value)
            results.append({
                "rule": "rrn", "value": value, "valid": valid,
                "index": start, "end": end, "context": _ctx(original_text, start, end)
            })
            rrn_spans.append((start, end))
        working_text = _mask_ranges_same_length(working_text, rrn_spans, "R")


    for rid in ordered_rules:
        if rid == "rrn":
            continue
        regex = RULES[rid]["regex"]
        validator = RULES[rid]["validator"]

        for m in regex.finditer(working_text):
            value = m.group(); start, end = m.start(), m.end()

            if rid == "card":
                # 같은 라인에 RRN이 있으면 카드 스킵
                line_start = working_text.rfind("\n", 0, start) + 1
                line_end = working_text.find("\n", end)
                line_end = len(working_text) if line_end == -1 else line_end
                line = working_text[line_start:line_end]
                if RULES["rrn"]["regex"].search(line):
                    continue
                # 좌우 이웃이 숫자면 스킵
                left = working_text[start - 1] if start > 0 else " "
                right = working_text[end] if end < len(working_text) else " "
                if left.isdigit() or right.isdigit():
                    continue
                # RRN 형태 자체는 방어
                if re.fullmatch(r"\d{6}[-\s]?\d{7}", value):
                    continue

            valid = validator(value)
            results.append({
                "rule": rid, "value": value, "valid": valid,
                "index": start, "end": end, "context": _ctx(original_text, start, end)
            })

    # 겹침 제거
    rrn_spans_final = [(r["index"], r["end"]) for r in results if r["rule"] == "rrn"]
    if rrn_spans_final:
        results = [
            r for r in results
            if not (r["rule"] == "card" and any(_overlaps((r["index"], r["end"]), s) for s in rrn_spans_final))
        ]
    mobile_spans = [(r["index"], r["end"]) for r in results if r["rule"] == "phone_mobile"]
    if mobile_spans:
        results = [
            r for r in results
            if not (r["rule"] == "phone_city" and any(_overlaps((r["index"], r["end"]), s) for s in mobile_spans))
        ]

    # 실제로 돌린것만 카운트
    counts = {rid: 0 for rid in ordered_rules}
    for r in results:
        counts[r["rule"]] = counts.get(r["rule"], 0) + 1
    return {"counts": counts, "items": results}
