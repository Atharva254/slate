import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi import Path as PathParameter
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.ai import AIError, ContentAssistant, create_assistant
from backend.database import Database
from backend.schemas import Entry, EntryCreate, EntryPage

ROOT = Path(__file__).resolve().parent.parent


def create_app(database_path: Path | None = None, ai: ContentAssistant | None = None) -> FastAPI:
    """Build the API; tests inject an isolated database and provider transport."""
    load_dotenv(ROOT / ".env")
    database = Database(
        database_path or Path(os.getenv("DATABASE_PATH", str(ROOT / "data" / "entries.db")))
    )
    assistant = ai if ai is not None else create_assistant()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await run_in_threadpool(database.initialize)
        yield

    app = FastAPI(title="Small AI Content Assistant", version="1.0.0", lifespan=lifespan)

    @app.exception_handler(AIError)
    async def ai_error(request: Request, exc: AIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not echo submitted text or Pydantic's raw input in error bodies/logs.
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": "Use text containing 1-10,000 characters and valid pagination parameters.",
                }
            },
        )

    @app.exception_handler(sqlite3.Error)
    async def database_error(request: Request, exc: sqlite3.Error):
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "storage_unavailable",
                    "message": "Storage is unavailable. Refresh saved entries before retrying your submission.",
                }
            },
        )

    @app.get("/health")
    def health():
        return {"status": "ok", **assistant.public_config()}

    @app.post("/entries", response_model=Entry, status_code=201)
    async def create_entry(body: EntryCreate):
        result = await assistant.generate(body.text)
        # Never hold a SQLite connection or transaction open during the model call.
        return await run_in_threadpool(database.save, body.text, result)

    @app.get("/entries", response_model=EntryPage)
    def list_entries(
        limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=2**63 - 1)
    ):
        return database.list(limit, offset)

    @app.get("/entries/{entry_id}", response_model=Entry)
    def get_entry(entry_id: int = PathParameter(ge=1, le=2**63 - 1)):
        entry = database.get(entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        return entry

    @app.delete("/entries/{entry_id}", status_code=204)
    def delete_entry(entry_id: int = PathParameter(ge=1, le=2**63 - 1)):
        if not database.delete(entry_id):
            raise HTTPException(status_code=404, detail="Entry not found")
        return Response(status_code=204)

    return app


app = create_app()
