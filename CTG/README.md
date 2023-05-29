# JIT-Vul Dataset for Just-In-Time Vulnerability Detection 

This repository provides the code for generating vulnerability-triggering commit dataset. To start, clone the repository and navigate to the root directory.

## Directory structure

```dir
(input/output)├── data
              │   ├── vul_commit_database       (INPUT files)
              |   ├── git_repository_data       (cloned Git repositories)
              │   ├── diff_output               (before-after commit line mapping dict)
              │   ├── joern_parsed_output       (Joern nodes & edges from source files)
              │   ├── dependency_output         (impact lines depend on added lines) 
              │   ├── jit_vul_dataset           (OUTPUT files)
(code/scripts)├── *.py
```

## Generate JIT-Vul dataset from scratch

### Required packages:
- Joern v1.1.1193
- srcML v1.0.0
- diff
- Python 3 dependencies from `./requirements.txt`

### Input preparation:
- INPUT FILE is formatted in CSV which contains fixing commit hashes of related Git repositories as shown in [filtered_c_lang__sampled_fixing_commits.csv](./data/vul_commit_database/filtered_c_lang__sampled_fixing_commits.csv)
- GIT REPOSITORIES (including `.git`) are cloned to `./data/git_repository_data/cloned_repositories`

### Run steps:
> **_Abstract Process :_**  From (a fixing commit) changes:
<br/> (1) filter **actual** added lines (by excluding modified lines) 
<br/> (2) find impact lines (in after-fixed code version) that have dependencies on these added lines
<br/> (3) map these impact lines to corresponding lines in before-fixed code version 
<br/> (4) blame **deleted lines** in fixing commits and **impact lines** in before-fixed version <br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&#8594; produce _a list of vulnerability-contributing commits_
<br/> (5) output  _a vulnerability-triggering commit_ as the latest commit in _the list of vulnerability-contributing commits_
 
**Step 1.** Configure working directories and runtime parameters in `./config.py`. Set `DEBUG=True` for using sample input [filtered_c_lang__sampled_fixing_commits.csv](./data/vul_commit_database/filtered_c_lang__sampled_fixing_commits.csv)  


**Step 2.** Parse surrounding lines have control/data dependencies from/to added lines in fixing commits (Step 1-3 in **Abstract Process**) 
 
```sh
$ python parse_impacted_dependency_lines.py
```

**Step 3.** Trace vulnerability-contributing commits (Step 4 in **Abstract Process**) 
 
```sh
$ python trace_jit_vul_contributing_commits.py
```

**Step 4.** Select a vulnerability-triggering commit and extract corresponding commit metadata & code (un)changes (Step 5 in **Abstract Process**) [NOT DONE YET]


```sh
$ python generate_jit_vul_triggering_commit_data.py 
```

**Step 5.** Extract the same information for clean commits and unlabelled commits [NOT DONE YET]


```sh
$ python generate_jit_clean_commit_data.py 
$ python generate_jit_unlabelled_commit_data.py 
```

## Data description

### Output of Step 3: List of (sorted-by-time) vulnerability-contributing commits 
(see [sample file](./data/jit_vul_dataset/vul_contributing_commit_data.jsonl.1667129895))
```json
{
    "repo_name": "ffmpeg___ffmpeg",
    "fixing_commit":
    {
        "commit_hash": "cdd5df8189ff1537f7abe8defe971f80602cc2d2",
        "commit_timestamp": 1378089143
    },
    "vulnerability_contributing_commits": [
    {
        "commit_hash": "7e350379f87e7f74420b4813170fe808e2313911",
        "commit_timestamp": 1362724638,
        "vulnerable_changes":
        {
            "libavfilter/vf_fps.c": [173, 211]
        }
    },
    {
        "commit_hash": "77a72d348519584bac1499210619ea38adead130",
        "commit_timestamp": 1351186964,
        "vulnerable_changes":
        {
            "libavfilter/vf_fps.c": [216, 217]
        }
    },
    {
        "commit_hash": "d4f89906e3b310609b636cf6071313ec557ec873",
        "commit_timestamp": 1342941245,
        "vulnerable_changes":
        {
            "libavfilter/vf_fps.c": [196]
        }
    },
    {
        "commit_hash": "54c5dd89e3125c1f363fe8f95d2837a796967c6e",
        "commit_timestamp": 1337362434,
        "vulnerable_changes":
        {
            "libavfilter/vf_fps.c": [170, 178, 192, 201, 220, 237]
        }
    }]
}
```

### Output of Step 4 & 5: Metadata & Code (un)changes of vul-triggering/vul-clean/vul-unlabelled commits
```json
[To be filled]
```
