from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import date


from database import get_db
import models
import schemas

router=APIRouter(
    prefix="/logs",
    tags=["Logs"]
)

@router.get("/", response_model=schemas.LogResponse)
def getLogs(log_date: date = date.today, db: Session=Depends(get_db)):
    logs=db.query(models.Dailylogs).filter(models.Dailylogs.log_date==log_date).all()
    return logs

@router.post("/toogle", response_model=schemas.LogResponse)
def toogle_log(log_data: schemas.LogToggle, db: Session=Depends(get_db)):
    target_date = log_data.log_date or date.today

    existing_log = db.query(models.Dailylogs).filter(
        models.Dailylogs.log_date==target_date,
        models.Dailylogs.task_id==log_data.task_id
    ).first()

    if existing_log:
        existing_log.completed=log_data.completed
        existing_log.hours_spent=log_data.hours_spent
        db.commit()
        db.refresh(existing_log)
        return existing_log
    else:
        new_log=models.Dailylogs(
            task_id=log_data.task_id,
            log_date=target_date,
            completed=log_data.completed,
            hours_spent=log_data.hours_spent
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return new_log

    
