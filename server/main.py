from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import re

from .redac_rules import RULES
from .normalize import normalize_text
from .extract_text import extract_text_from_file

app = FastAPI()

# CORS 허용 (프론트 로컬 파일/개발 서버에서 직접 호출 가능)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------
# 데이터 모델
# ---------------------------
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


# ---------------------------
# 헬퍼
# ---------------------------
def _ctx(text: str, start: int, end: int, window: int = 25) -> str:
    """탐지 문자열 주변 컨텍스트(좌우 25자)"""
    return (
        text[max(0, start - window): start]
        + "【" + text[start:end] + "】"
        + text[end: end + window]
    )


def _overlaps(a, b) -> bool:
    """구간 겹침 여부"""
    return a[0] < b[1] and b[0] < a[1]


def _mask_ranges_same_length(s: str, spans, mask_char: str = "R") -> str:
    """
    스팬 구간을 동일 길이로 마스킹(인덱스 유지).
    숫자/하이픈/스페이스만 치환하여 다른 텍스트는 보존.
    """
    if not spans:
        return s
    arr = list(s)
    L = len(arr)
    for st, ed in spans:
        st = max(0, min(st, L))
        ed = max(0, min(ed, L))
        for i in range(st, ed):
            if arr[i].isdigit() or arr[i] in "- ":
                arr[i] = mask_char
    return "".join(arr)


# ---------------------------
# API
# ---------------------------
@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/rules")
async def list_rules():
    return list(RULES.keys())


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    """PDF/TXT에서 텍스트 추출"""
    try:
        return await extract_text_from_file(file)
    except Exception as e:
        raise HTTPException(status_code=415, detail=str(e))


@app.post("/match", response_model=MatchResponse)
async def match(req: MatchRequest):
    """
    정규식 기반 PII 탐지
    - 우선순위: RRN 먼저 → 자리 마스킹 → 그 다음 규칙들 → 카드 마지막
    - 카드 탐지 시 추가 필터: 좌우 이웃 숫자 차단, RRN 모양/겹침 차단
    - 모바일/도시번호 겹침 제거
    """
    original_text = normalize_text(req.text) if req.normalize else req.text
    working_text = original_text  # 마스킹은 여기에 적용해서 인덱스 보존
    options = req.options or {}

    # 기본 탐지 우선순위 (상황 맞게 조정 가능)
    default_order = ["rrn", "email", "phone_mobile", "phone_city", "bizno", "card"]
    selected = req.rules if req.rules else list(RULES.keys())
    ordered_rules = [r for r in default_order if r in selected]

    results: List[Dict[str, Any]] = []

    # --- 1) RRN 먼저 탐지 ---
    rrn_spans = []
    if "rrn" in ordered_rules:
        regex = RULES["rrn"]["regex"]
        validator = RULES["rrn"]["validator"]

        for m in regex.finditer(working_text):
            value = m.group()
            start, end = m.start(), m.end()
            valid = validator(value, options)

            results.append({
                "rule": "rrn",
                "value": value,
                "valid": valid,
                "index": start,
                "end": end,
                "context": _ctx(original_text, start, end),
            })
            rrn_spans.append((start, end))

        # RRN이 잡힌 구간은 숫자/하이픈/스페이스만 동일 길이로 마스킹 → 이후 규칙이 다시 매치하지 못함
        working_text = _mask_ranges_same_length(working_text, rrn_spans, "R")

    # --- 2) 나머지 규칙 탐지 (카드는 가장 마지막) ---
    for rid in ordered_rules:
        if rid == "rrn":
            continue

        regex = RULES[rid]["regex"]
        validator = RULES[rid]["validator"]

        # 라인 단위 휴리스틱: 같은 라인에 RRN이 있으면 카드 스킵 (실무상 유용)
        skip_card_on_rrn_line = (rid == "card")

        for m in regex.finditer(working_text):
            value = m.group()
            start, end = m.start(), m.end()

            # 카드 특수 필터들
            if rid == "card":
                # (a) 같은 라인에 RRN이 있으면 카드 스킵
                if skip_card_on_rrn_line:
                    line_start = working_text.rfind("\n", 0, start) + 1
                    line_end = working_text.find("\n", end)
                    if line_end == -1:
                        line_end = len(working_text)
                    line = working_text[line_start:line_end]
                    if RULES["rrn"]["regex"].search(line):
                        continue

                # (b) 좌우 이웃이 숫자면 스킵 (큰 숫자 덩어리 방지)
                left = working_text[start - 1] if start > 0 else " "
                right = working_text[end] if end < len(working_text) else " "
                if left.isdigit() or right.isdigit():
                    continue

                # (c) RRN 형태 자체는 방어 (이중 안전장치)
                if re.fullmatch(r"\d{6}[-\s]?\d{7}", value):
                    continue

            valid = validator(value, options)

            results.append({
                "rule": rid,
                "value": value,
                "valid": valid,
                "index": start,
                "end": end,
                "context": _ctx(original_text, start, end),
            })

    # --- 3) 후처리 #1: RRN과 겹치는 카드 매치 제거 (우선순위: RRN > CARD) ---
    rrn_spans_final = [(r["index"], r["end"]) for r in results if r["rule"] == "rrn"]
    if rrn_spans_final:
        results = [
            r for r in results
            if not (r["rule"] == "card" and any(_overlaps((r["index"], r["end"]), s) for s in rrn_spans_final))
        ]

    # --- 4) 후처리 #2: 모바일과 겹치는 도시번호 제거 (우선순위: phone_mobile > phone_city) ---
    mobile_spans = [(r["index"], r["end"]) for r in results if r["rule"] == "phone_mobile"]
    if mobile_spans:
        results = [
            r for r in results
            if not (r["rule"] == "phone_city" and any(_overlaps((r["index"], r["end"]), s) for s in mobile_spans))
        ]

    # --- 5) 카운트 집계 ---
    counts = {rid: 0 for rid in RULES}
    for r in results:
        counts[r["rule"]] += 1

    return {"counts": counts, "items": results}
