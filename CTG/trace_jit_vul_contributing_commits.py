import json

import pandas as pd

from config import FIXING_COMMIT_FILE_PATH, C_FILE_EXTENSIONS, JIT_VUL_CONTRIBUTING_DATA_FILE_PATH
from file_manager import get_file_name, get_cloned_repository, get_file_name_with_parent
from helpers import get_logger, get_current_timestamp
from parse_impacted_dependency_lines import get_impacted_files_by_dependencies
from szz.v_szz import V_SZZ, merge_impacted_files

logger = get_logger(__name__)


def main():
    df = pd.read_csv(FIXING_COMMIT_FILE_PATH)
    grouped_commits_by_repo = df.groupby("project")["commit_id"].apply(list)
    out_file_path = f"{JIT_VUL_CONTRIBUTING_DATA_FILE_PATH}.{get_current_timestamp()}"
    with open(out_file_path, "w") as out_f:
        for repo_name, commit_ids in grouped_commits_by_repo.iteritems():
            repo_dir = get_cloned_repository(repo_name)
            # try:
            #     lock_dir(repo_dir)
            # except BlockingIOError as e:
            #     pass  # continue

            if repo_name == "chromium___chromium":
                continue

            run_szz(repo_dir, commit_ids, out_file=out_f)
            # break
    logger.info(f"Wrote vulnerability-contributing commit trace results "
                f"to file [{get_file_name_with_parent(out_file_path)}]")


def run_szz(repo_dir, commit_ids, out_file):
    repo_name = get_file_name(repo_dir)
    my_szz = V_SZZ(repo_name=repo_name, repo_dir=repo_dir)

    for commit_id in commit_ids:
        logger.info(f"[{repo_name}] Tracing vulnerability-contributing commits from [{commit_id}] fixing commits")
        deleted_lines_imp_files = my_szz.get_impacted_files(fix_commit_hash=commit_id,
                                                            file_ext_to_parse=C_FILE_EXTENSIONS,
                                                            only_deleted_lines=True)
        dep_added_lines_imp_files = get_impacted_files_by_dependencies(repo_name=repo_name,
                                                                       fixing_commit_hash=commit_id)
        if dep_added_lines_imp_files is None:
            continue
        imp_files = merge_impacted_files(deleted_lines_imp_files, dep_added_lines_imp_files)
        if len(imp_files) <= 0:
            continue
        bug_introducing_commits = my_szz.find_vcc(fix_commit_hash=commit_id,
                                                  impacted_files=imp_files,
                                                  ignore_revs_file_path=None)

        output_str = json.dumps({"repo_name": repo_name,
                                 "fixing_commit": {"commit_hash": commit_id,
                                                   "commit_timestamp": my_szz.get_commit(
                                                       commit_id).committed_date},
                                 "vulnerability_contributing_commits": bug_introducing_commits})
        out_file.write(f"{output_str}\n")


if __name__ == "__main__":
    main()
