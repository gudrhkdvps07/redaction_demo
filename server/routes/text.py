from fastapi import UploadFile, HTTPException
from ..doc_redactor import extract_text as extract_doc_text
from ..ppt_redactor import extract_text as extract_ppt_text
from ..xls_extractor import extract_text_from_xls
from ..hwp_redactor import extract_text as extract_hwp_text


async def extract_text_from_file(file: UploadFile):
    try:
        filename = (file.filename or "").lower()
        content_type = (file.content_type or "").lower()

        # 1️⃣ 기본 유효성 검사
        if not filename:
            raise HTTPException(status_code=415, detail="파일명이 비어 있습니다.")

        file_bytes = await file.read()
        if not file_bytes or len(file_bytes) < 8:
            raise HTTPException(status_code=415, detail="빈 파일이거나 손상된 파일입니다.")

        # 2️⃣ 확장자 및 MIME 타입 기반 분기 (x붙은 확장자 제외)
        if (filename.endswith(".doc") and not filename.endswith(".docx")) or "msword" in content_type:
            return extract_doc_text(file_bytes)

        elif (filename.endswith(".ppt") and not filename.endswith(".pptx")) or "powerpoint" in content_type:
            return extract_ppt_text(file_bytes)

        elif (filename.endswith(".xls") and not filename.endswith(".xlsx")) or "excel" in content_type:
            return extract_text_from_xls(file_bytes)

        elif filename.endswith(".hwp") or "hwp" in content_type:
            return extract_hwp_text(file_bytes)

        else:
            raise HTTPException(status_code=415, detail=f"지원하지 않는 파일 형식입니다. ({filename})")

    except HTTPException:
        raise
    except Exception as e:
        # 내부 오류는 500으로 분리해서 로그 확인 가능하게
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {e}")
