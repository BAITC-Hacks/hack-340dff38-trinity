import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from .core.config import settings
from .core.database import get_db
from .routers import auth, problems, submissions, people, ai, admin

app = FastAPI(
    title="AI Sana API",
    version="1.0.0",
    description="Demo-only business/student collaboration platform",
)
cfg = settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cfg.cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

for router in (
    auth.router,
    problems.router,
    submissions.router,
    people.router,
    ai.router,
    admin.router,
):
    app.include_router(router, prefix="/api")


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "aiMode": cfg.ai_mode,
        "demoTools": cfg.demo_tools_enabled,
        "demoAuth": cfg.demo_auth_enabled,
    }


@app.exception_handler(IntegrityError)
async def integrity_error(_request, _exc):
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Данные уже изменены другим запросом или такая запись существует. Обновите страницу."
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(_request, _exc):
    logging.getLogger(__name__).error("Database request failed; details suppressed")
    return JSONResponse(
        status_code=503,
        content={"detail": "База данных временно недоступна. Повторите запрос позже."},
    )


@app.exception_handler(Exception)
async def unexpected_error(_request, _exc):
    logging.getLogger(__name__).error("Unexpected request failure; details suppressed")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Не удалось выполнить операцию. Обновите страницу и повторите позже."
        },
    )
