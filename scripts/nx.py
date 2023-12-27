import os
import sys
import enum

import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.pyplot as plt
import seaborn as sns

from fikl.config import load_yaml
from fikl.proto import config_pb2
from fikl.graph import create_graph

yaml_paths = sys.argv[1:]
print(f"Loading config from {yaml_paths}")
config = load_yaml(*yaml_paths)


# class NodeT(enum.Enum):
#     SOURCE = enum.auto()
#     MEASURE = enum.auto()
#     METRIC = enum.auto()


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
