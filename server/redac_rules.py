import re
from .validators import (
    is_valid_rrn,
    is_valid_phone_mobile,
    is_valid_phone_city,
    is_valid_email,
    is_valid_card,
)

# --- 주민등록번호 ---
RRN_RE = re.compile(r"\d{6}-\d{7}")

# --- 카드번호 (단순화: 15~16자리 or 4-4-4-4) ---
CARD_RE = re.compile(
    r"(?:\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}|\d{15,16})"
)

# --- 이메일 ---
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}")

# --- 휴대폰 ---
MOBILE_RE = re.compile(r"01[016789]-?\d{3,4}-?\d{4}")

# --- 지역번호 전화 ---
CITY_RE = re.compile(r"(?:02|0(?:3[1-3]|4[1-4]|5[1-5]|6[1-4]))-?\d{3,4}-?\d{4}")

# --- 룰 정의 ---
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

# --- 사전 정의된 패턴 ---
PRESET_PATTERNS = [
    {"name": "rrn", "regex": RRN_RE.pattern, "case_sensitive": False, "whole_word": False},
    {"name": "email", "regex": EMAIL_RE.pattern, "case_sensitive": False, "whole_word": False},
    {"name": "phone_mobile", "regex": MOBILE_RE.pattern, "case_sensitive": False, "whole_word": False},
    {"name": "phone_city", "regex": CITY_RE.pattern, "case_sensitive": False, "whole_word": False},
    {"name": "card", "regex": CARD_RE.pattern, "case_sensitive": False, "whole_word": False},
]
