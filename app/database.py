import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


user = os.getenv("DB_USER")
password = os.getenv("DB_PASS")
dbname = os.getenv("DB_NAME")
hostname = os.getenv("DB_HOSTNAME")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{user}:{password}@{hostname}/{dbname}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()