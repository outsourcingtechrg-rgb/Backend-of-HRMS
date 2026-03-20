from fastapi import FastAPI
import logging
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, test_db_connection
from app.models import Base  # ensures all models are imported via app.models
# from app.background.sync_scheduler import start_sync_scheduler
# from app.background.scheduler import start_scheduler
from app.background.attendance_scheduler import schedule_all_devices
from app.api.router import router

logger = logging.getLogger("uvicorn.error")
scheduler = None
app = FastAPI(
    title="HRMS Backend",
    description="Human Resource Management System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    try:
        test_db_connection()
        logger.info("Database connection successful")
    except Exception as exc:  # pragma: no cover - runtime DB may be unavailable
        logger.warning("Database connection failed on startup: %s", exc)
        return

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created or already exist")
    except Exception as exc:  # pragma: no cover - catch DDL errors
        logger.error("Failed to create database tables on startup: %s", exc)
    
    # Start the background ZKT sync scheduler
    try:
        logger.info("Starting ZKT attendance sync scheduler...")
        # await start_scheduler()
        # start_scheduler()
        schedule_all_devices()
        logger.info("ZKT attendance sync scheduler started successfully")
    except Exception as exc:
        logger.error("Failed to start sync scheduler: %s", exc)
 

@app.on_event("shutdown")
async def shutdown_event():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)

app.include_router(router, prefix="/api/v1")