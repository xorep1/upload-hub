"""FastAPI application entrypoint.

Note on the database schema:
  The schema is managed by Alembic migrations, NOT auto-created at startup.
  Before running the app, apply migrations once:

      alembic upgrade head

  (For a quick throwaway dev DB you can instead call app.database.init_db().)
"""
from fastapi import FastAPI

from app.core.config import settings
from app.routers import admin, auth, files

app = FastAPI(title=settings.app_name)
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"app": settings.app_name, "docs": "/docs", "admin": "/admin"}
