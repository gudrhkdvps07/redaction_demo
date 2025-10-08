from fastapi import APIRouter, UploadFile, File, HTTPException
from ..extract_text import extract_text_from_file
from ..routes.redaction import match_text
from ..redac_rules import RULES

router = APIRouter(prefix="/text", tags=["Text"])


@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    try:
        result = await extract_text_from_file(file)
        if not result or "full_text" not in result:
            raise HTTPException(status_code=422, detail="텍스트 추출 실패")
        return result
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {e}")


@router.post("/match")
async def match(payload: dict):
    try:
        text = payload.get("full_text", "")
        if not text:
            raise HTTPException(status_code=400, detail="텍스트 없음")
        matches = match_text(text)
        return {"matches": matches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"매칭 오류: {e}")
    
@router.get("/rules")
def get_rules():
    """
    프론트에서 체크박스 표시용 규칙 목록 조회
    """
    return {"rules": RULES}