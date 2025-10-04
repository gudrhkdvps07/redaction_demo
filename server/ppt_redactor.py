import olefile, struct

def extract_text(file_bytes: bytes) -> dict:
    with olefile.OleFileIO(file_bytes) as ole:
        buf = ole.openstream("PowerPoint Document").read()

    off, n = 0, len(buf)
    texts = []
    while off < n:
        if off+8 > n: break
        recVerInst, recType, recLen = struct.unpack_from("<HHI", buf, off)
        off += 8
        payload = buf[off:off+recLen]

        if recType in (4000, 4008):  # 텍스트 계열 레코드
            try:
                txt = payload.decode("utf-16le", errors="ignore")
                texts.append(txt)
            except:
                pass
        off += recLen

    full = "\n".join(texts)
    return {"full_text": full, "pages": [{"page": 1, "text": full}]}
