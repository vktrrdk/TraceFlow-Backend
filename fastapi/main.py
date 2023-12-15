import json
import os
from json import JSONDecodeError

import asyncio

from redis import Redis

from rq import Queue

from fastapi import Depends, FastAPI, Query, HTTPException, WebSocket, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse, ORJSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from fastapi.middleware.gzip import GZipMiddleware


import crud, models, schemas, helpers


from database import SessionLocal, engine

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')

app = FastAPI(
    title="TraceFlow",
)

r_con = Redis(host=REDIS_HOST, port=6379)
request_queue = Queue("request_queue", connection=r_con)
calculation_queue = Queue("calculation_queue", connection=r_con)



origins = [
   "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=2500)

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
            result = crud.remove_token_and_connected_information(db, token)
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
    # # # TODO: adjust checking to be part of the persistence function --> give it to the worker instead of doing it with main component
    """
    if not token_id:
        return Response(status_code=404)
    token = crud.get_token(db, token_id)
    if token:
        
        if crud.check_for_workflow_completed(db, json_ob, token_id):
            return Response(status_code=400)
        job_instance = request_queue.enqueue(crud.persist_trace_async, json_ob, token_id)
        # what to do with the job instance?
        #second_job_instance = calculation_queue()

        return Response(status_code=204)
    else:
        return Response(status_code=400)
    

@app.post("/run/analysis/{token_id}/")
async def get_run_analysis(token_id: str, threshold_params: dict = None, db: Session = Depends(get_db), response_class=ORJSONResponse):
    result_by_task = crud.get_task_states_by_token(db, token_id)
    result_by_run_name = helpers.group_by_run_name(result_by_task)
    result_analysis = helpers.analyze(db, result_by_run_name, threshold_params)
    return ORJSONResponse(result_analysis, status_code=200)

@app.post("/test/redis")
async def test_redis(json_b: dict):
    job_instance = request_queue.enqueue(print, json_b)
    return {
        "id": job_instance.id
    }


"""
    what needs to be adjusted:
    From the database, only get the relevant traces -> for each job, only the latest one
    --> reduces data up to 3 times
    --> relies on good persistence
    
    
"""




@app.get("/run/table/{token_id}")
async def get_table_data(runName, token_id: str, db: Session = Depends(get_db), response_class=ORJSONResponse, page=1, rows=10, sortField="task_id", sortOrder=1):
    token = await check_token_request(token_id, db)
    if not isinstance(token, models.RunToken):
        return token
    
    run_name = json.loads(runName)
    page = json.loads(page)
    rows = json.loads(rows)
    sort_field = json.loads(sortField)
    sort_order = json.loads(sortOrder)

    paginated_table = crud.get_paginated_table(db, token_id, run_name, page, rows, sort_field, sort_order)

    return ORJSONResponse(content=jsonable_encoder(paginated_table), status_code=200)

@app.get("/run/ram_plot/{token_id}")
async def get_ram_plot_data(token_id: str, processFilter, tagFilter, runName, db: Session = Depends(get_db), response_class=ORJSONResponse):
    token = await check_token_request(token_id, db)
    if not isinstance(token, models.RunToken):
        return token
    
    process_filter = json.loads(processFilter)
    tag_filter = json.loads(tagFilter)
    run_name = json.loads(runName)

    filtered_ram_plot_results = crud.get_filtered_ram_plot_results(db, token_id, run_name, process_filter, tag_filter)
    
    return ORJSONResponse(content=jsonable_encoder(filtered_ram_plot_results), status_code=200)
    
@app.get("/run/cpu_allocation_plot/{token_id}")
async def get_cpu_allocation_plot_data(token_id: str, processFilter, tagFilter, runName,  db: Session = Depends(get_db), response_class=ORJSONResponse):
    token = await check_token_request(token_id, db)
    if not isinstance(token, models.RunToken):
        return token

    process_filter = json.loads(processFilter)
    tag_filter = json.loads(tagFilter)
    run_name = json.loads(runName)

    filtered_cpu_plot_results = crud.get_filtered_cpu_allocation_plot_results(db, token_id, run_name, process_filter, tag_filter)

    return ORJSONResponse(content=jsonable_encoder(filtered_cpu_plot_results), status_code=200)


### TODO: use this! implement function in crud and use response in ui
@app.get("/run/plots/{token_id}")
async def get_plot_data(token_id: str, processFilter, tagFilter, runName,  db: Session = Depends(get_db), response_class=ORJSONResponse):
    token = await check_token_request(token_id, db)
    if not isinstance(token, models.RunToken):
        return token

    process_filter = json.loads(processFilter)
    tag_filter = json.loads(tagFilter)
    run_name = json.loads(runName)

    full_plot_results = crud.get_plot_results(db, token_id, run_name, process_filter, tag_filter)
    
    return ORJSONResponse(content=jsonable_encoder(full_plot_results), status_code=200)

async def check_token_request(token_id, db: Session):
    if not token_id:
        return ORJSONResponse({"error": "No token provided"}, status_code=400)
    token = crud.get_token(db, token_id)
    if not token:
        return ORJSONResponse({"error": "No such token"}, status_code=404)
    return token


@app.get("/run/info/{token_id}/")
async def get_run_information(token_id: str, db: Session = Depends(get_db), response_class=ORJSONResponse):
    """
    Returns all information persisted for a certain token.
    :param token_id: The id of the run-token
    :param threshold_params: the threshold parameters
    :param db:
    :return: information on run with token
    """
    token = await check_token_request(token_id, db)
    if not isinstance(token, models.RunToken):
        return token
    
    meta = sorted(crud.get_meta_by_token(db, token_id), key=lambda obj: obj.timestamp)
    result_meta = meta if len(meta) > 0 else {}
    result_by_task = crud.get_task_states_by_token(db, token_id)
    result_by_run_name = helpers.group_by_run_name(result_by_task)
    result_stat = crud.get_stats_by_token(db, token_id)
    result_meta_processes = crud.get_process_by_token(db, token_id)
    result = {
        "result_meta": result_meta,
        "result_by_run_name": result_by_run_name,
        "result_stat": result_stat,
        "result_meta_processes": result_meta_processes,
    }
    return JSONResponse(content=jsonable_encoder(result), status_code=200)
"""
"""

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

@app.get("/test/trace/running/{token_id}/")
async def adjust_trace_to_running(token_id: str, db: Session = Depends(get_db)):
    return crud.set_all_tasks_running(db, token_id)

@app.post("/test/run/{token_id}/")
async def read_nextflow_run(token_id: str, push: dict):
    z = []
    try:
        with open(f"trace-{token_id}.json", "r+") as current:        
            z = json.load(current)
        current.close()
    except (JSONDecodeError,  FileNotFoundError):
        z = []
    with open(f"trace-{token_id}.json", "w+") as json_file:
        z.append(push)
        json.dump(z, json_file)
        json_file.close()

@app.post("/test/tower/{token_id}/{whatever}")
async def read_nextflow_tower_run(token_id: str, push: dict):
    z = []
    try:
        with open(f"trace-tower-{token_id}.json", "r+") as current:
            z = json.load(current)
        current.close()
    except(JSONDecodeError, FileNotFoundError):
        z = []
    with open(f"trace-tower-{token_id}.json", "w+") as json_file:
        z.append(push)
        json.dump(z, json_file)
        json_file.close()
