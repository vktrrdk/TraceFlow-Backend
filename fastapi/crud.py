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

def create_token(db: Session):
    token = create_random_token()
    db_token = models.RunToken(id=token)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token

def create_token_for_user(db: Session, user_id: int):
    token = create_random_token()
    db_token = models.RunToken(id=token, owner_id=user_id)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token

def create_random_token():
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    return ''.join((random.choice(alphabet) for i in range(0, 15)))


"""
class RunToken(Base):
    __tablename__ = "runtoken"
    id = Column(String, primary_key=True)
    owner = relationship("User", back_populates="run_tokens")
"""