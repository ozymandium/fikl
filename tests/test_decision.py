"""
Unit tests for fikl.decision.Decision, located in src/fikl/decision.py
"""
import unittest
import os

from fikl.decision import Decision

import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np


class TestBasic(unittest.TestCase):
    """Just run all the examples in the data folder and make sure they don't crash"""

    def test_basic(self) -> None:
        # get a list of all files in the data folder
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        files = os.listdir(data_dir)
        # each config and data file should have the same name
        configs = sorted([f for f in files if f.endswith(".yaml")])
        raws = sorted([f for f in files if f.endswith(".csv")])
        # make sure there are the same number of each
        self.assertEqual(len(configs), len(raws))
        self.assertEqual(len(configs), len(set(configs)))
        # run each one
        for config, raw in zip(configs, raws):
            config_path = os.path.join(data_dir, config)
            raw_path = os.path.join(data_dir, raw)
            decision = Decision(config_path=config_path, raw_path=raw_path)


class TestDecision(unittest.TestCase):
    CONFIG = os.path.join(os.path.dirname(__file__), "data", "simple.yaml")
    RAW = os.path.join(os.path.dirname(__file__), "data", "simple.csv")

    def setUp(self) -> None:
        self.decision = Decision(config_path=self.CONFIG, raw_path=self.RAW)

    def test_raw(self) -> None:
        expected = pd.read_csv(self.RAW, index_col="choice")
        # evaluate the expression column (power)
        expected["power"] = expected["power"].map(lambda x: eval(x))
        assert_frame_equal(self.decision.raw, expected)

    def test_scores(self) -> None:
        expected = pd.DataFrame(
            data=[
                ["one", 1.0, 0.2, 0.0, 0.2, 0.1],
                ["two", 0.75, 0.4, 0.25, 0.4, 0.2],
                ["three", 0.5, 0.6, 0.5, 0.4, 0.3],
                ["four", 0.25, 0.8, 0.75, 0.6, 0.4],
                ["five", 0.0, 1.0, 1.0, 0.6, 0.5],
            ],
            columns=["choice", "cost", "size", "looks", "economy", "power"],
        )
        expected = expected.set_index("choice")
        assert_frame_equal(self.decision.scores, expected)

    def test_weights(self) -> None:
        expected = pd.DataFrame(
            data=[
                [1.0 / 3.0, 1.0 / 3.0, 0.0, 1.0 / 3.0, 0.0],
                [0.0, 0.0, 0.5, 0.0, 0.5],
            ],
            columns=["cost", "size", "looks", "economy", "power"],
        )
        expected = expected.set_index(pd.Index(["smart", "fun"], dtype="object"))
        assert_frame_equal(self.decision.weights, expected)

    def test_results(self) -> None:
        expected = self.decision.scores.dot(self.decision.weights.T)
        assert_frame_equal(self.decision.results, expected)

    def test_getters(self) -> None:
        self.assertEqual(self.decision.choices(), ["one", "two", "three", "four", "five"])
        self.assertEqual(self.decision.metrics(), ["smart", "fun"])
        self.assertEqual(self.decision.factors(), ["cost", "size", "looks", "economy", "power"])
