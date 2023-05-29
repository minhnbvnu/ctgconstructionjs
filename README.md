# CTGConstruction

## Raw data

## CTGs after merging the graph of the versions before and after the commit

<a href="https://drive.google.com/file/d/1-2ezW8Hc9VOtalbaCx9i0N0BLzVXxAN5/view?usp=share_link">VTC</a>

<a href="https://drive.google.com/file/d/1QgLrB-0yEexOBzf8gUao02NDabahaO-y/view?usp=share_link">VFC</a>

## CTGs after trimming elements which are unrelated to the changed

<a href="https://drive.google.com/drive/folders/15C0WjoIq9DtNQpCgHRiESngOO8CJuZOW?usp=sharing"> VTC </a>

<a href="https://drive.google.com/drive/folders/1hFpVj11u_BJjVECqtgxrMRvj5-X46laZ?usp=sharing"> VFC </a>

Description: <a href="https://docs.google.com/spreadsheets/d/1shNpnsnqTv2B2aYwZAx6z7Bxi76W-Nzma1pRWiyztjo">Link</a>

## Instruction to construct CTGs

## Instruction to trim unrelated elements

In order to trim CTGs, execute the following command, in which:

--data_file_path: is the path of the the data file

--graph_dir: is the directory where the trimmed graph will be saved


```
 python3 Main_Trim_CTG.py --data_file_path="Data/example.csv" --graph_dir="Data/Graph"
```
