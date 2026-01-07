from fastapi import FastAPI

app = FastAPI(title="Assessment Service", version="0.1.0")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Assessment Service"}

@app.post("/generate-questions")
async def generate_questions():
    return {"message": "Not implemented yet"}
