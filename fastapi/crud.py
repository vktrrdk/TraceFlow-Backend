from sqlalchemy.orm import Session
import string, random
import models, schemas

def get_user(db: Session, id: string):
    return db.query(models.User).filter(models.User.id == id).first()


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


def get_run_information(db: Session, token_id: str):
    return db.query(models.RunTrace).filter(models.RunTrace.token == token_id).all()


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
    return {"removed": True, "from_user": user is not None}


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
        return {"added": True}
    return {"added": False}


def remove_token_from_user(db: Session, user, token):
    tokens = user.run_tokens
    try:
        idx = tokens.index(token.id)
    except ValueError:
        print(f"{token.id}: no such token in list of tokens for user {user.id}")
        return {"deleted": False, "from_user": True}
    new_tokens = [token for token in tokens if not tokens.index(token) == idx]
    print(new_tokens)
    user.run_tokens = new_tokens
    db.commit()
    db.refresh(user)

    return {"deleted": True, "from_user": True}

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
        )
        db.add(trace_object)
        db.commit()
        db.refresh(trace_object)
        trace_saved = True
    return {"metadata_saved": metadata_saved, "trace_saved": trace_saved}








def create_random_token():
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    return ''.join((random.choice(alphabet) for i in range(0, 15)))

