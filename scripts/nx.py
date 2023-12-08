import os
import sys

import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.pyplot as plt
import seaborn as sns

from fikl.config import load_yaml
from fikl.proto import config_pb2

yaml_paths = sys.argv[1:]
print(f"Loading config from {yaml_paths}")
config = load_yaml(*yaml_paths)

G = nx.DiGraph()

# add first level nodes, which are the measures
for measure in config.measures:
    G.add_node(measure.source, type="source")
    G.add_node(measure.name, type="measure")
    G.add_edge(measure.source, measure.name, weight=1.0)
# all nodes for all metrics before adding edges
for metric in config.metrics:
    G.add_node(metric.name, type="metric")
# go back and add edges for each metric's factors
for metric in config.metrics:
    for factor in metric.factors:
        G.add_edge(factor.name, metric.name, weight=factor.weight)

# make sure graph is a dag
assert nx.is_directed_acyclic_graph(G)

# draw graph
plt.figure()
pos = graphviz_layout(G, prog="dot", args="-Grankdir=LR")

# Draw the graph
nx.draw(G, pos, with_labels=True, arrows=True)

sns.set_theme()
sns.set_style("darkgrid")

plt.show()
