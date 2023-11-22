import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs, AsyncSession
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
asyncSession = create_async_engine(SQLALCHEMY_ASYNC_DATABASE_URL, echo=True, connect_args={"server_settings": {"jit": "off"}},) # check this!
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def get_async_session():
    async_engine = create_async_engine(SQLALCHEMY_ASYNC_DATABASE_URL, echo=True)
    async_session = async_sessionmaker(async_engine, expire_on_commit=False)
    return async_session()
