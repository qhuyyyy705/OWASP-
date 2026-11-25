import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.core.config import WEB_DIST
from app.database.session import Base, engine
from app import models  # register SQLAlchemy models
from sqlalchemy import inspect, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    columns = {item["name"] for item in inspect(engine).get_columns("traffic_entries")}
    with engine.begin() as connection:
        if "parent_id" not in columns:
            connection.execute(text("ALTER TABLE traffic_entries ADD COLUMN parent_id VARCHAR(36)"))
        if "repeater_name" not in columns:
            connection.execute(text("ALTER TABLE traffic_entries ADD COLUMN repeater_name VARCHAR(120) NOT NULL DEFAULT ''"))
    yield

app = FastAPI(title="WebSentinel API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])
app.include_router(router)
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="desktop-ui")
