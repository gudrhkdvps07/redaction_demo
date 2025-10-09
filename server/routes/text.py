from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ..extract_text import extract_text_from_file as _extract_text  # 서버 공용 추출기 사용
from ..redac_rules import PRESET_PATTERNS, RULES
from ..normalize import normalize_text
import re

router = APIRouter(prefix="/text", tags=["text"])

# 규칙 이름 목록 (프론트에서 체크박스 렌더링에 사용)
@router.get("/rules")
def list_rules():
    return [p["name"] for p in PRESET_PATTERNS]

# 파일 텍스트 추출 (프론트 /text/extract 호출)
@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    try:
        return await _extract_text(file)
    except HTTPException:
        raise
    except Exception as e:
        # 업로드/미지원 포맷/손상 파일 등은 415로 돌려 프론트 상태표시 유지
        raise HTTPException(status_code=415, detail=f"텍스트 추출 실패: {e}")

# 매칭 요청 스키마
class MatchRequest(BaseModel):
    text: str
    rules: Optional[List[str]] = None
    normalize: Optional[bool] = False

# 텍스트 매칭 (프론트 /text/match 호출)
@router.post("/match")
def match(req: MatchRequest):
    # 1) 전처리
    text = req.text or ""
    if req.normalize:
        text = normalize_text(text)

    # 2) 사용할 패턴 셀렉션
    patterns = PRESET_PATTERNS
    if req.rules:
        want = set(req.rules)
        patterns = [p for p in PRESET_PATTERNS if p["name"] in want]

    items = []
    counts = {}

    for p in patterns:
        name = p["name"]
        comp = re.compile(p["regex"], re.IGNORECASE if not p.get("case_sensitive") else 0)
        found = list(comp.finditer(text))
        counts[name] = len(found)

        validator = RULES.get(name, {}).get("validator")

        for m in found:
            ctx_start = max(0, m.start() - 20)
            ctx_end   = min(len(text), m.end() + 20)
            val_ok = True
            if callable(validator):
                try:
                    val_ok = bool(validator(m.group()))
                except Exception:
                    val_ok = False

            items.append({
                "rule": name,
                "value": m.group(),
                "valid": val_ok,
                "context": text[ctx_start:ctx_end],
            })

    return {"items": items, "counts": counts}
