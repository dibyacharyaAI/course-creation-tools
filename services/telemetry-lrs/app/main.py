from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telemetry LRS Service", version="0.1.0")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Telemetry LRS Service"}

@app.post("/track")
async def track_event():
    logger.info(f"Telemetry event received")
    return {"status": "success", "message": "Event tracked"}
