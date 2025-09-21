import re
from datetime import datetime

def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")

# --- RRN ---
def is_valid_rrn_date_only(rrn: str) -> bool:
    d = _digits(rrn)
    if len(d) != 13:
        return False
    birth = d[:6]
    gender = d[6]
    try:
        y = ("20" if gender in "34" else "19") + birth[:2]
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

# --- 카드 ---
def _luhn_ok(d: str) -> bool:
    s = 0
    alt = False
    for ch in reversed(d):
        n = ord(ch) - 48
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        s += n
        alt = not alt
    return (s % 10) == 0

def is_valid_card(number: str, options: dict | None = None) -> bool:
    """
    정책:
      - 길이: 15 또는 16
      - IIN(시작대역):
          * 16자리: 4(Visa), 5(Master 51–55), 2(2221–2720 범위), 6(Discover 등) 허용
          * 15자리: 34/37 (AMEX)
      - Luhn 통과
    옵션:
      options = {"luhn": True (default), "iin": True (default)}
    """
    opts = {"luhn": True, "iin": True}
    if options:
        opts.update(options)

    d = _digits(number)
    if len(d) not in (15, 16):
        return False

    # IIN 필터
    if opts["iin"]:
        if len(d) == 16:
            if d[0] not in "2456":
                return False
            # 2xxx는 Mastercard 2-series(2221–2720)만 엄격 적용
            if d[0] == "2":
                prefix4 = int(d[:4])
                if not (2221 <= prefix4 <= 2720):
                    return False
        else:  # 15
            if not (d.startswith("34") or d.startswith("37")):
                return False

    # Luhn
    if opts["luhn"] and not _luhn_ok(d):
        return False

    return True

# --- 휴대폰 ---
def is_valid_phone_mobile(number: str, options: dict | None = None) -> bool:
    d = _digits(number)
    return d.startswith("010") and len(d) == 11

# --- 지역번호 ---
def is_valid_phone_city(number: str, options: dict | None = None) -> bool:
    d = _digits(number)
    if d.startswith("02") and 9 <= len(d) <= 10:
        return True
    if d[:2] in {f"0{x}" for x in range(31, 65)} and 10 <= len(d) <= 11:
        return True
    return False

# --- 이메일 ---
def is_valid_email(addr: str, options: dict | None = None) -> bool:
    pat = re.compile(r"^[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}$")
    return bool(pat.match(addr or ""))
