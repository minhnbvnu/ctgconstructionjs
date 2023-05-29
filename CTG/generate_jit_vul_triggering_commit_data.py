import json
from collections import defaultdict

import pandas as pd

from config import (COMMIT_EXTRACT_OUTPUTS_DIR, JIT_VUL_CLEAN_DATA_FILE_PATH,
                    JIT_VUL_CONTRIBUTING_COMMIT_FILE_PATH, JIT_VUL_DATA_DIR,
                    JIT_VUL_TRIGGERING_DATA_FILE_PATH, MAX_CHANGE,
                    PROJECT_EXTRACT_OUTPUTS_DIR)
from file_manager import (find_all_files_by_wildcard, get_cloned_repository,
                          get_file_name, is_path_exist, join_path, lock_dir,
                          write_file, unlink)
from helpers import get_logger
from pyszz.extract.commit_extractor import CommitExtractor

logger = get_logger(__name__)

JIT_VUL_CONTRIBUTING_COMMIT_DATA_FILE = "vul_contributing_commit_data.jsonl.1667660526"
JIT_VUL_CONTRIBUTING_COMMIT_DATA_PATH = join_path(
    JIT_VUL_DATA_DIR, JIT_VUL_CONTRIBUTING_COMMIT_DATA_FILE)


"""
    extract_type: 
        fc  - fixing commit
        vcc - vul contributing commit
        vtc - vul triggering commit
"""
extract_type = "vtc"
extract_level = "function"  # file or function

PATH_TO_SAVE_CSV = {"fc": JIT_VUL_CLEAN_DATA_FILE_PATH.replace(".csv", f"_{extract_level}_level.csv"),
                    "vcc": JIT_VUL_CONTRIBUTING_COMMIT_FILE_PATH.replace(".csv", f"_{extract_level}_level2.csv"),
                    "vtc": JIT_VUL_TRIGGERING_DATA_FILE_PATH.replace(".csv", f"_{extract_level}_level.csv")}
labels = {"fc": 1,
          "vcc": 0,
          "vtc": 0}

PATH_VTC_COMMITS = "vtc_ctg.csv.txt"

VTCS_DICT = defaultdict(lambda:list())
grouped_commits_by_repo = defaultdict(lambda: dict())


def merge_dict(d1, d2):
    result = dict()
    for k, v in d1.items():
        if k in d2.keys():
            v = list(set(v + d2[k]))
        result[k] = v
    for k, v in d2.items():
        if k not in d1.keys():
            result[k] = v
    return result


def main():
    vtc_commit_list = list()
    with open(PATH_VTC_COMMITS) as f:
        vtc_commit_list = f.read().splitlines()

    with open(JIT_VUL_CONTRIBUTING_COMMIT_DATA_PATH) as fp:
        for line in fp.readlines():
            data = json.loads(line)
            if len(data["vulnerability_contributing_commits"]) == 0:
                continue
            fixing_commit_id = data["fixing_commit"]["commit_hash"]
            vtc_id = data["vulnerability_contributing_commits"][0]["commit_hash"]
            if vtc_id in vtc_commit_list or True:
                blames_vtc = data["vulnerability_contributing_commits"][0]["vulnerable_changes"]
                VTCS_DICT[vtc_id + fixing_commit_id] = [el for el in data["vulnerability_contributing_commits"]]
                if vtc_id in grouped_commits_by_repo[data["repo_name"]].keys():
                    grouped_commits_by_repo[data["repo_name"]][vtc_id] = (fixing_commit_id,merge_dict(
                        blames_vtc, grouped_commits_by_repo[data["repo_name"]][vtc_id][1]))
                    continue
                grouped_commits_by_repo[data["repo_name"]][vtc_id] = (fixing_commit_id,blames_vtc)
    total_cm = 0
    for repo_name, list_commit_ids in grouped_commits_by_repo.items():
        repo_dir = get_cloned_repository(repo_name)
        if repo_name == "chromium___chromium":
            continue
        try:
            lock_dir(repo_dir)
        except BlockingIOError as e:
            continue
        df_extracted_data = extract_info(
            repo_dir, list_commit_ids)
        total_cm += len(df_extracted_data.groupby("commit_id"))
        path_to_save_csv = join_path(
            PROJECT_EXTRACT_OUTPUTS_DIR, f"{repo_name}_{extract_level}_{extract_type}.csv")

        df_extracted_data.to_csv(path_to_save_csv, index=False)
    logger.info(f"Extracted : {total_cm} commit")


def get_commit_data(repo_dir, commit_id, extract_level="function", fx_id = None ,blame=None):
    print("*"*33)
    print(f"Get commit data: {commit_id}")
    if len(commit_id) != 40:
        return list()
    if not VTCS_DICT[commit_id+fx_id] and len(VTCS_DICT[commit_id+fx_id]) >= 0:
        VTCS_DICT[commit_id+fx_id].pop(0)
    path_to_save_commit_infos = join_path(
        COMMIT_EXTRACT_OUTPUTS_DIR, get_file_name(repo_dir), f"{extract_level}_{commit_id}.jsonl2")
    if is_path_exist(path_to_save_commit_infos):
        with open(path_to_save_commit_infos) as f:
            commit_infos = json.load(f)
            check = False
            for cm_if in commit_infos:
                if len(cm_if[-1]) > 0:
                    check = True
            if not check:
                if VTCS_DICT[commit_id+fx_id] or len(VTCS_DICT[commit_id+fx_id]) <= 0:
                    unlink(path_to_save_commit_infos)
                    write_file(path_to_save_commit_infos, "[]")
                    return list()
                print(VTCS_DICT[commit_id+fx_id])
                vtc_if = VTCS_DICT[commit_id+fx_id][0]
                vtc_id = vtc_if["commit_hash"]
                VTCS_DICT[vtc_id+fx_id] = VTCS_DICT[commit_id+fx_id]
                blames_vtc = vtc_if["vulnerable_changes"]
                repo_name = get_file_name(repo_dir)
                if vtc_id in grouped_commits_by_repo[repo_name].keys():
                    grouped_commits_by_repo[repo_name][vtc_id] = (fx_id,merge_dict(
                        blames_vtc, grouped_commits_by_repo[repo_name][vtc_id][1]))
                else:
                    grouped_commits_by_repo[repo_name][vtc_id] = (fx_id,blames_vtc)
                print("Re get data:" +vtc_id)
                return get_commit_data(repo_dir, vtc_id, extract_level,fx_id,grouped_commits_by_repo[repo_name][vtc_id][1])
            else:
                print("Check okie")
            return commit_infos
    ce = CommitExtractor(repo_dir=repo_dir, commit_id=commit_id)
    if len(ce.modifies) >= MAX_CHANGE:
        print("Ignore")
        if VTCS_DICT[commit_id+fx_id] or len(VTCS_DICT[commit_id+fx_id]) <= 0:
            write_file(path_to_save_commit_infos, "[]")
            return list()
        print(VTCS_DICT[commit_id+fx_id])
        vtc_if = VTCS_DICT[commit_id+fx_id][0]
        vtc_id = vtc_if["commit_hash"]
        VTCS_DICT[vtc_id+fx_id] = VTCS_DICT[commit_id+fx_id]
        blames_vtc = vtc_if["vulnerable_changes"]
        repo_name = get_file_name(repo_dir)
        if vtc_id in grouped_commits_by_repo[repo_name].keys():
            grouped_commits_by_repo[repo_name][vtc_id] = (fx_id,merge_dict(
                blames_vtc, grouped_commits_by_repo[repo_name][vtc_id][1]))
        else:
            grouped_commits_by_repo[repo_name][vtc_id] = (fx_id,blames_vtc)
        print("Re get data:" +vtc_id)
        return get_commit_data(repo_dir, vtc_id, extract_level,fx_id,grouped_commits_by_repo[repo_name][vtc_id][1])
    commit_infos = list()
    count = 0
    check = False
    for me in ce.modifies:
        lines_bl = list()
        if blame is not None and me.new_path in blame.keys():
            lines_bl = blame[me.new_path]
        functions = set(
            [*me.modified_deleted_in_function] + [*me.modified_add_in_function])
        for idx, func in enumerate(functions):
            line_bl = list()
            function_after = None
            function_before = None
            added = None
            deleted = None
            start_end_after = None
            start_end_before = None
            if func in me.modified_add_in_function:
                func_after_info = me.modified_add_in_function[func]
                added = func_after_info["line"]
                added_line = [int(float(el)) for el in added.split(",")]
                function_after = func_after_info["raw"]
                start_at = func_after_info["start_function"]
                end_at = func_after_info["end_function"]
                start_end_after = f'{start_at},{end_at}'
                for ll in lines_bl:
                    if ll >= start_at and ll <= end_at and ll - start_at in added_line:
                        line_bl.append(str(ll - start_at))
                        check = True
            elif func in me.function_after_map:
                function_after = "\n".join(me.function_after_map[func])
            if func in me.modified_deleted_in_function:
                func_delete_info = me.modified_deleted_in_function[func]
                deleted = me.modified_deleted_in_function[func]["line"]
                function_before = me.modified_deleted_in_function[func]["raw"]
                start_end_before = f'{func_delete_info["start_function"]},{func_delete_info["end_function"]}'
            elif func in me.function_before_map:
                function_before = "\n".join(me.function_before_map[func])
            
            commit_infos.append([commit_id, count, function_before, function_after, deleted,
                                added, me.new_path, start_end_before, start_end_after, ','.join(line_bl)])
            count += 1
    if not check:
        if VTCS_DICT[commit_id+fx_id] or len(VTCS_DICT[commit_id+fx_id]) <= 0:
            write_file(path_to_save_commit_infos, "[]")
            return list()
        print(VTCS_DICT[commit_id+fx_id])
        vtc_if = VTCS_DICT[commit_id+fx_id][0]
        vtc_id = vtc_if["commit_hash"]
        VTCS_DICT[vtc_id+fx_id] = VTCS_DICT[commit_id+fx_id]
        blames_vtc = vtc_if["vulnerable_changes"]
        repo_name = get_file_name(repo_dir)
        if vtc_id in grouped_commits_by_repo[repo_name].keys():
            grouped_commits_by_repo[repo_name][vtc_id] = (fx_id,merge_dict(
                blames_vtc, grouped_commits_by_repo[repo_name][vtc_id][1]))
        else:
            grouped_commits_by_repo[repo_name][vtc_id] = (fx_id,blames_vtc)
        print("Re get data:" +vtc_id)
        return get_commit_data(repo_dir, vtc_id, extract_level,fx_id,grouped_commits_by_repo[repo_name][vtc_id][1])
    write_file(path_to_save_commit_infos, json.dumps(commit_infos))
    return commit_infos


def extract_info(repo_dir, commit_dicts):
    commit_ids = list(commit_dicts.keys())
    data = list()
    logger.info(f"extract {repo_dir} : {len(commit_ids)}")
    for commit_id in commit_ids:
        commit_infos = get_commit_data(
            repo_dir, commit_id, extract_level, commit_dicts[commit_id][0], commit_dicts[commit_id][1])
        if len(commit_infos) == 0:
            logger.warning(f"faild to extracted commit: {commit_id}")
        data.extend(commit_infos)
    df_full_information = pd.DataFrame(data, columns=["commit_id", "count", "function_before", "function_after", "deleted","added", "me.new_path", "start_end_before", "start_end_after", "line_bl"])
    return df_full_information


def merge_extracted():
    dfs = list()
    for csv_file in find_all_files_by_wildcard(PROJECT_EXTRACT_OUTPUTS_DIR, f"*_{extract_level}_{extract_type}.csv"):
        df_tmp = pd.read_csv(csv_file)
        dfs.append(df_tmp)
    df = pd.concat(dfs)
    df.to_csv(PATH_TO_SAVE_CSV[extract_type])


if __name__ == "__main__":
    main()
    # merge_extracted()
