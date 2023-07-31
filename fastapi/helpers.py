import json
from datetime import datetime

from sqlalchemy.orm import Session
import string, random
import models, schemas, crud

INTERVAL_VALID_RAM = (0.6, 1.2)

def is_in_valid_ram_interval(process: models.RunTrace):
    if process.memory is not None and process.rss is not None:
        relative = process.rss / process.memory
        return INTERVAL_VALID_RAM[0] <= relative <= INTERVAL_VALID_RAM[1], relative
    return True, None

def group_by_run_name(result_by_task):
    run_name_dictionary = {}
    for process in result_by_task:
        if process.run_name not in run_name_dictionary:
            run_name_dictionary[process.run_name] = [process]
        else:
            run_name_dictionary[process.run_name].append(process)

    return run_name_dictionary

def analyze(grouped_processes):
    # TODO: Go from here
    invalid_ram_processes = []
    for key in grouped_processes:
        group = grouped_processes[key]
        for process in group:
            process: models.RunTrace = process
            # print(f"cpus: {process.cpus} - cpu usage: {process.cpu_percentage}")
            valid, relative_value = is_in_valid_ram_interval(process)
            if not valid:
                invalid_ram_processes.append({"process": process.process, "task_id": process.task_id, "ram_relation": relative_value})
    return invalid_ram_processes
            