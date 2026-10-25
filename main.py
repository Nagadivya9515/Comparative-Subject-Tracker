from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from typing import List, Optional
from datetime import date

app = FastAPI(
    title="Comparative Daily Task & Subject Tracker",
    description="Backend API for tracking GATE subjects and daily routines with relative effort analytics.",
    version="1.0.0"
)

# Allow CORS for local front-end testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

# -----------------------------------------------------------------------------
# DATABASE INITIALIZATION & SEEDING
# -----------------------------------------------------------------------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Master Tasks Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # 2. Daily Completion Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            log_date TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            UNIQUE(task_id, log_date)
        );
    """)
    
    # Seed initial 7 GATE subjects + 5 daily routines if table is empty
    cursor.execute("SELECT COUNT(*) FROM tasks;")
    if cursor.fetchone()[0] == 0:
        seed_tasks = [
            # 7 GATE Subjects
            ("gate_em", "Engineering Mathematics", "GATE"),
            ("gate_ds", "Data Structures & Algorithms", "GATE"),
            ("gate_algo", "Design & Analysis of Algorithms", "GATE"),
            ("gate_os", "Operating Systems", "GATE"),
            ("gate_dbms", "Database Management Systems", "GATE"),
            ("gate_cn", "Computer Networks", "GATE"),
            ("gate_toc", "Theory of Computation & Compilers", "GATE"),
            
            # 5 Daily Routines
            ("rt_aptitude", "Aptitude & Logical Reasoning", "Routine"),
            ("rt_revision", "Subject Revision & Flashcards", "Routine"),
            ("rt_mock", "Daily Problem Solving Set", "Routine"),
            ("rt_workout", "Physical Exercise & Health", "Routine"),
            ("rt_reading", "Technical Reading / Journaling", "Routine")
        ]
        cursor.executemany(
            "INSERT INTO tasks (id, title, category) VALUES (?, ?, ?);", 
            seed_tasks
        )
        conn.commit()
    
    conn.close()

@app.on_event("startup")
def startup_event():
    init_db()

# -----------------------------------------------------------------------------
# PYDANTIC SCHEMAS (DATA VALIDATION)
# -----------------------------------------------------------------------------
class LogToggleRequest(BaseModel):
    task_id: str
    log_date: Optional[str] = None  # Format: 'YYYY-MM-DD', defaults to today if null
    completed: bool

class TaskCreateRequest(BaseModel):
    id: str
    title: str
    category: str

# -----------------------------------------------------------------------------
# API ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/tasks", summary="Get all tracked subjects/tasks")
def get_tasks():
    """Returns the list of all 12 tracked items with their category."""
    conn = get_db_connection()
    tasks = conn.execute("SELECT id, title, category FROM tasks ORDER BY category, title").fetchall()
    conn.close()
    return [dict(t) for t in tasks]

@app.get("/api/logs", summary="Get completion logs for a specific date")
def get_logs(log_date: Optional[str] = None):
    """Returns checkbox statuses for all tasks on a given date (defaults to today)."""
    target_date = log_date if log_date else date.today().isoformat()
    conn = get_db_connection()
    
    query = """
        SELECT 
            t.id AS task_id, 
            t.title, 
            t.category,
            COALESCE(l.completed, 0) AS completed
        FROM tasks t
        LEFT JOIN daily_logs l 
            ON t.id = l.task_id AND l.log_date = ?
        ORDER BY t.category, t.title;
    """
    logs = conn.execute(query, (target_date,)).fetchall()
    conn.close()
    return {"date": target_date, "logs": [dict(l) for l in logs]}

@app.post("/api/logs/toggle", summary="Check or uncheck a task")
def toggle_log(payload: LogToggleRequest):
    """Upserts the completion status (1 or 0) for a specific task and date."""
    target_date = payload.log_date if payload.log_date else date.today().isoformat()
    completed_val = 1 if payload.completed else 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure task exists
    cursor.execute("SELECT id FROM tasks WHERE id = ?;", (payload.task_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Task ID not found")
        
    cursor.execute("""
        INSERT INTO daily_logs (task_id, log_date, completed)
        VALUES (?, ?, ?)
        ON CONFLICT(task_id, log_date) 
        DO UPDATE SET completed = excluded.completed;
    """, (payload.task_id, target_date, completed_val))
    
    conn.commit()
    conn.close()
    return {"status": "success", "task_id": payload.task_id, "date": target_date, "completed": payload.completed}

@app.get("/api/analytics/comparative", summary="Fetch Comparative Effort Share Data")
def get_comparative_analytics():
    """
    Calculates total completions, relative effort share percentage, 
    and overall benchmark average across all tasks.
    """
    conn = get_db_connection()
    
    query = """
        WITH TaskTotals AS (
            SELECT 
                t.id,
                t.title,
                t.category,
                COALESCE(SUM(l.completed), 0) AS total_completions
            FROM tasks t
            LEFT JOIN daily_logs l ON t.id = l.task_id
            GROUP BY t.id
        ),
        GrandTotal AS (
            SELECT SUM(total_completions) AS overall_sum FROM TaskTotals
        )
        SELECT 
            tt.id,
            tt.title,
            tt.category,
            tt.total_completions,
            CASE 
                WHEN gt.overall_sum IS NULL OR gt.overall_sum = 0 THEN 0.0
                ELSE ROUND((tt.total_completions * 100.0) / gt.overall_sum, 1)
            END AS effort_share_pct
        FROM TaskTotals tt, GrandTotal gt
        ORDER BY effort_share_pct ASC;
    """
    
    rows = conn.execute(query).fetchall()
    
    # Calculate group benchmark average
    task_list = [dict(r) for r in rows]
    total_tasks = len(task_list)
    group_average_pct = round(100.0 / total_tasks, 1) if total_tasks > 0 else 0.0
    
    conn.close()
    return {
        "group_average_pct": group_average_pct,
        "tasks": task_list
    }

@app.get("/api/analytics/line-trend", summary="Fetch Daily Output Trend")
def get_line_trend():
    """Returns total completed tasks grouped by date for the line graph."""
    conn = get_db_connection()
    query = """
        SELECT 
            log_date,
            SUM(completed) AS total_completed
        FROM daily_logs
        GROUP BY log_date
        ORDER BY log_date ASC;
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    return {"trend": [dict(r) for r in rows]}