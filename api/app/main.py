"""FastAPI application entry point.

Run:  uvicorn app.main:app --reload --port 8000     (from the api/ directory)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from . import models
from .config import get_settings
from .content.loader import ContentError, load_content, seed
from .db import Base, SessionLocal, engine
from .routers import account, annotations, curriculum, forge, learning, practice, projects

log = logging.getLogger("academy")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        empty = (db.scalar(select(func.count()).select_from(models.Lesson)) or 0) == 0
        if empty:
            try:
                counts = seed(db, load_content())
                log.info("Seeded content: %s", counts)
            except ContentError as e:  # fail loudly: the platform is useless without valid content
                log.error("Content validation failed:\n%s", e)
                raise
    yield


app = FastAPI(title="AI Engineering Academy API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=get_settings().cors_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
def health():
    return {"status": "ok"}


for r in (curriculum.router, learning.router, practice.router, projects.router, forge.router, account.router, annotations.router):
    app.include_router(r, prefix="/api")
