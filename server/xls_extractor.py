import struct, olefile

SST = 0x00FC

def extract_text_from_xls(file_bytes: bytes) -> dict:
    ole = olefile.OleFileIO(file_bytes)
    wb = ole.openstream("Workbook").read()

    off, n = 0, len(wb)
    texts = []

    while off + 4 <= n:
        opcode, length = struct.unpack("<HH", wb[off:off+4])
        payload_off = off + 4
        payload = wb[payload_off:payload_off+length]

        if opcode == SST:
            if len(payload) < 8:
                break
            cstTotal, cstUnique = struct.unpack("<II", payload[:8])
            pos = 8

            for _ in range(cstUnique):
                if pos + 3 > length:
                    break
                cch = struct.unpack("<H", payload[pos:pos+2])[0]; pos+=2
                option = payload[pos]; pos+=1

                fHigh = option & 0x01
                fExt  = option & 0x04
                fRich = option & 0x08

                if fRich:
                    pos += 2
                if fExt:
                    pos += 4

                # 문자열 본문
                if fHigh:
                    raw = payload[pos:pos+cch*2]; pos+=cch*2
                    txt = raw.decode("utf-16le", errors="ignore")
                else:
                    raw = payload[pos:pos+cch]; pos+=cch
                    try:
                        txt = raw.decode("cp949")
                    except:
                        txt = raw.decode("latin1", errors="ignore")

                texts.append(txt)

                # RichText/ExtRst 데이터 건너뛰기
                if fRich:
                    cRun = struct.unpack("<H", payload[pos-2:pos])[0]
                    pos += cRun * 4
                if fExt:
                    cbExtRst = struct.unpack("<I", payload[pos-4:pos])[0]
                    pos += cbExtRst

        off = payload_off + length

    full = "\n".join(texts)
    return {"full_text": full, "pages": [{"page": 1, "text": full}]}
