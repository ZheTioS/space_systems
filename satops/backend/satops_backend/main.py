"""SatOps Dashboard — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from satops_backend.api import link_budget, observations, sdr, tracking, websocket
from satops_backend.config import settings
from satops_backend.db import init_db
from satops_backend.services import tracking as tracking_service
from satops_backend.services.sdr import sdr_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing SatOps backend...")
    await init_db()
    await tracking_service.load_tles()
    await sdr_service.connect()
    await sdr_service.start_streaming()
    logger.info("SatOps backend ready")
    yield
    # Shutdown
    await sdr_service.disconnect()
    logger.info("SatOps backend shut down")


app = FastAPI(
    title="SatOps Dashboard",
    description="Satellite Communications Ground Segment API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(sdr.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(link_budget.router, prefix="/api")
app.include_router(observations.router, prefix="/api")

# WebSocket
app.include_router(websocket.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "sdr": sdr_service.status.model_dump()}
