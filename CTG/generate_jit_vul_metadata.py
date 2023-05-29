import json
import logging
import math
from collections import defaultdict
from datetime import datetime
from statistics import mean
import random
import pandas as pd
from dateutil.relativedelta import relativedelta
from pydriller import Repository

from config import (JIT_VUL_DATA_DIR, JIT_VUL_METADATA_COMMIT_FILE_PATH,
                    MAX_CHANGE, METADATA_EXTRACT_OUTPUTS_DIR,
                    PROJECT_EXTRACT_OUTPUTS_DIR)
from file_manager import (find_all_files_by_wildcard, get_cloned_repository,
                          get_file_name, is_path_exist, join_path, lock_dir,
                          unlink, write_file)
from helpers import get_logger, subprocess_cmd
from pyszz.extract.commit_extractor import CommitExtractor

logger = get_logger(__name__)

JIT_VUL_CONTRIBUTING_COMMIT_DATA_FILE = "vul_contributing_commit_data.jsonl.1667660526"
JIT_VUL_CONTRIBUTING_COMMIT_DATA_PATH = join_path(
    JIT_VUL_DATA_DIR, JIT_VUL_CONTRIBUTING_COMMIT_DATA_FILE)

etype = "all2"
NUM_WORKER = 32
MAX_PRE_CM = 10000


CACHE_REPO = dict()


def main():
    grouped_commits_by_repo = defaultdict(
        lambda: set())
    with open(JIT_VUL_CONTRIBUTING_COMMIT_DATA_PATH) as fp:
        for line in fp.readlines():
            data = json.loads(line)
            with open("vtc_ctg.csv.txt") as f:
                vtcs = [line.strip() for line in f.readlines()]
            with open("fc_ctg.csv.txt") as f:
                fcs = [line.strip() for line in f.readlines()]
            fixing_commit_id = data["fixing_commit"]["commit_hash"]
            vtc_id = data["vulnerability_contributing_commits"][0]["commit_hash"]
            if fixing_commit_id in fcs:
                grouped_commits_by_repo[data["repo_name"]].add(fixing_commit_id)
            if vtc_id in vtcs:
                grouped_commits_by_repo[data["repo_name"]].add(vtc_id)
    for repo_name, list_commit_ids in grouped_commits_by_repo.items():
        repo_dir = get_cloned_repository(repo_name)
        try:
            lock_dir(repo_dir)
        except BlockingIOError as e:
            continue
        df_extracted_data = extract_info(
            repo_dir, set(list_commit_ids))
        if df_extracted_data is None:
            continue
        path_to_save_csv = join_path(
            PROJECT_EXTRACT_OUTPUTS_DIR, f"{repo_name}_{etype}_metadata.csv")
        df_extracted_data.to_csv(path_to_save_csv, index=False)


def calc_fix(msg):
    partern = ["fix", "bug", "defect", "patch"]
    for pt in partern:
        if pt in msg:
            return 1
    return 0

def get_subs_dire_name(fileDirs):
    if fileDirs is None:
        return None, None, None
    fileDirs = fileDirs.split("/")
    if (len(fileDirs) == 1):
        subsystem = "root"
        directory = "root"
    else:
        subsystem = fileDirs[0]
        directory = "/".join(fileDirs[0:-1])
    file_name = fileDirs[-1]
    return subsystem, directory, file_name

import re
def get_repo_file(repo_dir, commit_id, file_path, from_date, to_date=None, loop=0):
    if file_path is None:
        logger.error(f"get file none? commit: {commit_id}")
        return None
    cmd = f"cd {repo_dir} && git --no-pager log --full-history {file_path}"
    results = list()
    if cmd in CACHE_REPO.keys():
        result = CACHE_REPO[cmd]
        for cm_if in result:
            if cm_if["committer_date"] < to_date and cm_if["committer_date"] > from_date:
                results.append(cm_if)
        return results
    else:
        rs = subprocess_cmd(cmd)
        if rs[1] != "":
            logger.error(f"error when get file: {file_path}, err: {rs[1]}")
            cmd0 = f"cd {repo_dir} && git reset --hard {commit_id}"
            ss = subprocess_cmd(cmd0)
            logger.error(ss)
            if loop > 2:
                print("loop")
                return None
            ress = get_repo_file(repo_dir, commit_id, file_path,
                                 from_date, to_date, loop+1)
            if ress is None:
                return None
            return ress
        cms = list()
        index = 0
        for line in rs[0].splitlines():
            index += 1
            if line.startswith("commit"):
                commit = line[7:]
                assert len(commit) == 40
            elif line.startswith("Author"):
                author = re.findall("<(.*)>",line)[0]
            elif line.startswith("Date"):
                date = line[8:].strip()
                dt = datetime.strptime(date, '%a %b %d %H:%M:%S %Y %z')
                cms.append({"hash":commit,"committer_date":dt,"author":author})
        if len(cms) > MAX_PRE_CM:
            cms2 = random.sample(cms, MAX_PRE_CM)
        else:
            cms2 = cms
        CACHE_REPO[cmd] = cms2
        for cm_info in cms2:
            if cm_info["committer_date"] < to_date and cm_info["committer_date"] > from_date:
                results.append(cm_info)

    return results

def get_repo_author(repo_dir, author, from_date, to_date=None):
    cmd = f'cd {repo_dir} && git --no-pager log --author="{author}"'
    results = list()
    if cmd in CACHE_REPO.keys():
        result = CACHE_REPO[cmd]
        for commit in result.traverse_commits():
            if commit.committer_date < to_date and commit.committer_date > from_date:
                results.append(commit)
        return results
    else:
        rs = subprocess_cmd(cmd)
        if rs[1] != "":
            logger.error(
                f"Error when get diff. command: {cmd[100:]}, err: {rs[1]}")
            return None
        cms = list()
        index = 0
        for line in rs[0].splitlines():
            index += 1
            if line.startswith("commit"):
                commit = line[7:]
                cms.append(commit)
                assert len(commit) == 40
    c = 0
    while len(results) <= 0:
        if len(cms) > MAX_PRE_CM:
            cms2 = random.sample(cms, MAX_PRE_CM)
        else:
            cms2 = cms
        result = Repository(repo_dir, only_commits=cms2,
                            num_workers=NUM_WORKER)
        CACHE_REPO[cmd] = result
        for commit in result.traverse_commits():
            if commit.committer_date < to_date and commit.committer_date > from_date:
                results.append(commit)
        c += 1
        if c > 50:
            return results
    return results

def extract_info(repo_dir, commit_ids):
    data = list()
    for commit_id in commit_ids:
        path_to_save_commit_infos = join_path(
            METADATA_EXTRACT_OUTPUTS_DIR, get_file_name(repo_dir), f"{commit_id}.jsonl")
        if is_path_exist(path_to_save_commit_infos):
            with open(path_to_save_commit_infos) as f:
                commit_info = json.load(f)
                # parser change 
                data.append(commit_info)
                
                continue
        logger.info(f"extract metadata: {commit_id}")
        logging.getLogger().setLevel(logging.WARNING)

        commit_extractor = CommitExtractor(repo_dir, commit_id, False)
        modifiers  = [m.modified for m in commit_extractor.modifies]
        cm_message = commit_extractor.commit.msg
        LA = commit_extractor.commit.insertions
        LD = commit_extractor.commit.deletions
        LT = sum(
            [len(el.source_code_before.splitlines()) for el in modifiers if el.source_code_before is not None])
        
        commit_date = commit_extractor.commit.committer_date
        fix = calc_fix(cm_message)
        NSs = set()
        NDs = set()
        NFs = set()
        ENTROPY = 0
        NDEVs = set()
        NUCs = set()
        AGEs = set()
        rexp = 0
        sexps = set()
        exp = 0
        since = commit_date - relativedelta(days=(365.24*10))
        for mdf in modifiers:
            s, d, f = get_subs_dire_name(mdf.old_path)
            NSs.add(s)
            NDs.add(d)
            NFs.add(s)
            if mdf.nloc is not None and mdf.nloc != 0:
                en_tmp = (mdf.added_lines + mdf.deleted_lines)/(mdf.nloc *2)
                if en_tmp > 0:
                    ENTROPY -= (en_tmp * math.log(en_tmp, 2))
            file_path = mdf.old_path if mdf.old_path is not None else mdf.new_path
            rp_tmp_files = get_repo_file(
                repo_dir, commit_id, file_path, since, commit_date)
            if rp_tmp_files is None:
                continue
            last_cm = None
            last_time = since
            for tmp_cm in rp_tmp_files:
                NDEVs.add(tmp_cm["author"])
                if tmp_cm["hash"] == commit_id:
                    continue
                if tmp_cm["committer_date"] > last_time:
                    last_time = tmp_cm["committer_date"]
                    last_cm = tmp_cm
            if last_cm is None:
                continue
            NUCs.add(last_cm["hash"])
            tmp_date = (commit_date - last_cm["committer_date"])
            AGEs.add(tmp_date.days)
        NS = len(NSs)
        ND = len(NDs)
        NF = len(NFs)
        Entropy = ENTROPY
        NDEV = len(NDEVs)
        AGE = 0
        if len(AGEs) > 0:
            AGE = mean(AGEs)
        NUC = len(NUCs) if len(NUCs) > 0 else 1
        
        EXP = exp
        REXP = rexp
        SEXP = len(sexps)
        FIX = fix
        logging.getLogger().setLevel(logging.INFO)
        logger.info(
            f"NS: {NS}, ND: {ND}, NF: {NF}, ETP: {Entropy}, NDEV: {NDEV}, AGE: {AGE}, NUC: {NUC}, EXP: {EXP}, REXP: {REXP}, SEXP: {SEXP} ")
        commit_meta_data = [commit_id,LA, LD,LT,FIX, Entropy, NS, ND, NF, NDEV, AGE, NUC, EXP, REXP, SEXP]

        write_file(path_to_save_commit_infos, json.dumps(
            commit_meta_data, default=str))

        data.append(commit_meta_data)

    full_data_project = pd.DataFrame(data, columns=["commit_id", "LA","LD","LT","FIX","Entropy","NS","ND","NF","NDEV","AGE","NUC","EXP","REXP","SEXP"])
    return full_data_project


def merge_extracted():
    dfs = list()
    for csv_file in find_all_files_by_wildcard(PROJECT_EXTRACT_OUTPUTS_DIR, f"*_{etype}_metadata.csv"):
        df_tmp = pd.read_csv(csv_file, low_memory=False)
        dfs.append(df_tmp)
    df = pd.concat(dfs)
    df = df.drop_duplicates(subset=["commit_id"])
    df = df.reset_index()
    df.to_csv(JIT_VUL_METADATA_COMMIT_FILE_PATH, index=False)


if __name__ == "__main__":
    main()