import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

PG_USER = os.environ.get('POSTGRES_USER')
PG_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
PG_HOST = os.environ.get('POSTGRES_HOST')
PG_PORT = os.environ.get('POSTGRES_PORT')
PG_DB = os.environ.get('POSTGRES_DB')

# adjust to host env variable

SQLALCHEMY_DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
#SQLALCHEMY_DATABASE_URL = "postgresql://postgres:pgpassword1@localhost:5432/nextflow_analysis"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_session():
    print(PG_PORT)
    return SessionLocal()