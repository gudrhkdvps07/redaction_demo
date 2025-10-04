import olefile
from .redac_rules import apply_redaction_rules, RULES

def extract_text(file_bytes: bytes) -> dict:
    with olefile.OleFileIO(file_bytes) as ole:
        data = ole.openstream("WordDocument").read()
    text = data.decode("utf-16le", errors="ignore")
    return {"full_text": text, "pages": [{"page": 1, "text": text}]}

def redact(file_bytes: bytes, rules: dict = RULES) -> bytes:
    with olefile.OleFileIO(file_bytes) as ole:
        data = bytearray(ole.openstream("WordDocument").read())
    text = data.decode("utf-16le", errors="ignore")
    new_text = apply_redaction_rules(text, rules)
    if len(new_text) != len(text):
        raise ValueError("DOC는 동일 길이 치환만 허용")
    return new_text.encode("utf-16le")
