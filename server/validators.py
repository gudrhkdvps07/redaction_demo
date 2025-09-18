import re
from datetime import date
from .normalize import digits_only

_RRN_RE = re.compile(r"^(\d{6})-([0-9]{7})$")

def _infer_century(year2: int, s7: int) -> int | None:
    if s7 in (1,2,5,6): return 1900 + year2
    if s7 in (3,4,7,8): return 2000 + year2
    return None

def _valid_date_yyyymmdd(yyMMdd: str, s7: int) -> bool:
    yy, mm, dd = int(yyMMdd[:2]), int(yyMMdd[2:4]), int(yyMMdd[4:6])
    yyyy = _infer_century(yy, s7)
    if yyyy is None: return False
    try:
        d = date(yyyy, mm, dd)
    except ValueError:
        return False
    return d <= date.today()

def is_valid_rrn_date_only(rrn: str) -> bool:
    m = _RRN_RE.match(rrn or "")
    if not m: return False
    return _valid_date_yyyymmdd(m.group(1), int(m.group(2)[0]))

def is_valid_rrn_checksum(rrn: str) -> bool:
    m = _RRN_RE.match(rrn or "")
    if not m: return False
    s = m.group(1) + m.group(2)
    if len(s) != 13 or not s.isdigit(): return False
    digits = [ord(c) - 48 for c in s]
    weights = [2,3,4,5,6,7,8,9,2,3,4,5]
    total = sum(digits[i]*weights[i] for i in range(12))
    check = (11 - (total % 11)) % 10
    return check == digits[12]

def is_valid_rrn(rrn: str, use_checksum: bool = False) -> bool:
    if not is_valid_rrn_date_only(rrn): 
        return False
    return is_valid_rrn_checksum(rrn) if use_checksum else True

# -------------------------------
# 통일된 validate 함수 시그니처
# -------------------------------

_AREACODE_RE = re.compile(r"^(?:02|0(?:3[1-3]|4[1-4]|5[1-5]|6[1-4]))")

def is_valid_phone_mobile(number: str, options: dict | None = None) -> bool:
    d = digits_only(number)
    return d.startswith("010") and len(d) == 11

def is_valid_phone_city(number: str, options: dict | None = None) -> bool:
    d = digits_only(number)
    if not _AREACODE_RE.match(d): 
        return False
    return (len(d) in (9,10)) if d.startswith("02") else (len(d) in (10,11))

_EMAIL_STRICT = re.compile(r"^[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}$")

def is_valid_email(addr: str, options: dict | None = None) -> bool:
    return bool(_EMAIL_STRICT.match((addr or "").strip()))

def _luhn_ok(number: str) -> bool:
    d = digits_only(number)
    if not (13 <= len(d) <= 19): 
        return False
    total, dbl = 0, False
    for ch in reversed(d):
        n = ord(ch) - 48
        if dbl:
            n *= 2
            if n > 9: 
                n -= 9
        total += n
        dbl = not dbl
    return total % 10 == 0

def is_valid_card(number: str, options: dict | None = None) -> bool:
    return _luhn_ok(number)

def is_valid_bizno(bno: str, options: dict | None = None) -> bool:
    d = digits_only(bno)
    if len(d) != 10: 
        return False
    nums = [ord(c) - 48 for c in d]
    ws = [1,3,7,1,3,7,1,3,5]
    s = sum(nums[i]*ws[i] for i in range(9))
    s += (nums[8]*5) // 10
    check = (10 - (s % 10)) % 10
    return check == nums[9]
