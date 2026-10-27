from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from typing import Optional, List
from datetime import date, datetime, timedelta

app = FastAPI(
    title="Comparative Subject & Habit Tracker v2.0",
    description="Backend with Matrix Skill Mapping, 3-5 Day Active Sprint Damping, and Weighted Hours.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "database2.db"
SIMULATED_DAY_OFFSET = 0

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Users Table (Lightweight Scaffold - No JWT)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("INSERT OR IGNORE INTO users (id, name, email) VALUES ('user_nagadivya', 'Nagadivya', 'nagadivya@example.com');")
    
    # 2. Tasks Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            is_sprint INTEGER DEFAULT 0,
            sprint_duration_days INTEGER DEFAULT 0,
            sprint_start_date TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # 3. Task Skill Mappings (For Automatic Matrix Mapping)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_skill_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            gate_subject_id TEXT NOT NULL,
            credit_weight REAL NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY(gate_subject_id) REFERENCES tasks(id) ON DELETE CASCADE
        );
    """)
    
    # 4. Daily Logs Table (With Weighted Hours)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            log_date TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            hours_spent REAL DEFAULT 1.0,
            completed_at DATETIME,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            UNIQUE(task_id, log_date)
        );
    """)
    
    # Migration checks
    try:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN hours_spent REAL DEFAULT 1.0;")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN is_sprint INTEGER DEFAULT 0;")
        cursor.execute("ALTER TABLE tasks ADD COLUMN sprint_duration_days INTEGER DEFAULT 0;")
        cursor.execute("ALTER TABLE tasks ADD COLUMN sprint_start_date TEXT;")
    except sqlite3.OperationalError:
        pass
        
    # Seed default GATE & Routine tasks if empty
    cursor.execute("SELECT COUNT(*) FROM tasks;")
    if cursor.fetchone()[0] == 0:
        seed_tasks = [
            ("gate_em", "Engineering Mathematics", "GATE", 0, 0, None),
            ("gate_ds", "Data Structures & Algorithms", "GATE", 0, 0, None),
            ("gate_algo", "Design & Analysis of Algorithms", "GATE", 0, 0, None),
            ("gate_os", "Operating Systems", "GATE", 0, 0, None),
            ("gate_dbms", "Database Management Systems", "GATE", 0, 0, None),
            ("gate_cn", "Computer Networks", "GATE", 0, 0, None),
            ("gate_toc", "Theory of Computation & Compilers", "GATE", 0, 0, None),
            
            ("rt_aptitude", "Aptitude & Logical Reasoning", "Routine", 0, 0, None),
            ("rt_revision", "Subject Revision & Flashcards", "Routine", 0, 0, None),
            ("rt_mock", "Daily Problem Solving Set", "Routine", 0, 0, None),
            ("rt_workout", "Physical Exercise & Health", "Routine", 0, 0, None),
            ("rt_reading", "Technical Reading / Journaling", "Routine", 0, 0, None)
        ]
        cursor.executemany("INSERT INTO tasks (id, title, category, is_sprint, sprint_duration_days, sprint_start_date) VALUES (?, ?, ?, ?, ?, ?);", seed_tasks)
        conn.commit()
    
    conn.close()

@app.on_event("startup")
def startup_event():
    init_db()

# Schemas

class SkillTagInput(BaseModel):
    gate_subject_id: str # e.g., 'gate_dbms', 'gate_cn', 'gate_ds'

class SkillMappingInput(BaseModel):
    gate_subject_id: str
    credit_weight: float  # e.g. 0.40 for 40%

class TaskCreateRequest(BaseModel):
    title: str
    category: str
    is_sprint: bool = False
    sprint_duration_days: int = 3
    selected_gate_tags: List[str] = []  # List of selected GATE subject IDs

class LogToggleRequest(BaseModel):
    task_id: str
    log_date: Optional[str] = None
    completed: bool
    hours_spent: float = 1.0

# -----------------------------------------------------------------------------
# SIMULATION ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/simulation/current-date")
def get_simulated_date():
    simulated_date = date.today() + timedelta(days=SIMULATED_DAY_OFFSET)
    return {
        "simulated_date": simulated_date.isoformat(),
        "offset_days": SIMULATED_DAY_OFFSET
    }

@app.post("/api/simulation/advance-day")
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
# TASK & SPRINT CRUD
# -----------------------------------------------------------------------------

@app.get("/api/tasks")
def get_tasks():
    conn = get_db_connection()
    tasks = conn.execute("SELECT * FROM tasks ORDER BY is_sprint DESC, category, title").fetchall()
    conn.close()
    return [dict(t) for t in tasks]

@app.post("/api/tasks")
def create_task(payload: TaskCreateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    simulated_date_str = (date.today() + timedelta(days=SIMULATED_DAY_OFFSET)).isoformat()
    task_id = f"{'sprint' if payload.is_sprint else payload.category.lower()}_{payload.title.lower().replace(' ', '_')}"
    
    cursor.execute("SELECT id FROM tasks WHERE id = ?;", (task_id,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Task or Sprint already exists.")
        
    sprint_start = simulated_date_str if payload.is_sprint else None
    
    cursor.execute(
        """INSERT INTO tasks 
           (id, title, category, is_sprint, sprint_duration_days, sprint_start_date) 
           VALUES (?, ?, ?, ?, ?, ?);""",
        (task_id, payload.title, payload.category, 1 if payload.is_sprint else 0, payload.sprint_duration_days if payload.is_sprint else 0, sprint_start)
    )
    
    # AUTO-CALCULATE WEIGHTS BASED ON SELECTED TAGS
    tags = payload.selected_gate_tags
    if tags:
        equal_weight = round(1.0 / len(tags), 3) # e.g., 2 tags = 0.50, 3 tags = 0.333
        for tag_id in tags:
            cursor.execute(
                "INSERT INTO task_skill_mappings (task_id, gate_subject_id, credit_weight) VALUES (?, ?, ?);",
                (task_id, tag_id, equal_weight)
            )
            
    conn.commit()
    conn.close()
    return {"status": "created", "task_id": task_id, "mapped_tags": tags}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted", "task_id": task_id}

# -----------------------------------------------------------------------------
# LOGS & EFFORT TOGGLE WITH HOURS
# -----------------------------------------------------------------------------

@app.get("/api/logs")
def get_logs(log_date: Optional[str] = None):
    target_date = log_date if log_date else (date.today() + timedelta(days=SIMULATED_DAY_OFFSET)).isoformat()
    conn = get_db_connection()
    query = """
        SELECT 
            t.id AS task_id, 
            t.title, 
            t.category,
            t.is_sprint,
            t.sprint_duration_days,
            t.sprint_start_date,
            COALESCE(l.completed, 0) AS completed,
            COALESCE(l.hours_spent, 1.0) AS hours_spent,
            l.completed_at
        FROM tasks t
        LEFT JOIN daily_logs l 
            ON t.id = l.task_id AND l.log_date = ?
        ORDER BY t.is_sprint DESC, t.category, t.title;
    """
    logs = conn.execute(query, (target_date,)).fetchall()
    conn.close()
    return {"date": target_date, "logs": [dict(l) for l in logs]}

@app.post("/api/logs/toggle")
def toggle_log(payload: LogToggleRequest):
    target_date = payload.log_date if payload.log_date else (date.today() + timedelta(days=SIMULATED_DAY_OFFSET)).isoformat()
    completed_val = 1 if payload.completed else 0
    now_timestamp = datetime.now().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO daily_logs (task_id, log_date, completed, hours_spent, completed_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(task_id, log_date) 
        DO UPDATE SET 
            completed = excluded.completed,
            hours_spent = excluded.hours_spent,
            completed_at = excluded.completed_at;
    """, (payload.task_id, target_date, completed_val, payload.hours_spent, now_timestamp))
    
    conn.commit()
    conn.close()
    return {"status": "success", "task_id": payload.task_id, "hours_spent": payload.hours_spent}

# -----------------------------------------------------------------------------
# ANALYTICS: MATRIX MAPPING + DYNAMIC DECAY DAMPING (α = 0.97)
# -----------------------------------------------------------------------------

@app.get("/api/analytics/comparative")
def get_comparative_analytics():
    simulated_date = date.today() + timedelta(days=SIMULATED_DAY_OFFSET)
    simulated_date_str = simulated_date.isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if any Sprint is currently ACTIVE (within start_date to start_date + sprint_duration_days)
    active_sprint = cursor.execute("""
        SELECT * FROM tasks 
        WHERE is_sprint = 1 
          AND sprint_start_date IS NOT NULL 
          AND julianday(?) >= julianday(sprint_start_date)
          AND julianday(?) <= (julianday(sprint_start_date) + sprint_duration_days);
    """, (simulated_date_str, simulated_date_str)).fetchone()
    
    # Dynamic Decay Factor: alpha = 0.97 (Slow Decay Damping) during Sprints, else 0.90 (Standard)
    alpha = 0.97 if active_sprint else 0.90
    
    # 1. Calculate Direct Decayed Hours for all tasks
    all_tasks = cursor.execute("SELECT id, title, category, is_sprint FROM tasks;").fetchall()
    
    task_scores = {}
    for t in all_tasks:
        task_id = t["id"]
        # Direct effort sum = SUM(completed * hours_spent * (alpha ^ days_ago))
        query = """
            SELECT COALESCE(SUM(
                completed * hours_spent * POWER(?, MAX(0.0, julianday(?) - julianday(log_date)))
            ), 0.0) AS direct_score
            FROM daily_logs 
            WHERE task_id = ? AND completed = 1;
        """
        score = cursor.execute(query, (alpha, simulated_date_str, task_id)).fetchone()["direct_score"]
        task_scores[task_id] = score
        
    # 2. AUTOMATIC MATRIX SKILL MAPPING: Route Sprint Scores to GATE subjects
    matrix_mappings = cursor.execute("SELECT task_id, gate_subject_id, credit_weight FROM task_skill_mappings;").fetchall()
    for m in matrix_mappings:
        sprint_id = m["task_id"]
        gate_id = m["gate_subject_id"]
        weight = m["credit_weight"]
        
        if sprint_id in task_scores and task_scores[sprint_id] > 0:
            transferred_score = task_scores[sprint_id] * weight
            if gate_id in task_scores:
                task_scores[gate_id] += transferred_score
                
    # 3. Calculate Effort Share Percentages across primary tasks
    primary_tasks = [t for t in all_tasks if t["is_sprint"] == 0]
    total_score_sum = sum(task_scores[t["id"]] for t in primary_tasks)
    total_count = len(primary_tasks)
    group_average_pct = round(100.0 / total_count, 1) if total_count > 0 else 0.0
    
    results = []
    for t in primary_tasks:
        t_id = t["id"]
        raw_score = task_scores[t_id]
        share_pct = round((raw_score * 100.0) / total_score_sum, 1) if total_score_sum > 0 else group_average_pct
        results.append({
            "id": t_id,
            "title": t["title"],
            "category": t["category"],
            "score": round(raw_score, 2),
            "effort_share_pct": share_pct
        })
        
    results.sort(key=lambda x: x["effort_share_pct"])
    conn.close()
    
    return {
        "simulated_date": simulated_date_str,
        "is_sprint_active": bool(active_sprint),
        "decay_factor_alpha": alpha,
        "group_average_pct": group_average_pct,
        "tasks": results
    }

@app.get("/api/analytics/line-trend")
def get_line_trend():
    conn = get_db_connection()
    query = """
        SELECT 
            log_date,
            SUM(completed * hours_spent) AS total_hours_completed
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
        trend_data = [{"log_date": simulated_date_str, "total_hours_completed": 0}]
        
    return {"trend": trend_data}


