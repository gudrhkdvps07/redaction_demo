import re

RULES = [
    {  # 1) 주민등록번호(형식만: YYMMDD-XXXXXXX)
        "id": "rrn", 
        "pattern" : r"\b\d{6}-[1-8]\d{6}\b"
    },
    {   # 2) 휴대전화(010, 구분자 -, 공백, . 허용)
        "id": "phone_mobile", 
        "pattern": r"\b010[-.\s]?\d{3,4}[-.\s]?\d{4}\b"
    },
    {   # 3) 지역전화(02, 031~064)
        "id": "phone_city", 
        "pattern": r"\b(?:02|0(?:3[1-3]|4[1-4]|5[1-5]|6[1-4]))[-.\s]?\d{3,4}[-.\s]?\d{4}\b"
    },
    {   # 4) 이메일
        "id": "email", 
        "pattern": r"\b[a-zA-Z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    },
    {   # 5) 카드번호
        "id": "card", 
        "pattern": r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"
    },
    {   # 6) 사업자등록번호(3-2-5 자리, 구분자 - 선택)
        "id": "bizno", 
        "pattern": r"\b\d{3}-?\d{2}-?\d{5}\b"
    },
]

COMPILED_RULES = [{"id": r["id"], "pattern": re.compile(r["pattern"])} for r in RULES]
