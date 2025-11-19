import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from database import db, create_document, get_documents
from schemas import User as UserSchema, Tasktype as TasktypeSchema, Roster as RosterSchema

app = FastAPI(title="Productivity & Roster API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Roster API running"}


@app.get("/test")
def test_database():
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
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# ---------------------- Models for Requests ----------------------
class CreateUser(BaseModel):
    name: str
    email: EmailStr
    alias: Optional[str] = None
    role: str = "member"  # admin, manager, member
    manager_id: Optional[str] = None
    geo: Optional[str] = None
    timezone: Optional[str] = None


class CreateTasktype(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    active: bool = True


class CreateRoster(BaseModel):
    user_id: str
    tasktype_id: str
    start_time: str  # ISO string
    end_time: str    # ISO string
    timezone: Optional[str] = None
    notes: Optional[str] = None


# ---------------------- Helper ----------------------
from bson import ObjectId

def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id format")


# ---------------------- User Endpoints ----------------------
@app.post("/api/users")
def create_user(payload: CreateUser):
    data = UserSchema(**payload.model_dump())
    # Check existing by email
    existing = db.user.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    inserted_id = create_document("user", data)
    return {"id": inserted_id}


@app.get("/api/users")
def list_users(role: Optional[str] = None, manager_id: Optional[str] = None):
    filt = {}
    if role:
        filt["role"] = role
    if manager_id:
        filt["manager_id"] = manager_id
    users = get_documents("user", filt)
    # Convert ObjectId to str
    for u in users:
        u["id"] = str(u.pop("_id"))
    return users


# ---------------------- Task Types ----------------------
@app.post("/api/tasktypes")
def create_tasktype(payload: CreateTasktype):
    data = TasktypeSchema(**payload.model_dump())
    # Unique by name or code
    filt = {"$or": [{"name": data.name}]}
    if data.code:
        filt["$or"].append({"code": data.code})
    existing = db.tasktype.find_one(filt)
    if existing:
        raise HTTPException(status_code=400, detail="Task type with same name/code exists")
    inserted_id = create_document("tasktype", data)
    return {"id": inserted_id}


@app.get("/api/tasktypes")
def list_tasktypes(active: Optional[bool] = None):
    filt = {}
    if active is not None:
        filt["active"] = active
    docs = get_documents("tasktype", filt)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


# ---------------------- Rosters ----------------------
@app.post("/api/rosters")
def create_roster(payload: CreateRoster):
    # Basic overlap check (same user)
    start = datetime.fromisoformat(payload.start_time)
    end = datetime.fromisoformat(payload.end_time)
    if end <= start:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    overlap = db.roster.find_one({
        "user_id": payload.user_id,
        "$or": [
            {"start_time": {"$lt": payload.end_time}, "end_time": {"$gt": payload.start_time}}
        ]
    })
    if overlap:
        raise HTTPException(status_code=400, detail="Overlapping roster for this user")

    data = RosterSchema(**payload.model_dump())
    inserted_id = create_document("roster", data)
    return {"id": inserted_id}


@app.get("/api/rosters")
def list_rosters(user_id: Optional[str] = None, date: Optional[str] = None):
    filt = {}
    if user_id:
        filt["user_id"] = user_id
    if date:
        # Return entries touching this day (00:00 to 23:59)
        day_start = f"{date}T00:00:00"
        day_end = f"{date}T23:59:59"
        filt["$or"] = [
            {"start_time": {"$lte": day_end}, "end_time": {"$gte": day_start}}
        ]
    docs = get_documents("roster", filt)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


# ---------------------- Schema Endpoint (for viewer) ----------------------
@app.get("/schema")
def get_schema():
    # Minimal schema exposure for tooling
    return {
        "collections": [
            "user", "tasktype", "roster"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
