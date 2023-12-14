"""
Unit tests for fikl.decision.Decision, located in src/fikl/decision.py
"""
import unittest
import os
import yaml
import pprint

import fikl.decision
import fikl.config
import fikl.scorers
import fikl.graph

import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
import numpy as np
import networkx as nx


class TestDecision(unittest.TestCase):
    """Tests fikl.decision.DecisionBase"""

    def setUp(self) -> None:
        self.maxDiff = None
        self.config = fikl.config.load_yaml(
            os.path.join(os.path.dirname(__file__), "data", "simple", "simple.yaml"),
            os.path.join(os.path.dirname(__file__), "data", "simple", "factors.yaml"),
        )
        self.raw_path = os.path.join(os.path.dirname(__file__), "data", "simple", "simple.csv")
        self.expected_choices = pd.Index(
            ["one", "two", "three", "four", "five"], dtype="object", name="choice"
        )

    def test_get_source_data(self) -> None:
        """Tests fikl.decision._get_source_data"""
        source_data = fikl.decision._get_source_data(self.config, self.raw_path)
        expected = pd.DataFrame(
            data=[
                [1.0, 1.0, 1, 1.0, 1.0],
                [2.0, 2.0, 2, 2.0, 2.0],
                [3.0, 3.0, 3, 3.0, 3.0],
                [4.0, 4.0, 4, 4.0, 4.0],
                [5.0, 5.0, 5, 5.0, 5.0],
            ],
            columns=["cost", "size", "looks", "economy", "power"],
            index=self.expected_choices,
        )
        # sort the columns in expected alphabetically
        expected = expected.sort_index(axis=1)
        assert_frame_equal(source_data, expected)

    def test_get_measure_data(self) -> None:
        """Tests fikl.decision._get_measure_data"""
        source_data = fikl.decision._get_source_data(self.config, self.raw_path)
        scorer_info = fikl.scorers.get_scorer_info_from_config(self.config)
        measure_data = fikl.decision._get_measure_data(source_data, scorer_info)
        expected = pd.DataFrame(
            data=[
                [1.0, 0.2, 0.0, 0.2, 0.1],
                [0.75, 0.4, 0.25, 0.4, 0.2],
                [0.5, 0.6, 0.5, 0.4, 0.3],
                [0.25, 0.8, 0.75, 0.6, 0.4],
                [0.0, 1.0, 1.0, 0.6, 0.5],
            ],
            columns=["Cost", "Size", "Looks", "Economy", "Power"],
            index=self.expected_choices,
        )
        assert_frame_equal(measure_data, expected)

    def test_get_weights(self) -> None:
        """Tests fikl.decision._get_weights"""
        weights = fikl.decision._get_weights(self.config)
        expected = pd.DataFrame(
            data=[
                [1.0 / 3.0, 1.0 / 3.0, 0.0, 1.0 / 3.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.5, 0.0, 0.5, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.67, 0.33, 0.0],
            ],
            columns=["Cost", "Size", "Looks", "Economy", "Power", "smart", "fun", "final"],
            index=pd.Index(["smart", "fun", "final"], dtype="object", name="metric"),
        )
        assert_frame_equal(weights, expected)

    def test_get_metric_results(self) -> None:
        """Tests fikl.decision._get_metric_results"""
        source_data = fikl.decision._get_source_data(self.config, self.raw_path)
        scorer_info = fikl.scorers.get_scorer_info_from_config(self.config)
        measure_data = fikl.decision._get_measure_data(source_data, scorer_info)
        weights = fikl.decision._get_weights(self.config)
        metric_eval_order = list(nx.topological_sort(fikl.graph.create_graph(self.config)))
        metric_results = fikl.decision._get_metric_results(measure_data, weights, metric_eval_order)
        expected = pd.DataFrame(
            data=[
                [0.4666666666666667, 0.05, 0.32916666666666666],
                [0.5166666666666667, 0.225, 0.4204166666666667],
                [0.5, 0.4, 0.467],
                [0.55, 0.575, 0.55825],
                [0.5333333333333333, 0.75, 0.6048333333333333],
            ],
            columns=["smart", "fun", "final"],
            index=self.expected_choices,
        )
        assert_frame_equal(metric_results, expected)

    def test_final(self) -> None:
        """Tests fikl.decision.final"""
        decision = fikl.decision.Decision(self.config, self.raw_path)
        expected = pd.DataFrame(
            data=[0.32916666666666666, 0.4204166666666667, 0.467, 0.55825, 0.6048333333333333],
            index=self.expected_choices,
            columns=["final"],
        )
        assert_frame_equal(decision.final_table(), expected)
        assert_frame_equal(
            decision.final_table(sort=True), expected.sort_values(by="final", ascending=False)
        )

    def test_answer(self) -> None:
        """Tests fikl.decision.answer"""
        decision = fikl.decision.Decision(self.config, self.raw_path)
        expected = "five"
        self.assertEqual(type(decision.answer()), str)
        self.assertEqual(decision.answer(), expected)

    def test_scorer_info_source_order(self) -> None:
        decision = fikl.decision.Decision(self.config, self.raw_path)
        self.assertEqual([entry.source for entry in decision.scorer_info], decision.sources())

    def test_scorer_info_measure_order(self) -> None:
        decision = fikl.decision.Decision(self.config, self.raw_path)
        self.assertEqual([entry.measure for entry in decision.scorer_info], decision.measures())

    def test_metric_print_order(self) -> None:
        decision = fikl.decision.Decision(self.config, self.raw_path)
        self.assertEqual(decision.metric_print_order(), [2, 1, 0])

    def test_get_metric_weight_tables(self) -> None:
        """Tests fikl.Decision.metric_weight_tables"""
        decision = fikl.decision.Decision(self.config, self.raw_path)
        expected = [
            pd.Series(
                data=[1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0],
                index=["Cost", "Size", "Economy"],
                name="smart",
            ),
            pd.Series(
                data=[0.5, 0.5],
                index=["Looks", "Power"],
                name="fun",
            ),
            pd.Series(
                data=[0.67, 0.33],
                index=["smart", "fun"],
                name="final",
            ),
        ]
        result = decision.metrics_weight_tables()
        self.assertEqual(len(result), len(expected))
        for i in range(len(result)):
            assert_series_equal(result[i], expected[i])
