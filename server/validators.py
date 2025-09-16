import re
from datetime import date
from typing import Optional

# ---------- 공통 유틸 ----------
_ONLY_DIGITS = re.compile(r"\D+")

def _digits_only(s: str) -> str:
    return _ONLY_DIGITS.sub("", s or "")

# ---------- 1) 주민등록번호 ----------
# 형식: YYMMDD-XXXXXXX (하이픈 강제). 무하이픈까지 허용하려면 패턴의 '-'를 '-?'로 바꾸세요.
_RRN_RE = re.compile(r'^(\d{6})-([0-9]{7})$')

def _infer_century(year2: int, s7: int) -> Optional[int]:
    """7번째 자리(성별/세기/내·외국인 코드)로 세기 추정"""
    if s7 in (1, 2, 5, 6):      # 1900~1999 (내국인/외국인)
        base = 1900
    elif s7 in (3, 4, 7, 8):    # 2000~2099 (내국인/외국인)
        base = 2000
    else:
        return None
    return base + year2

def _valid_date_from_yyMMdd(yyMMdd: str, s7: int) -> bool:
    yy = int(yyMMdd[0:2]); mm = int(yyMMdd[2:4]); dd = int(yyMMdd[4:6])
    yyyy = _infer_century(yy, s7)
    if yyyy is None:
        return False
    try:
        d = date(yyyy, mm, dd)
        return d <= date.today()   # 미래일자 차단
    except ValueError:
        return False

def is_valid_rrn_date_only(rrn: str) -> bool:
    """주민등록번호: 형식 + 생년월일 유효성만 검사 (체크섬 미적용)"""
    m = _RRN_RE.match(rrn or "")
    if not m:
        return False
    front, back = m.group(1), m.group(2)
    s7 = int(back[0])
    return _valid_date_from_yyMMdd(front, s7)

def is_valid_rrn_checksum(rrn: str) -> bool:
    """
    주민등록번호 체크섬 검사.
    주의: 2020-10 이후 새로 부여된 번호는 뒤 6자리가 무작위화되어
    기존 체크섬 규칙이 항상 성립하지 않을 수 있습니다.
    """
    m = _RRN_RE.match(rrn or "")
    if not m:
        return False
    s = m.group(1) + m.group(2)  # 13자리
    if len(s) != 13 or not s.isdigit():
        return False
    digits = [int(c) for c in s]
    weights = [2,3,4,5,6,7,8,9,2,3,4,5]  # 앞 12자리에 곱함
    total = sum(d * w for d, w in zip(digits[:12], weights))
    check = (11 - (total % 11)) % 10
    return check == digits[12]

def is_valid_rrn(rrn: str, *, use_checksum: bool = False) -> bool:
    """
    주민등록번호 종합 검증
    - 항상: 포맷 + 날짜 유효성
    - 옵션(use_checksum=True): 체크섬까지 검증
    (2020-10 이후 부여분은 무작위화로 불일치 가능)
    """
    if not is_valid_rrn_date_only(rrn):
        return False
    return is_valid_rrn_checksum(rrn) if use_checksum else True

# ---------- 2) 휴대전화(010) ----------
# 요구사항이 "국내 010만"이라면 길이 11(010 + 8자리) 검사로 충분합니다.
def is_valid_phone_mobile(number: str) -> bool:
    d = _digits_only(number)
    return len(d) == 11 and d.startswith("010")

# ---------- 3) 지역전화(02, 031~064) ----------
# 02는 가입자번호 7자리 또는 8자리 → 전체 9자리 또는 10자리
# 나머지 지역(0xx)은 가입자번호 7자리 또는 8자리 → 전체 10자리 또는 11자리
_AREACODE_RE = re.compile(r'^(?:02|0(?:3[1-3]|4[1-4]|5[1-5]|6[1-4]))')

def is_valid_phone_city(number: str) -> bool:
    d = _digits_only(number)
    if not _AREACODE_RE.match(d):
        return False
    if d.startswith("02"):
        return len(d) in (9, 10)
    else:
        return len(d) in (10, 11)

# ---------- 4) 이메일(현실 친화적 문법 검사) ----------
_EMAIL_RE = re.compile(
    r'^[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}$'
)

def is_valid_email(addr: str) -> bool:
    """RFC 전체를 다 포괄하지는 않음(국제화 도메인/희귀 케이스 제외)."""
    return bool(_EMAIL_RE.match((addr or "").strip()))

# ---------- 5) 카드번호(Luhn, 13~19자리) ----------
def luhn_check(number: str) -> bool:
    d = _digits_only(number)
    if not (13 <= len(d) <= 19):
        return False
    total = 0
    reverse = d[::-1]
    for i, ch in enumerate(reverse):
        n = ord(ch) - 48
        if i % 2 == 1:  # 오른쪽부터 짝수번째(0-index 기준) 자리 더블
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

def is_valid_card(number: str) -> bool:
    return luhn_check(number)

# ---------- 6) 사업자등록번호(10자리, 체크섬) ----------
def is_valid_bizno(bno: str) -> bool:
    d = _digits_only(bno)
    if len(d) != 10:
        return False
    nums = [int(c) for c in d]
    weights = [1,3,7,1,3,7,1,3,5]
    s = sum(n * w for n, w in zip(nums[:9], weights))
    s += (nums[8] * 5) // 10  # 9번째(인덱스 8) 보정
    check = (10 - (s % 10)) % 10
    return check == nums[9]
