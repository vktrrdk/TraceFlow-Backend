from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base

class User(Base):
    __tablename__ = "user"

    token = Column(String, primary_key=True)
    name = Column(String)
    run_tokens = relationship("RunToken", back_populates="owner")

    # how to solve the problems with the relations?

class RunToken(Base):
    __tablename__ = "runtoken"
    id = Column(String, primary_key=True)
    owner = relationship("User", back_populates="run_tokens")

