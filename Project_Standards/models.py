from sqlalchemy import Column, Integer, String, DateTime, func, Date, Float ,ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from database import Base
from datetime import date


class Task(Base):
    __tablename__="tasks"

    id=Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id=Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, default=1)
    title=Column(String(250), nullable=False)
    category=Column(String(100), nullable=False)
    is_sprint=Column(Integer, default=0)
    sprint_start_date:Mapped[date] = mapped_column(Date, default=date.today, nullable=True)
    sprint_duration_days=Column(Integer, default=3)
    is_deleted = Column(Boolean, default=False)


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )

    logs=relationship("Dailylogs", back_populates="tasks",cascade="all, delete-orphan")
    owner=relationship("User", back_populates="tasks")
    

class Dailylogs(Base):
    __tablename__="daily_logs"

    id=Column(Integer, primary_key=True, autoincrement=True, index=True)
    task_id=Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    log_date:Mapped[date]=mapped_column(Date, default=date.today)
    completed=Column(Boolean, default=False)
    hours_spent=Column(Integer, default=0.0)
    completed_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    tasks = relationship("Task", back_populates="logs")


class TaskSillMapping(Base):
    __tablename__="tasks_skill_mappings"

    id=Column(Integer, primary_key=True, autoincrement=True, index=True)
    task_id=Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    gate_subject_id=Column(String(100), nullable=False)
    credit_weight=Column(Float, default=1.0)

class User(Base):
    __tablename__="users"

    id=Column(Integer, primary_key=True, autoincrement=True)
    name=Column(String(30), nullable=False)
    email=Column(String, unique=True, nullable=False)
    created_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    tasks=relationship("Task", back_populates="owner")

