import re
from .validators import (
    is_valid_rrn, is_valid_phone_mobile, is_valid_phone_city,
    is_valid_email, is_valid_card, is_valid_bizno
)

RULES: dict[str, dict] = {
    "rrn": {
        "id": "rrn",
        "pattern": re.compile(r"\b\d{6}-[1-8]\d{6}\b"),
        "validate": lambda s, opts=None: is_valid_rrn(s, bool(opts and opts.get("rrn_checksum"))),
    },
    "phone_mobile": {
        "id": "phone_mobile",
        "pattern": re.compile(r"\b010[-.\s]?\d{3,4}[-.\s]?\d{4}\b"),
        "validate": is_valid_phone_mobile,
    },
    "phone_city": {
        "id": "phone_city",
        "pattern": re.compile(r"\b(?:02|0(?:3[1-3]|4[1-4]|5[1-5]|6[1-4]))[-.\s]?\d{3,4}[-.\s]?\d{4}\b"),
        "validate": is_valid_phone_city,
    },
    "email": {
        "id": "email",
        "pattern": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "validate": is_valid_email,
    },
    "card": {
        "id": "card",
        "pattern": re.compile(r"(?:\d[ -]?){13,19}"),
        "validate": is_valid_card,
    },
    "bizno": {
        "id": "bizno",
        "pattern": re.compile(r"\b\d{3}-?\d{2}-?\d{5}\b"),
        "validate": is_valid_bizno,
    },
}
