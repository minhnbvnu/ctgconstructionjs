import pandas
import json
from CTG.parse_joern import get_node_edges
from CTG.Joern_Node import *


def print_stmt(stmt_nodes, edges):
    #print(stmt_nodes.columns)
    sentence = ""
    for i, n in stmt_nodes.iterrows():
        #print(n)
        tmp = NODE(stmt_nodes.at[i, "id"], stmt_nodes.at[i, "_label"], stmt_nodes.at[i, "code"],
                   stmt_nodes.at[i, "name"])
        sentence += tmp.print_node()
    return sentence


if __name__ == '__main__':
    _skiprows = 0
    vocabulary_file_path = "Data/word2vec.vocabulary.txt"
    vocab_f = open(vocabulary_file_path, "a")

  
    while(_skiprows <= 8000):
        print("_skiprows:", _skiprows)
        df = pandas.read_csv('Data/JIT_DATASET/CTG/vtc_ctg_n.csv', skiprows = _skiprows, nrows = 1000)
        df.columns = ['commit_id', 'nodes', 'edges', 'vul_lines']
        #print(df.columns)
        separate_token = "="*100

        for idx, row in df.iterrows():
        
            sub_graph_nodes = df.at[idx, "nodes"].split(separate_token)
            sub_graph_edges = df.at[idx, "edges"].split(separate_token)

            for sub_graph_idx in range(0, len(sub_graph_nodes)):
                try:
                  node_content = sub_graph_nodes[sub_graph_idx].split("_____")[1]
                  edge_content = sub_graph_edges[sub_graph_idx].split("_____")[1]
            
                  nodes, edges = get_node_edges(edge_content, node_content)

                  lineNumbers = nodes.lineNumber.unique()
                  func_code = ""
                  for x in lineNumbers:
                      if x != "":
                          stmt_nodes = nodes[nodes["lineNumber"] == x]
                          func_code += print_stmt(stmt_nodes, edges) + " "
                  vocab_f.write(func_code + "\n")
                except:
                 print("exception: ", df.at[idx, "commit_id"] )
        _skiprows += 1000
        
