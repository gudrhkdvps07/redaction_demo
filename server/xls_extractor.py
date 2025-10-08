import io
import struct
import olefile

# BIFF opcodes
BOF        = 0x0809
EOF        = 0x000A
SST        = 0x00FC
CONTINUE   = 0x003C
LABELSST   = 0x00FD
LABEL      = 0x0204
RSTRING    = 0x00D6
CODEPAGE   = 0x0042  # (참고용) 8-bit 문자열 디폴트 코드페이지

# --------- 유틸: Chunks(=SST + CONTINUE 연속 바디) 를 가로질러 읽는 리더 ----------
class ChunkReader:
    def __init__(self, chunks):
        self.chunks = chunks
        self.i = 0
        self.pos = 0

    def _advance(self):
        # 다음 청크로
        self.i += 1
        self.pos = 0

    def read(self, n) -> bytes:
        """연속된 n바이트를 끊김 없이 반환 (CONTINUE 경계 자동 처리)"""
        out = bytearray()
        while n > 0 and self.i < len(self.chunks):
            chunk = self.chunks[self.i]
            remain = len(chunk) - self.pos
            if remain <= 0:
                self._advance()
                continue
            take = min(remain, n)
            out += chunk[self.pos:self.pos + take]
            self.pos += take
            n -= take
            if self.pos >= len(chunk):
                self._advance()
        return bytes(out)

    def read_u8(self):  return self.read(1)[0]
    def read_u16(self): return struct.unpack("<H", self.read(2))[0]
    def read_u32(self): return struct.unpack("<I", self.read(4))[0]

# --------- SST 안의 XLUnicodeRichExtendedString 파서 (BIFF8) ----------
def _read_xlunicode_string(reader: ChunkReader, codepage: str) -> str:
    """BIFF8 XLUnicodeRichExtendedString 파서 (rt/ext 포함)"""
    cch = reader.read_u16()            # 글자 수(문자 단위)
    flags = reader.read_u8()           # fHighByte(1), fExtSt(4), fRichSt(8)
    fHigh = (flags & 0x01) != 0        # 1이면 16-bit(UTF-16LE), 0이면 8-bit(single byte)
    fExt  = (flags & 0x04) != 0
    fRich = (flags & 0x08) != 0

    rt = reader.read_u16() if fRich else 0    # 서식 런 개수
    sz = reader.read_u32() if fExt  else 0    # 확장 데이터 크기

    # 본문
    if fHigh:
        raw = reader.read(cch * 2)
        text = raw.decode("utf-16le", errors="ignore")
    else:
        raw = reader.read(cch)
        # 코드페이지 기반 8-bit 디코딩
        for enc in (codepage, "cp949", "cp1252", "latin1"):
            try:
                text = raw.decode(enc, errors="ignore")
                break
            except Exception:
                continue

    # rich/ext 데이터 스킵
    if fRich:
        _ = reader.read(rt * 4)        # 각 런 4바이트
    if fExt:
        _ = reader.read(sz)

    return text

def _collect_sst_strings(wb: bytes) -> list[str]:
    """Workbook Globals Substream에서 SST(+CONTINUE) 읽어서 문자열 리스트 생성"""
    # 1) SST와 연속 CONTINUE 덩어리 모으기
    chunks = []
    collecting = False
    codepage = "cp949"  # 기본값 (필요시 CODEPAGE 읽어 갱신)

    off, n = 0, len(wb)
    while off + 4 <= n:
        opcode, length = struct.unpack("<HH", wb[off:off+4])
        off += 4
        payload = wb[off:off+length]
        off += length

        if opcode == CODEPAGE and length == 2:
            cp_val = struct.unpack("<H", payload)[0]
            # 간단 매핑(안전하게 기본 cp949 유지, 일부만 대응)
            # 0x03B5(949) 등 다양한 값이 존재. 치명적이지 않게 best-effort.
            if cp_val in (0x03B5, 949):
                codepage = "cp949"
            elif cp_val in (0x04E4, 1252):
                codepage = "cp1252"

        if opcode == SST:
            collecting = True
            chunks = [payload]
            # 첫 8바이트는 cstTotal(4), cstUnique(4) → 파싱에 필요하므로 보존
            # 이후부터 문자열들이 연달아 붙음
            # 다음 루프에서 CONTINUE면 추가, 다른 레코드면 종료
        elif collecting and opcode == CONTINUE:
            chunks.append(payload)
        elif collecting:
            break

    if not chunks:
        return []

    # 2) SST 파싱
    r = ChunkReader(chunks)
    _cstTotal = r.read_u32()
    cstUnique = r.read_u32()

    strings = []
    for _ in range(cstUnique if cstUnique > 0 else _cstTotal):
        try:
            s = _read_xlunicode_string(r, codepage)
            strings.append(s)
        except Exception:
            # CONTINUE 경계 등으로 파싱이 실패하면 중단
            break
    return strings

def _iter_biff_records(data: bytes):
    off, n = 0, len(data)
    while off + 4 <= n:
        opcode, length = struct.unpack("<HH", data[off:off+4])
        off += 4
        payload = data[off:off+length]
        off += length
        yield opcode, payload

def extract_text_from_xls(file_bytes: bytes) -> dict:
    """XLS 텍스트 추출: SST(strings) + LABELSST(셀 참조) 기반"""
    with olefile.OleFileIO(io.BytesIO(file_bytes)) as ole:
        wb = ole.openstream("Workbook").read()

    # 1) SST에서 유니크 문자열 전부 복원
    sst_strings = _collect_sst_strings(wb)

    # 2) 워크시트/셀 레코드 스캔: LABELSST → sst index 참조
    texts = []

    for opcode, payload in _iter_biff_records(wb):
        if opcode == LABELSST and len(payload) >= 10:
            # row(2) col(2) xf(2) sstIndex(4)
            sst_index = struct.unpack_from("<I", payload, 6)[0]
            if 0 <= sst_index < len(sst_strings):
                val = sst_strings[sst_index]
                if val and val.strip():
                    texts.append(val.strip())

        elif opcode in (LABEL, RSTRING):
            # 구형 문자열 셀: 구조가 복잡하지만 best-effort로 본문만 디코드 시도
            # (라틴/CP949/UTF-16 추정 순서)
            raw = payload
            for enc in ("utf-16le", "cp949", "cp1252", "latin1"):
                try:
                    t = raw.decode(enc, errors="ignore").strip()
                    if t:
                        texts.append(t)
                    break
                except Exception:
                    continue

    full = "\n".join(texts)
    return {"full_text": full, "pages": [{"page": 1, "text": full}]}
