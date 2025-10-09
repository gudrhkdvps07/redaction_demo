import io
import struct
import olefile


def _iter_records(buf: bytes):
    """
    PowerPoint 'PowerPoint Document' 스트림 내 레코드 반복자
    RecordHeader: 2B recVerInst + 2B recType + 4B recLen
    """
    off, n = 0, len(buf)
    while off + 8 <= n:
        recVerInst, recType, recLen = struct.unpack_from("<HHI", buf, off)
        off += 8
        payload = buf[off:off + recLen]
        yield recType, payload
        off += recLen


def extract_text(file_bytes: bytes) -> dict:
    """
    구형 PPT(OLE 기반)에서 텍스트 추출
    - TextCharsAtom (0x0FA0): UTF-16LE 텍스트
    - TextBytesAtom (0x0FA8): ANSI 텍스트
    - CString       (0x0FBA): 메타데이터 문자열
    """
    with olefile.OleFileIO(io.BytesIO(file_bytes)) as ole:
        if not ole.exists("PowerPoint Document"):
            raise ValueError("PowerPoint Document 스트림이 없습니다.")
        buf = ole.openstream("PowerPoint Document").read()

    texts = []

    for recType, payload in _iter_records(buf):
        # UTF-16 문자열
        if recType == 0x0FA0:  # TextCharsAtom
            try:
                t = payload.decode("utf-16le", errors="ignore")
                if t.strip():
                    texts.append(t.strip())
            except Exception:
                pass

        # ANSI 문자열
        elif recType == 0x0FA8:  # TextBytesAtom
            for enc in ("cp949", "utf-8", "latin1"):
                try:
                    t = payload.decode(enc, errors="ignore")
                    if t.strip():
                        texts.append(t.strip())
                    break
                except Exception:
                    continue

        # CString (예: 제목, 저자 등 메타정보)
        elif recType == 0x0FBA:
            try:
                t = payload.decode("utf-16le", errors="ignore")
                if t.strip():
                    texts.append(t.strip())
            except Exception:
                pass

    # 중복 제거 + 줄 단위 조합
    seen = set()
    clean_texts = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            clean_texts.append(t)

    full_text = "\n".join(clean_texts)
    return {"full_text": full_text, "pages": [{"page": 1, "text": full_text}]}
