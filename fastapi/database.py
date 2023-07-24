from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# adjust to host env variable

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:pgpassword1@nfa_db:5432/nextflow_analysis"
#SQLALCHEMY_DATABASE_URL = "postgresql://postgres:pgpassword1@localhost:5432/nextflow_analysis"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()