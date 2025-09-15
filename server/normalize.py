"""
PDF에서 뽑은 텍스트를 규칙적으로 정리해서 정규식 매칭 정확도를 높여주기 위해 만들어짐
"""

import re
import unicodedata


_ZERO_WIDTH = r"\u200B\u200C\u200D\u2060\ufeff" #비가시 제로폭/제어문자들
_DASHES =  "\u2010\u2011\u2012\u2013\u2014\u2212\ufe63\u2043" #하이픈/대시를 아스키 '-'로 통일할 때 쓰는 패턴
_NBSP = "\u00A0\u2007\u202F"    #NBSP(공백처럼 보이지만 다른 문자) 계열

def strip_invisible(s: str) -> str:
    '''제로폭, 필요하지 않은 제어문자 제거(개행은 유지)'''
    #제어문자 중 탭/개행 제외 제거
    s = re.sub(rf"[{_ZERO_WIDTH}]", "", s)
    s = re.sub(r"[^\S\r\n\t]", " ", s)  #이상한 공백류는 보통 공백으로
    return s

def normalize_text(s: str) -> str:
    """
    정규화 파이프라인:
    1. 유니코드 정규화
    2. 줄바꿈 통일 \r\n, \r -> \n
    3. 제로폭/ 숨은 공백 제거, NESP류 -> 일반 공백
    4. 하이픈/ 대시류 -> '-'
    5. 공백 정리(연속 공백 축약, 라인 끝 공백 제거)
    """

    if not s:
        return s
    
    # 1. 유니코드 정규화
    s = unicodedata.normalize("NFKC", s)

    # 2. 줄바꿈 통일
    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # 3. 보이지 않는 문자, 특수공백 정리
    s = strip_invisible(s)
    s = re.sub(rf"[{_NBSP}]", " ", s)

    # 4. 하이픈/ 대시 통일
    s = re.sub(rf"[{_DASHES}]", "-", s)

    # 5. 공백 정리
    s = s.replace("\t", " ")
    s = re.sub(r"[ \f\v]+", " ", s)    #연속 공백은 하나로 (개행은 보존함)
    s = "\n".join(line.rstrip() for line in s.split("\n"))  #줄마다 끝 공백을 제거함

    return s

def digits_only(s: str) -> str:
    ''' 검증기(유효한 숫자인지 검증하는)에서 쓸 숫자만 추출'''

    return re.sub(r"\D", "", s)