# server/routes_redaction.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Form
from typing import List
import json

from ..schemas import DetectRequest, DetectResponse, RedactRequest, PatternItem
from ..pdf_redaction import detect_boxes_from_patterns, apply_redaction
from ..redac_rules import PRESET_PATTERNS

router = APIRouter(tags=["redaction"])

@router.get("/patterns")
def list_patterns():
    return {"patterns": PRESET_PATTERNS}

@router.post("/redactions/detect", response_model=DetectResponse)
async def detect(file: UploadFile = File(...), req: DetectRequest = DetectRequest()):
    # 파일 검증
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="PDF 파일을 업로드하세요.")
    pdf = await file.read()

    # 요청에 패턴이 없으면 서버 프리셋 기본 사용
    patterns: List[PatternItem] = req.patterns or [PatternItem(**p) for p in PRESET_PATTERNS]

    boxes = detect_boxes_from_patterns(pdf, patterns)
    return DetectResponse(total_matches=len(boxes), boxes=boxes)

@router.post("/redactions/apply", response_class=Response)
async def apply(
    file: UploadFile = File(...),
    req: str = Form('{"boxes": [], "fill": "black"}')):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="PDF 파일을 업로드하세요.")
    try:
        data = json.loads(req)
        model = RedactRequest(**data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"invalid req json: {e}")
    if not model.boxes:
        raise HTTPException(status_code=400, detail="boxes가 비어있습니다.")
    pdf = await file.read()

    out = apply_redaction(pdf, model.boxes, fill=model.fill)
    return Response(
        content=out,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="redacted.pdf"'}
    )
