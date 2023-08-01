import json
from datetime import datetime

from sqlalchemy.orm import Session
import string, random
import models, schemas, crud

def group_by_run_name(result_by_task):
    run_name_dictionary = {}
    for process in result_by_task:
        if process.run_name not in run_name_dictionary:
            run_name_dictionary[process.run_name] = [process]
        else:
            run_name_dictionary[process.run_name].append(process)

    return run_name_dictionary

"""
Analysis part
"""
INTERVAL_VALID_RAM_RELATION = (0.6, 1.2)
INTERVAL_VALID_CPU_ALLOCATION_PERCENTAGE = (60, 140)
THRESHOLD_DURATION_RELATION = 5
DURATION_TO_CONSIDER_AVERAGES_THRESHOLD = 120000 # two minutes
DURATION_REQUESTED_RELATION_THRESHOLD = 1.3


def check_valid_ram_interval(process: models.RunTrace):
    if process.memory is not None and process.rss is not None:
        relative = process.rss / process.memory
        return INTERVAL_VALID_RAM_RELATION[0] <= relative <= INTERVAL_VALID_RAM_RELATION[1], {"ram_relative": relative}
    return True, None

def check_valid_cpu_interval(process: models.RunTrace):
    if process.cpus:
        if process.cpu_percentage:
            allocation = process.cpu_percentage / process.cpus
            return INTERVAL_VALID_CPU_ALLOCATION_PERCENTAGE[0] <= allocation <= INTERVAL_VALID_CPU_ALLOCATION_PERCENTAGE[1], {"cpu_allocation": allocation}
    return True, None


def analyze(grouped_processes):
    process_analysis = []
    for key in grouped_processes:
        group = grouped_processes[key]
        execution_duration = []
        for process in group:
            execution_duration.append({"process": process.process, "task_id": process.task_id, "duration": process.duration})
        for process in group:
            process: models.RunTrace = process
            possible_return = { "process": process.process, "task_id": process.task_id, "run_name": process.run_name, "problems": [] }
            valid, problems = get_process_invalidities(process, execution_duration)
            if not valid:
                possible_return["problems"] = problems
                process_analysis.append(possible_return)
    return process_analysis

def get_process_invalidities(process: models.RunTrace, duration_mapping):
    invalidities_list = []
    to_return = False
    ram_valid, problems = check_valid_ram_interval(process)
    if not ram_valid:
        invalidities_list.append(problems)
        to_return = True

    cpu_valid, problems = check_valid_cpu_interval(process)
    if not cpu_valid:
        invalidities_list.append(problems)
        to_return = True
    
    duration_values_without_process = [dur_obj["duration"] for dur_obj in duration_mapping if dur_obj["process"] != process.process]
    duration_values_without_this_explicit_task = [dur_obj["duration"] for dur_obj in duration_mapping if dur_obj["process"] != process.process and dur_obj["task_id"] != process.task_id]
    duration_values_within_process = [dur_obj["duration"] for dur_obj in duration_mapping if dur_obj["process"] == process.process and dur_obj["task_id"] != process.task_id]
    
    if process.duration:
        if process.duration > DURATION_TO_CONSIDER_AVERAGES_THRESHOLD:
            len_duration_wo_p = len(duration_values_without_process)
            if len_duration_wo_p > 0:
                average_without_process = sum(duration_values_within_process) / len_duration_wo_p
                if average_without_process > THRESHOLD_DURATION_RELATION:
                    invalidities_list.append({"duration_ratio_compared_to_other_processes": average_without_process})
                    to_return = True

            len_duration_wo_et = len(duration_values_without_this_explicit_task)
            if len_duration_wo_et > 0:
                average_without_task = sum(duration_values_without_this_explicit_task) / len_duration_wo_et 
                if average_without_task > THRESHOLD_DURATION_RELATION:
                    invalidities_list.append({"duration_ratio_compared_to_all": average_without_task})
                    to_return = True

            len_duration_within = len(duration_values_within_process)
            if len_duration_within:
                average_within = sum(duration_values_within_process) / len_duration_within
                if average_within > THRESHOLD_DURATION_RELATION:
                    invalidities_list.append({"duration_ratio_compared_to_same": average_within})
                    to_return = True
        if process.time:
            duration_ratio = process.duration / process.time
            if duration_ratio > DURATION_REQUESTED_RELATION_THRESHOLD:
                invalidities_list.append({"duration_ratio_to_requested", duration_ratio})
                to_return = True
    return (not to_return, invalidities_list)
    
"""
End of analysis part
"""