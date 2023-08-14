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


def calculate_scores(db: Session, grouped_processes, threshold_numbers):
    RAM_WEIGHT, CPU_WEIGHT = 0.5, 0.5
    scores_for_run = {}
    plain_values = {}

    # threshold numbers to be used later on
    for run_name in grouped_processes:
        scores_for_run[run_name] = {"task_scores": {}, "process_scores": {}}
        task_scores = {}
        cpu_allocation_scores = {}
        ram_allocation_scores = {}
        duration = {}
        memory_requested = {}
        cpus_requested = {}
        run = grouped_processes[run_name]
        all_cpu_alloc_values = []
        all_memory_alloc_values = []
        plain_values[run_name] = {}
       
        
        number_of_tasks = len(run)


        for task in run:
            tid = task.task_id
            plain_values[run_name][tid] = {}
            plain_values[run_name][tid]["duration"] = task.realtime
            plain_values[run_name][tid]["process"] = task.process
            proc_name = task.process
            if task.cpus and task.cpus > 0 and task.cpu_percentage:
                
                cpu_alloc_score = (task.cpu_percentage / task.cpus)
                plain_values[run_name][tid]["cpu_allocation"] = cpu_alloc_score
                plain_values[run_name][tid]["cpus"] = task.cpus
                plain_values[run_name][tid]["cpu_percentage"] = task.cpu_percentage

                cpu_alloc_score = cpu_alloc_score / 100
                cpu_alloc_score = abs(1 - cpu_alloc_score)
                cpu_allocation_scores[tid] = {"process": proc_name, "value": cpu_alloc_score}
                cpus_requested[tid] = {"process": proc_name, "value": task.cpus}
                all_cpu_alloc_values.append(cpu_alloc_score)
        
            if task.memory and task.memory > 0 and task.rss:
                ram_alloc_score = task.rss / task.memory # no division with 100, as ratio is already [0, 1]

                plain_values[run_name][tid]["ram_allocation"] = ram_alloc_score * 100
                plain_values[run_name][tid]["memory"] = task.memory
                plain_values[run_name][tid]["rss"] = task.rss

                ram_alloc_score = abs(1 - ram_alloc_score)
                ram_allocation_scores[tid] = {"process": proc_name, "value": ram_alloc_score}
                memory_requested[tid] = {"process": proc_name, "value": task.memory}
                all_memory_alloc_values.append(ram_alloc_score)
            if task.realtime and task.realtime > 0:
                duration[tid] = {"process": proc_name, "value": task.realtime}
        
        plain_values[run_name]

        if len(all_cpu_alloc_values) > 0: 
            min_cpu_alloc, max_cpu_alloc = 0, max(all_cpu_alloc_values)

            for task_id in cpu_allocation_scores:
                t_val_cpu = cpu_allocation_scores[task_id]["value"]
                cpu_allocation_scores[task_id]["value"] = (t_val_cpu - min_cpu_alloc) / (max_cpu_alloc - min_cpu_alloc)
        

        if len(all_memory_alloc_values) > 0: 
            min_mem_alloc, max_mem_alloc = 0, max(all_memory_alloc_values)
            for task_id in ram_allocation_scores:
                t_val_mem = ram_allocation_scores[task_id]["value"]
                ram_allocation_scores[task_id]["value"] = (t_val_mem - min_mem_alloc) / (max_mem_alloc - min_mem_alloc)

        cpu_key_list, ram_key_list = list(cpu_allocation_scores.keys()), list(ram_allocation_scores.keys())
        scoreable_task_ids = [key for key in cpu_key_list if key in ram_key_list]
        for task_id in scoreable_task_ids:
            weighted_cpu_score = CPU_WEIGHT * (1 - cpu_allocation_scores[task_id]["value"])
            weighted_ram_score = RAM_WEIGHT * (1 - ram_allocation_scores[task_id]["value"])
            task_scores[task_id] = weighted_cpu_score + weighted_ram_score
        weighted_scoreable_key_list = [key for key in scoreable_task_ids if key in duration]
        scores_for_run[run_name]["task_scores"] = task_scores
        weighted_process_scores = {}
        for task_id in weighted_scoreable_key_list:
            process_name = duration[task_id]["process"]
            if process_name not in weighted_process_scores:
                weighted_process_scores[process_name] = []
            cpu_score = 1 - cpu_allocation_scores[task_id]["value"]
            ram_score = 1 - ram_allocation_scores[task_id]["value"]
            cpu_requ_value = cpus_requested[task_id]["value"]
            mem_requ_value = memory_requested[task_id]["value"]
            dur_value = duration[task_id]["value"]
            value_numerator = (cpu_score * cpu_requ_value + ram_score * mem_requ_value) * dur_value
            value_denominator = (cpu_requ_value + mem_requ_value) * dur_value
            weighted_process_scores[process_name].append({"numerator": value_numerator, "denominator": value_denominator})
        
        per_process_scores = {}
        
        for process in weighted_process_scores:
            numerator_sum = sum(calculated['numerator'] for calculated in weighted_process_scores[process])
            denominator_sum = sum(calculated['denominator'] for calculated in weighted_process_scores[process])
            result = numerator_sum / denominator_sum
            per_process_scores[process] = result

        scores_for_run[run_name]["process_scores"] = per_process_scores # check if this can be calculated differently

        full_workflow_score = sum(task_scores.values()) / number_of_tasks
        scores_for_run[run_name]["full_run_score"] = full_workflow_score


        # TODO: describe these values with equations in the thesis

    scores_for_run["detail"] = plain_values
    return scores_for_run



def analyze(db: Session, grouped_processes, threshold_numbers):
    result_scores = calculate_scores(db, grouped_processes, threshold_numbers)
    analysis = {}
    process_analysis = []
    tags_presave = []
    tag_process_mapping = []
    tag_analysis = []
    
    for elem in threshold_numbers.items():
        match elem[0]:
            case "interval_valid_ram_relation":
                global interval_valid_ram_relation
                interval_valid_ram_relation = elem[1]
            case "interval_valid_cpu_allocation_percentage":
                global interval_valid_cpu_allocation_percentage
                interval_valid_cpu_allocation_percentage = elem[1]
            case "threshold_duration_relation":
                global threshold_duration_relation
                threshold_duration_relation = elem[1]
            case "duration_to_consider_threshold":
                global duration_to_consider_averages_threshold
                duration_to_consider_averages_threshold = elem[1]
            case "duration_requested_relation_relation_threshold":
                global duration_requested_relation_threshold
                duration_requested_relation_threshold = elem[1]
            case "tag_duration_ratio_threshold":
                global tag_duration_ratio_threshold
                tag_duration_ratio_threshold = elem[1]
            case "tag_duration_full_threshold":
                global tag_duration_ratio_full_threshold
                tag_duration_ratio_full_threshold = elem[1]
            case "tag_cpu_allocation_ratio_threshold":
                global tag_cpu_allocation_ratio_threshold
                tag_cpu_allocation_ratio_threshold = elem[1]
            case "tag_cpu_percentage_ratio_threshold":
                global tag_cpu_percentage_ratio_threshold
                tag_cpu_percentage_ratio_threshold = elem[1]
            case "tag_memory_rss_average_ratio_threshold":
                global tag_memory_rss_average_ratio_threshold
                tag_memory_rss_average_ratio_threshold = elem[1]
            case "top_percent_ratio":
                global top_percent_ratio
                top_percent_ratio = elem[1]
            case "limit_processes_per_domain_by_number":
                global limit_processes_per_domain_by_number
                limit_processes_per_domain_by_number = elem[1]
    

    
    per_run_bad_duration = {}  # bad durations by run
    # per_run_process_duration_average = {}
    per_run_process_duration_sum = {}
    per_run_process_duration_average = {}
    per_run_process_cpu_average = {}
    per_run_process_cpu_allocation_average = {}
    per_run_process_least_cpu_allocation = {}
    per_run_process_most_cpu_allocation = {}
    # per_run_process_memory_average = {}
    per_run_process_memory_relation_average = {}
    per_run_process_memory_allocation_average = {}

    per_run_cpu_ram_ratio_data = {}

    for key in grouped_processes:
        max_cpu_requested_value = 0
        max_memory_available = 0

        process_mapping_cpu_raw = {}
        process_mapping_allocation = {}
        process_mapping_duration = {}
        
        process_mapping_memory_percentage = {} # memory_percentage
        process_mapping_memory_allocation = {} # rss/mem
        process_mapping_memory_relation = {} # rss/vmem


        process_duration_sum = {}
        process_duration_average = {}
        process_memory_allocation_average = {}
        process_memory_relation_average = {}
        process_cpu_allocation_average = {}
        process_cpu_raw_usage = {}
        process_cpu_raw_average = {}


        group = grouped_processes[key]
        group_dicts = [vars(process) for process in group]
        check_number = min([limit_processes_per_domain_by_number, len(group_dicts)])
        number_of_elems_to_return = min([limit_processes_per_domain_by_number, int(len(group_dicts) * top_percent_ratio)])
        number_of_elems_to_return = max([check_number, number_of_elems_to_return])

        # sort by duration
        mapping_keys = ["process", "task_id", "duration"]  # only retrieve these
        duration_sorted_list = sorted(group_dicts, key=lambda proc: proc.get('duration', 0) or 0, reverse=True)
        duration_list = [{key: process[key] for key in mapping_keys if process[key] and process[key] is not None} for process in duration_sorted_list]
        duration_sum = sum([process["duration"] for process in group_dicts if process["duration"] is not None])
        average_duration = duration_sum / len(group_dicts)
        
        worst_duration_list = duration_list[:number_of_elems_to_return]
        per_run_bad_duration[key] = worst_duration_list

        cpu_percentage_sorted_allocation_list_least = sorted(group_dicts, key=lambda proc: (proc.get('cpu_percentage') or sys.maxsize) / (proc.get('cpus') or 0.00000001)) # is there a better wy=
        
        cpu_allocated_least_list = [
            {"process": proc["process"], "task_id": proc["task_id"], "allocation": (proc['cpu_percentage'] or 0) / (proc['cpus'] or 1)} for proc in cpu_percentage_sorted_allocation_list_least
            ][:number_of_elems_to_return]
    
        per_run_process_least_cpu_allocation[key] = cpu_allocated_least_list
        
        cpu_percentage_sorted_allocation_list_most = sorted(group_dicts, key=lambda proc: (proc.get('cpu_percentage') or 0.000001) / (proc.get('cpus') or sys.maxsize), reverse=True)
        cpu_allocated_most_list = [
            {"process": proc["process"], "task_id": proc["task_id"], "allocation": (proc['cpu_percentage'] or 0) / (proc['cpus'] or 1)} for proc in cpu_percentage_sorted_allocation_list_most
            ][:number_of_elems_to_return]

        per_run_process_most_cpu_allocation[key] = cpu_allocated_most_list
        

        for process in group_dicts:
            if process["cpus"] and process["cpus"] > 0:
                if process["cpus"] > max_cpu_requested_value:
                    max_cpu_requested_value = process["cpus"]
            if process["process"] not in process_mapping_cpu_raw:
                process_mapping_cpu_raw[process["process"]] = []
            if process["cpu_percentage"]:
                process_mapping_cpu_raw[process["process"]].append(process["cpu_percentage"])

            if process["process"] not in process_mapping_allocation:
                process_mapping_allocation[process["process"]] = []
            if process["cpu_percentage"] and process["cpus"] > 0:
                process_mapping_allocation[process["process"]].append(process["cpu_percentage"] / process["cpus"])

            if process["duration"]:
                if process["process"] not in process_mapping_duration:
                    process_mapping_duration[process["process"]] = []
                process_mapping_duration[process["process"]].append(process["duration"])
            
            
            if process["process"] not in process_mapping_memory_percentage:
                process_mapping_memory_percentage[process["process"]] = []
            if process["memory_percentage"]:
                process_mapping_memory_percentage[process["process"]].append(process["memory_percentage"])
            


            if process["rss"]:
                if process["memory"] and process["memory"] > 0:
                    if process["process"] not in process_mapping_memory_allocation:
                        process_mapping_memory_allocation[process["process"]] = []
                    process_mapping_memory_allocation[process["process"]].append((process["rss"] / process["memory"]) * 100)

                if process["vmem"] and process["vmem"] > 0:
                    if process["process"] not in process_mapping_memory_relation:
                        process_mapping_memory_relation[process["process"]] = []
                    process_mapping_memory_relation[process["process"]].append((process["rss"] / process["vmem"]) * 100)
            if process["memory_percentage"] and process["rss"]:
                if max_memory_available == 0:
                    max_memory_available = process["rss"] * (1 / (process["memory_percentage"] / 100))

                

        for process, raw_usages in process_mapping_cpu_raw.items():
            process_sum = sum(raw_usages)
            average = 0
            if len(raw_usages) > 0:
                average = process_sum / len(raw_usages)
            process_cpu_raw_average[process] = average


        per_run_process_cpu_average[key] = process_cpu_raw_average


        for process, allocation_usages in process_mapping_allocation.items():
            process_sum = sum(allocation_usages)
            process_average = 0
            if len(allocation_usages) > 0:
                process_average = process_sum  / len (allocation_usages)
            process_cpu_allocation_average[process] = process_average
        
        per_run_process_cpu_allocation_average[key] = process_cpu_allocation_average
        

        for process, duration_mapping in process_mapping_duration.items():
            duration_sum = sum(duration_mapping)
            process_average = 0
            if len(duration_mapping) > 0:
                process_average = duration_sum / len(duration_mapping)
            process_duration_sum[process] = duration_sum
            process_duration_average[process] = process_average

        per_run_process_duration_sum[key] = process_duration_sum
        per_run_process_duration_average[key] = process_duration_average

        # check for process, percentage_mapping in process_mapping_memory_percentage

        for process, mapping in process_mapping_memory_allocation.items():
            m_sum = sum(mapping)
            average = 0
            if len(mapping) > 0:
                average = m_sum / len(mapping)

            process_memory_allocation_average[process] = average

        per_run_process_memory_relation_average[key] = process_memory_allocation_average
    
        
        for process, mapping in process_mapping_memory_relation.items():
            relation_sum = sum(mapping)
            average = 0
            if len(mapping) > 0:
                average = relation_sum / len(mapping)
    
            process_memory_relation_average[process] = average

        per_run_process_memory_allocation_average[key] = process_memory_relation_average

        # set the data for the plot

        
        ram_cpu_relation_labels = []
        ram_cpu_relation_data = []

        for item in process_mapping_allocation:
            if len(process_mapping_allocation[item]) > 0:
                if item in process_mapping_memory_allocation and    len(process_mapping_memory_allocation[item]) > 0:
                    
                    x_vals = process_mapping_allocation[item]
                    y_vals = process_mapping_memory_allocation[item]
                    rel_data = {
                        "xMin": min(x_vals),
                        "x": sum(x_vals) / len(x_vals),
                        "xMax": max(x_vals),
                        "yMin": min(y_vals),
                        "y": sum(y_vals) / len(y_vals),
                        "yMax": max(y_vals),
                        "id": item,
                    }
                    
                    ram_cpu_relation_labels.append(item)
                    ram_cpu_relation_data.append(rel_data)

        final_error_bar_data = {
            "data": ram_cpu_relation_data,
            "label": "CPU - RAM ratio",
        }

        per_run_cpu_ram_ratio_data[key] = {
            "labels": ram_cpu_relation_labels,
            "data": final_error_bar_data
        }

        result_scores['detail'][key] = get_process_invalidities(result_scores['detail'][key], {"max_cpu": max_cpu_requested_value, "max_ram": max_memory_available})
        result_scores['detail'][key] = [{"task_id": tid, "score": result_scores[key]['task_scores'][tid], **values} for tid, values in result_scores['detail'][key].items() if tid in result_scores[key]['task_scores']]


        """        for process in group:
            
            process: models.RunTrace = process
            possible_return = {"process": process.process, "task_id": process.task_id, "run_name": process.run_name,
                               "problems": [], score: result_scores}
            valid, problems = get_process_invalidities(process, execution_duration)
            if not valid:
                possible_return["problems"] = problems
            process_analysis.append(possible_return)
        #full_duration = sum(full_duration)  # there is a bug somewhere
        """
    
               
    analysis["process_wise"] = group_runwise(process_analysis)
    analysis["tag_wise"] = group_runwise(tag_analysis)
    
        
    analysis["bad_duration"] = per_run_bad_duration
    analysis["least_cpu"] = per_run_process_least_cpu_allocation
    analysis["most_cpu"] = per_run_process_most_cpu_allocation
    analysis["cpu_average"] = per_run_process_cpu_average
    analysis["cpu_allocation_average"] = per_run_process_cpu_allocation_average
    analysis["duration_sum"] = per_run_process_duration_sum
    analysis["worst_duration_sum"]=  sort_values_per_run(per_run_process_duration_sum, 'duration', reverse=True)
    analysis["duration_average"] = per_run_process_duration_average
    analysis["worst_duration_average"] = sort_values_per_run(per_run_process_duration_average, 'duration', reverse=True)
    analysis["memory_allocation"] = per_run_process_memory_allocation_average
    analysis["least_memory_allocation_average"] = sort_values_per_run(per_run_process_memory_allocation_average, 'memory_allocation')
    analysis["most_memory_allocation_average"] = sort_values_per_run(per_run_process_memory_allocation_average , 'memory_allocation', reverse=True)
    analysis["memory_relation_average"] = per_run_process_memory_relation_average
    analysis["worst_memory_relation_average"] = sort_values_per_run(per_run_process_memory_relation_average, 'memory_relation')

    analysis["cpu_ram_relation_data"] = per_run_cpu_ram_ratio_data
    analysis["workflow_scores"] = result_scores


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
    if tags is None or tags == '':
        return [{'_': None}]
    pairs = []
    splitted = tags.split(',')
    for splitted_string in splitted:
        splitted_string = splitted_string
        pair = splitted_string.split(':')
        if len(pair) > 1:
            pairs.append({pair[0].strip(), pair[1].strip()})
        else:
            pairs.append({'_': pair[0].strip()})
    return pairs


def get_process_invalidities(details_for_run, comparison_values):
    """
    needs thresholds!
    """
    for x in details_for_run:
        task_details = details_for_run[x]
        task_details["problems"] = []
        if "cpus" in task_details and "cpu_allocation" in task_details:
            cpus_needed_float = task_details["cpu_percentage"] / 100
            full_cpus_needed = math.ceil(cpus_needed_float)
            global interval_valid_cpu_allocation_percentage
            lower_limit_cpu, upper_limit_cpu = interval_valid_cpu_allocation_percentage

            if task_details["cpu_allocation"] > upper_limit_cpu: 
                if cpus_needed_float - full_cpus_needed > 0.2: # replace with other threshold value
                    full_cpus_needed = full_cpus_needed + 1
                if task_details["cpus"] < comparison_values["max_cpu"]: # 
                    if full_cpus_needed > comparison_values["max_cpu"]:
                       
                        task_details["problems"].append({"cpu": "more", "restriction": None, "solution": {"cpus": full_cpus_needed}})
                        
                    else:
                        task_details["problems"].append({"cpu": "more", "restriction": "max_reached", "solution": {"needed": full_cpus_needed, "available": comparison_values["max_cpu"]}})
            elif task_details["cpu_allocation"] < lower_limit_cpu:
                
                if task_details["cpus"] > 1: 
                    if full_cpus_needed == task_details["cpus"]:
                        full_cpus_needed = full_cpus_needed - 1
                    task_details["problems"].append({"cpu": "less", "restriction": None, "solution": {"cpus": full_cpus_needed}})
                else:
                    task_details["problems"].append({"cpu": "less", "restriction": "min_reached", "solution": {"process": "split"}})

        if "ram_allocation" in task_details and "memory" in task_details and "rss" in task_details:
            mem_alloc_percentage = task_details["ram_allocation"]
            used_physical = task_details["rss"]
            global interval_valid_ram_relation
            lower_limit_ram, upper_limit_ram = interval_valid_ram_relation
            if mem_alloc_percentage < lower_limit_ram:
                task_details["problems"].append({"ram": "less", "restriction": None, "solution": {"ram": transfer_ram_limit(used_physical)}})
            elif mem_alloc_percentage > upper_limit_ram:
                restriction = None
                if used_physical > comparison_values["max_ram"]:
                    restriction = "max_reached"
                task_details["problems"].append({"ram": "more", "restriction": restriction, "solution": {"ram": transfer_ram_limit(used_physical, True) }})
            
          
    return details_for_run

def transfer_ram_limit(ram_in_bytes, up=False):
    gib_value_float = ram_in_bytes / (math.pow(1024,3))
    gib_value_full_lower = math.floor(gib_value_float)
    gib_value_full_higher = math.ceil(gib_value_float)
    if gib_value_float - gib_value_full_lower <  gib_value_full_higher - gib_value_float or up:
        return gib_value_full_higher * math.pow(1024, 3)
    else:
        return gib_value_full_lower * math.pow(1024, 3)

"""
 not used at the moment
"""
def OLD_get_process_invalidities(process: models.RunTrace, duration_mapping):
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
    
    duration_values_without_process = [dur_obj["duration"] for dur_obj in duration_mapping if dur_obj["process"] != process.process and dur_obj["duration"]]
    duration_values_without_this_explicit_task = [dur_obj["duration"] for dur_obj in duration_mapping if dur_obj["process"] != process.process and dur_obj["task_id"] != process.task_id and dur_obj["duration"]]
    duration_values_within_process = [dur_obj["duration"] for dur_obj in duration_mapping if dur_obj["process"] == process.process and dur_obj["task_id"] != process.task_id and dur_obj["duration"]]
    
    if process.duration:
        if process.duration > duration_to_consider_averages_threshold:
            len_duration_wo_p = len(duration_values_without_process)
            if len_duration_wo_p > 0:
                average_without_process = sum(duration_values_within_process) / len_duration_wo_p
                if average_without_process > threshold_duration_relation:
                    invalidities_list.append({"duration_ratio_compared_to_other_processes": average_without_process})
                    to_return = True

            len_duration_wo_et = len(duration_values_without_this_explicit_task)
            if len_duration_wo_et > 0:
                average_without_task = sum(duration_values_without_this_explicit_task) / len_duration_wo_et 
                if average_without_task > threshold_duration_relation:
                    invalidities_list.append({"duration_ratio_compared_to_all": average_without_task})
                    to_return = True

            len_duration_within = len(duration_values_within_process)
            if len_duration_within:
                average_within = sum(duration_values_within_process) / len_duration_within
                if average_within > threshold_duration_relation:
                    invalidities_list.append({"duration_ratio_compared_to_same": average_within})
                    to_return = True
        if process.time:
            duration_ratio = process.duration / process.time
            if duration_ratio > duration_requested_relation_threshold:
                invalidities_list.append({"duration_ratio_to_requested", duration_ratio})
                to_return = True
    return (not to_return, invalidities_list)

    
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