import re
from datetime import datetime

# --------------------------------------
# 공통 유틸
# --------------------------------------
def _digits(s: str) -> str:
    """숫자만 추출"""
    return re.sub(r"\D", "", s or "")


# --------------------------------------
# 날짜 검증
# --------------------------------------
def is_valid_date6(digits: str) -> bool:
    """YYMMDD 형식 날짜 유효성 검사"""
    try:
        datetime.strptime(digits, "%y%m%d")
        return True
    except ValueError:
        return False


# --------------------------------------
# 주민등록번호 (내국인)
# --------------------------------------
def is_valid_rrn(rrn: str, opts: dict | None = None) -> bool:
    """주민등록번호 검증 (2020년 이후 발급분은 checksum 없음)"""
    d = _digits(rrn)
    if len(d) != 13:
        return False
    if not is_valid_date6(d[:6]):
        return False

    # 옵션으로 checksum 사용 여부 결정
    use_checksum = (opts or {}).get("rrn_checksum", True)
    if use_checksum and not is_valid_rrn_checksum(d):
        return False

    return True


# --------------------------------------
# 외국인등록번호
# --------------------------------------
def is_valid_fgn(fgn: str, opts: dict | None = None) -> bool:
    """외국인등록번호 검증 (2020년 이후 발급분은 checksum 없음)"""
    d = _digits(fgn)
    if len(d) != 13:
        return False
    if not is_valid_date6(d[:6]):
        return False
    if d[6] not in "5678":  # 외국인 식별 코드
        return False

    use_checksum = (opts or {}).get("fgn_checksum", True)
    if use_checksum and not is_valid_rrn_checksum(d):
        return False

    return True


def is_valid_rrn_checksum(rrn: str) -> bool:
    """주민등록번호/외국인번호 checksum 검증 (2020년 이전 발급분)"""
    d = _digits(rrn)
    if len(d) != 13:
        return False
    weights = [2,3,4,5,6,7,8,9,2,3,4,5]
    total = sum(int(x) * w for x, w in zip(d[:-1], weights))
    chk = (11 - (total % 11)) % 10
    return chk == int(d[-1])


# --------------------------------------
# 카드번호
# --------------------------------------
def _luhn_ok(d: str) -> bool:
    """Luhn 알고리즘"""
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
    """신용카드 번호 검증"""
    opts = {"luhn": True, "iin": True}
    if options:
        opts.update(options)

    d = _digits(number)
    if len(d) not in (15, 16):
        return False

    if opts["iin"]:
        if len(d) == 16:
            prefix2 = int(d[:2]) if d[:2].isdigit() else None
            prefix4 = int(d[:4]) if d[:4].isdigit() else None

            if d[0] == "4":        # Visa
                pass
            elif d[0] == "5" and 51 <= int(d[:2]) <= 55:  # Master
                pass
            elif d[0] == "2" and 2221 <= prefix4 <= 2720:  # Master 2-series
                pass
            elif d[0] == "6":      # Discover
                pass
            elif d[0] == "9":      # 국내 카드 BIN 허용
                pass
            elif prefix2 == 35:    # JCB
                pass
            else:
                return False
        else:  # 15자리 → Amex
            if not (d.startswith("34") or d.startswith("37")):
                return False

    if opts["luhn"] and not _luhn_ok(d):
        return False

    return True


# --------------------------------------
# 전화번호
# --------------------------------------
def is_valid_phone_mobile(number: str, options: dict | None = None) -> bool:
    """휴대폰 번호 검증"""
    d = _digits(number)
    return d.startswith("010") and len(d) == 11


def is_valid_phone_city(number: str, options: dict | None = None) -> bool:
    """지역번호 유선 전화 검증"""
    d = _digits(number)
    if d.startswith("02") and 9 <= len(d) <= 10:
        return True
    if d[:2] in {f"0{x}" for x in range(31, 65)} and 10 <= len(d) <= 11:
        return True
    return False


# --------------------------------------
# 이메일
# --------------------------------------
def is_valid_email(addr: str, options: dict | None = None) -> bool:
    """이메일 주소 검증"""
    pat = re.compile(r"^[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}$")
    return bool(pat.match(addr or ""))

