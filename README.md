# Comparative Subject & Habit Tracker v2.0

A full-stack, math-driven study tracking engine built for **GATE Computer Science & Engineering** preparation. 

Instead of treating study habits as binary checkmarks, this application calculates real-time **exponential memory decay**, weights effort by **actual hours spent**, dynamically maps multi-subject activities to your syllabus, and tracks active focus sprints with time-decay damping.

---

## Key Features & Core Mechanics

* **Exponential Memory Decay ($\alpha = 0.90$):** Unrevised subjects decay exponentially by 10% each day. The dashboard automatically calculates your relative effort share and turns lagging subject bars **RED** whenever they fall below the group benchmark average ($8.3\%$).
* **Weighted Hours Engine:** Effort is calculated using actual time spent rather than simple checkmarks:
  $$\text{Subject Score} = \text{Completed} \times \text{Hours Spent} \times \alpha^{\text{Days Ago}}$$
* **Multi-Select Auto-Weighted Skill Mapping:** Create tasks or activities with multi-subject tags (e.g., `DBMS`, `Operating Systems`, `Networks`). The engine auto-calculates equal fractional splits (e.g., $50\% / 50\%$ or $33.3\%$ each) and routes effort credit directly into target GATE subjects.
* **Active 3–5 Day Sprint Lifecycle & Locking:** Sprints enforce a daily quota ($5\text{h/day}$, e.g., 3-day sprint = $15\text{h}$ total target). Sprints feature real-time status rules:
  * **Today Only:** Log incremental hours on the active day.
  * **Past Day Locking:** Historical days show `🔒 Past Day Locked` to prevent retroactive editing.
  * **Auto-Archiving & 75% Success Gate:** Expired sprints auto-archive into a dedicated side panel. Logging $\ge 75\%$ of target volume earns a `🏆 SUCCESSFUL SPRINT` badge, while $< 75\%$ marks the sprint as `⚠️ INCOMPLETE`.
* **Active Sprint Focus Damping ($\alpha = 0.97$):** Running an active sprint temporarily drops daily memory decay from $10\%$ to $3\%$ per day across all GATE subjects so deep marathons don't crash your revision baseline.
* **Historical Back-Filling & Timeline Analytics:** Step day-by-day (`< Prev` / `Next >` / `Today`) or use the date picker to back-fill past study notes (e.g., August/September). The app dynamically generates a 60-day workload volume curve and updates historical effort shares.
* **Theme-Adaptive Guided Onboarding Tour:** Interactive step-by-step walkthrough (`Tour`) featuring an elevated UI spotlight overlay (`tour-spotlight-active`), smooth auto-scrolling, and theme-matched popovers.
* **Polished Modern UI:** Built-in Light/Dark mode switcher with `localStorage` persistence, dynamic Chart.js theme adaptation, modern non-blocking toast notifications (`showToast`), and custom delete confirmation modals.

---

## Tech Stack

* **Backend:** Python, FastAPI, SQLite (`database.db`), Uvicorn
* **Frontend:** HTML5, Tailwind CSS (with Dark Mode support), JavaScript (ES6+), Chart.js (with Annotation plugin), Lucide Icons

---

## Project Architecture & Directory Structure

```text
SubjectCoverage/
├── main.py              # FastAPI REST API, SQLite connection & decay math engine
├── index.html           # Full single-page application (UI, Chart.js, Tour, Toast)
├── database.db          # Auto-generated SQLite database
└── README.md            # Project documentation
```

Database Schema Highlights
The SQLite backend initializes four core tables on startup:

users: Multi-user scaffold (id, name, email, created_at).

tasks: Tracks core GATE subjects, daily routines, and sprint parameters (id, title, category, is_sprint, sprint_duration_days, sprint_start_date).

task_skill_mappings: Stores multi-select subject tag mappings and auto-calculated credit weights (task_id, gate_subject_id, credit_weight).

daily_logs: Logs daily execution status and weighted hours per calendar date (task_id, log_date, completed, hours_spent, completed_at).
