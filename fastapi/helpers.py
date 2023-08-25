import json
from datetime import datetime
import sys
import math

from sqlalchemy.orm import Session
import string, random
import models, schemas, crud


"""
Analysis part
"""
interval_valid_ram_relation = (0.6, 1.2)  # from 60 to 120%
interval_valid_cpu_allocation_percentage = (60, 140)  # from 60 to 140%
interval_valid_ram_allocation = (60, 100)
threshold_duration_relation = 5  # a process can run 5 times longer than the average over the others
duration_to_consider_averages_threshold = 120000  # two minutes threshold to consider only bigger processes
duration_requested_relation_threshold = 1.3  # process can run 30% longer than requested
tag_duration_ratio_threshold = 1.4  # processes with this tag are allowed
tag_duration_ratio_full_threshold = 0.3  # processes with a certain tag are allowed to take up to 30% of full duration
tag_cpu_allocation_ratio_threshold = 1.5  # 150% in relation to other processes
tag_cpu_percentage_ratio_threshold = 1.5  # same
tag_memory_rss_average_ratio_threshold = 1.4  # 140% memory in relation to others
top_percent_ratio = 0.1  # 10 percent. could be set as env variable !
limit_processes_per_domain_by_number = 10  # if 10% s more than this number, limit it

def get_relevant_information_per_task(task):
    task_dict = task.__dict__
    relevant_keys = ['task_id', 'process', 'run_name', 'cpus', 'tag', 'memory', 'duration', 'vmem', 'realtime', 'cpu_percentage', 'rss', 'status']
    task_to_return = {rel_key: task_dict[rel_key] for rel_key in relevant_keys}
    return task_to_return

def calculate_raw_scores_per_task(reduced_task, w_cpu, w_ram):
    if reduced_task['status'] == "FAILED":
        reduced_task['raw_cpu_penalty'] = None
        reduced_task['raw_memory_penalty'] = None
        reduced_task['memory_allocation'] = None
        reduced_task['cpu_allocation'] = None
        reduced_task['raw_memory_score'] = None
        reduced_task['raw_cpu_score'] = None
        
    else:
        if reduced_task['cpus'] and reduced_task['cpus'] > 0 and reduced_task['cpu_percentage']:
            cpu_alloc = reduced_task['cpu_percentage'] / reduced_task['cpus']
            reduced_task['cpu_allocation'] = cpu_alloc
            reduced_task['raw_cpu_penalty'] = abs(1 - (cpu_alloc / 100))
            if cpu_alloc > 100:
                delta = reduced_task['raw_cpu_penalty']
                reduced_task['raw_cpu_score'] = math.exp(-4 * delta)
            else:
                reduced_task['raw_cpu_score'] = cpu_alloc / 100
            
        else:
            reduced_task['cpu_allocation'] = None
            reduced_task['raw_cpu_penalty'] = None
            reduced_task['raw_cpu_score'] = None
        if reduced_task['memory'] and reduced_task['memory'] > 0 and reduced_task['rss']:
            memory_alloc = reduced_task['rss'] / reduced_task['memory']
            reduced_task['memory_allocation'] = memory_alloc * 100
            reduced_task['raw_memory_penalty'] = abs(1 - memory_alloc)
            if memory_alloc > 1:
                delta = reduced_task['raw_memory_penalty']
                reduced_task['raw_memory_score'] = math.exp(-4 * delta)
            else:
                reduced_task['raw_memory_score'] = memory_alloc
        else:
            reduced_task['memory_allocation'] = None
            reduced_task['raw_memory_penalty'] = None
            reduced_task['raw_memory_score'] = None
        
        reduced_task['weight_cpu'] = w_cpu
        reduced_task['weight_memory'] = w_ram
    return reduced_task

def calculate_weighted_metric_scores_for_run(task):
    if task['status'] != "FAILED":
        # and task['raw_cpu_score'] and task['raw_memory_score']:
        pure_nom_value = 0
        pure_denom_value = 0
        if task['raw_cpu_score']: 
            pure_denom_value = pure_denom_value + task['weight_cpu']
            weighted_cpu_score = task['weight_cpu'] * task['raw_cpu_score'] 
            pure_nom_value = pure_nom_value + weighted_cpu_score
        else:
            weighted_cpu_score = None
        if task['raw_memory_score']:
             pure_denom_value = pure_denom_value + task['weight_memory']
             weighted_memory_score = task['weight_memory'] * task['raw_memory_score']
             pure_nom_value = pure_nom_value + weighted_memory_score
        else:
            weighted_memory_score = None
        task['weighted_cpu_score'] = weighted_cpu_score
        task['weighted_memory_score'] = weighted_memory_score
        if pure_denom_value == 0:
            task['pure_score'] = None
        else:
            task['pure_score'] = pure_nom_value / pure_denom_value
    else:
        task['weighted_cpu_score'] = None
        task['weighted_memory_score'] = None
        task['pure_score'] = None
    return task

def calculate_weighted_scores(tasks, process_name=None, limits={}):
    nominator_sum = 0
    denominator_sum = 0
    for task in tasks:
        if task['weighted_cpu_score'] and task['cpu_percentage'] and task['weighted_memory_score'] and task['rss'] and task['realtime']:
            
            numbers_cpu = (task['cpu_percentage'] / 100)
            cpu_with_absoulte = task['weighted_cpu_score'] * numbers_cpu
            gibs = task['rss'] / math.pow(1024,3)
            mem_adjusted = gibs / 8
            memory_with_absolute = task['weighted_memory_score'] * mem_adjusted
            cpu_plus_memory = cpu_with_absoulte + memory_with_absolute
            to_add_nom = cpu_plus_memory * task['realtime']
            cpu_weight_with_absolute = task['weight_cpu'] * numbers_cpu
            memory_weight_with_absolute = task['weight_memory'] * mem_adjusted
            to_add_denom = (cpu_weight_with_absolute +  memory_weight_with_absolute) * task['realtime']
            nominator_sum = nominator_sum + to_add_nom
            denominator_sum = denominator_sum + to_add_denom
    if denominator_sum == 0:
        score = None
    else:
        score = nominator_sum / denominator_sum

    if process_name:
        return {
            "process": process_name, "score": score, 
            "problems": get_process_invalidities(tasks, limits["max_cpu_requested"], limits["max_memory"], limits["max_memory_requested"], limits['cpu_deviation'], limits['memory_deviation'])
        }
    else:
        return score

def calculate_scores(grouped_processes, threshold_numbers):
    if threshold_numbers['valid_cpu_allocation_deviation']:
        VALID_CPU_DEVIATION = float(threshold_numbers['valid_cpu_allocation_deviation'] / 100)
    else: 
        VALID_CPU_DEVIATION = 0.25
    if threshold_numbers['valid_memory_allocation_deviation']:
        VALID_MEMORY_DEVIATION = float(threshold_numbers['valid_memory_allocation_deviation'] / 100)
    else:
        VALID_MEMORY_DEVIATION = 0.25
    if threshold_numbers['cpu_weight'] and threshold_numbers['ram_weight']:
        RAM_WEIGHT = float(threshold_numbers['ram_weight'])
        CPU_WEIGHT = float(threshold_numbers['cpu_weight'])
    else:
        RAM_WEIGHT = 0.5
        CPU_WEIGHT = 0.5

    process_scores_per_run = {}
    full_score_per_run = {}
    raw_task_information_per_run = {}
    weighted_task_information_per_run = {}

    # threshold numbers to be used later on
    for run_name in grouped_processes:
        max_cpu_requested = 0
        available_memory = 0
        available_rss = 0
        max_memory_requested = 0
        run_tasks = grouped_processes[run_name]
        raw_task_information_per_run[run_name] = []
        for task in run_tasks:
            reduced_task = get_relevant_information_per_task(task)
            task_with_scores = calculate_raw_scores_per_task(reduced_task, CPU_WEIGHT, RAM_WEIGHT)

            raw_task_information_per_run[run_name].append(task_with_scores)
            if task.cpus and task.cpus > max_cpu_requested:
                max_cpu_requested = task.cpus
            if task.memory and task.memory > max_memory_requested:
                max_memory_requested = task.memory
            if task.rss and task.rss > available_rss:
                available_rss = task.rss
            if available_memory == 0 and task.memory_percentage and task.memory_percentage > 0 and task.rss and task.rss > 0:
                available_memory = (100 / task.memory_percentage) * task.rss
            available_memory = max([available_memory, available_rss])

        limits = {
            "max_cpu_requested": max_cpu_requested, "max_memory_requested": max_memory_requested, "max_memory": available_memory,
            "cpu_deviation": VALID_CPU_DEVIATION, "memory_deviation": VALID_MEMORY_DEVIATION,
        
        }
        weighted_task_information_per_run[run_name] = []
        for task in raw_task_information_per_run[run_name]:
            x = calculate_weighted_metric_scores_for_run(task)
            weighted_task_information_per_run[run_name].append(x)        
        
        process_scores_per_run[run_name] = []
        distinct_process_names = list(set([task['process'] for task in weighted_task_information_per_run[run_name]]))
        for process in distinct_process_names:
            tasks_by_process = [task for task in weighted_task_information_per_run[run_name] if task['process'] == process]
            process_scores_per_run[run_name].append(calculate_weighted_scores(tasks_by_process, process, limits))
        
        full_score_per_run[run_name] = calculate_weighted_scores(weighted_task_information_per_run[run_name])

    return {"task_information": weighted_task_information_per_run, "process_scores": process_scores_per_run, "full_scores": full_score_per_run}

def get_per_process_worst_rss_ratios(process_name, tasks):
    ratios = [1 if task['vmem'] == 0 else task['rss'] / task['vmem'] for task in tasks if task['rss'] and task['vmem']]
    ratio_sum = sum(ratios)
    ratio_average = 1
    if len(ratios) > 0:
        ratio_average = ratio_sum / len(ratios)
    return {"ratio_average": ratio_average, "tasks": len(tasks), "process_name": process_name}

def get_per_process_cpu_allocation_results(process_name, tasks):
    cpu_penalties = [task['raw_cpu_penalty'] for task in tasks if task['raw_cpu_penalty'] is not None]
    sum_penalty = sum(cpu_penalties)
    average_penalty = 0
    if len(cpu_penalties) > 0:
        average_penalty = sum_penalty / len(cpu_penalties)

    return {"deviation_sum": sum_penalty, "deviation_average": average_penalty, "tasks": [len(tasks)], "process_name": process_name}

def get_memory_allocation_average_over_tasks(tasks):
    count_allocation = 0
    count_absolute_requested = 0
    count_absolute_used = 0
    allocation_sum = 0
    absoulte_requested_sum = 0
    absolute_used_sum = 0
    for task in tasks:
        if task['memory_allocation']:
            count_allocation = count_allocation + 1
            allocation_sum = allocation_sum + task['memory_allocation']
        if task['memory']:
            count_absolute_requested = count_absolute_requested + 1
            absoulte_requested_sum = absoulte_requested_sum + task['memory']
        if task['rss']:
            count_absolute_used = count_absolute_used + 1
            absolute_used_sum = absolute_used_sum + task['rss']
    
    return {
        'allocation_average': 0 if count_allocation == 0 else allocation_sum / count_allocation,
        'requested_average': 0 if count_absolute_requested == 0 else absoulte_requested_sum / count_absolute_requested,
        'used_average': 0 if count_absolute_used == 0 else absolute_used_sum / count_absolute_used
    }


def get_cpu_allocation_average_over_tasks(tasks):
    count_allocation = 0
    count_absolute_requested = 0
    count_absolute_used = 0
    allocation_sum = 0
    absoulte_requested_sum = 0
    absolute_used_sum = 0
    for task in tasks:
        if task['cpu_allocation']:
            count_allocation = count_allocation + 1
            allocation_sum = allocation_sum + task['cpu_allocation']
        if task['cpus']:
            count_absolute_requested = count_absolute_requested + 1
            absoulte_requested_sum = absoulte_requested_sum + task['cpus']
        if task['cpu_percentage'] and task['cpu_percentage']:
            count_absolute_used = count_absolute_used + 1
            absolute_used_sum = absolute_used_sum + task['cpu_percentage'] / 100
    
    return {
        'allocation_average': 0 if count_allocation == 0 else allocation_sum / count_allocation,
        'requested_average': 0 if count_absolute_requested == 0 else absoulte_requested_sum / count_absolute_requested,
        'used_average': 0 if count_absolute_used == 0 else absolute_used_sum / count_absolute_used
    }


def get_per_process_memory_allocation_results(process_name, tasks):
    memory_penalties = [task['raw_memory_penalty'] for task in tasks if task['raw_memory_penalty'] is not None]
    sum_penalty = sum(memory_penalties)
    average_penalty = 0
    if len(memory_penalties) > 0:
        average_penalty = sum_penalty / len(memory_penalties)

    return {"deviation_sum": sum_penalty, "deviation_average": average_penalty, "tasks": [len(tasks)], "process_name": process_name}

def get_process_relation_data(tasks):

    cpu_allocation_values = [task['cpu_allocation'] for task in tasks if task['cpu_allocation'] and task['cpus'] and task['memory_allocation'] and task['memory']]
    memory_allocation_values = [task['memory_allocation'] for task in tasks if task['cpu_allocation'] and task['cpus'] and task['memory_allocation'] and task['memory']]

    rel_data = {}
    if len(cpu_allocation_values) > 0:
        rel_data["xMin"] = min(cpu_allocation_values)
        rel_data["x"] = sum(cpu_allocation_values) / len(cpu_allocation_values)
        rel_data["xMax"] = max(cpu_allocation_values)
    
    if len(memory_allocation_values) > 0:
        rel_data["yMin"] = min(memory_allocation_values)
        rel_data["y"] = sum(memory_allocation_values) / len(memory_allocation_values)
        rel_data["yMax"] = max(memory_allocation_values)
    
    return rel_data


def analyze(db: Session, grouped_processes, threshold_numbers):
    result_scores = calculate_scores(grouped_processes, threshold_numbers)
    analysis = {}


    # duration
    
    per_run_bad_duration_tasks = {}  # bad durations per task

    per_run_bad_duration_processes_sums = {} # bad duration summarized over all tasks of a process
    per_run_bad_duration_processes_average = {} # bad duration averaged over all tasks of a process

    # allocations

    per_run_process_cpu_allocation_deviation_sums = {} # bad cpu allocations by process summarized
    per_run_task_worst_cpu_allocation = {}
    per_run_process_cpu_allocation_deviation_averages = {} # bad cpu allocations by process averaged

    per_run_process_memory_allocation_deviation_sums = {} # bad memory allocation by process summarized
    per_run_task_worst_memory_allocation = {}
    per_run_process_memory_allocation_deviation_averages = {} # bad memory allocation by process averaged
    
    # ratio

    per_run_cpu_ram_ratio_data = {} # for plot

    per_run_worst_rss_vmem_ratio_processes = {} # worst ratio for rss/vmem
   

    for run_name in result_scores['task_information']:
        run_task_information = result_scores['task_information'][run_name]
        distinct_process_names = list(set([task['process'] for task in run_task_information]))
        
        return_number_tasks = min([10, len(run_task_information)]) # could be more dynamic
        return_number_processes = min([10, len(distinct_process_names)]) # as well

        # duration
        duration_sorted_list_descending = sorted(run_task_information, key=lambda task: task.get('realtime', -1) or -1, reverse=True)
        # cpu_alloc
        cpu_alloc_sorted_list_descending = sorted(run_task_information, key=lambda task: task.get('raw_cpu_penalty', -1) or -1, reverse=True)
        # memory_alloc
        memory_alloc_sorted_list_descending = sorted(run_task_information, key=lambda task: task.get('raw_memory_penalty', -1) or -1, reverse=True)
        
        per_run_bad_duration_tasks[run_name] = duration_sorted_list_descending[:return_number_tasks]
        per_run_task_worst_cpu_allocation[run_name] = cpu_alloc_sorted_list_descending[:return_number_tasks]
        per_run_task_worst_memory_allocation[run_name] = memory_alloc_sorted_list_descending[:return_number_tasks]

        per_process_duration_sum = []
        per_process_duration_average = []
        per_process_cpu_allocation = []
        per_process_memory_allocation = []
        per_process_rss_ratio = []

        # ratio plot
        ram_cpu_relation_labels = distinct_process_names
        ram_cpu_relation_data = []

        for process_name in distinct_process_names:
            by_process_tasks = [task for task in run_task_information if task['process'] == process_name]
            per_process_realtime_list = [task['realtime'] for task in by_process_tasks if task['realtime'] is not None]
            per_process_duration_sum.append({"process": process_name, "sum": sum(per_process_realtime_list)})
            if len(per_process_realtime_list) == 0:
                per_process_duration_average.append({"process": process_name, "average": 0})
            else: 
                per_process_duration_average.append({"process": process_name, "average": sum(per_process_realtime_list) / len(per_process_realtime_list)})
            
            cpu_allocation_results = get_per_process_cpu_allocation_results(process_name, by_process_tasks)
            per_process_cpu_allocation.append(cpu_allocation_results)
            memory_allocation_results = get_per_process_memory_allocation_results(process_name, by_process_tasks)
            per_process_memory_allocation.append(memory_allocation_results)

            memory_physical_ratio_results = get_per_process_worst_rss_ratios(process_name, by_process_tasks)
            per_process_rss_ratio.append(memory_physical_ratio_results)

            process_relation_data = get_process_relation_data(by_process_tasks)
            ram_cpu_relation_data.append(process_relation_data)

            final_error_bar_data = {
                "data": ram_cpu_relation_data,
                "label": "CPU - RAM ratio"
            }

            per_run_cpu_ram_ratio_data[run_name] = {
                "data": final_error_bar_data,
                "labels": ram_cpu_relation_labels,
            }

    
        per_run_bad_duration_processes_sums[run_name] = sorted(per_process_duration_sum, key=lambda process: process.get('sum'), reverse=True)[:return_number_processes]
       
        per_run_bad_duration_processes_average[run_name] = sorted(per_process_duration_average, key=lambda process: process.get('average'), reverse=True)[:return_number_processes]

    
        
        per_run_process_cpu_allocation_deviation_sums[run_name] = sorted(per_process_cpu_allocation, key=lambda process: process.get('deviation_sum'), reverse=True)[:return_number_processes]
        per_run_process_cpu_allocation_deviation_averages[run_name] = sorted(per_process_cpu_allocation, key=lambda process: process.get('deviation_average'), reverse=True)[:return_number_processes]

        per_run_process_memory_allocation_deviation_sums[run_name] = sorted(per_process_memory_allocation, key=lambda process: process.get('deviation_sum'), reverse=True)[:return_number_processes]
        per_run_process_memory_allocation_deviation_averages[run_name] = sorted(per_process_memory_allocation, key=lambda process: process.get('deviation_average'), reverse=True)[:return_number_processes]
        per_run_worst_rss_vmem_ratio_processes[run_name] = sorted(per_process_rss_ratio, key=lambda process: process.get('ratio_average'))[:return_number_processes]

        




    
        
       

    
        
    analysis["workflow_scores"] = result_scores
    
    analysis["bad_duration_tasks"] = per_run_bad_duration_tasks
    analysis["bad_duration_processes_sum"] = per_run_bad_duration_processes_sums
    analysis["bad_duration_processes_average"] = per_run_bad_duration_processes_average

    analysis["cpu_allocation_deviation_sum"] = per_run_process_cpu_allocation_deviation_sums
    analysis["cpu_allocation_deviation_average"] = per_run_process_cpu_allocation_deviation_averages
    analysis["bad_cpu_allocation_tasks"] = per_run_task_worst_cpu_allocation

    analysis["memory_allocation_deviation_sum"] = per_run_process_memory_allocation_deviation_sums
    analysis["memory_allocation_deviation_average"] = per_run_process_memory_allocation_deviation_averages
    analysis["bad_memory_allocation_tasks"] = per_run_task_worst_memory_allocation

    analysis["bad_memory_ratio"] = per_run_worst_rss_vmem_ratio_processes
    analysis["cpu_ram_relation_data"] = per_run_cpu_ram_ratio_data


    return analysis

def sort_values_per_run(run_duration_data, key_name, reverse=False):
    per_run_mapping = {}
    for run_name, values in run_duration_data.items():
        list_of_values = list(values.items())
        sorted_list = sorted(list_of_values, key=lambda process: process[1], reverse=reverse)
        sorted_processes = []
        for value in sorted_list:
            if len(sorted_processes) < limit_processes_per_domain_by_number:
                sorted_processes.append({"process": value[0], key_name: value[1]})
        per_run_mapping[run_name] = sorted_processes
    
    return per_run_mapping


def group_runwise(data):
    run_groups = {}
    for item in data: 
        run_name = item["run_name"]
        run_groups.setdefault(run_name, []).append(item)
    return run_groups

"""
not in use at the moment
"""
def get_tag_invalidities(tag_obj, execution_duration_mapping, full_duration):
    valid = True
    problems = []
    same_tag_durations = []
    same_tag_memory = []
    same_tag_cpu_percentage = []
    same_tag_cpu_allocation = []
    without_tag_memory = []
    without_tag_cpu_percentage = []
    without_tag_cpu_allocation = []
    without_tag_durations = []
    for elem in execution_duration_mapping:
        if tag_obj["tag"] in elem["tags"]:
            for process in tag_obj["processes"]:
                if process.duration:
                    same_tag_durations.append(process.duration)
                if process.cpu_percentage:
                    same_tag_cpu_percentage.append(process.cpu_percentage)
                    if process.cpus:
                        same_tag_cpu_allocation.append(process.cpu_percentage / process.cpus)
                if process.rss:
                    same_tag_memory.append(process.rss)
        else:
            for process in tag_obj["processes"]:
                if process.duration:
                    without_tag_durations.append(process.duration)
                if process.cpu_percentage:
                    without_tag_cpu_percentage.append(process.cpu_percentage)
                    if process.cpus:
                        without_tag_cpu_allocation.append(process.cpu_percentage / process.cpus)
                if process.rss:
                    without_tag_memory.append(process.rss)

    # duration

    same_tag_duration_sum = sum(same_tag_durations)
    without_tag_duration_sum = sum(without_tag_durations)
    if len(same_tag_durations) > 0 and len(without_tag_durations) > 0:
        same_tag_duration_average = same_tag_duration_sum / len(same_tag_durations)
        without_tag_duration_average = without_tag_duration_sum / len(without_tag_durations)
        ratio_with_without = same_tag_duration_average / without_tag_duration_average
        if ratio_with_without > tag_duration_ratio_threshold:
            valid = False
            problems.append({"tag_duration_comparison_ratio": ratio_with_without})
        ratio_with_full = same_tag_duration_sum / full_duration
        if ratio_with_full > tag_duration_ratio_full_threshold:
            valid = False
            problems.append({"tag_duration_to_full_ratio": ratio_with_full})
    
    # cpu

    if len(same_tag_cpu_allocation) > 0 and len(without_tag_cpu_allocation) > 0:
        same_tag_cpu_allocation_average = sum(same_tag_cpu_allocation) / len(same_tag_cpu_allocation)
        without_tag_cpu_allocation_average = sum(without_tag_cpu_allocation) / len(without_tag_cpu_allocation)
        ratio = same_tag_cpu_allocation_average / without_tag_cpu_allocation_average
        if ratio > tag_cpu_allocation_ratio_threshold:
            valid = False
            problems.append({"tag_cpu_allocation_ratio": ratio})

    if len(same_tag_cpu_percentage) > 0 and len(without_tag_cpu_percentage) > 0:
        same_tag_cpu_percentage_average =  sum(same_tag_cpu_percentage) / len(same_tag_cpu_percentage)
        without_tag_cpu_percentage_average =  sum(without_tag_cpu_percentage) / len(without_tag_cpu_percentage)
        ratio = same_tag_cpu_percentage_average / without_tag_cpu_percentage_average
        if ratio > tag_cpu_percentage_ratio_threshold:
            valid = False
            problems.append({"tag_cpu_percentage_ratio": ratio})
    
    # memory 

    if len(same_tag_memory) > 0 and len(without_tag_memory) > 0:
        same_tag_memory_average = sum(same_tag_memory) / len(same_tag_memory)
        without_tag_memory_average = sum(without_tag_memory) / len(without_tag_memory)
        ratio = same_tag_memory_average / without_tag_memory_average
        if ratio > tag_memory_rss_average_ratio_threshold:
            valid = False
            problems.append({"tag_memory_ratio": ratio})

    return valid, problems

def tags_from_process(process: models.RunTrace):
    tags = process.tag
    return tags_from_string(tags)

def tags_from_string(str: string):
    if str is None or str == '':
        return [{'_': None}]
    pairs = []
    splitted = str.split(',')
    for splitted_string in splitted:
        splitted_string = splitted_string
        pair = splitted_string.split(':')
        if len(pair) > 1:
            pairs.append({pair[0].strip(), pair[1].strip()})
        else:
            pairs.append({'_': pair[0].strip()})
    return pairs

def get_process_invalidities(tasks, max_cpu_requested, max_memory, max_memory_requested, cpu_deviation, memory_deviation):

    problems = []
    if len(tasks) == 0:
        return problems
    memory_allocation_results = get_per_process_memory_allocation_results('', tasks)
    cpu_allocation_results = get_per_process_cpu_allocation_results('', tasks)
    memory_allocation_average = get_memory_allocation_average_over_tasks(tasks)
    cpu_allocation_average = get_cpu_allocation_average_over_tasks(tasks)
    
    if cpu_allocation_results['deviation_average'] > cpu_deviation:
        cpu_needed_float = cpu_allocation_average['used_average']
        cpu_requested_average = cpu_allocation_average['requested_average']
        if cpu_needed_float < cpu_requested_average:
            if cpu_needed_float < 1:
                problems.append({"cpu": "less", "requested": cpu_requested_average, "restriction": "min_reached", "solution": {"process": "split"}})
            else:
                problems.append({"cpu": "less", "requested": cpu_requested_average, "restriction": None, "solution": {"cpus": cpu_needed_float}})
        else:
            if cpu_needed_float < max_cpu_requested:
                problems.append({"cpu": "more", "requested": cpu_requested_average, "restriction": None, "solution": {"cpus": cpu_needed_float}})
            else:
                if max_cpu_requested == 0:
                    problems.append({"cpu": "more", "requested": cpu_requested_average, "restriction": "max_reached_unsure", "solution": {"needed": cpu_needed_float, "available": max_cpu_requested}})
                else:
                    problems.append({"cpu": "more", "requested": cpu_requested_average, "restriction": "max_reached", "solution": {"needed": cpu_needed_float, "available": max_cpu_requested}})
    if memory_allocation_results['deviation_average'] > memory_deviation:
        memory_needed_average = memory_allocation_average['used_average']
        memory_requested_average = memory_allocation_average['requested_average']
        if memory_needed_average < memory_requested_average:
            problems.append({"ram": "less", "requested": memory_requested_average, "restriction": None, "solution": {"ram": memory_needed_average}})
        else:
            if memory_needed_average > max_memory:
                if max_memory == 0:
                    problems.append({"ram": "more", "requested": memory_requested_average, "restriction": "max_reached_unsure", "solution": {"ram": memory_needed_average , "available": max_memory }})
                else:
                    problems.append({"ram": "more", "requested": memory_requested_average, "restriction": "max_reached", "solution": {"ram": memory_needed_average, "available": max_memory }})
            else:
                problems.append({"ram": "more", "requested": memory_requested_average, "restriction": None, "solution": {"ram": memory_needed_average, "available": max_memory }})

    return problems


"""
Not used at the moment
"""
def transfer_ram_limit(ram_in_bytes, up=False):
    gib_value_float = ram_in_bytes / (math.pow(1024,3))
    gib_value_full_lower = math.floor(gib_value_float)
    gib_value_full_higher = math.ceil(gib_value_float)
    if gib_value_float - gib_value_full_lower <  gib_value_full_higher - gib_value_float or up:
        return gib_value_full_higher * math.pow(1024, 3)
    else:
        return gib_value_full_lower * math.pow(1024, 3)

def get_cpu_severity(information):
    return get_minutes(information["duration"]) * information["cpus"] * abs(100 - information["cpu_allocation"])

def get_memory_severity(information):
    return get_minutes(information["duration"]) * get_gibs(information["rss"]) * abs(100 - information["ram_allocation"])

def get_minutes(milliseconds):
    return milliseconds / 60000

def get_gibs(bytes):
    return bytes / 1073741824
    
    
def check_valid_ram_interval(process: models.RunTrace):
    if process.memory is not None and process.rss is not None:
        relative = process.rss / process.memory
        return interval_valid_ram_relation[0] <= relative <= interval_valid_ram_relation[1], {"ram_relative": relative}
    return True, None

def check_valid_cpu_interval(process: models.RunTrace):
    if process.cpus:
        if process.cpu_percentage:
            allocation = process.cpu_percentage / process.cpus
            return interval_valid_cpu_allocation_percentage[0] <= allocation <= interval_valid_cpu_allocation_percentage[1], {"cpu_allocation": allocation}
    return True, None
"""
end of not used at the moment
"""

def group_by_run_name(result_by_task):
    run_name_dictionary = {}
    for process in result_by_task:
        if process.run_name not in run_name_dictionary:
            run_name_dictionary[process.run_name] = [process]
        else:
            run_name_dictionary[process.run_name].append(process)

    return run_name_dictionary


"""
End of analysis part
"""