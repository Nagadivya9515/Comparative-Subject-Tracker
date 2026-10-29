import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url

# Set DATABASE_URL in the environment to use MySQL or Oracle. For example:
# mysql+pymysql://user:password@host:3306/database
# oracle+oracledb://user:password@host:1521/?service_name=service
# URL-encode special characters when credentials are embedded in the URL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./subject_coverage.db")
database_url = make_url(DATABASE_URL)
connect_args = {"check_same_thread": False} if database_url.drivername == "sqlite" else {}
engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()