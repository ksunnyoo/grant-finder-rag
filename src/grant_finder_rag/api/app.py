"""FastAPI 앱. 서비스 객체는 서버가 시작될 때 한 번만 만들고 재사용한다."""

import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from grant_finder_rag.api.request_log import RequestLog
from grant_finder_rag.bootstrap import refuse_threshold
from grant_finder_rag.contracts.errors import LLMUnavailableError
from grant_finder_rag.contracts.models import SearchFilters
from grant_finder_rag.generation.answer import AnswerGenerator
from grant_finder_rag.retrieval.query_analyzer import CATEGORIES, REGIONS, TARGETS
from grant_finder_rag.service import AskService

logger = logging.getLogger(__name__)

CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


class FilterIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    region: list[str] = Field(default_factory=list)
    target: list[str] = Field(default_factory=list)
    biz_age: list[str] = Field(default_factory=list)
    age: int | None = None
    category: list[str] = Field(default_factory=list)
    include_closed: bool = False
    end_from: date | None = None
    end_to: date | None = None


class AskIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    question: str = Field(min_length=1, max_length=500)
    filters: FilterIn | None = None


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def to_camel_keys(value):
    if isinstance(value, dict):
        return {to_camel(k): to_camel_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_camel_keys(v) for v in value]
    return value


def to_explicit(filters: FilterIn | None, as_of: date) -> SearchFilters | None:
    if filters is None:
        return None
    given = {k: v for k, v in filters.model_dump().items() if v not in ([], None, False)}
    if not given:
        return None
    return SearchFilters(as_of_date=as_of, **given)


def record_ask(request: Request, question: str, data: dict) -> None:
    """질문 처리 결과를 요청 로그에 남긴다. 질문 내용은 글자 수만 기록한다."""
    log = getattr(request.app.state, "request_log", None)
    if log is None:
        return
    log.write(
        {
            "event": "ask",
            "question_chars": len(question),
            "refused": bool(data.get("refused")),
            "refuse_reason": data.get("refuse_reason"),
            "provider": data.get("llm_provider"),
            "latency_ms": data.get("latency_ms"),
            "stages": data.get("stages") or {},
            "sources": len(data.get("sources") or []),
        }
    )


def record_error(request: Request, code: str, exc: Exception) -> None:
    log = getattr(request.app.state, "request_log", None)
    if log is not None:
        log.write({"event": "error", "code": code, "type": type(exc).__name__, "path": request.url.path})


def create_app(
    service=None, as_of: date | None = None, request_log: RequestLog | None = None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = None
        app.state.lock = threading.Lock()
        if service is None:
            from grant_finder_rag.bootstrap import build_llm, build_retriever

            load_dotenv()
            app.state.request_log = RequestLog(
                Path(os.getenv("REQUEST_LOG_PATH", "logs/requests.jsonl"))
            )
            app.state.as_of = date.fromisoformat(
                os.getenv("AS_OF_DATE") or date.today().isoformat()
            )
            retriever, store = build_retriever(with_reranker=True)
            generator = AnswerGenerator(
                build_llm(os.getenv("LLM_PROVIDER_ORDER")),
                refuse_threshold=refuse_threshold(),
            )
            app.state.service = AskService(retriever, generator, app.state.as_of)
        else:
            app.state.service = service
            app.state.request_log = request_log
            app.state.as_of = as_of or date(2026, 11, 6)
        try:
            yield
        finally:
            if store is not None:
                store.close()

    app = FastAPI(title="grant-finder-rag", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def on_validation_error(request: Request, exc: RequestValidationError):
        record_error(request, "INVALID_REQUEST", exc)
        return error_response(400, "INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")

    @app.exception_handler(LLMUnavailableError)
    async def on_llm_unavailable(request: Request, exc: LLMUnavailableError):
        record_error(request, "LLM_UNAVAILABLE", exc)
        return error_response(
            503, "LLM_UNAVAILABLE", "답변 생성 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해 주십시오."
        )

    @app.exception_handler(Exception)
    async def on_unexpected_error(request: Request, exc: Exception):
        logger.exception("처리하지 못한 오류")
        record_error(request, "INTERNAL_ERROR", exc)
        return error_response(500, "INTERNAL_ERROR", "서버 내부 오류가 발생했습니다.")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/meta")
    def meta(request: Request):
        return {
            "asOfDate": request.app.state.as_of.isoformat(),
            "regions": list(REGIONS),
            "targets": list(TARGETS),
            "categories": list(CATEGORIES),
            "refuseThreshold": refuse_threshold(),
        }

    @app.post("/api/ask")
    def ask(body: AskIn, request: Request):
        question = body.question.strip()
        if not question:
            return error_response(400, "INVALID_REQUEST", "질문을 입력해 주십시오.")
        explicit = to_explicit(body.filters, request.app.state.as_of)
        with request.app.state.lock:
            result = request.app.state.service.ask(question, explicit)
        data = result.model_dump(mode="json")
        record_ask(request, question, data)
        return to_camel_keys(data)

    return app


app = create_app()
