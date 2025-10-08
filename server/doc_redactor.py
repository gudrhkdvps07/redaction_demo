import io, olefile, struct

# WordDocument 내부 Piece Table 기반 텍스트 복원
def extract_text(file_bytes: bytes) -> dict:
    with olefile.OleFileIO(io.BytesIO(file_bytes)) as ole:
        fib_base = ole.openstream("WordDocument").read(512)
        fc_clx, lcb_clx = struct.unpack_from("<II", fib_base, 0x01A2)

        table_stream_name = "1Table" if ole.exists("1Table") else "0Table"
        table_data = ole.openstream(table_stream_name).read()
        clx = table_data[fc_clx:fc_clx + lcb_clx]

        # Clx 구조 → Piece Table 추출
        plc_pcd = clx[1:] if clx and clx[0] == 0x02 else b""
        pieces = []
        if plc_pcd:
            c_pcd = (len(plc_pcd) - 4) // 12
            for i in range(c_pcd):
                fc = struct.unpack_from("<I", plc_pcd, 4 + i * 12 + 2)[0]
                fc = fc >> 1  # offset in WordDocument stream
                fc_next = struct.unpack_from("<I", plc_pcd, 4 + (i + 1) * 12 + 2)[0] >> 1
                pieces.append((fc, fc_next))

        word_stream = ole.openstream("WordDocument").read()
        texts = []
        for fc, fc_next in pieces:
            seg = word_stream[fc:fc_next]
            try:
                txt = seg.decode("utf-16le", errors="ignore")
            except Exception:
                txt = seg.decode("cp949", errors="ignore")
            texts.append(txt)

    full = "".join(texts)
    return {"full_text": full, "pages": [{"page": 1, "text": full}]}
