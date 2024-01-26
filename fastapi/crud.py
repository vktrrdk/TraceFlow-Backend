import json
from datetime import datetime
from fastapi import Depends
import os
from database import engine, get_session, get_async_session

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, select, desc, text, or_
from sqlalchemy.sql.expression import func
import string, random
import models, schemas, helpers
import logging
import numpy as np
from redis import Redis
from pottery import Redlock

logger = logging.getLogger('rq.worker')

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
r_con = Redis(host=REDIS_HOST, port=6379)

"""
Change the Session for each database query, instead of using all the same!
Also check, that the redis queue worker has the correct env variables set, so it is able to perform the session-creation
Check performance with redis queue on cluster machine
"""


def get_user(db: Session, id: string):
    query = db.query(models.User).filter(models.User.id == id).first()
    return query


def create_user(db: Session, name: str):
    token = create_random_token()
    db_user = models.User(id=token, name=name, run_tokens=[])
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_all_users(db: Session):
    return db.query(models.User).all()


def get_all_token(db: Session):
    return db.query(models.RunToken).all()


def get_full_trace(db: Session):
    return db.query(models.RunTrace).all()

def get_full_stats(db: Session):
    return db.query(models.Stat).all()

def get_full_processes(db: Session):
    return db.query(models.Process).all()

def get_process_by_token(db: Session, token_id):
    stats = get_stats_by_token(db, token_id)
    processes = []
    for stat in stats:
        st = db.query(models.Process).filter(models.Process.parent_id == stat.id).all()
        for s in st:
            processes.append(s)
    return processes
    

def get_stats_by_token(db: Session, token_id):
    metas = db.query(models.RunMetadata).filter(models.RunMetadata.token == token_id).all()
    #return db.query(models.Stat).filter(models.Stat.parent_id == token_id).all()
    # more pythonic way for sure
    stats = []
    for meta in metas:
        mt = db.query(models.Stat).filter(models.Stat.parent_id == meta.id).all()
        for m in mt: 
            stats.append(m)
    return stats

def get_meta_by_token(db: Session, token_id):
    metas = db.query(models.RunMetadata).filter(models.RunMetadata.token == token_id).all()
    return metas


def set_all_tasks_running(db: Session, token_id):
    trace_for_token = get_run_trace_by_token(db, token_id)
    for token in trace_for_token:
        token.status = "RUNNING"
    db.commit()
    return True


def get_run_trace(db: Session, token: models.RunToken):
    return db.query(models.RunTrace).filter(models.RunTrace.token == token.id).all()


def timestamp_sort(obj):
    if obj.complete is not None:
        return obj.complete
    elif obj.start is not None:
        return obj.start
    else:
        return obj.submit

def get_task_states_by_token(db: Session, token_id):
    traces = db.query(models.RunTrace).filter(models.RunTrace.token == token_id).all()
    return traces

def get_run_trace_by_token(db: Session, token_id):
    return db.query(models.RunTrace).filter(models.RunTrace.token == token_id).all()


def get_run_state_by_process(objects):
    objects = sorted(objects, key=timestamp_sort, reverse=True)
    processes_splitty = {}
    for entry in objects:
        if not entry.process in processes_splitty:
            processes_splitty[entry.process] = [entry.task_id]
        elif entry.task_id not in processes_splitty[entry.process]:
            processes_splitty[entry.process].append(entry.task_id)
    #print(processes_splitty)

    processes = {}

    """
    openai distinguisher
    result_dict = {}
    for obj in objects:
        name_parts = obj.name.split(":")
        for i, part in enumerate(name_parts):
            if i not in result_dict:
                result_dict[i] = {}
            if part not in result_dict[i]:
                result_dict[i][part] = []
            result_dict[i][part].append(obj)
            if len(result_dict[i]) > 1:
                break
    print(result)
    """
    
    for process in processes_splitty:
        tasks = processes_splitty[process]
        if process not in processes:
            processes[process] = {"tasks": {}}
        for task_id in tasks:
             

            latest_obj = next((x for x in objects if x.task_id == task_id), None)
            process_tasks = processes[process]["tasks"]
            if not task_id in process_tasks:
                process_tasks[task_id] = vars(latest_obj)
            # check how to adjust sub_task !

    return processes
    """
    processes = {}

    for entry in objects:
        process = entry.process.split(":")[0]
        if process not in processes:
            processes[process] = {"tasks": {}}

    for entry in objects:
        splitted_process_name = entry.process.split(":", 1)
        task_subname = None
        if len(splitted_process_name) > 1:
            task_subname = splitted_process_name[1]
        process_tasks = processes[splitted_process_name[0]]["tasks"]
        if not entry.task_id in process_tasks:
            process_tasks[entry.task_id] = vars(entry)
            process_tasks[entry.task_id]["sub_task"] = task_subname

    print(processes != processes_2)
    return processes
    """


def get_status_score(status):
    if status == "RUNNING":
        return 10
    elif status == "COMPLETED":
        return 100
    else:
        return 0

def get_full_meta(db: Session):
    return db.query(models.RunMetadata).all()


def create_token(db: Session):
    token = create_random_token()
    db_token = models.RunToken(id=token)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def get_token(db: Session, token_id: str):
    return db.query(models.RunToken).get(token_id)


def remove_token(db: Session, token):
    user = db.query(models.User).filter(models.User.run_tokens.contains([token.id])).first()
    if user:
        remove_token_from_user(db, user, token)
    db.delete(token)
    db.commit()
    return {"removed_token": token.id, "removed_from_user": user is not None}

def remove_token_and_connected_information(db, token):
    token_id = token.id
    processes = get_process_by_token(db, token_id)
    for process in processes:
        db.delete(process)
    db.commit()
    stats = get_stats_by_token(db, token_id)   
    for stat in stats:
        db.delete(stat)
    db.commit()
    metas = get_meta_by_token(db, token_id)
    for meta in metas:
        db.delete(meta)
    db.commit()
    traces = get_run_trace_by_token(db, token_id)
    for trace in traces:
        db.delete(trace)
    db.commit()
    db.delete(token)
    db.commit()
    return {"deleted": True}
 
    
   



def remove_all_token_from_user(user_id: str, db: Session):
    user = get_user(db, user_id)
    tokens = user.run_tokens
    user.run_tokens = []
    db.commit()
    db.refresh(user)
    return {"user": user_id, "removed_tokens": tokens}


def add_token_to_user(db: Session, user_id, token):
    user = get_user(db, user_id)
    if token.id not in user.run_tokens:
        user.run_tokens.append(token.id)
        db.commit()
        db.refresh(user)
        return {"added_token": token.id}
    return {"added_token": None}


def remove_token_from_user(db: Session, user, token):
    tokens = user.run_tokens
    try:
        idx = tokens.index(token.id)
    except ValueError:
        print(f"{token.id}: no such token in list of tokens for user {user.id}")
        return {"removed_token": None}
    new_tokens = [token for token in tokens if not tokens.index(token) == idx]
    user.run_tokens = new_tokens
    db.commit()
    db.refresh(user)

    return {"removed_token", token.id}


def get_metadata_data(json_ob, token_id):
    metadata = json_ob.get("metadata", None)
    run_name = json_ob.get("runName", None)
    run_id = json_ob.get("runId", None)
    event = json_ob.get("event", None)
    timestamp = json_ob.get("utcTime", "")
    if timestamp == "":
        timestamp = datetime.utcnow()
    else:
        timestamp_format = "%Y-%m-%dT%H:%M:%SZ"
        timestamp = datetime.strptime(timestamp, timestamp_format)
    command_line = None
    error_message = None
    script_file = None
    reference = None
    nextflow_version = None
    reference = None
    nextflow_version = None
    scratch = json_ob.get("scratch", None)
    project_name = None
    revision = None
    work_dir = None
    user_name = None

    params = metadata.get("parameters", None)
    workflow = metadata.get("workflow", None)
    if workflow is not None:
        command_line = workflow.get("commandLine", None)
        error_message = workflow.get("errorMessage", None)
        script_file =  workflow.get("script_file", None)
        nextflow_version = workflow.get("nextflow", None)
        project_name = workflow.get("project_name", None)
        revision = workflow.get("revision", None)
        work_dir = workflow.get("workDir", None)
        user_name = workflow.get("userName", None)
        if nextflow_version:
            nextflow_version = nextflow_version.get("version", None)
        if params is not None:
            reference = params.get("reference")
    metadata_dict = {
        "command_line": command_line,
        "run_id": run_id,
        "run_name": run_name,
        "event": event,
        "reference": reference,
        "error_message": error_message,
        "script_file": script_file,
        "nextflow_version": nextflow_version,
        "token": token_id,
        "timestamp": timestamp,
        "scratch": scratch, 
        "project_name": project_name,
        "revision": revision,
        "work_dir": work_dir,
        "user_name": user_name,
    }
    return metadata_dict

def get_stat_data(json_ob, meta_id):
    metadata = json_ob.get("metadata", None)
    if metadata is not None:
        workflow_data = metadata.get("workflow", None)
        if workflow_data is not None:
            stats = workflow_data.get("stats", None)
            if stats is not None:
                stats_dict = {
                    "succeeded_count": stats.get("succeededCount", None),
                    "compute_time_fmt": stats.get("computeTimeFmt", None),
                    "cached_count": stats.get("cachedCount", None),
                    "succeeded_duration": stats.get("succeededDuration", None),
                    "cached_pct": stats.get("cachedPct", None),
                    "load_memory": stats.get("loadMemory", None),
                    "succeed_count_fmt": stats.get("succeedCountFmt", None),
                    "failed_percentage": stats.get("failedPct", None),
                    "ignored_count": stats.get("ignoredCount", None),
                    "submitted_count": stats.get("submittedCount", None),
                    "peak_memory": stats.get("peakMemory", None),
                    "succeed_percentage": stats.get("succeedPct", None),
                    "running_count": stats.get("runningCount", None),
                    "pending_count": stats.get("pendingCount", None),
                    "load_cpus": stats.get("loadCpus", None),
                    "cached_duration": stats.get("cachedDuration", None),
                    "aborted_count": stats.get("abortedCount", None),
                    "failed_duration":stats.get("failedDuration", None),
                    "failed_count": stats.get("failedCount", None),
                    "load_memory_fmt": stats.get("loadMemoryFmt", None),
                    "retries_count": stats.get("retriesCount", None),
                    "cached_count_fmt": stats.get("cachedCountFmt", None),
                    "process_length": stats.get("processLength", None),
                    "peak_memory_fmt": stats.get("peakMemoryFmt", None),
                    "failed_count_fmt": stats.get("failedCountFmt", None),
                    "ignored_count_fmt": stats.get("ignoredCountFmt", None),
                    "peak_cpus": stats.get("peakCpus", None),
                    "ignored_percentage": stats.get("ignoredPct", None),
                    "parent_id": meta_id,
                }
                return stats_dict
    return {}

def get_process_data(json_ob, stat_id):
    metadata = json_ob.get("metadata", None)
    if metadata is not None:
        workflow_data = metadata.get("workflow", None)
        if workflow_data is not None:
            stats = workflow_data.get("stats", None)
            if stats is not None:
                processes = stats.get("processes", None)
                if processes is not None:
                    processes_list = []
                    for process in processes:
                        process_dict = {
                            "parent_id": stat_id,
                            "index": process.get("index", None),
                            "pending": process.get("pending", None),
                            "ignored": process.get("ingored", None),
                            "load_cpus": process.get("loadCpus", None),
                            "total_count": process.get("totalCount", None),
                            "succeeded": process.get("succeeded", None),
                            "errored": process.get("errored", None),
                            "running": process.get("running", None),
                            "retries": process.get("retries", None),
                            "peak_running": process.get("peakRunning", None),
                            "name": process.get("name", None),
                            "task_name": process.get("taskName", None),
                            "load_memory": process.get("loadMemory", None),
                            "stored": process.get("stored", None),
                            "terminated": process.get("terminated", None),
                            "process_hash": process.get("hash", None),
                            "aborted": process.get("aborted", None),
                            "peak_cpus": process.get("peakCpus", None),
                            "peak_memory": process.get("peakMemory", None),
                            "completed_count": process.get("completedCount", None),
                            "cached": process.get("cached", None),
                            "submitted": process.get("submitted", None),
                        }
                        processes_list.append(process_dict)
                    return processes_list
    return []

def get_trace_data(json_obj, token_id):
    trace = json_obj.get("trace", None)
    if trace is not None:
        start_time = trace.get("start", None)
        if start_time is not None:
            start_time = datetime.fromtimestamp(start_time / 1000)
        submit_time = trace.get("submit", None)
        if submit_time is not None:
            submit_time = datetime.fromtimestamp(submit_time / 1000)
        complete_time = trace.get("complete", None)
        if complete_time is not None:
            complete_time = datetime.fromtimestamp(complete_time / 1000)
        
        
        trace_data = {
            "token": token_id,
            "run_id": json_obj.get("runId", None),
            "run_name": json_obj.get("runName", None),
            "start": start_time,
            "submit": submit_time,
            "complete": complete_time,
            "task_id": trace.get("task_id", None),
            "status": trace.get("status", None),
            "process": trace.get("process", None),
            "tag": trace.get("tag", None),
            "cpus": trace.get("cpus", None),
            "memory": trace.get("memory", None),
            "disk": trace.get("disk", None),
            "duration": trace.get("duration", None),
            "name": trace.get("name", None),
            "attempt": trace.get("attempt", None),
            "script": trace.get("script", None),
            "time": trace.get("time", None),
            "realtime": trace.get("realtime", None),
            "cpu_percentage": trace.get("%cpu", None),
            "rchar": trace.get("rchar", None),
            "wchar": trace.get("wchar", None),
            "syscr": trace.get("syscr", None),
            "syscw": trace.get("syscw", None),
            "read_bytes": trace.get("read_bytes", None),
            "write_bytes": trace.get("write_bytes", None),
            "memory_percentage": trace.get("%mem", None),
            "vmem": trace.get("vmem", None),
            "rss": trace.get("rss", None),
            "peak_vmem": trace.get("peak_vmem", None),
            "peak_rss": trace.get("trace", None),
            "vol_ctxt": trace.get("vol_ctxt", None),
            "inv_ctxt": trace.get("inv_ctxt", None),
            "event": json_obj.get("event", None),
            "scratch": trace.get("scratch", None),
        }

        return trace_data
    return {}
    # adjust this functions in the near future because there certainly is a more pythonic way to do this...

def get_paginated_table(db: Session, token_id: str, run_name: str, page, rows, sort_field, sort_order, filters):
    # will need further adjustments --> order function for problematic tasks --> calculation of problematic task needs data entered by user
    # see processIsDeclaredProblematic in workflowComponent
    offset = page * rows
    print(f"offset: {offset}, page: {page}, rows: {rows}")
    process_name_to_filter_by = helpers.get_process_name_to_filter_by(filters)
    full_name_to_filter_by = helpers.get_full_name_to_filter_by(filters)
    process_tags_filter_query = helpers.get_process_tags_to_filter_by(filters) ## 
    process_statuses_to_filter_by = helpers.get_process_statuses_to_filter_by(filters)
    if sort_field is None or sort_field == "null" or sort_field == "":
        sort_field = 'task_id'
    sort_method = text(sort_field) if sort_order == 1 or sort_order is None or sort_order == "null" else desc(text(sort_field)) 
    traces = (
        db.query(models.RunTrace)
        .filter(
            models.RunTrace.token == token_id, 
            models.RunTrace.run_name == run_name, 
            models.RunTrace.process.contains(process_name_to_filter_by),
            models.RunTrace.name.contains(full_name_to_filter_by),
            or_(models.RunTrace.status.in_(process_statuses_to_filter_by), process_statuses_to_filter_by == []),
            process_tags_filter_query,
            )
    )

    number_of_matching_entries = len(traces.all())
    return traces.order_by(sort_method).offset(offset).limit(rows).all(), number_of_matching_entries



def check_for_workflow_completed(db: Session, json_ob: object, token_id: string):
    metas = get_meta_by_token(db, token_id)
    run_id = json_ob["runId"];
    run_name = json_ob["runName"]
    return any(
        meta.event in ['completed', 'failed'] and meta.run_id == run_id and meta.run_name == run_name
        for meta in metas
    )


"""
    What needs to be adjusted:
    When persisting a trace for a job, do the following:
    Set the information of the corresponding values, when they are newer than the one available
    So if a certain task-id (they are unique!) trace gets in, check if the information is "newer" 
    --> submitted - started - completed: update all relevant fields accordingly, instead of saving 3 traces for the same job!

    consider the following code:
    from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, select

app = FastAPI()

# Create a SQLAlchemy engine to connect to the PostgreSQL database
engine = create_engine('postgresql://username:password@localhost/database_name')

metadata = MetaData()
trace_table = Table('trace', metadata,
    Column('id', Integer, primary_key=True),
    Column('trace_id', String),
    Column('state', String),
    Column('timestamp', String)  # Use a proper timestamp type
)

@app.put("/update_trace_state/{trace_id}/{new_state}")
def update_trace_state(trace_id: str, new_state: str):
    # Start a transaction and acquire a lock on the selected row
    with engine.begin() as conn:
        stmt = select([trace_table]).where(trace_table.c.trace_id == trace_id).with_for_update()
        result = conn.execute(stmt)
        row = result.fetchone()

        if row:
            # Perform your modifications to the row
            row.state = new_state
            # Update the row in the database
            conn.execute(trace_table.update().values(state=new_state).where(trace_table.c.trace_id == trace_id))
        else:
            raise HTTPException(status_code=404, detail="Trace not found")

    # The lock is released when the transaction is committed or rolled back
    return {"message": "Trace state updated successfully"}

"""    

def get_progress_for_token_and_run(db: Session, token_id, run_name):
    traces = db.query(models.RunTrace).filter(models.RunTrace.token == token_id, models.RunTrace.run_name == run_name).all()
    progress_values = helpers.get_progress_values_for_trace_list(traces) 

    return progress_values



def get_processes_for_token_and_run(db: Session, token_id, run_name):
    traces = db.query(models.RunTrace).filter(models.RunTrace.token == token_id, models.RunTrace.run_name == run_name).all()
    process_values = helpers.get_processes_for_trace_list(traces)


    processes_to_return = {}
    
    for process_value in process_values:
        processes_to_return[process_value] = [{"tags": trace.tag, "attempt": trace.attempt, "task_id": trace.task_id} for trace in traces if trace.status == "RUNNING" and trace.process == process_value] 

    return processes_to_return

"""
PLOT DATA RETRIEVAL BELOW
FILTERING needs to be implemented!
We also need to consider the units given (gib, mib, ..., s, m, h)
"""

def get_plot_results(db: Session, token_id, run_name, process_filter, tag_filter, memory_format, duration_format):
    trace_query = db.query(models.RunTrace).filter(models.RunTrace.token == token_id, models.RunTrace.run_name == run_name)

    if len(process_filter) > 0:
        trace_query = trace_query.filter(models.RunTrace.process.in_(process_filter))
    if len(tag_filter) > 0:
        if "" in tag_filter:
            tag_filter = [tf for tf in tag_filter if tf != ""]
            first_query = trace_query.filter(
                or_(*[func.replace(models.RunTrace.tag, " ", "").ilike(f'%{tag.replace(" ", "")}%') for tag in tag_filter])
            )
            second_query = trace_query.filter(models.RunTrace.tag.is_(None))
            trace_query = first_query.union(second_query)
        else:
            trace_query = trace_query.filter(
                or_(*[func.replace(models.RunTrace.tag, " ", "").ilike(f'%{tag.replace(" ", "")}%') for tag in tag_filter])
            )
    # TODO: refactor, check why this is not working as wanted. also consider having this filter applied to all crud methods when filtering
            # is neccessary for that function, as duplication would not be nice
            

    traces = trace_query.all()

    
    grouped_traces = helpers.group_by_process(traces)
    relative_ram_boxplot_values = {}
    cpu_allocation_boxplot_values = {}
    cpu_used_boxplot_values = {}
    io_read_boxplot_values = {}
    io_written_boxplot_values = {}
    ram_requested_boxplot_values = {}
    vmem_boxplot_values = {}
    rss_boxplot_values = {}
    duration_time_boxplot_values = {}
    duration_sum_bar_values = {}
    ram_ratio_plot_values = {}

    for process, tasks in grouped_traces.items():
        percentage_values = [(task.rss / task.memory) * 100 for task in tasks if task.rss and task.memory]
        
        try:
            q1 = np.percentile(percentage_values, 25)
            median = np.percentile(percentage_values, 50)
            q3 = np.percentile(percentage_values, 75)
            min_val = np.min(percentage_values)
            max_val = np.max(percentage_values)
        
            relative_ram_boxplot_values[process] = {
                'min': min_val,
                'q1': q1,
                'median': median,
                'q3': q3,
                'max': max_val,
            }

        except IndexError as e:
            logger.info(f"IndexError - {e}\n\nDue to missing memory percentage values")
            relative_ram_boxplot_values[process] = {}

        allocation_values = [task.cpu_percentage / task.cpus for task in tasks if task.cpu_percentage and task.cpus]
        
        try:
            q1 = np.percentile(allocation_values, 25)
            median = np.percentile(allocation_values, 50)
            q3 = np.percentile(allocation_values, 75)
            min_val = np.min(allocation_values)
            max_val = np.max(allocation_values)

            cpu_allocation_boxplot_values[process] = {
                'min': min_val,
                'q1': q1,
                'median': median,
                'q3': q3,
                'max': max_val,
            }
        
        except IndexError as e:
            logger.info(f"IndexError - {e}\n\nDue to missing cpu allocation values")
            cpu_allocation_boxplot_values[process] = {}

        cpu_raw_used_values = [task.cpu_percentage for task in tasks if task.cpu_percentage]

        try:
            
            q1 = np.percentile(cpu_raw_used_values, 25)
            median = np.percentile(cpu_raw_used_values, 50)
            q3 = np.percentile(cpu_raw_used_values, 75)
            min_val = np.min(cpu_raw_used_values)
            max_val = np.max(cpu_raw_used_values)

            cpu_used_boxplot_values[process] = {
                'min': min_val,
                'q1': q1,
                'median': median,
                'q3': q3,
                'max': max_val,
            }

        except IndexError as e:
            logger.info(f"IndexError - {e}\n\nDue to missing raw cpu usage values")
            cpu_used_boxplot_values[process] = {}

        io_read_data_values = [helpers.convert_to_memory_format(memory_format=memory_format, value=np.int64(task.read_bytes)) for task in tasks if task.read_bytes]
        
        try:
            q1 = np.percentile(io_read_data_values, 25)
            median = np.percentile(io_read_data_values, 50)
            q3 = np.percentile(io_read_data_values, 75)
            min_val = np.min(io_read_data_values)
            max_val = np.max(io_read_data_values)

            io_read_boxplot_values[process] = {
                'min': min_val,
                'q1': q1,
                'median': median,
                'q3': q3,
                'max': max_val,
            }
        except IndexError as e:
            logger.info(f"IndexError - {e}\n\nDue to missing i/o read values")
            io_read_boxplot_values[process] = {}
        
        io_write_data_values = [helpers.convert_to_memory_format(memory_format=memory_format, value=np.int64(task.write_bytes)) for task in tasks if task.write_bytes]
        
        try:
            q1 = np.percentile(io_write_data_values, 25)
            median = np.percentile(io_write_data_values, 50)
            q3 = np.percentile(io_write_data_values, 75)
            min_val = np.min(io_write_data_values)
            max_val = np.max(io_write_data_values)

            io_written_boxplot_values[process] = {
                'min': min_val,
                'q1': q1,
                'median': median,
                'q3': q3,
                'max': max_val,
            }
        except IndexError as e:
            logger.info(f"IndexError - {e}\n\nDue to missing i/o write values")
            io_written_boxplot_values[process] = {}

        requested_ram_values = [helpers.convert_to_memory_format(memory_format=memory_format, value=np.int64(task.memory)) for task in tasks if task.memory]
        vmem_ram_values = [helpers.convert_to_memory_format(memory_format=memory_format, value=np.int64(task.vmem)) for task in tasks if task.vmem]
        rss_ram_values = [helpers.convert_to_memory_format(memory_format=memory_format, value=np.int64(task.rss)) for task in tasks if task.rss]
        
        try:
            q1 = np.percentile(vmem_ram_values, 25)
            median = np.percentile(vmem_ram_values, 50)
            q3 = np.percentile(vmem_ram_values, 75)
            min_val = np.min(vmem_ram_values)
            max_val = np.max(vmem_ram_values)

            vmem_boxplot_values[process] = {
                'min': min_val,
                'q1': q1,
                'median': median,
                'q3': q3,
                'max': max_val,
            }
        except IndexError as e:
            logger.info(f"IndexError - {e}\n\nDue to missing virtual memory values")
            vmem_boxplot_values[process] = {}
        
        try:
            q1 = np.percentile(requested_ram_values, 25)
            median = np.percentile(requested_ram_values, 50)
            q3 = np.percentile(requested_ram_values, 75)
            min_val = np.min(requested_ram_values)
            max_val = np.max(requested_ram_values)

            ram_requested_boxplot_values[process] = {
                'min': min_val,
                'q1': q1,
                'median': median,
                'q3': q3,
                'max': max_val,
            }
        except IndexError as e:
            logger.info(f"IndexError - {e}\n\nDue to missing requested memory values")
            ram_requested_boxplot_values[process] = {}
        
        try:
            q1 = np.percentile(rss_ram_values, 25)
            median = np.percentile(rss_ram_values, 50)
            q3 = np.percentile(rss_ram_values, 75)
            min_val = np.min(rss_ram_values)
            max_val = np.max(rss_ram_values)

            rss_boxplot_values[process] = {
                'min': min_val,
                'q1': q1,
                'median': median,
                'q3': q3,
                'max': max_val,
            }
        except IndexError as e:
            logger.info(f"IndexError - {e}\n\nDue to missing rss memory values")
            rss_boxplot_values[process] = {}


        
        single_realtime_values = [helpers.convert_to_time_format(time_format=duration_format, value=np.int64(task.realtime)) for task in tasks if task.realtime]
        summarized_realtime_values = sum(single_realtime_values)

    

        try: 
            q1 = np.percentile(single_realtime_values, 25)
            median = np.percentile(single_realtime_values, 50)
            q3 = np.percentile(single_realtime_values, 75)
            min_val = np.min(single_realtime_values)
            max_val = np.max(single_realtime_values)
            
            duration_time_boxplot_values[process] = {
                'min': min_val,
                'q1': q1,
                'median': median,
                'q3': q3,
                'max': max_val,
            }
            duration_sum_bar_values[process] = summarized_realtime_values

        except IndexError as e:
            logger.info(f"IndexError - {e}\n\nDue to missing time values")
            duration_time_boxplot_values[process] = {}
            duration_sum_bar_values[process] = 0

        cpu_allocation_values = [task.cpu_percentage / task.cpus for task in tasks if task.cpu_percentage and task.cpus and task.rss and task.memory]
        memory_allocation_values = [(task.rss / task.memory) * 100 for task in tasks if task.cpu_percentage and task.cpus and task.rss and task.memory]

        try:
            x_min = np.min(cpu_allocation_values)
            x_max = np.max(cpu_allocation_values)
            x_mean = np.mean(cpu_allocation_values)
            y_min = np.min(memory_allocation_values)
            y_max = np.max(memory_allocation_values)
            y_mean = np.mean(memory_allocation_values)

            ram_ratio_plot_values[process] = {
                'xMin': x_min,
                'x': x_mean,
                'xMax': x_max,
                'yMin': y_min,
                'y': y_mean,
                'yMax': y_max,
            }

        except IndexError as e:
            logger.info(f"IndexError - {e}\n\nDue to missing cpu or memory allocation values")
            ram_ratio_plot_values[process] = {}



    cpu_usage_data = [cpu_allocation_boxplot_values, cpu_used_boxplot_values]
    io_data = [io_read_boxplot_values, io_written_boxplot_values]
    ram_data = [ram_requested_boxplot_values, vmem_boxplot_values, rss_boxplot_values]
    duration_data = [duration_time_boxplot_values, duration_sum_bar_values]
    
    keylist = list(grouped_traces.keys())
    full_plot_data = {
        "relative_ram": [keylist, relative_ram_boxplot_values],
        "cpu": [keylist, cpu_usage_data],
        "io": [keylist, io_data],
        "ram": [keylist, ram_data],
        "duration": [keylist, duration_data],
        "cpu_ram_ratio": [keylist, ram_ratio_plot_values]
    }

    return full_plot_data

    ### TODO: Numpy int64 values lead to errors on json-encoding - for values like bytes and/or other small units this may lead to problems! --> needs to be adjusted

def get_available_processes_and_tags(db: Session, token_id, run_name):
    traces = db.query(models.RunTrace).filter(models.RunTrace.token == token_id, models.RunTrace.run_name == run_name).all()
    temp_result_processes, temp_result_tags = [], []
    for trace in traces:
        temp_result_processes.append(trace.process)
        process_tags = helpers.tags_from_process(trace)
        temp_result_tags.extend(process_tags)
    tag_result = helpers.get_unique_tags(temp_result_tags)
    return {'processes': list(set(temp_result_processes)), 'tags': tag_result}


def persist_trace(json_ob, token):
  
    db = get_session()
    

    metadata_saved = False
    trace_saved = False
    metadata = json_ob.get("metadata", None)
    if metadata is not None:
        metadata_data = get_metadata_data(json_ob, token.id)
        meta_object = models.RunMetadata(**metadata_data)
        db.add(meta_object)
        db.commit()
        db.refresh(meta_object)
        
        stat_data = get_stat_data(json_ob, meta_object.id)
        stat_object = models.Stat(**stat_data)
        db.add(stat_object)
        db.commit()
        db.refresh(stat_object)

        processes_data = get_process_data(json_ob, stat_object.id)
        for process_data in processes_data:
            process_object = models.Process(**process_data)
            db.add(process_object)
            db.commit()
            db.refresh(process_object)
    
    trace = json_ob.get("trace")
    
    if trace is not None:
        trace_data = get_trace_data(json_ob, token.id)
        trace_object = models.RunTrace(**trace_data)
           
        db.add(trace_object)
        db.commit()
        db.refresh(trace_object)
        trace_saved = True
    db.close()
    return {"metadata_saved": metadata_saved, "trace_saved": trace_saved}


async def persist_object_data(async_session, add_object):
    async with async_session.begin():
        async_session.add(add_object)
    await async_session.commit()

async def persist_singleton_trace_data(async_session, trace_object: models.RunTrace):
    async with async_session.begin():

        task_lock = Redlock(
            key=f"trace_{trace_object.token}_{trace_object.run_name}_{trace_object.task_id}",
            masters={r_con}
        )
        with task_lock:
            result_traces = await async_session.execute(
                select(models.RunTrace).where(
                    models.RunTrace.task_id == trace_object.task_id,
                    models.RunTrace.token == trace_object.token, 
                    models.RunTrace.run_name == trace_object.run_name,
                )
            )

            task_trace_object = result_traces.first()
            if task_trace_object:
                task_trace_object = task_trace_object[0]
                if helpers.has_newer_state(task_trace_object, trace_object):
                    await async_session.delete(task_trace_object)
                    async_session.add(trace_object)
            else:
                async_session.add(trace_object)
            await async_session.commit()

        




async def persist_object_list_data(async_session, add_object_list):
    async with async_session.begin():
        async_session.add_all(add_object_list)
    await async_session.commit()


async def persist_trace_async(json_ob, token_id):
    """
    CONSIDER: token_id needs to be checked # 
    TODO: implement check
    """

    async_db = get_async_session()
    metadata = json_ob.get("metadata", None)
    if metadata is not None:
        metadata_data = get_metadata_data(json_ob, token_id)
        meta_object = models.RunMetadata(**metadata_data)
        stat_data = get_stat_data(json_ob, meta_object.id)
        stat_object = models.Stat(**stat_data)
        process_object_list = []
        processes_data = get_process_data(json_ob, stat_object.id)
        for process_data in processes_data:
                process_object = models.Process(**process_data)
                process_object_list.append(process_object)

        await persist_object_data(async_db, meta_object)
        await persist_object_data(async_db, stat_object)
        if len(process_object_list) > 0:
            await persist_object_list_data(async_db, process_object_list)
            
    trace = json_ob.get("trace")
        
    if trace is not None:
        trace_data = get_trace_data(json_ob, token_id)
        trace_object = models.RunTrace(**trace_data)
        
        await persist_singleton_trace_data(async_db, trace_object)


def create_random_token():
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    return ''.join((random.choice(alphabet) for i in range(0, 15)))

