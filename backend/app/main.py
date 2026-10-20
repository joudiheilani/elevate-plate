import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .routers import pantry, plan, recipes, restrictions
from .seed import seed_if_empty

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def init_db() -> None:
    """Create tables and insert sample data. Safe to call more than once."""
    Base.metadata.create_all(bind=engine)
    if os.getenv("SEED_SAMPLE_DATA", "true").lower() == "true":
        with SessionLocal() as db:
            seed_if_empty(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Meal Planner API", version="1.0.0", lifespan=lifespan)
app.include_router(recipes.router)
app.include_router(plan.router)
app.include_router(pantry.router)
app.include_router(restrictions.router)


@app.get("/api/health", tags=["health"])
def health(db: Annotated[Session, Depends(get_db)]):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


# Locally, FastAPI serves the frontend too. On Vercel the frontend is served as static
# files by Vercel itself and isn't bundled with the function, so the mount is skipped.
# Mounted last so the /api routes above take precedence.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
