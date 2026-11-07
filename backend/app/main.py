import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .migrations import migrate
from .routers import (
    auth,
    dining_out,
    generator,
    groceries,
    pantry,
    plan,
    profile,
    recipes,
    restrictions,
)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


# The iPhone app (Capacitor) serves its pages from capacitor://localhost and calls this
# API cross-origin, so those origins are allowed. Add more with CORS_ORIGINS="a,b".
DEFAULT_CORS_ORIGINS = ["capacitor://localhost", "ionic://localhost", "http://localhost"]


def init_db() -> None:
    """Create missing tables and apply migrations. Safe to call more than once."""
    Base.metadata.create_all(bind=engine)
    migrate(engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Elevate Plate API", version="3.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *DEFAULT_CORS_ORIGINS,
        *(o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()),
    ],
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(recipes.router)
app.include_router(plan.router)
app.include_router(dining_out.router)
app.include_router(pantry.router)
app.include_router(restrictions.router)
app.include_router(profile.router)
app.include_router(groceries.router)
app.include_router(generator.router)


@app.get("/api/health", tags=["health"])
def health(db: Annotated[Session, Depends(get_db)]):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


# Locally, FastAPI serves the frontend too. On Vercel the frontend is served as static
# files by Vercel itself and isn't bundled with the function, so the mount is skipped.
# Mounted last so the /api routes above take precedence.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
