from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date, timedelta
import math
from sqlalchemy import func

from database import get_db
import models
import schemas

router=APIRouter(
    prefix="/analytics",
    tags=["Anlaytics"]
)

GATE_SUBJECTS = [
    {"id": "dbms", "name": "Database Management Systems"},
    {"id": "os", "name": "Operating Systems"},
    {"id": "cn", "name": "Computer Networks"},
    {"id": "algo", "name": "Algorithms & Data Structures"},
    {"id": "toc", "name": "Theory of Computation"},
    {"id": "compiler", "name": "Compiler Design"},
    {"id": "coa", "name": "Computer Organization & Architecture"},
    {"id": "discrete_math", "name": "Discrete Mathematics"}
]

@router.get("/comparative", response_model=schemas.ComparativeAnalyticsResponse)
def get_comparative_analysis(db: Session=Depends(get_db)):
    today=date.today()

    active_sprints = db.query(models.Task).filter(
        models.Task.is_sprint==True,
        models.Task.is_deleted==False
    ).all()

    has_active_sprint= len(active_sprints)>0
    alpha=0.97 if has_active_sprint else 0

    logs = db.query(models.Dailylogs).join(models.Task).filter(
        models.Task.is_deleted==False,
        models.Dailylogs.completed==True
    ).all()

    subject_scores={}
    for s in GATE_SUBJECTS:
        subject_scores[s[id]]={
            'raw_hours': 0.0,
            'decayed_scores': 0.0,
            'name': s['name']
        }

    for log in logs:
        days_ago=(today-log.log_date).days
        if days_ago>=0:
            decay_factor=math.pow(alpha, days_ago)
            weighted_score=log.hours_spent*decay_factor

            mappings=db.query(models.TaskSillMapping).filter(
                models.TaskSillMapping.task_id==log.task_id
            ).all()

            if mappings:
                for map_item in mappings:
                    if map_item.gate_subject_id in subject_scores:
                        subject_scores[map_item.gate_subject_id]['raw_hours'] += log.hours_spent*map_item
                        subject_scores[map_item.gate_subject_id]['decayed_scores'] += weighted_score*map_item.credit_weight
                    else:
                        # If no mapping exists, attribute directly if task category matches a subject ID
                        cat_id = log.task.category.lower().replace(" ", "_")
                        if cat_id in subject_scores:
                            subject_scores[cat_id]["raw_hours"] += log.hours_spent
                            subject_scores[cat_id]["decayed_score"] += weighted_score


            total_decayed_scores=sum(s["decayed_scores"] for s in subject_scores.values())

            subject_results=[]

            for sub_id, data in subject_scores():
                effort_share=(data["delayed_score"]/total_decayed_scores*100) if total_decayed_scores>0 else 0

                subject_results.append({
                    "subject_id": sub_id,
                    "subject_name": data["name"],
                    "raw_hours": round(data["raw_hours"], 2),
                    "decayed_score": round(data["decayed_score"], 2),
                    "effort_share_pct": round(effort_share, 2),
                    "is_alert": effort_share < 8.3  # Group benchmark average (100% / 12 ~ 8.3%)
                })

            return {
                "alpha_decay": alpha,
                "damping_active": has_active_sprint,
                "subjects": subject_results
            }

@router.get("/line-trend", response_model=List[schemas.LineTrendPoint])
def get_line_trend(days: int = 30, db: Session = Depends(get_db)):
    start_date = date.today() - timedelta(days=days)

    # SQL: SELECT log_date, SUM(hours_spent) FROM daily_logs WHERE completed=1 GROUP BY log_date
    results = db.query(
        models.Dailylogs.log_date,
        func.sum(models.Dailylogs.hours_spent).label("total_hours")
    ).join(models.Task).filter(
        models.Task.is_deleted == False,
        models.Dailylogs.completed == True,
        models.Dailylogs.log_date >= start_date
    ).group_by(
        models.Dailylogs.log_date
    ).order_by(
        models.Dailylogs.log_date.asc()
    ).all()

    # Format into list of objects
    trend_data = [
        {"log_date": row.log_date, "total_hours": float(row.total_hours or 0.0)}
        for row in results
    ]

    return trend_data
    