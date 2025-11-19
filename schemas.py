"""
Database Schemas for Productivity & Roster App

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name (e.g., User -> "user").
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal

# Roles: admin, manager, member
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    alias: Optional[str] = Field(None, description="Short name used internally")
    role: Literal["admin", "manager", "member"] = Field("member", description="Access role")
    manager_id: Optional[str] = Field(None, description="User ID of the reporting manager")
    geo: Optional[str] = Field(None, description="Geo location, e.g., India, US, Costa Rica")
    timezone: Optional[str] = Field(None, description="IANA timezone, e.g., Asia/Kolkata, America/New_York")
    is_active: bool = Field(True, description="Whether user is active")

class Tasktype(BaseModel):
    name: str = Field(..., description="Task name visible in calendar")
    code: Optional[str] = Field(None, description="Short code, e.g., DEV, QA, MEET")
    description: Optional[str] = Field(None, description="Details about the task type")
    active: bool = Field(True, description="Whether task type is available for assignment")

class Roster(BaseModel):
    user_id: str = Field(..., description="Assignee user id")
    tasktype_id: str = Field(..., description="Task type id")
    start_time: str = Field(..., description="ISO datetime string (UTC preferred)")
    end_time: str = Field(..., description="ISO datetime string (UTC preferred)")
    timezone: Optional[str] = Field(None, description="Assignee timezone at scheduling time")
    notes: Optional[str] = Field(None, description="Optional notes")
