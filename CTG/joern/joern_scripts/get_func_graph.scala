@main def exec(filepath: String, outputDir: String, workspaceName: String) = {
   importCode.javascript(filepath, workspaceName)
   run.ossdataflow
   val fileName = filepath.split("/").last.toString()
   println(fileName)
   cpg.graph.E.filter(node=>node.label=="CDG" || node.label == "REACHING_DEF").map(node=>List(node.inNode.id, node.outNode.id, node.label, node.propertiesMap.get("VARIABLE"))).toJson |> outputDir + "/" + fileName + ".edges.json"
   cpg.graph.V.map(node=>node).toJson |> outputDir + "/" + fileName + ".nodes.json"
}
