from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base

class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True)
    name = Column(String)
    run_tokens = Column('run_tokens', String, ForeignKey('runtoken.id'))

    # how to solve the problems with the relations?

class RunToken(Base):
    __tablename__ = "runtoken"
    id = Column(String, primary_key=True)

