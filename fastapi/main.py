from fastapi import FastAPI, Query
import random, string
from pydantic import BaseModel
from typing import Annotated

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/create/token/user/{user_id}")
async def create_token_for_user(user_id: str):
    if not user_id:
        return {"create": "Not able to create"}
    else:

        return {"token": create_random_token()}

@app.get("/create/token/")
async def create_token():
    return {"token": create_random_token()}

@app.get("/user/runs/{user_id}")
async def get_user_runs(user_id: str):
    if user_id:
        runs = get_runs_for_user(user_id)
        return {"runs": runs}
    else:
        return {"runs": []}
    """
    check the annotation stuff - why is python 3.9 runnning and not 3.11?
    https://fastapi.tiangolo.com/tutorial/query-params-str-validations/
    """

@app.get("user/create/{name}")
async def create_user(name: str):
    #user = User()


def get_runs_for_user(user_id):
    for user in fake_items_db:
        if user["user_id"] == user_id:
            return user["run_tokens"]
    return []


def create_random_token():
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    return ''.join((random.choice(alphabet) for i in range(0, 15)))



fake_items_db = [
    {"user_id": "OucOzJNhOXMJBKH", "name": "Viktor", "run_tokens":
        [
            "kqLWDTvDBxWyvXK",
            "WIfClnobxtgNHIJ",
            "QfDHMmzoJaeJjpu",
        ]
    },
{"user_id": "vTKWofVaGnHbzud", "name": "Peter", "run_tokens":
        [
            "MvWjWbynemjdZzy",
        ]
    },

]

class User(BaseModel):
    user_id: str
    name: str
    run_tokens: [str]
