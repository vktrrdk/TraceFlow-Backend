import datetime
from typing import List
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship

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
    run_id = Column(String, nullable=True) #runId
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
    attempt = Column(Integer, nullable=True) # trace:attempt
    script = Column(String, nullable=True) # trace:script
    time = Column(Integer, nullable=True) #trace:time
    realtime = Column(Integer, nullable=True) # trace:realtime
    cpu_percentage = Column(Float(4), nullable=True) # trace:%cpu
    rchar = Column(Integer, nullable=True) # trace:rchar
    wchar = Column(Integer, nullable=True) # trace:wchar
    syscr = Column(Integer, nullable=True) # trace:syscr
    syscw = Column(Integer, nullable=True) # trace:syscw
    read_bytes = Column(Integer, nullable=True) # trace:read_bytes
    write_bytes = Column(Integer, nullable=True) # trace:write_bytes
    memory_percentage = Column(Float(4), nullable=True) # trace:%mem
    vmem = Column(Integer, nullable=True) # trace:vmem
    rss = Column(Integer, nullable=True) # trace:rss
    peak_vmem = Column(Integer, nullable=True) # trace:peak_vmem
    peak_rss = Column(Integer, nullable=True) # trace:peak_rss
    vol_ctxt = Column(Integer, nullable=True) # trace:vol_ctxt
    inv_ctxt = Column(Integer, nullable=True) # trace:inv_ctxt
    event = Column(String, nullable=True) # event



# metadata:workflow:stats
class Stat(Base):
    __tablename__ = "stat"
    succeeded_count = Column(Integer, nullable=True) # succeededCount
    compute_time_fmt = Column(String, nullable=True) #computeTimeFmt
    cached_count = Column(Integer, nullable=True) # cachedCount
    id: Mapped[int] = mapped_column(primary_key=True)
    processes: Mapped[List["Process"]] = relationship() #processes
    parent_id: Mapped[int] = mapped_column(ForeignKey("run_metadata.id"))
    peak_running = Column(Integer, nullable=True) #peakRunning
    succeeded_duration = Column(Integer, nullable=True) # succeededDuration
    cached_pct = Column(Float(4), nullable=True) # cachedPct
    load_memory = Column(Integer, nullable=True) # loadMemory
    succeed_count_fmt = Column(String, nullable=True) #succedCountFmt
    failed_percentage = Column(Float(4), nullable=True) #failedPct
    ignored_count = Column(Integer, nullable=True) #ignoredCount
    submitted_count = Column(Integer, nullable=True) #submittedCount
    running_count = Column(Integer, nullable=True) # runningCount
    peak_memory = Column(Integer, nullable=True) # peakMemory
    succeed_percentage = Column(Float(4), nullable=True) #succeedPercentage
    pending_count = Column(Integer, nullable=True) # pendingCount
    load_cpus = Column(Integer, nullable=True) # loadCpus
    cached_duration = Column(Integer, nullable=True) # cachedDuration
    aborted_count = Column(Integer, nullable=True) #abortedCount
    failed_duration = Column(Integer, nullable=True) # failedDuration
    failed_count = Column(Integer, nullable=True) # failedCount
    load_memory_fmt = Column(String, nullable=True) # loadMemoryFmt
    retries_count = Column(Integer, nullable=True) # retriesCount
    cached_count_fmt = Column(String, nullable=True) # cachedCountFmt
    process_length = Column(Integer, nullable=True) # processLength
    peak_memory_fmt = Column(String, nullable=True) # peakMemoryFmt
    failed_count_fmt = Column(String, nullable=True) # failedCountFmt
    ignored_count_fmt = Column(String, nullable=True) # ignoredCountFmt
    peak_cpus = Column(Integer, nullable=True) # peakCpus
    ignored_percentage = Column(Float(4), nullable=True) # ignoredPct

# metadata:workflow:stats:processes
class Process(Base):
    __tablename__ = "process"
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("stat.id"))
    index = Column(Integer, nullable=True) #index
    pending = Column(Integer, nullable=True) #pending
    ignored = Column(Integer, nullable=True) #ignored
    load_cpus = Column(Integer, nullable=True) # loadCpus
    total_count = Column(Integer, nullable=True) # totalCount
    succeeded = Column(Integer, nullable=True) # succeeded
    errored = Column(Boolean, default=False) # errored
    running = Column(Integer, nullable=True) # running
    retries = Column(Integer, nullable=True) # retries
    peak_running = Column(Integer, nullable=True) # peakRunning
    name = Column(String, nullable=True) # name
    task_name = Column(String, nullable=True) # taskName
    load_memory = Column(Integer, nullable=True) # loadMemory
    stored = Column(Integer, nullable=True) # stored
    terminated = Column(Boolean, default=False) #terminated
    process_hash = Column(String, nullable=True) # hash
    aborted = Column(Integer, nullable=True) #aborted
    failed = Column(Integer, nullable=True) # failed
    peak_cpus = Column(Integer, nullable=True) # peakCpus
    peak_memory = Column(Integer, nullable=True) # peakMemory
    completed_count = Column(Integer, nullable=True) # completedCount
    cached = Column(Integer, nullable=True) # cached
    submitted = Column(Integer, nullable=True) # submitted


class RunMetadata(Base):
    __tablename__ = "run_metadata"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id = Column(String, nullable=True) # runId
    stats: Mapped[List["Stat"]] = relationship()
    token = Column(String)
    run_name = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow())
    reference = Column(String, nullable=True)
    # metadata:workflow to add
    command_line = Column(String, nullable=True) #commandLine
    error_message = Column(String, nullable=True) #errorMessage
    script_file = Column(String, nullable=True) #scriptFile
    
    event = Column(String, nullable=True) # head of json not metadata
    nextflow_version = Column(String, nullable=True) # metadata:workflow:nextflow:version
