from fastapi import FastAPI

app = FastAPI(title="HITL Gateway Service", version="0.1.0")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "HITL Gateway Service"}

@app.post("/review")
async def request_review():
    return {"status": "success", "message": "Review request logged"}
