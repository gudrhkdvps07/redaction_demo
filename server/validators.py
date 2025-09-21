import re
from datetime import datetime

# --- 유틸 ---
def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")

# --- 주민등록번호 ---
def is_valid_rrn_date_only(rrn: str) -> bool:
    d = _digits(rrn)
    if len(d) != 13:
        return False
    birth = d[:6]
    gender = d[6]
    try:
        if gender in "34":  # 2000~
            y = "20" + birth[:2]
        else:               # 1900~
            y = "19" + birth[:2]
        dt = datetime.strptime(y + birth[2:], "%Y%m%d")
        if dt > datetime.today():
            return False
    except ValueError:
        return False
    return True

def is_valid_rrn_checksum(rrn: str) -> bool:
    d = _digits(rrn)
    if len(d) != 13:
        return False
    weights = [2,3,4,5,6,7,8,9,2,3,4,5]
    total = sum(int(x)*w for x, w in zip(d[:-1], weights))
    chk = (11 - (total % 11)) % 10
    return chk == int(d[-1])

def is_valid_rrn(rrn: str, use_checksum: bool = False) -> bool:
    if not is_valid_rrn_date_only(rrn):
        return False
    if use_checksum and not is_valid_rrn_checksum(rrn):
        return False
    return True

# --- 카드 (무조건 True 처리, 숫자만 추출) ---
def is_valid_card(number: str, options: dict | None = None) -> bool:
    d = _digits(number)
    # 카드번호는 15~16자리면 무조건 허용 (AMEX 15자리, 일반 16자리)
    return len(d) in (15, 16)

# --- 전화 ---
def is_valid_phone_mobile(number: str, options: dict | None = None) -> bool:
    d = _digits(number)
    return d.startswith("010") and len(d) == 11

def is_valid_phone_city(number: str, options: dict | None = None) -> bool:
    d = _digits(number)
    # 02 / 031~064 범위
    if d.startswith("02") and 9 <= len(d) <= 10:
        return True
    if d[:2] in {f"0{x}" for x in range(31, 65)} and 10 <= len(d) <= 11:
        return True
    return False

# --- 이메일 ---
def is_valid_email(addr: str, options: dict | None = None) -> bool:
    pat = re.compile(r"^[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}$")
    return bool(pat.match(addr or ""))
