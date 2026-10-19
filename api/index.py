"""Vercel serverless entry point: every /api/* request is routed here (see vercel.json)."""

from backend.app.main import app, init_db

# Serverless functions don't reliably run ASGI startup events, so initialise on cold start.
init_db()

__all__ = ["app"]
