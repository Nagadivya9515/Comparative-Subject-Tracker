from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from typing import Optional
from datetime import date, datetime, timedelta

app = FastAPI(
    title="Comparative Subject & Habit Tracker",
    description="Backend with fast-forward simulation and 0.90 age decay.",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "database.db"

# Global offset counter for fast-forward simulation (0 = Today, 1 = Tomorrow, 2 = Day 2, etc.)
SIMULATED_DAY_OFFSET = 0

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            log_date TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            completed_at DATETIME,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            UNIQUE(task_id, log_date)
        );
    """)
    
    try:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN completed_at DATETIME;")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    cursor.execute("SELECT COUNT(*) FROM tasks;")
    if cursor.fetchone()[0] == 0:
        seed_tasks = [
            ("gate_em", "Engineering Mathematics", "GATE"),
            ("gate_ds", "Data Structures & Algorithms", "GATE"),
            ("gate_algo", "Design & Analysis of Algorithms", "GATE"),
            ("gate_os", "Operating Systems", "GATE"),
            ("gate_dbms", "Database Management Systems", "GATE"),
            ("gate_cn", "Computer Networks", "GATE"),
            ("gate_toc", "Theory of Computation & Compilers", "GATE"),
            
            ("rt_aptitude", "Aptitude & Logical Reasoning", "Routine"),
            ("rt_revision", "Subject Revision & Flashcards", "Routine"),
            ("rt_mock", "Daily Problem Solving Set", "Routine"),
            ("rt_workout", "Physical Exercise & Health", "Routine"),
            ("rt_reading", "Technical Reading / Journaling", "Routine")
        ]
        cursor.executemany("INSERT INTO tasks (id, title, category) VALUES (?, ?, ?);", seed_tasks)
        conn.commit()
    
    conn.close()

@app.on_event("startup")
def startup_event():
    init_db()

class LogToggleRequest(BaseModel):
    task_id: str
    log_date: Optional[str] = None
    completed: bool

# -----------------------------------------------------------------------------
# SIMULATION ENDPOINTS (FAST-FORWARD TIME)
# -----------------------------------------------------------------------------

@app.get("/api/simulation/current-date", summary="Get current simulated date")
def get_simulated_date():
    simulated_date = date.today() + timedelta(days=SIMULATED_DAY_OFFSET)
    return {
        "simulated_date": simulated_date.isoformat(),
        "offset_days": SIMULATED_DAY_OFFSET
    }

@app.post("/api/simulation/advance-day", summary="Fast-forward time by 1 day")
def advance_day():
    global SIMULATED_DAY_OFFSET
    SIMULATED_DAY_OFFSET += 1
    simulated_date = date.today() + timedelta(days=SIMULATED_DAY_OFFSET)
    return {
        "status": "advanced",
        "simulated_date": simulated_date.isoformat(),
        "offset_days": SIMULATED_DAY_OFFSET
    }

# -----------------------------------------------------------------------------
# MAIN API ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/tasks")
def get_tasks():
    conn = get_db_connection()
    tasks = conn.execute("SELECT id, title, category FROM tasks ORDER BY category, title").fetchall()
    conn.close()
    return [dict(t) for t in tasks]

@app.get("/api/logs")
def get_logs(log_date: Optional[str] = None):
    # Use simulated date if log_date is not explicitly passed
    if not log_date:
        target_date = (date.today() + timedelta(days=SIMULATED_DAY_OFFSET)).isoformat()
    else:
        target_date = log_date
        
    conn = get_db_connection()
    query = """
        SELECT 
            t.id AS task_id, 
            t.title, 
            t.category,
            COALESCE(l.completed, 0) AS completed,
            l.completed_at
        FROM tasks t
        LEFT JOIN daily_logs l 
            ON t.id = l.task_id AND l.log_date = ?
        ORDER BY t.category, t.title;
    """
    logs = conn.execute(query, (target_date,)).fetchall()
    conn.close()
    return {"date": target_date, "logs": [dict(l) for l in logs]}

@app.post("/api/logs/toggle")
def toggle_log(payload: LogToggleRequest):
    if not payload.log_date:
        target_date = (date.today() + timedelta(days=SIMULATED_DAY_OFFSET)).isoformat()
    else:
        target_date = payload.log_date
        
    completed_val = 1 if payload.completed else 0
    now_timestamp = datetime.now().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM tasks WHERE id = ?;", (payload.task_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Task ID not found")
        
    cursor.execute("""
        INSERT INTO daily_logs (task_id, log_date, completed, completed_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(task_id, log_date) 
        DO UPDATE SET 
            completed = excluded.completed,
            completed_at = excluded.completed_at;
    """, (payload.task_id, target_date, completed_val, now_timestamp))
    
    conn.commit()
    conn.close()
    return {"status": "success", "task_id": payload.task_id, "date": target_date, "completed_at": now_timestamp}

@app.get("/api/analytics/comparative")
def get_comparative_analytics():
    # Calculate simulated date
    simulated_date = date.today() + timedelta(days=SIMULATED_DAY_OFFSET)
    simulated_date_str = simulated_date.isoformat()
    
    conn = get_db_connection()
    
    # 1. Compute exact floating-point date difference using julianday
    # 2. Apply 0.90 ^ days_ago decay factor
    query = f"""
        WITH DecayedScores AS (
            SELECT 
                t.id,
                t.title,
                t.category,
                COALESCE(SUM(
                    l.completed * POWER(0.90, MAX(0.0, julianday('{simulated_date_str}') - julianday(l.log_date)))
                ), 0.0) AS decayed_score,
                MAX(l.log_date) AS last_logged_date
            FROM tasks t
            LEFT JOIN daily_logs l ON t.id = l.task_id AND l.completed = 1
            GROUP BY t.id
        ),
        GrandTotal AS (
            SELECT COALESCE(SUM(decayed_score), 0.0) AS overall_sum FROM DecayedScores
        )
        SELECT 
            ds.id,
            ds.title,
            ds.category,
            ROUND(ds.decayed_score, 3) AS score,
            ds.last_logged_date,
            CASE 
                WHEN tds.overall_sum = 0 THEN ROUND(100.0 / (SELECT COUNT(*) FROM tasks), 1)
                ELSE ROUND((ds.decayed_score * 100.0) / tds.overall_sum, 1)
            END AS effort_share_pct
        FROM DecayedScores ds, GrandTotal tds
        ORDER BY effort_share_pct ASC;
    """
    
    rows = conn.execute(query).fetchall()
    task_list = [dict(r) for r in rows]
    total_tasks = len(task_list)
    group_average_pct = round(100.0 / total_tasks, 1) if total_tasks > 0 else 0.0
    
    conn.close()
    return {
        "simulated_date": simulated_date_str,
        "offset_days": SIMULATED_DAY_OFFSET,
        "group_average_pct": group_average_pct,
        "tasks": task_list
    }

@app.get("/api/analytics/line-trend")
def get_line_trend():
    conn = get_db_connection()
    query = """
        SELECT 
            log_date,
            SUM(completed) AS total_completed
        FROM daily_logs
        WHERE completed = 1
        GROUP BY log_date
        ORDER BY log_date ASC;
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    
    trend_data = [dict(r) for r in rows]
    if not trend_data:
        simulated_date_str = (date.today() + timedelta(days=SIMULATED_DAY_OFFSET)).isoformat()
        trend_data = [{"log_date": simulated_date_str, "total_completed": 0}]
        
    return {"trend": trend_data}