import datetime

from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.mutable import MutableList

from pydantic import BaseModel

from database import Base

class AddTokenItem(BaseModel):
    token: str
    user_token: str

class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True)
    name = Column(String)
    run_tokens = Column(MutableList.as_mutable(ARRAY(String)))


class RunToken(Base):
    __tablename__ = "runtoken"
    id = Column(String, primary_key=True)


class RunTrace(Base):
    __tablename__ = "run_metric"
    id = Column(Integer, primary_key=True)
    token = Column(String, nullable=False)
    run_name = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow())
    task_id = Column(Integer, nullable=True)
    status = Column(String, nullable=True)
    process = Column(String, nullable=True)
    tag = Column(String, nullable=True)
    cpus = Column(Integer, nullable=True)
    memory = Column(Integer, nullable=True)
    disk = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)
    name = Column(String, nullable=True)


class RunMetadata(Base):
    __tablename__ = "run_metadata"
    id = Column(Integer, primary_key=True)
    token = Column(String, nullable=False)
    run_name = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow())
    reference = Column(String, nullable=True)
