import json
from datetime import datetime

from sqlalchemy.orm import Session
import string, random
import models, schemas

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
            print(1)
            stats.append(m)
    return stats


def get_run_trace(db: Session, token: models.RunToken):
    return db.query(models.RunTrace).filter(models.RunTrace.token == token.id).all()


def get_run_state_by_process(objects):
    processes = {}
    objects = sorted(objects, key=lambda obj: obj.timestamp)

    for entry in objects:
        process = entry.process.split(":")[0]
        if process not in processes:
            processes[process] = {"tasks": {}}

    for entry in objects:
        splitted_process_name = entry.process.split(":")
        task_subname = None
        if len(splitted_process_name) > 1:
            task_subname = splitted_process_name[1]
        process_tasks = processes[entry.process.split(":")[0]]["tasks"]
        if entry.task_id in process_tasks:
            task = process_tasks[entry.task_id]
            task["status"] = entry.status
            task["status_score"] = get_status_score(entry.status)
            task["tag"] = entry.tag
            task["cpus"] = entry.cpus
            task["memory"] = entry.memory
            task["disk"] = entry.disk
            task["duration"] = entry.duration
        else:
            process_tasks[entry.task_id] = {
                "sub_task": task_subname,
                "status": entry.status,
                "status_score": get_status_score(entry.status),
                "tag": entry.tag,
                "cpus": entry.cpus,
                "memory": entry.memory,
                "disk": entry.disk,
                "duration": entry.duration,
            }

    return processes


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
    command_line = None
    error_message = None
    script_file = None
    reference = None
    nextflow_version = None
    reference = None
    nextflow_version = None

    params = metadata.get("parameters", None)
    workflow = metadata.get("workflow", None)
    if workflow is not None:
        command_line = workflow.get("commandLine", None)
        error_message = workflow.get("errorMessage", None)
        script_file =  workflow.get("script_file", None)
        manifest = workflow.get("manifest", None)
        if manifest is not None:
            nextflow_version = manifest.get("nextflowVersion", None)
        if params is not None:
            reference = params.get("reference")
    metadata_dict = {
        "command_line": command_line,
        "run_name": run_name,
        "event": event,
        "reference": reference,
        "error_message": error_message,
        "script_file": script_file,
        "nextflow_version": nextflow_version,
        "token": token_id,
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
                            "terminaded": process.get("terminated", None),
                            "process_has": process.get("hash", None),
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
        trace_data = {
            "token": token_id,
            "run_id": json_obj.get("runId", None),
            "run_name": json_obj.get("runName", None),
            "timestamp": datetime.utcnow(),
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
            "cpu_percentage": trace.get("%%cpu", None),
            "rchar": trace.get("rchar", None),
            "wchar": trace.get("wchar", None),
            "syscr": trace.get("syscr", None),
            "syscw": trace.get("syscw", None),
            "read_bytes": trace.get("read_bytes", None),
            "write_bytes": trace.get("write_bytes", None),
            "memory_percentage": trace.get("%%mem", None),
            "vmem": trace.get("vmem", None),
            "rss": trace.get("rss", None),
            "peak_vmem": trace.get("peak_vmem", None),
            "peak_rss": trace.get("trace", None),
            "vol_ctxt": trace.get("vol_ctxt", None),
            "inv_ctxt": trace.get("inv_ctxt", None),
            "event": json_obj.get("event", None),
        }

        return trace_data
    return {}
    # adjust this functions in the near future because there certainly is a more pythonic way to do this...

def persist_trace(db: Session, json_ob, token):
    """
    token = create_random_token()
            db_user = models.User(id=token, name=name)
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        """
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
    return {"metadata_saved": metadata_saved, "trace_saved": trace_saved}








def create_random_token():
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    return ''.join((random.choice(alphabet) for i in range(0, 15)))

