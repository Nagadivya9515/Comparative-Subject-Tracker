from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from typing import Optional, List

class UserCreate(BaseModel):
    name: str
    email: EmailStr

class UserResponse(BaseModel):
    id: int
    name: str 
    email: EmailStr

    class Config:
        from_attributes=True


class TaskCreate(BaseModel):
    title: str
    category: str
    is_sprint: bool = False
    sprint_start_date: Optional[date]=None
    sprint_duration_days: Optional[int]=1


class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    category: str
    is_sprint: bool
    sprint_duration_days: int
    sprint_start_date:Optional[date]=None
    is_deleted: bool
    
    class Config:
        from_attributes=True


class LogToggle(BaseModel):
    task_id: str
    log_date: Optional[date] = None
    completed: bool
    hours_spent: float = 1.0


class LogResponse(BaseModel):
    id: int
    task_id: int
    log_date: date
    completed: bool
    hours_spent: float
    completed_at: datetime

    class Config:
        from_attributes = True

class TaskSkillMappingCreate(BaseModel):
    gate_subject_id: str
    credit_weight: float

class SubjectAnalyticsResponse(BaseModel):
    subject_id: int
    subject_name: str
    raw_hours: int
    decayed_score: float
    effort_share_pct: float 
    is_Active: bool 

class ComparativeAnalyticsResponse(BaseModel):
    alpha_decay: float
    damping_active: bool
    subject_active: List[SubjectAnalyticsResponse]


class LineTrendPoint(BaseModel):
    log_date: date
    total_hours: float