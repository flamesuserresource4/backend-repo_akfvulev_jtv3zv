from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
from database import db, create_document
from schemas import Lead

app = FastAPI(title="Expat Solutions API")

# CORS for frontend previews
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LeadResponse(BaseModel):
    success: bool
    id: str | None = None


@app.get("/test")
async def test_db() -> Dict[str, Any]:
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    return {"status": "ok"}


@app.post("/api/leads", response_model=LeadResponse)
async def create_lead(payload: Lead):
    try:
        inserted_id = create_document("lead", payload)
        return LeadResponse(success=True, id=inserted_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
