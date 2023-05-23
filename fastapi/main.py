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
    return {"message": "Hello World"}

@app.get("/create/token/user/{user_id}")
async def create_token_for_user(user_id: str):
    if not user_id:
        return {"create": "Not able to create"}
    else:

        return {"token": ""}

@app.get("/create/token/")
async def create_token():
    return {"token": ""}

@app.get("/user/runs/{user_id}")
async def get_user_runs(user_id: str):
    if user_id:
        runs = get_runs_for_user(user_id)
        return {"runs": runs}
    else:
        return {"runs": []}

@app.get("/user/create/{name}")
async def create_user(name: str, db: Session = Depends(get_db)):
    return crud.create_user(db, name=name)


def get_runs_for_user(user_id):
    for user in fake_items_db:
        if user["user_id"] == user_id:
            return user["run_tokens"]
    return []



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
