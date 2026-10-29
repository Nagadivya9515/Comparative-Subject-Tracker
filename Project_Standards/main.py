from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
import taskroutes
import logroutes
import analyticsroutes
import models

models.Base.metadata.create_all(bind=engine)

app=FastAPI(
    title="Subject Coverage & Habit Tracker API",
    version=2.0
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"]
)

app.include_router(taskroutes.router)
app.include_router(logroutes.router)
app.include_router(analyticsroutes.router)

@app.get("/")
def root():
    return {"status": "online", "message": "Subject Coverage API running with SQLAlchemy"}


