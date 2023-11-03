import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

PG_USER = os.environ.get('POSTGRES_USER', 'postgres')
PG_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'pgpassword1')
PG_HOST = os.environ.get('POSTGRES_HOST', 'nfa_db')
PG_PORT = os.environ.get('POSTGRES_PORT', '5432')
PG_DB = os.environ.get('POSTGRES_DB', 'nextflow_analysis')

# adjust to host env variable

SQLALCHEMY_DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
SQLALCHEMY_ASYNC_DATABASE_URL = f"postgresql+asyncpg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}" # check thsi!
#SQLALCHEMY_DATABASE_URL = "postgresql://postgres:pgpassword1@localhost:5432/nextflow_analysis"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
test_engine = create_async_engine(SQLALCHEMY_ASYNC_DATABASE_URL, echo=True) # check this!
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()