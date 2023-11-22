from pydantic import ConfigDict, BaseModel

class RunToken(BaseModel):
    id: str


class User(BaseModel):
    id: str
    name: str
    run_tokens: list[RunToken] = []
    model_config = ConfigDict(from_attributes=True)
"""
 TODO SCHEMAS: adjust so all classes are used correcty - this might speed up the parsing process

 """