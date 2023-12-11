from fikl.proto import config_pb2

import networkx as nx


def create_graph(config: config_pb2.Config) -> nx.DiGraph:
    """
    Create a directed acyclic graph from a config.
    """
    G = nx.DiGraph()

    # add first level nodes, which are the measures
    for measure in config.measures:
        # ensure the measure is not already in the graph
        if measure.name in G.nodes:
            raise ValueError(f"Measure {measure.name} already in graph")
        G.add_node(measure.source)
        G.add_node(measure.name)
        G.add_edge(measure.source, measure.name)

    # all nodes for all metrics before adding edges
    for metric in config.metrics:
        # ensure the metric is not already in the graph
        if metric.name in G.nodes:
            raise ValueError(f"Metric {metric.name} already in graph")
        G.add_node(metric.name)

    # go back and add edges for each metric's factors
    for metric in config.metrics:
        for factor in metric.factors:
            # ensure the factor exists in the graph
            if factor.name not in G.nodes:
                raise ValueError(f"Factor {factor.name} not in graph")
            G.add_edge(factor.name, metric.name, weight=factor.weight)

    # make sure graph is a DAG
    if not nx.is_directed_acyclic_graph(G):
        # explain why it's not a DAG
        cycles = nx.find_cycle(G)
        raise ValueError(f"Graph is not a DAG. Cycles:\n{cycles}")

    return G
