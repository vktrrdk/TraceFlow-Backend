import json
from datetime import datetime

from fastapi import Depends

from database import engine, get_session

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
import string, random
import models, schemas


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
    traces_test = db.query(models.RunTrace).all()
    print(len(traces_test))
    traces = sorted(traces, key=timestamp_sort, reverse=True)
    by_task = []
    task_ids = []
    for trace in traces:
        if not trace.task_id in task_ids:
            task_ids.append(trace.task_id)
            by_task.append(trace)
        else:
            tasks_with_same_id_and_name = [obj for obj in by_task if obj.task_id == trace.task_id and obj.run_name == trace.run_name]
            if not any(obj.run_id == trace.run_id and obj.run_name == trace.run_name for obj in tasks_with_same_id_and_name):
                by_task.append(trace);
    return by_task

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
    timestamp = json_ob.get("utcTime", datetime.utcnow())
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
        existing_trace_obj = db.query(models.RunTrace).filter(
            models.RunTrace.task_id == trace_object.task_id, 
            models.RunTrace.token == trace_object.token
        ).first()
        print(existing_trace_obj)
        print(trace_object)
        if existing_trace_obj:
            trace_object.id = existing_trace_obj.id
            object_to_update = db.merge(trace_object)
        else:
            db.add(trace_object)
            object_to_update = trace_object

        db.commit()
        db.refresh(object_to_update)
        trace_saved = True
    db.close()
    return {"metadata_saved": metadata_saved, "trace_saved": trace_saved}








def create_random_token():
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    return ''.join((random.choice(alphabet) for i in range(0, 15)))

