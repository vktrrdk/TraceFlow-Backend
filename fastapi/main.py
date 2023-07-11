import json
from json import JSONDecodeError

from fastapi import Depends, FastAPI, Query, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

import crud, models, schemas
from database import SessionLocal, engine


app = FastAPI(
    title="TraceFlow",
    # root_path="/timelessKnuth_100/proxy/8000/",
)

#"http://localhost",
#    "http://localhost:5173/",
#    "https://localhost",
#    "https://localhost:5173/"

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)

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

@app.get("/user/{user_id}/token/create")
async def create_token_for_user(user_id: str, db: Session = Depends(get_db)):
    """
    Creating a token for a user provided by his/her id.

    :param user_id: The user id of the user for whom the token is to be created
    :param db: the database to send the request to
    :return: json-response with user-token and newly generated token or error message
    """
    if not user_id:
        return JSONResponse(content={"error": "No user id provided"}, status_code=400)
    else:
        user = crud.get_user(db, user_id)
        if not user:
            return JSONResponse(content={"error": "User with given id not found"}, status_code=404)
        token = crud.create_token(db)
        result = crud.add_token_to_user(db, user.id, token)
        if result["added_token"] == token.id:
            return JSONResponse(content={"user": user_id, "token": token.id}, status_code=201)
        else:
            return JSONResponse(content={"error": "An error occurred while adding the token"}, status_code=500)


@app.post("/user/token/add")
async def add_token_to_user(add_token_item: models.UserTokenItem, db: Session = Depends(get_db)):
    """
    Enables adding a token to a user, given both the user id and the token id is valid.
    :param add_token_item: The request body with user id and token id provided
    :param db: the database to send the request to
    :return: json-response with user-token and newly generated token or error message
    """
    token = add_token_item.token
    user_token = add_token_item.user_token
    if not user_token:
        return JSONResponse(content={"error": "No user id provided"}, status_code=400)
    else:
        user = crud.get_user(db, user_token)
        if user:
            token = crud.get_token(db, token_id=token)
            if token is not None:
                content = crud.add_token_to_user(db=db, token=token, user_id=user_token)
                if content["added_token"] == token.id:
                    return JSONResponse(content=content, status_code=200)
                else: return JSONResponse(
                    content={"error": "An error occurred while adding the token to the user"},
                    status_code=500,
                )
            else:
                return JSONResponse(content={"error": "Invalid token provided"}, status_code=400)
        else:
            return JSONResponse(content={"error": "No user for id provided"}, status_code=404)


@app.delete("/user/{user_id}}/token/{token_id}")
async def remove_token_from_user(user_id: str, token_id: str, db: Session = Depends(get_db)):
    """
    Removes a given token from a given user.
    :param user_id: The id of the user
    :param token_id: The id of the token
    :param db: the database to send the request to
    :return: json-response with deletion result or error message
    """
    if not user_id:
        return JSONResponse(content={"error": "No user id provided"}, status_code=400)
    elif not token_id:
        return JSONResponse(content={"error": "No token id provided"}, status_code=400)
    else:
        user = crud.get_user(db, user_id)
        if not user:
            return JSONResponse(content={"error": "No user for id provided"}, status_code=404)
        else:
            token = crud.get_token(db, token_id)
            if not token:
                return JSONResponse(content={"error": "No token for id provided"}, status_code=404)
            else:
                result = crud.remove_token_from_user(db, user, token)
                if result["removed_token"] == token_id:
                    return JSONResponse(content=result, status_code=200)
                else:
                    return JSONResponse(
                        content={"error": "An error occurred while removing token from user"},
                        status_code=500,
                    )


@app.get("/token/validate/{token_id}")
async def validate_token(token_id: str, db: Session = Depends(get_db)):
    """
    Returns whether a given token is valid (exists in the database) or not
    :param token_id: The id of the token
    :param db: the database to send the request to
    :return: json-response with token-validity value or error message
    """
    if not token_id:
        return JSONResponse(content={"error": "No token id provided"}, status_code=400)
    else:
        token = crud.get_token(db, token_id)
        if token is not None:
            return JSONResponse(content={"valid": True}, status_code=200)
        else:
            return JSONResponse(content={"valid": False}, status_code=200)


@app.delete("/token/remove/{token_id}")
async def remove_token(token_id: str, db: Session = Depends(get_db)):
    """
    Removing a token from the database. In case the token is associated with a user - it also gets removed from the
    users token list

    :param token_id: the id of the token
    :param db: the database to send the request to
    :return: json-response with removal result or error message
    """
    if not token_id:
        return JSONResponse(content={"error": "No token id provided"}, status_code=400)
    else:
        token = crud.get_token(db, token_id)
        if token:
            result = crud.remove_token(db, token)
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content={"error": "No such token"}, status_code=404)

@app.delete("/user/{user_id}/remove/token/all/")
async def remove_user_tokens(user_id: str, db: Session = Depends(get_db)):
    """
    Removes all tokens for a given user.
    :param user_id: the id of the user to remove all tokens from
    :param db: the database to send the request to
    :return: json-response with all removed tokens or error message
    """
    if not user_id:
        return JSONResponse(content={"error": "No user id provided"}, status_code=400)
    user = crud.get_user(db, user_id)
    if not user:
        return JSONResponse(content={"error": "No such user"}, status_code=404)
    result = crud.remove_all_token_from_user(user_id, db)
    return JSONResponse(content=result, status_code=200)


@app.get("/token/create/")
async def create_token(db: Session = Depends(get_db)):
    """
    Creates a token, which is not linked to a user in this step.
    :param db: the database to send the request to
    :return: returns the token object in json
    """
    created_token = crud.create_token(db)
    return JSONResponse(content=jsonable_encoder(created_token), status_code=201)


@app.get("/user/{user_id}")
async def get_user_information(user_id: str, db: Session = Depends(get_db)):
    """
    Returns user information for user given by id
    :param user_id: the user id
    :param db: the database to send the request to
    :return: returns the user information or an error message
    """
    if user_id:
        user = crud.get_user(db, user_id)
        if not user:
            return JSONResponse(content={"error": "No such user"}, status_code=404)
        else:
            return JSONResponse(content=jsonable_encoder(user), status_code=200)
    else:
        return JSONResponse(content={"error": "No user id provided"}, status_code=400)


@app.post("/user/create")
async def create_user(add_user_item: models.AddUserItem, db: Session = Depends(get_db)):
    """
    Creates a new user with a name provided
    :param add_user_item: The request body consisting of the name value
    :param db: the database to send the request to
    :return: returns the newly created user or an error message
    """
    name = add_user_item.name
    if not name:
        return JSONResponse(content={"error": "No name provided"}, status_code=400)
    result = crud.create_user(db, name=name)
    return JSONResponse(content=jsonable_encoder(result), status_code=201)


@app.delete("/run/{token_id}")
async def remove_run_information_for_token(token_id: str, db: Session = Depends(get_db)):
    pass
    """
    TODO: implement
    """

@app.post("/run/{token_id}")
async def persist_run_for_token(token_id: str, json_ob: dict, db: Session = Depends(get_db)):
    """
    Endpoint for persistence of run information. Users do use this endpoint when executing
    their workflows.
    :param token_id: The token id to connect the information with
    :param json_ob: The request json object including e.g. the trace
    :param db: The database to persist the information in
    :return: Response state
    """
    if not token_id:
        return Response(status_code=404)
    token = crud.get_token(db, token_id)
    if token:
        crud.persist_trace(db, json_ob, token)
        return Response(status_code=204)
    else:
        return Response(status_code=400)


@app.get("/run/{token_id}")
async def get_run_information(token_id: str, db: Session = Depends(get_db)):
    """
    Returns all information persisted for a certain token.
    :param token_id: The id of the run-token
    :param db:
    :return: information on run with token
    """
    if not token_id:
        return JSONResponse(content={"error": "No token provided"}, status_code=200)
    token = crud.get_token(db, token_id)
    if not token:
        return JSONResponse(content={"error": "No such token"}, status_code=404)
    result_trace = crud.get_run_trace(db, token)
    result_processes = crud.get_run_state_by_process(result_trace)
    result_trace = sorted(result_trace, key=lambda obj: obj.timestamp)
    result = {
        "result_list": result_trace,
        "result_processes": result_processes,
    }
    return JSONResponse(content=jsonable_encoder(result), status_code=200)

"""
@app.websocket("/run/{token}")
async def websocket_test(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Test")
"""
        

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

@app.get("/test/stats/all/")
async def get_full_stats(db: Session = Depends(get_db)):
    return crud.get_full_stats(db)

@app.get("/test/stats/{token_id}/")
async def get_stats_by_token(token_id: str, db: Session = Depends(get_db)):
    return crud.get_stats_by_token(db, token_id)

@app.get("/test/meta/{token_id}/")
async def get_meta_by_token(token_id: str, db: Session = Depends(get_db)):
    return crud.get_meta_by_token(db, token_id)

@app.get("/test/process/all/")
async def get_processes_full(db: Session = Depends(get_db)):
    return crud.get_full_processes(db)

@app.get("/test/process/{token_id}/")
async def get_process_by_token(token_id: str, db: Session = Depends(get_db)):
    return crud.get_process_by_token(db, token_id)

@app.get("/test/trace/{token_id}/")
async def get_trace_by_token(token_id: str, db: Session = Depends(get_db)):
    return crud.get_run_trace_by_token(db, token_id)

@app.post("/test/run/{token_id}/")
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


