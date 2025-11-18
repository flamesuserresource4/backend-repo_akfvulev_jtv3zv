import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from database import create_document, get_documents, db
from schemas import Lead

app = FastAPI(title="Expat Solutions in Asia API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Expat Solutions in Asia API running"}

@app.get("/api/hello")
def hello():
    return {"message": "Welcome to Expat Solutions in Asia"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

# Lead submission models
class LeadCreate(Lead):
    pass

class LeadOut(BaseModel):
    id: str
    name: str
    email: str
    phone: str | None
    interest: str
    notes: str | None
    created_at: datetime | None = None

# Create lead endpoint
@app.post("/api/leads", response_model=dict)
def create_lead(lead: LeadCreate):
    try:
        inserted_id = create_document("lead", lead)
        return {"success": True, "id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List leads endpoint (limited)
@app.get("/api/leads", response_model=List[LeadOut])
def list_leads(limit: int = 50):
    try:
        docs = get_documents("lead", limit=limit)
        # Normalize Mongo ObjectId and timestamps
        result: List[LeadOut] = []
        for d in docs:
            result.append(LeadOut(
                id=str(d.get("_id")),
                name=d.get("name", ""),
                email=d.get("email", ""),
                phone=d.get("phone"),
                interest=d.get("interest", ""),
                notes=d.get("notes"),
                created_at=d.get("created_at")
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
