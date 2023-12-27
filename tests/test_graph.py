"""
Unit tests for fikl.graph module, located in src/fikl/graph.py
"""
import unittest
import os

import fikl.config
import fikl.graph


class TestCreateGraph(unittest.TestCase):
    CONFIG_PATHS = [
        os.path.join(os.path.dirname(__file__), "data", "simple", "simple.yaml"),
        os.path.join(os.path.dirname(__file__), "data", "simple", "factors.yaml"),
    ]

    def setUp(self) -> None:
        self.maxDiff = None
        self.graph = fikl.graph.create_graph(fikl.config.load_yaml(*self.CONFIG_PATHS))

    def test_create_graph(self) -> None:

        self.assertEqual(
            set(self.graph.nodes),
            {
                "cost",
                "size",
                "looks",
                "economy",
                "power",
                "Cost",
                "Size",
                "Looks",
                "Economy",
                "Power",
                "smart",
                "fun",
                "final",
            },
        )

        self.assertEqual(
            set(self.graph.edges),
            {
                ("cost", "Cost"),
                ("size", "Size"),
                ("looks", "Looks"),
                ("economy", "Economy"),
                ("power", "Power"),
                ("Cost", "smart"),
                ("Size", "smart"),
                ("Economy", "smart"),
                ("Power", "fun"),
                ("Looks", "fun"),
                ("smart", "final"),
                ("fun", "final"),
            },
        )

    # TODO: test failure cases
