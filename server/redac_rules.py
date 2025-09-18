import re
from .validators import (
    is_valid_rrn,
    is_valid_phone_mobile,
    is_valid_phone_city,
    is_valid_email,
    is_valid_card,
    is_valid_bizno,
)

# ---------------------------
# 정규식 정의
# ---------------------------

# RRN: 6자리-7자리 (양끝 단어 경계)
RRN_RE = re.compile(r"\b\d{6}-[0-9]{7}\b")

# 카드번호:
#  - RRN 모양(6-7) 및 13자리(하이픈 없음) 숫자열(사실상 RRN) 명시적 제외
#  - 4-4-4-4 (Visa/Master 등 시작 4~6), 구분자는 하이픈/스페이스만, 그리고 동일한 구분자 반복(백레퍼런스)
#  - 16자리 연속(시작 4~6)
#  - AMEX 15자리 연속(34/37), 혹은 4-6-5 형태(동일 구분자)
CARD_RE = re.compile(
    r"""
    \b
    (?!\d{6}-\d{7}\b)                  # 정확한 RRN(6-7) 제외
    (?!\d{13}\b)                       # 하이픈 없는 13자리 제외(주로 RRN)
    (?:
        (?:[4-6]\d{3})(?:([- ])\d{4}){3}    # 4-4-4-4 (동일 구분자)
      | [4-6]\d{15}                         # 16자리 연속(시작 4..6)
      | 3[47]\d{13}                         # AMEX 15자리 연속
      | 3[47]\d{2}(?:([- ])\d{6})\2\d{5}    # AMEX 4-6-5 (동일 구분자)
    )
    \b
    """,
    re.VERBOSE,
)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")
MOBILE_RE = re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")
CITY_RE = re.compile(r"\b(?:02|0(?:3[1-3]|4[1-4]|5[1-5]|6[1-4]))-?\d{3,4}-?\d{4}\b")
BIZNO_RE = re.compile(r"\b\d{3}-?\d{2}-?\d{5}\b")


# ---------------------------
# RULES 매핑
# ---------------------------

RULES = {
    "rrn": {
        "regex": RRN_RE,
        "validator": lambda v, opts=None: is_valid_rrn(
            v,
            # 옵션 키를 맞춰서 전달 (없으면 기본 False)
            bool((opts or {}).get("rrn_checksum", False))
        ),
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
