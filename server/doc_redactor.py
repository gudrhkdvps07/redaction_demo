import io
import struct
import olefile


def _extract_plcpcd(clx: bytes) -> bytes:
    """CLX 블록 안에서 PlcPcd(0x02) 추출"""
    i = 0
    while i < len(clx):
        tag = clx[i]
        i += 1
        if tag == 0x01:  # Prc (서식 정보) → cb + grpprl
            if i + 2 > len(clx):
                break
            cb = struct.unpack_from("<H", clx, i)[0]
            i += 2 + cb
        elif tag == 0x02:  # Pcdt(PlcPcd)
            if i + 4 > len(clx):
                break
            lcb = struct.unpack_from("<I", clx, i)[0]
            i += 4
            return clx[i:i + lcb]
        else:
            break
    return b""


def _parse_plcpcd(plcpcd: bytes):
    """PlcPcd 파싱 → fc, fCompressed, byte_count 계산"""
    size = len(plcpcd)
    if size < 4 or (size - 4) % 12 != 0:
        return []

    n = (size - 4) // 12
    aCp = [struct.unpack_from("<I", plcpcd, 4 * i)[0] for i in range(n + 1)]
    pcd_off = 4 * (n + 1)
    pieces = []
    for k in range(n):
        pcd_bytes = plcpcd[pcd_off + 8 * k : pcd_off + 8 * (k + 1)]
        fc_raw = struct.unpack_from("<I", pcd_bytes, 2)[0]

        fc = fc_raw & 0x3FFFFFFF
        fCompressed = (fc_raw & 0x40000000) != 0

        cp_start = aCp[k]
        cp_end = aCp[k + 1]
        char_count = cp_end - cp_start
        byte_count = char_count if fCompressed else char_count * 2

        pieces.append({
            "index": k,
            "fc": fc,
            "byte_count": byte_count,
            "fCompressed": fCompressed
        })
    return pieces


def _decode_piece(chunk: bytes, fCompressed: bool) -> str:
    """조각별 압축 여부에 따라 디코딩"""
    try:
        if fCompressed:
            return chunk.decode("cp1252", errors="ignore")
        else:
            return chunk.decode("utf-16le", errors="ignore")
    except Exception:
        return ""


def extract_text(file_bytes: bytes) -> dict:
    try:
        with olefile.OleFileIO(io.BytesIO(file_bytes)) as ole:
            if not ole.exists("WordDocument"):
                print(" WordDocument 스트림 없음")
                raise ValueError("WordDocument 없음")

            word_data = ole.openstream("WordDocument").read()
            print("WordDocument 크기:", len(word_data))

            fib_flags = struct.unpack_from("<H", word_data, 0x000A)[0]
            print("FIB flags:", hex(fib_flags))

            fWhichTblStm = (fib_flags & 0x0200) != 0
            tbl_name = "1Table" if fWhichTblStm and ole.exists("1Table") else "0Table"
            if not ole.exists(tbl_name):
                print("Table 스트림 없음:", tbl_name)
                raise ValueError("Table 스트림 없음")

            table_data = ole.openstream(tbl_name).read()
            print(f"Table 스트림({tbl_name}) 크기:", len(table_data))

            fcClx = struct.unpack_from("<I", word_data, 0x01A2)[0]
            lcbClx = struct.unpack_from("<I", word_data, 0x01A6)[0]
            print(f"fcClx={fcClx}, lcbClx={lcbClx}")

            if fcClx + lcbClx > len(table_data):
                print("CLX 범위 초과")
                raise ValueError("CLX 범위 초과")

            clx = table_data[fcClx:fcClx+lcbClx]
            plcpcd = _extract_plcpcd(clx)
            if not plcpcd:
                print("PlcPcd 없음")
                raise ValueError("PlcPcd 없음")

            pieces = _parse_plcpcd(plcpcd)
            print("조각 수:", len(pieces))

            texts = []
            for p in pieces[:5]:
                print("조각:", p)
                start, end = p["fc"], p["fc"] + p["byte_count"]
                if end > len(word_data): continue
                chunk = word_data[start:end]
                texts.append(_decode_piece(chunk, p["fCompressed"]))

            full_text = "\n".join(texts)
            return {"full_text": full_text, "pages": [{"page": 1, "text": full_text}]}

    except Exception as e:
        print(" 내부 예외:", repr(e))
        raise ValueError(f".doc 텍스트 추출 실패: {e}")
