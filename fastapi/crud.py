from sqlalchemy.orm import Session
import string, random
import models, schemas

def get_user(db: Session, id: string):
    return db.query(models.User).filter(models.User.id == id).first()

def create_user(db: Session, name: str):
    token = create_random_token()
    db_user = models.User(id=token, name=name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_all_users(db: Session):
    return db.query(models.User).all()

def get_all_token(db: Session):
    return db.query(models.RunToken).all()

def create_token(db: Session):
    token = create_random_token()
    db_token = models.RunToken(id=token)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token

def get_token(db: Session, token_id: str):
    token = db.query(models.RunToken).get(token_id)
    return token

def remove_token(db: Session, token):
    user = db.query(models.User).join(models.RunToken).filter(models.RunToken.id == token.id).first()
    # session.query(WhateverClass).join(ContainerClass).filter(ContainerClass.id == 5).all()
    remove_token_from_user(db, user) # need to be adjusted to multiple token
    db.delete(token)
    db.commit()
    return {"deleted": True} # could fail?

# scenarios = Scenario.query.join(Hint).filter(Hint.release_time < time.time())


def add_token_to_user(db: Session, user_id, token):
    user = get_user(db, user_id)
    user.run_tokens = token.id
    db.commit()
    db.refresh(user)
    return user

def remove_token_from_user(db: Session, user):
    user.run_tokens = ""
    db.commit()
    db.refresh(user)
    return user


def create_random_token():
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    return ''.join((random.choice(alphabet) for i in range(0, 15)))

