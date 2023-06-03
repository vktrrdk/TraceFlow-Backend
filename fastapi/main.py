import json
from json import JSONDecodeError

from fastapi import Depends, FastAPI, Query, HTTPException
from sqlalchemy.orm import Session

import crud, models, schemas
from database import SessionLocal, engine


app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def root():
    """
    Sanity check function
    :return:
    """
    return {"message": "Hello World"}

@app.get("/create/token/user/{user_id}")
async def create_token_for_user(user_id: str, db: Session = Depends(get_db)):
    """
    Creating a token for a user provided by his/her id.

    :param user_id: The user id of the user for whom the token is to be created
    :param db: the database to connect to
    :return: json with user-token and newly generated token
    """
    if not user_id:
        return {"create": "Not able to create"}
    else:
        user = crud.get_user(db, user_id)
        if not user:
            return {"create": "Not able to create"}
        token = crud.create_token(db)
        user = crud.add_token_to_user(db, user.id, token)
        return {"user": user.id, "token": token.id}

@app.get("/remove/token/{token_id}")
async def remove_token(token_id: str, db: Session = Depends(get_db)):
    """
    Removing a token from the database

    :param token_id: the id of the token
    :param db: --
    :return: json with result
    """
    if not token_id:
        return {"remove": "Not able to remove"}
    else:
        token = crud.get_token(db, token_id)
        if token:
            return crud.remove_token(db, token)
        else:
            return {"remove": "No such token"}


@app.get("/remove/token/user/{user_id}")
async def remove_user_tokens(user_id: str, db: Session = Depends(get_db)):
    """
    :param user_id: the id of the user to remove all tokens from
    :param db:
    :return: returns the result of the removal
    """
    return {"remove": crud.remove_all_token_from_user(user_id, db)}


@app.get("/create/token/")
async def create_token(db: Session = Depends(get_db)):
    """
    Creates a token, but it is not linked to a specific user
    :param db:
    :return: returns the token object in json
    """
    created_token = crud.create_token(db)
    return {"token": created_token}

@app.get("/user/token/{user_id}")
async def get_user_runs(user_id: str):
    if user_id:
        runs = []
        return {"runs": runs}
    else:
        return {"runs": []}

@app.get("/user/create/{name}")
async def create_user(name: str, db: Session = Depends(get_db)):
    return crud.create_user(db, name=name)


@app.post("/test/run/{token_id}")
async def read_nextflow_run(token_id: str, push: dict):
    with open(f"trace-{token_id}.json", "r") as current:
        try:
            z = json.load(current)
        except JSONDecodeError:
            print("NO NOT WORKING")
            z = []
        current.close()
    with open(f"trace-{token_id}.json", "w+") as json_file:
        z.append(push)
        json.dump(z, json_file)
        json_file.close()



@app.post("/run/{token_id}")
async def persist_run_for_token(token_id: str, json_ob: dict, db: Session = Depends(get_db)):
    token = crud.get_token(db, token_id)
    if token:
        crud.persist_trace(db, json_ob, token)
    else:
        print("no such token")



@app.get("/test/token/")
async def get_all_tokens(db: Session = Depends(get_db)):
    """
    Shows all tokens - this test function is about to be removed
    :param db:
    :return: List of all tokens in db
    """
    return crud.get_all_token(db)

@app.get("/test/users/")
async def get_all_users(db: Session = Depends(get_db)):
    """
    Shows all users - this test function os about to be removed
    :param db:
    :return:
    """
    return crud.get_all_users(db)

@app.get("/test/trace/all/")
async def get_full_trace(db: Session = Depends(get_db)):
    return crud.get_full_trace(db)

@app.get("/test/meta/all/")
async def get_full_meta(db: Session = Depends(get_db)):
    return crud.get_full_meta(db)

