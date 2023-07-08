import datetime

from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.mutable import MutableList

from pydantic import BaseModel

from database import Base

"""
Request models
"""


class UserTokenItem(BaseModel):
    token: str
    user_token: str


class AddUserItem(BaseModel):
    name: str


"""
Database models
"""
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
    # to add 
    attempt = Column(Integer, nullable=True) # attempt
    script = Column(String, nullable=True) # script




class RunMetadata(Base):
    __tablename__ = "run_metadata"
    id = Column(Integer, primary_key=True)
    token = Column(String, nullable=False)
    run_name = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow())
    reference = Column(String, nullable=True)
    # to add
    command_line = Column(String, nullable=True) #commandLine
    error_message = Column(String, nullable=True) #errorMessage
    script_file = Column(String, nullable=True) #scriptFile
    # all following under "stats": 
    succeeded_count = Column(Integer, nullable=True) # succeededCount
    # processes = list of processes, how to handle this?
    peak_running = Column(Integer, nullable=True) # peakRunning
    aborted = Column(Integer, nullable=True)
    failed = Column(Integer, nullable=True)
    peak_cpus = Column(Integer, nullable=True) # peakCPUS
    peak_memory = Column(Integer, nullable=True) #peakMemory


    # process in processes: 
    """
    index (int)
    pending (int)
    ignored (int)
    loadCpus (int)
    totalCount (int)
    succeeded (int)
    errored (bool)
    running (int)
    retries (int)
    peakRunning (int)
    name (string)
    loadMemory (int)
    stored (int)
    terminated (bool)
    hash (string)
    aborted (int)
    failed (int)
    peakCpus (int)
    peakMemory (int)
    completedCount (int)
    cached (int)
    submitted (int)
    """