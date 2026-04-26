"""Vercel serverless entrypoint. Re-exports the FastAPI ASGI app."""
from connect_the_stars.api import app  # noqa: F401
