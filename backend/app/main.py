import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.api import repositories, analysis, testing, findings, reports

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("security_platform")

settings = get_settings()

app = FastAPI(
    title="World Monitor Security Assessment Platform (Basic Model)",
    description="Repository-aware, evidence-driven authorized security assessment platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repositories.router)
app.include_router(analysis.router)
app.include_router(testing.router)
app.include_router(findings.router)
app.include_router(reports.router)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized. Allowed target hosts: %s", settings.ALLOWED_TARGET_HOSTS)


@app.get("/")
def root():
    return {
        "name": "World Monitor Security Assessment Platform",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
