import io
import olefile, struct


def extract_text(file_bytes: bytes) -> dict:
    with olefile.OleFileIO(io.BytesIO(file_bytes)) as ole:
        buf = ole.openstream("PowerPoint Document").read()

    off, n = 0, len(buf)
    texts = []
    while off < n:
        if off + 8 > n:
            break
        recVerInst, recType, recLen = struct.unpack_from("<HHI", buf, off)
        off += 8
        payload = buf[off:off + recLen]

        # 텍스트 계열 레코드(대표값 예시)
        if recType in (4000, 4008):
            try:
                txt = payload.decode("utf-16le", errors="ignore")
                texts.append(txt)
            except Exception:
                pass
        off += recLen

    full = "\n".join(texts)
    try:
        text = buf.decode("utf-16le", errors="ignore")
    except Exception:
        text = buf.decode("cp949", errors="ignore")
    return {"text": text}
