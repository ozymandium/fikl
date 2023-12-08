import os
import sys
import enum

import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.pyplot as plt
import seaborn as sns

from fikl.config import load_yaml
from fikl.proto import config_pb2

yaml_paths = sys.argv[1:]
print(f"Loading config from {yaml_paths}")
config = load_yaml(*yaml_paths)


class NodeT(enum.Enum):
    SOURCE = enum.auto()
    MEASURE = enum.auto()
    METRIC = enum.auto()

class SourceNodeT(enum.Enum):
    RAW = enum.auto()
    FETCH = enum.auto()

class MetricNodeT(enum.Enum):
    INTERMED = enum.auto()
    FINAL = enum.auto()

def create_graph(config: config_pb2.Config) -> nx.DiGraph:
    """
    Create a directed acyclic graph from a config.
    """
    G = nx.DiGraph()

    # add first level nodes, which are the measures
    for measure in config.measures:
        G.add_node(measure.source, type=NodeT.SOURCE)
        G.add_node(measure.name, type=NodeT.MEASURE)
        G.add_edge(measure.source, measure.name)

    # all nodes for all metrics before adding edges
    for metric in config.metrics:
        # is_final = config.final == metric.name
        G.add_node(metric.name, type=NodeT.METRIC)

    # go back and add edges for each metric's factors
    for metric in config.metrics:
        for factor in metric.factors:
            G.add_edge(factor.name, metric.name, weight=factor.weight)

    # make sure graph is a DAG
    if not nx.is_directed_acyclic_graph(G):
        # explain why it's not a DAG
        cycles = nx.find_cycle(G)
        raise ValueError(f"Graph is not a DAG. Cycles:\n{cycles}")

    return G

def plot_graph(G: nx.DiGraph) -> plt.Figure:
    """
    Plot a graph using networkx and matplotlib.
    """
    fig = plt.figure()
    pos = graphviz_layout(G, prog="dot", args="-Grankdir=LR")

    # Draw the graph
    nx.draw(G, pos, with_labels=True, arrows=True)

    sns.set_theme()
    sns.set_style("darkgrid")

    return plt.gcf()

G = create_graph(config)
order = list(nx.topological_sort(G))
print(f"Topological sort: \n{order}")
fig = plot_graph(G)
plt.show()
