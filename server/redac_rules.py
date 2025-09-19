import re
from .validators import (
    is_valid_rrn,
    is_valid_phone_mobile,
    is_valid_phone_city,
    is_valid_email,
    is_valid_card,
)

# --- RRN ---
RRN_RE = re.compile(r"\b\d{6}-\d{7}\b")

# --- 카드 + RRN 제외 ---
SEP = r"[-\s\u2010\u2011\u2012\u2013\u2014\u2212\ufe63\u2043]"  # 하이픈/모든 공백/유니코드 대시
CARD_RE = re.compile(
    r"""
    \b
    (?!\d{6}-\d{7}\b)                  # 정확한 RRN(6-7) 제외
    (?!\d{13}\b)                       # 13자리 연속(주로 RRN) 제외
    (?:
        # 4-4-4-4 : 하이픈/임의의 공백 허용, 섞여도 OK
        (?:[2-6]\d{3})(?:[-\s]\d{4}){3}
        | [2-6]\d{15}                    # 16자리 연속 (2~6 시작: MC(2/5), Visa(4), Discover(6) 등)
        | 3[47]\d{13}                    # AMEX 15자리 연속
        | 3[47]\d{2}(?:[-\s]\d{6})[-\s]\d{5}  # AMEX 4-6-5, 구분자 섞여도 허용
    )
    \b
    """,
    re.VERBOSE,
)
EMAIL_RE  = re.compile(r"\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")
MOBILE_RE = re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")
# 도시번호: 02, 031~064만 허용 (01x 배제)
CITY_RE   = re.compile(r"\b(?:02|0(?:3[1-3]|4[1-4]|5[1-5]|6[1-4]))-?\d{3,4}-?\d{4}\b")

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
    {"name": "card",          "regex": CARD_RE.pattern,   "case_sensitive": False, "whole_word": False},
]