# server/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 라우터 임포트 
from .routes.text import router as text_router          
from .routes.redaction import router as redact_router   

app = FastAPI(title="Anonymizer API (Demo)", version="1.0.0")

# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/v1/health")
def v1_health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}

# 라우터 등록
app.include_router(text_router)
app.include_router(redact_router)
