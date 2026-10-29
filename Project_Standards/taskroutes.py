
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas

router=APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

@router.get("/", response_model=List[schemas.TaskResponse], status_code=status.HTTP_200_OK)
def get_tasks(db: Session=Depends(get_db)):
    tasks=db.query(models.tasks).filter(models.Task.is_deleted == 0).all()
    return tasks

@router.post("/",response_model=schemas.TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task:schemas.TaskCreate, db: Session=Depends(get_db)):
    new_task=models.Task(title=task.title, 
                         category=task.category, 
                         is_sprint=1 if task.is_sprint else 0, 
                         sprint_duration_days=task.sprint_duration_days if task.is_sprint else 0, 
                         sprint_start_date=task.sprint_start_date)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session=Depends(get_db)):
    task_query=db.query(models.Task).filter(models.Task.id==task_id)
    task=task_query.firstone()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )

    task.is_deleted=1
    db.commit()
    return {"status": "soft_deleted", "task_id": task_id}

@router.post("/{task_id}/restore", status_code=status.HTTP_200_OK)
def restore_task(task_id: int, db: Session=Depends(get_db)):
    task_query=db.query(models.Task).filter(models.Task.id==task_id)
    task=task_query.first()

    task.is_deleted=0
    db.commit()
    return {"status": "restored", "task_id": task_id}


