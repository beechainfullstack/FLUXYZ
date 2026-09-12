import asyncio
import logging
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import monotonic
from typing import Literal

import httpx
import pymysql
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from fluxyz import agent, store
from fluxyz.ingest import cycle
from fluxyz.models import Dashboard
from fluxyz.providers import ProviderError
from fluxyz.service import dashboard
from fluxyz.settings import settings

logger = logging.getLogger("fluxyz")
ready = False
chat_lock = asyncio.Semaphore(2)
requests: dict[str, deque[float]] = defaultdict(deque)
daily_count = 0
count_day = ""


async def worker() -> None:
    global ready
    while not ready:
        try:
            await asyncio.to_thread(store.initialize)
            ready = True
        except pymysql.MySQLError:
            logger.warning("StarRocks is not ready; retrying in 15 seconds")
            await asyncio.sleep(15)
    while settings.ingestion_enabled:
        try:
            await asyncio.to_thread(cycle)
        except Exception:
            logger.error("Ingestion cycle failed; retained stored data; retrying next cycle")
        await asyncio.sleep(settings.poll_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(worker())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="fluxyz", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    if not ready:
        raise HTTPException(503, "StarRocks is initializing")
    try:
        store.query("SELECT 1")
    except pymysql.MySQLError as error:
        raise HTTPException(503, "StarRocks is temporarily unavailable") from error
    return {"status": "ok", "database": "starrocks"}


@app.get("/api/dashboard", response_model=Dashboard)
def get_dashboard(range: Literal["1d", "1w", "1m"] = "1w") -> Dashboard:
    if not ready:
        raise HTTPException(503, "Connecting to StarRocks. Please retry shortly.")
    try:
        return dashboard(range)
    except pymysql.MySQLError as error:
        raise HTTPException(503, "Stored observations are temporarily unavailable.") from error


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1200)
    range: Literal["1d", "1w", "1m"] = "1w"


class ChatResponse(BaseModel):
    answer: str
    model: str
    grounded_at: datetime
    sources: list[str]


def rate_limit(ip: str) -> None:
    global daily_count, count_day
    now = monotonic()
    for key in list(requests):
        if not requests[key] or now - requests[key][-1] > 60:
            del requests[key]
    queue = requests[ip]
    while queue and now - queue[0] > 60:
        queue.popleft()
    today = datetime.now(timezone.utc).date().isoformat()
    if today != count_day:
        count_day, daily_count = today, 0
    if len(queue) >= 5 or daily_count >= settings.chat_daily_limit:
        raise HTTPException(429, "Agent request limit reached. Please try again later.")
    queue.append(now)
    daily_count += 1


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    if not ready:
        raise HTTPException(503, "The observatory is still connecting to StarRocks.")
    rate_limit(request.client.host if request.client else "unknown")
    async with chat_lock:
        try:
            data = await asyncio.to_thread(dashboard, body.range)
            if not any(data.prices.values()):
                raise HTTPException(503, "No market observations have been collected yet.")

            def answer() -> str:
                with httpx.Client() as client:
                    return agent.generate(client, data, body.question)

            text = await asyncio.to_thread(answer)
        except (httpx.HTTPError, ValidationError, ProviderError) as error:
            raise HTTPException(
                503, "Gemini is temporarily unavailable. No simulated answer was generated."
            ) from error
        except pymysql.MySQLError as error:
            raise HTTPException(503, "Stored observations are temporarily unavailable.") from error
    return ChatResponse(
        answer=text,
        model=settings.gemini_model,
        grounded_at=data.generated_at,
        sources=["StarRocks", "Twelve Data", "EIA", "NOAA SWPC", "Astronomical date math"],
    )
