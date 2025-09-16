from __future__ import annotations
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .normalize import normalize_text
from .extract_text import extract_pdf_text, extract_txt_text
from .redac_rules import RULES

app = FastAPI(title="De-ID Inspector API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class MatchRequest(BaseModel):
    text: str = Field(..., min_length=1)
    rules: List[str] | None = None
    options: Dict[str, Any] | None = None
    normalize: bool = True

class MatchItem(BaseModel):
    rule: str; value: str; valid: bool; index: int; end: int; context: str

class MatchResponse(BaseModel):
    counts: Dict[str, int]
    items: List[MatchItem]

@app.get("/health")
def health(): return {"ok": True}

@app.get("/rules")
def list_rules(): return {"rules": list(RULES.keys())}

@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    data = await file.read()
    if not data: raise HTTPException(400, "empty file")
    name = (file.filename or "").lower()
    if name.endswith(".pdf") or (file.content_type == "application/pdf"):
        res = extract_pdf_text(data)
    else:
        res = extract_txt_text(data)
    return {"full_text": res["full_text"], "pages": res["pages"]}

def _ctx(s: str, a: int, b: int, pad: int = 25) -> str:
    L = max(0, a - pad); R = min(len(s), b + pad)
    return s[L:a] + "【" + s[a:b] + "】" + s[b:R]

@app.post("/match", response_model=MatchResponse)
def match(req: MatchRequest):
    text = normalize_text(req.text) if req.normalize else req.text
    picked = req.rules or list(RULES.keys())
    options = req.options or {}

    results = []
    for rid in picked:
        rule = RULES.get(rid)
        if not rule: continue
        pattern = rule["pattern"]; validate = rule["validate"]
        for m in pattern.finditer(text):
            value = m.group(0)
            if rid == "card":  # 경계 보정
                prev = text[m.start()-1] if m.start()>0 else ""
                nxt  = text[m.end()] if m.end()<len(text) else ""
                if prev.isdigit() or nxt.isdigit(): continue
            ok = bool(validate(value, options)) if callable(validate) else True
            results.append({
                "rule": rid, "value": value, "valid": ok,
                "index": m.start(), "end": m.end(),
                "context": _ctx(text, m.start(), m.end())
            })

    counts = {rid: sum(1 for r in results if r["rule"] == rid) for rid in picked}
    items = [MatchItem(**r) for r in results]
    return MatchResponse(counts=counts, items=items)
