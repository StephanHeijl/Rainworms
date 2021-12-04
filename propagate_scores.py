import pandas
import networkx as nx


def get_out_nodes(node, G):
    return [list(edge)[1] for edge in G.out_edges(node)]


def propagate_scores(graph):
    """ Propagate scores from the leaves to the root of the graph. """
    # Calculate the distances from the root for each node
    node_ranks = next(nx.all_pairs_shortest_path_length(graph))[1]
    node_ranks_sorted = sorted(node_ranks.items(), key=lambda k: int(str(k[0]).split(".")[0]))

    df = pandas.DataFrame({"node": list(graph.nodes), "rank": [r for n, r in node_ranks_sorted]})
    max_rank = df["rank"].max()

    # We can ignore the last rank because these are by definition leaves
    for rank in list(range(0, max_rank))[::-1]:
        nodes_of_rank = df.loc[df["rank"] == rank]
        for node in nodes_of_rank.node:
            out_nodes = get_out_nodes(node, graph)
            for out_node in out_nodes:
                try:
                    graph.nodes[node]["score"] += graph.nodes[out_node].get("score", 0) / len(out_nodes)
                except KeyError:
                    graph.nodes[node]["score"] = graph.nodes[out_node].get("score", 0) / len(out_nodes)

    return graph
