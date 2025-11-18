import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import smtplib
from email.message import EmailMessage
import logging

from database import create_document, get_documents, db
from schemas import Lead

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("expat-api")

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

    # Email config status
    response["email_from"] = "✅ Set" if os.getenv("SMTP_FROM") else "❌ Not Set"
    response["smtp_host"] = "✅ Set" if os.getenv("SMTP_HOST") else "❌ Not Set"

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


def _send_email_sync(subject: str, body: str, to_emails: list[str]):
    """Send an email using SMTP settings from environment variables.
    This function is synchronous and intended to be run in a background task.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM")

    if not (smtp_host and smtp_from and to_emails):
        logger.warning("SMTP not fully configured or recipients missing; skipping email notification")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = ", ".join(to_emails)
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info("Lead notification email sent to %s", to_emails)
    except Exception as e:
        logger.error("Failed to send email notification: %s", e)


def queue_lead_notification(lead: LeadCreate, inserted_id: str):
    subject = "New consultation lead – Expat Solutions in Asia"
    lines = [
        "A new lead has been submitted:",
        f"ID: {inserted_id}",
        f"Name: {lead.name}",
        f"Email: {lead.email}",
        f"Phone: {lead.phone or '-'}",
        f"Interest: {lead.interest}",
        f"Notes: {lead.notes or '-'}",
        "",
        "Reply directly to the contact to follow up."
    ]
    body = "\n".join(lines)

    to_list = [
        os.getenv("NOTIFY_EMAIL_PRIMARY", "ken@expatsolutionsinasia.com"),
        os.getenv("NOTIFY_EMAIL_SECONDARY", "cloud@expatsolutionsinasia.com"),
    ]
    # Filter out empties and duplicates
    to_list = [e for i, e in enumerate(to_list) if e and e not in to_list[:i]]

    _send_email_sync(subject, body, to_list)


# Create lead endpoint
@app.post("/api/leads", response_model=dict)
def create_lead(lead: LeadCreate, background_tasks: BackgroundTasks):
    try:
        inserted_id = create_document("lead", lead)
        # Schedule email notification without blocking the response
        background_tasks.add_task(queue_lead_notification, lead, inserted_id)
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
