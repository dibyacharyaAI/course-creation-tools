from fastapi import FastAPI
from shared.core.settings import BaseAppSettings
from shared.core.logging import setup_logging

class Settings(BaseAppSettings):
    APP_NAME: str = "Exporter & Validator Service"

settings = Settings()
logger = setup_logging(settings.APP_NAME)

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}
