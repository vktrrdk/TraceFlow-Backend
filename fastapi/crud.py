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



# {'BOWTIE':
#   {'sub_processes':
#       [
#           {'name': 'Index', 'task_id': 2, 'status': 'COMPLETED', 'status_score': 2},
#           {'name': 'Align', 'task_id': 5, 'status': 'COMPLETED', 'status_score': 2},
#           {'name': 'Align', 'task_id': 4, 'status': 'COMPLETED', 'status_score': 2}
#       ]
#   },
# 'fastqc':
#   {'sub_processes':
#       [
#           {'name': None, 'task_id': 3, 'status': 'COMPLETED', 'status_score': 2},
#           {'name': None, 'task_id': 1, 'status': 'COMPLETED', 'status_score': 2}
#       ]
#   },
# 'multiqc':
#   {'sub_processes':
#       [
#           {'name': None, 'task_id': 6, 'status': 'COMPLETED', 'status_score': 2}
#       ]
#   }
# }


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

    metadata = json_ob.get("metadata")
    if metadata is not None:
        run_name = json_ob.get("run_name")
        params = metadata.get("parameters")
        reference = None
        if params is not None:
            reference = params.get("reference")
        meta_object = models.RunMetadata(
            token=token.id,
            run_name=run_name,
            reference=reference
        )
        db.add(meta_object)
        db.commit()
        db.refresh(meta_object)
        metadata_saved = True
    trace = json_ob.get("trace")
    if trace is not None:
        task_id = trace.get("task_id")
        status = trace.get("status")
        run_name = json_ob.get("run_name")
        process = trace.get("process")
        name = trace.get("name")
        tag = trace.get("tag")
        cpus = trace.get("cpus")
        memory = trace.get("memory")
        disk = trace.get("disk")
        duration = trace.get("duration")
        trace_object = models.RunTrace(
            token=token.id,
            task_id=task_id,
            status=status,
            run_name=run_name,
            process=process,
            tag=tag,
            cpus=cpus,
            name=name,
            memory=memory,
            disk=disk,
            duration=duration,
            timestamp=datetime.utcnow(),
        )
        db.add(trace_object)
        db.commit()
        db.refresh(trace_object)
        trace_saved = True
    return {"metadata_saved": metadata_saved, "trace_saved": trace_saved}








def create_random_token():
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    return ''.join((random.choice(alphabet) for i in range(0, 15)))

