import io
import re
import olefile


ASCII_PRINT = (0x0020, 0x007E)
HANGUL_SYLL = (0xAC00, 0xD7A3)
HANGUL_COMP = (0x3130, 0x318F)
HANGUL_JAMO = (0x1100, 0x11FF)
WHITES      = {0x0009, 0x000A, 0x000D}

# 템플릿 / 마스터 / 폰트 / 오브젝트명 제거
NOISE_SUBSTR = [
    "___ppt", "textbox", "office", "slide", "shape", "font",
    "제목 개체 틀", "텍스트 개체 틀", "마스터", "제목 스타일", "텍스트 스타일",
    "수준", "날짜 개체 틀", "바닥글 개체 틀", "슬라이드 번호 개체 틀", "테마",
    "맑은 고딕", "arial", "gulim", "dotum", "batang", "malgun", "nanum",
    "calibri", "times new roman",
]

ONLY_PUNCT = re.compile(r"^[\s_\-–—=,.+:/\\|(){}\[\]<>~`!@#$%^&*]+$")
MEANING = re.compile(r"[가-힣A-Za-z0-9]")

KEEP_HINTS = [
    "이름", "전번", "전화", "집번", "번호", "이메일",
    "주민등록", "외국인", "여권", "운전면허", "카드",
    "신여권", "구여권",
]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
DIGITISH = re.compile(r"\d")

# === 1️⃣ 허용 문자 범위 설정 ===
def _is_allowed_cp(cp: int) -> bool:
    if cp in WHITES:
        return True
    if ASCII_PRINT[0] <= cp <= ASCII_PRINT[1]:
        return True
    if HANGUL_SYLL[0] <= cp <= HANGUL_SYLL[1]:
        return True
    if HANGUL_COMP[0] <= cp <= HANGUL_COMP[1]:
        return True
    if HANGUL_JAMO[0] <= cp <= HANGUL_JAMO[1]:
        return True
    return False  # 한자/잡문 영역 제거


# === 2️⃣ 문자열 정리 ===
def _collapse(s: str) -> str:
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" ?\n ?", "\n", s)
    return s.strip()


def _is_noise_line(s: str) -> bool:
    ls = s.lower()
    for t in NOISE_SUBSTR:
        if t in ls:
            return True
    if ONLY_PUNCT.match(s):
        return True
    return False


def _is_real_content(s: str) -> bool:
    """전화/주민/이메일/한글+숫자/라벨형 텍스트만 통과"""
    if EMAIL_RE.search(s):
        return True
    if DIGITISH.search(s):
        return True
    for h in KEEP_HINTS:
        if h in s:
            return True
    # 한글과 영문/숫자 혼합된 경우
    has_hangul = any(HANGUL_SYLL[0] <= ord(ch) <= HANGUL_SYLL[1] for ch in s)
    has_ascii = any("a" <= ch.lower() <= "z" for ch in s)
    if has_hangul and has_ascii:
        return True
    return False


def _is_garbage_pattern(s: str) -> bool:
    """
    잔여 쓰레기 필터:
      - 길이 <= 3 이면 버림
      - 숫자/영문 없는 이상한 조합(예: '픁r쑩', 'P찖', '뜀J', 'Z챕') 버림
      - 한글/영문 비율이 너무 낮은 라인 버림
    """
    if len(s) <= 3:
        return True
    if not MEANING.search(s):
        return True
    hangul_cnt = sum(1 for ch in s if "가" <= ch <= "힣")
    alpha_cnt = sum(1 for ch in s if ch.isalpha())
    digit_cnt = sum(1 for ch in s if ch.isdigit())
    # 한글/영문/숫자 합쳐서 전체의 30% 미만이면 잡문
    if (hangul_cnt + alpha_cnt + digit_cnt) / max(len(s), 1) < 0.3:
        return True
    return False


# === 3️⃣ UTF-16LE 바이트 스캔 ===
def _utf16_runs_from(buf: bytes, start_offset: int) -> list[str]:
    out = []
    i, n = start_offset, len(buf)
    run = []

    def flush():
        nonlocal run
        if not run:
            return
        s = _collapse("".join(run))
        run = []
        if len(s) < 2:
            return
        if _is_noise_line(s):
            return
        if _is_garbage_pattern(s):
            return
        if not _is_real_content(s):
            return
        out.append(s)

    while i + 1 < n:
        cp = buf[i] | (buf[i + 1] << 8)
        if _is_allowed_cp(cp):
            if cp in (0x000A, 0x000D):
                run.append("\n")
            elif cp == 0x0009:
                run.append("\t")
            else:
                run.append(chr(cp))
        else:
            flush()
        i += 2
    flush()
    return out


# === 4️⃣ 메인 추출 함수 ===
def extract_text(file_bytes: bytes) -> dict:
    """
    PPT(.ppt) 텍스트 추출 – 실내용만 남기기 (마스터/폰트/이진 조각 제거)
    """
    with olefile.OleFileIO(io.BytesIO(file_bytes)) as ole:
        if not ole.exists("PowerPoint Document"):
            raise ValueError("PowerPoint Document 스트림이 없습니다.")
        buf = ole.openstream("PowerPoint Document").read()

    runs = _utf16_runs_from(buf, 0) + _utf16_runs_from(buf, 1)
    seen, clean = set(), []
    for s in runs:
        if s not in seen:
            seen.add(s)
            clean.append(s)

    full_text = "\n".join(clean)
    return {"full_text": full_text, "pages": [{"page": 1, "text": full_text}]}
