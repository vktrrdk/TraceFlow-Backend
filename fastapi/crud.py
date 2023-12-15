import json
from datetime import datetime
import time
from fastapi import Depends

from database import engine, get_session, get_async_session

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, select, desc
import string, random
import models, schemas, helpers
import logging
import numpy as np

logger = logging.getLogger('rq.worker')

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

def get_paginated_table(db: Session, token_id: str, run_name, page, rows, sort_field, sort_order):
    # will need further adjustments!
    offset = page * rows
    if sort_field is None or sort_field == "null" or sort_field == "":
        sort_field = "task_id"
    print(sort_order)
    sort_method = sort_field if sort_order == 1 or sort_order is None or sort_order == "null" else desc(sort_field) 
    traces = db.query(models.RunTrace).filter(models.RunTrace.token == token_id, models.RunTrace.run_name == run_name).order_by(sort_method).offset(offset).limit(10).all()
    return traces



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

"""
PLOT DATA RETRIEVAL BELOW

! -- this should be refactored, so only one request is made and all plot data is returned via this single request! would prevent multiple database queries
FILTERING needs to be implemented!
"""

def get_plot_results(db: Session, token_id, run_name, process_filter, tag_filter):
    traces = db.query(models.RunTrace).filter(models.RunTrace.token == token_id, models.RunTrace.run_name == run_name).all()
    
    grouped_traces = helpers.group_by_process(traces)
    relative_ram_boxplot_values = {}
    cpu_allocation_boxplot_values = {}

    for process, tasks in grouped_traces.items():
        percentage_values = [(task.rss / task.memory) * 100 for task in tasks if task.rss and task.memory]

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

        allocation_values = [task.cpu_percentage / task.cpus for task in tasks if task.cpu_percentage and task.cpus]
        
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
    
    full_plot_data = {
        "relative_ram": [list(grouped_traces.keys()), relative_ram_boxplot_values],
        "cpu_allocation": [list(grouped_traces.keys()), cpu_allocation_boxplot_values]
    }

    return full_plot_data

#### use as example
def get_filtered_ram_plot_results(db: Session, token_id, run_name, process_filter, tag_filter):
    traces = db.query(models.RunTrace).filter(models.RunTrace.token == token_id, models.RunTrace.run_name == run_name).all()
    
    grouped_traces = helpers.group_by_process(traces)
    process_boxplot_values = {}
    for process, tasks in grouped_traces.items():
        percentage_values = [(task.rss / task.memory) * 100 for task in tasks if task.rss and task.memory]

        q1 = np.percentile(percentage_values, 25)
        median = np.percentile(percentage_values, 50)
        q3 = np.percentile(percentage_values, 75)
        min_val = np.min(percentage_values)
        max_val = np.max(percentage_values)

        process_boxplot_values[process] = {
            'min': min_val,
            'q1': q1,
            'median': median,
            'q3': q3,
            'max': max_val,
        }

    return list(grouped_traces.keys()), process_boxplot_values

def get_filtered_cpu_allocation_plot_results(db: Session, token_id, run_name, process_filter, tag_filter):
    traces = db.query(models.RunTrace).filter(models.RunTrace.token == token_id, models.RunTrace.run_name == run_name).all()

    grouped_traces = helpers.group_by_process(traces)
    process_boxplot_values = {}
    
    for process, tasks in grouped_traces.items():
        allocation_values = [task.cpu_percentage / task.cpus for task in tasks if task.cpu_percentage and task.cpus]
        
        q1 = np.percentile(allocation_values, 25)
        median = np.percentile(allocation_values, 50)
        q3 = np.percentile(allocation_values, 75)
        min_val = np.min(allocation_values)
        max_val = np.max(allocation_values)

        process_boxplot_values[process] = {
            'min': min_val,
            'q1': q1,
            'median': median,
            'q3': q3,
            'max': max_val,
        }
    return list(grouped_traces.keys()), process_boxplot_values

"""

FURTHER TODO: add the labels to the response 

example data for precalculated boxplots:

const data: ChartConfiguration<'boxplot'>['data'] = {
  labels: ['array', '{boxplot values}', 'with items', 'as outliers'],
  datasets: [
    {
      label: 'Dataset 1',
      borderWidth: 1,
      itemRadius: 2,
      itemStyle: 'circle',
      itemBackgroundColor: '#000',
      outlierBackgroundColor: '#000',
      data: [
        [1, 2, 3, 4, 5, 11],
        {
          min: 1,
          q1: 2,
          median: 3,
          q3: 4,
          max: 5,
        },
        {
          min: 1,
          q1: 2,
          median: 3,
          q3: 4,
          max: 5,
          items: [1, 2, 3, 4, 5],
        },
        {
          min: 1,
          q1: 2,
          median: 3,
          q3: 4,
          max: 5,
          outliers: [11],
        },
      ],
    },
  ],
};

"""

    

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
        result_traces = await async_session.execute(
            select(models.RunTrace).where(
                models.RunTrace.task_id == trace_object.task_id,
                models.RunTrace.token == trace_object.token, 
                models.RunTrace.run_id == trace_object.run_id,
            )
        )
        
        task_trace_object = result_traces.first()
        if task_trace_object:
            # this needs to be adjusted! seems like some adds are still slipping through - e.g when during retrieval of the object there is a an update -->
            # check for race condition fix
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

