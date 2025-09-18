import re
from .validators import (
    is_valid_rrn,
    is_valid_phone_mobile,
    is_valid_phone_city,
    is_valid_email,
    is_valid_card,
    is_valid_bizno,
)

# --- RRN ---
RRN_RE = re.compile(r"\b\d{6}-\d{7}\b")

# --- 카드: 현실 포맷 + RRN 네거티브 가드 ---
CARD_RE = re.compile(
    r"""
    \b
    (?!\d{6}-\d{7}\b)             # RRN 모양 제외
    (?!\d{13}\b)                  # 하이픈 없는 13자리(사실상 RRN) 제외
    (?:
        (?:[4-6]\d{3})(?:([- ])\d{4}){3}   # 4-4-4-4 (동일 구분자)
        | [4-6]\d{15}                        # 16 연속(시작 4..6)
        | 3[47]\d{13}                        # AMEX 15 연속
        | 3[47]\d{2}(?:([- ])\d{6})\2\d{5}   # AMEX 4-6-5 (동일 구분자)
    )
    \b
    """,
    re.VERBOSE,
)

EMAIL_RE  = re.compile(r"\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")
MOBILE_RE = re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")
# 도시번호: 02, 031~064만 허용 (01x 배제)
CITY_RE   = re.compile(r"\b(?:02|0(?:3[1-3]|4[1-4]|5[1-5]|6[1-4]))-?\d{3,4}-?\d{4}\b")
BIZNO_RE  = re.compile(r"\b\d{3}-?\d{2}-?\d{5}\b")

RULES = {
    "rrn": {
        "regex": RRN_RE,
        "validator": lambda v, _opts=None: is_valid_rrn(v, use_checksum=True),
    },
    "email": {
        "regex": EMAIL_RE,
        "validator": is_valid_email,
    },
    "phone_mobile": {
        "regex": MOBILE_RE,
        "validator": is_valid_phone_mobile,
    },
    "phone_city": {
        "regex": CITY_RE,
        "validator": is_valid_phone_city,
    },
    "bizno": {
        "regex": BIZNO_RE,
        "validator": is_valid_bizno,
    },
    "card": {
        "regex": CARD_RE,
        "validator": is_valid_card,
    },
}

PRESET_PATTERNS = [
    {"name": "rrn",           "regex": RRN_RE.pattern,    "case_sensitive": False, "whole_word": False},
    {"name": "email",         "regex": EMAIL_RE.pattern,  "case_sensitive": False, "whole_word": False},
    {"name": "phone_mobile",  "regex": MOBILE_RE.pattern, "case_sensitive": False, "whole_word": False},
    {"name": "phone_city",    "regex": CITY_RE.pattern,   "case_sensitive": False, "whole_word": False},
    {"name": "bizno",         "regex": BIZNO_RE.pattern,  "case_sensitive": False, "whole_word": False},
    {"name": "card",          "regex": CARD_RE.pattern,   "case_sensitive": False, "whole_word": False},
]