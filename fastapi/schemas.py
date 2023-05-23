from pydantic import BaseModel

class RunToken(BaseModel):
    id: str


class User(BaseModel):
    id: str
    name: str
    run_tokens: list[RunToken] = []

    class Config:
        orm_mode = True
