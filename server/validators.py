import re
from datetime import date, datetime

_RRN_RE = re.compile(r'^(\d{6})-([1-8]\d{6})$')

def _infer_century(year2: int, gender_digit: int) -> int:
    """
    주민번호 7번째 자리(성별/세대 코드)로 세기 추정
    1,2,5,6 -> 1900대 / 3,4,7,8 -> 2000대
    """
    if gender_digit in (1,2,5,6):
        return 1900 + year2
    elif gender_digit in (3,4,7,8):
        return 2000 + year2
    return 1900 + year2 

def _valid_date_from_yyMMdd(yyMMdd: str, gender_digit: int) -> bool:
    yy = int(yyMMdd[0:2])
    mm = int(yyMMdd[2:4])
    dd = int(yyMMdd[4:6])
    yyyy = _infer_century(yy, gender_digit)
    try:
        d = date(yyyy, mm, dd)
        if d > date.today():
            return False
        return True
    except ValueError:
        return False

def is_valid_rrn_date_only(rrn: str) -> bool:
    """
    날짜 유효성만 확인 (체크섬 미사용)
    - 포맷: YYMMDD-XXXXXXX
    - 7번째 자리(성별/세대 코드)로 세기 추정
    """
    m = _RRN_RE.match(rrn)
    if not m:
        return False
    front, back = m.group(1), m.group(2)
    gender_digit = int(back[0])
    return _valid_date_from_yyMMdd(front, gender_digit)

def is_valid_rrn_checksum(rrn: str) -> bool:

    m = _RRN_RE.match(rrn)
    if not m:
        return False
    s = (m.group(1) + m.group(2)).replace("-", "")
    # 13자리: 앞 12자리 * 가중치 후 검증
    if len(s) != 13:
        return False
    digits = [int(c) for c in s]
    weights = [2,3,4,5,6,7,8,9,2,3,4,5]  # 앞 12자리에 곱함
    total = sum(d * w for d, w in zip(digits[:12], weights))
    check = (11 - (total % 11)) % 10
    return check == digits[12]

def is_valid_rrn(rrn: str, use_checksum: bool = False) -> bool:
    """
    주민등록번호 종합 검증
    - 항상: 포맷 + 날짜 유효성
    - 옵션: 체크섬
    """
    if not is_valid_rrn_date_only(rrn):
        return False
    return is_valid_rrn_checksum(rrn) if use_checksum else True
