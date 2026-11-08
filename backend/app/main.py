import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.congress import router as congress_router
from app.api.congress_collections import router as congress_collections_router
from app.api.journal import router as journal_router
from app.api.onboarding import router as onboarding_router
from app.api.research import router as research_router
from app.api.routes import router
from app.api.strategy_inputs import router as strategy_inputs_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine
from app.llm.chat_routes import router as chat_router
from app.llm.routes import router as llm_router

configure_logging()
app = FastAPI(title="Trading Lab", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)
app.include_router(router)
app.include_router(research_router)
app.include_router(journal_router)
app.include_router(congress_router)
app.include_router(congress_collections_router)
app.include_router(strategy_inputs_router)
app.include_router(llm_router)
app.include_router(chat_router)
app.include_router(onboarding_router)
logger = logging.getLogger(__name__)


@app.middleware("http")
async def request_size(request: Request, call_next):
    total = 0
    chunks = []
    async for chunk in request.stream():
        total += len(chunk)
        if total > settings().max_request_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": {
                        "code": "request_too_large",
                        "message": "Request exceeds configured size limit",
                    }
                },
            )
        chunks.append(chunk)
    request._body = b"".join(chunks)
    return await call_next(request)


@app.exception_handler(ValueError)
@app.exception_handler(ValidationError)
async def invalid(request: Request, exc):
    logger.info("validation_failed")
    return JSONResponse(
        status_code=422, content={"detail": {"code": "validation_error", "message": str(exc)}}
    )


@app.exception_handler(RequestValidationError)
async def request_invalid(request: Request, exc):
    logger.info("request_validation_failed")
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": errors}))


@app.exception_handler(IntegrityError)
async def conflict(request: Request, exc):
    return JSONResponse(
        status_code=409,
        content={
            "detail": {
                "code": "conflict",
                "message": "Concurrent update or duplicate resource; reload and retry",
            }
        },
    )


@app.get("/api/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(text("SELECT version_num FROM alembic_version"))
        return {"status": "ok", "database": "connected"}
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "message": "Database unavailable or migrations required",
            },
        )
