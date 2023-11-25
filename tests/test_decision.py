"""
Unit tests for fikl.decision.Decision, located in src/fikl/decision.py
"""
import unittest
import os
import yaml

from fikl.decision import Decision
import fikl.scorers

import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np


class TestDecision(unittest.TestCase):
    CONFIG = os.path.join(os.path.dirname(__file__), "data", "simple.yaml")
    RAW = os.path.join(os.path.dirname(__file__), "data", "simple.csv")

    def test_get_scorers(self) -> None:
        self.maxDiff = None
        with open(self.CONFIG, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        result = Decision._get_scorers(config)
        expected = {
            "smart": {
                "cost": fikl.scorers.Relative(invert=True),
                "size": fikl.scorers.Interpolate(
                    knots=[
                        {"in": 0.0, "out": 0.0},
                        {"in": 5.0, "out": 1.0},
                        {"in": 10.0, "out": 0.0},
                    ]
                ),
                "economy": fikl.scorers.Bucket(
                    buckets=[
                        {"min": 0.0, "max": 2.0, "val": 0.2},
                        {"min": 2.0, "max": 4.0, "val": 0.4},
                        {"min": 4.0, "max": 6.0, "val": 0.6},
                        {"min": 6.0, "max": 8.0, "val": 0.8},
                        {"min": 8.0, "max": 10.0, "val": 1.0},
                    ]
                ),
            },
            "fun": {
                "looks": fikl.scorers.Star(min=1, max=5),
                "power": fikl.scorers.Range(best=10.0, worst=0.0),
            },
        }
        self.assertEqual(result.keys(), expected.keys())
        for key in result.keys():
            self.assertEqual(result[key].keys(), expected[key].keys())
            for subkey in result[key].keys():
                self.assertEqual(result[key][subkey], expected[key][subkey])

    def test_get_raw(self) -> None:
        with open(self.CONFIG, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        result = Decision._get_raw(config, self.RAW, Decision._get_scorers(config))
        expected = pd.DataFrame(
            data=[
                ["one", 1.0, 1.0, 1, 1.0, 1.0],
                ["two", 2.0, 2.0, 2, 2.0, 2.0],
                ["three", 3.0, 3.0, 3, 3.0, 3.0],
                ["four", 4.0, 4.0, 4, 4.0, 4.0],
                ["five", 5.0, 5.0, 5, 5.0, 5.0],
            ],
            columns=["choice", "cost", "size", "looks", "economy", "power"],
        )
        expected = expected.set_index("choice")
        assert_frame_equal(result, expected)

    def test_get_scores(self) -> None:
        with open(self.CONFIG, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        raw = Decision._get_raw(config, self.RAW, Decision._get_scorers(config))
        scorers = Decision._get_scorers(config)
        result = Decision._get_scores(raw, scorers)
        expected = {
            "smart": pd.DataFrame(
                data=[
                    ["one", 1.0, 0.2, 0.0, 0.2, 0.0],
                    ["two", 0.75, 0.4, 0.0, 0.4, 0.0],
                    ["three", 0.5, 0.6, 0.0, 0.4, 0.0],
                    ["four", 0.25, 0.8, 0.0, 0.6, 0.0],
                    ["five", 0.0, 1.0, 0.0, 0.6, 0.0],
                ],
                columns=["choice", "cost", "size", "looks", "economy", "power"],
            ),
            "fun": pd.DataFrame(
                data=[
                    ["one", 0.0, 0.0, 0.0, 0.0, 0.1],
                    ["two", 0.0, 0.0, 0.25, 0.0, 0.2],
                    ["three", 0.0, 0.0, 0.5, 0.0, 0.3],
                    ["four", 0.0, 0.0, 0.75, 0.0, 0.4],
                    ["five", 0.0, 0.0, 1.0, 0.0, 0.5],
                ],
                columns=["choice", "cost", "size", "looks", "economy", "power"],
            ),
        }
        expected["smart"] = expected["smart"].set_index("choice")
        expected["fun"] = expected["fun"].set_index("choice")
        self.assertEqual(result.keys(), expected.keys())
        for key in result.keys():
            assert_frame_equal(result[key], expected[key], check_exact=False)

    def test_get_weights(self) -> None:
        with open(self.CONFIG, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        raw = Decision._get_raw(config, self.RAW, Decision._get_scorers(config))
        scores = Decision._get_scores(
            raw,
            Decision._get_scorers(config),
        )
        result = Decision._get_weights(config, raw)
        expected = pd.DataFrame(
            data=[
                [1.0 / 3.0, 1.0 / 3.0, 0.0, 1.0 / 3.0, 0.0],
                [0.0, 0.0, 0.5, 0.0, 0.5],
            ],
            columns=["cost", "size", "looks", "economy", "power"],
        )
        expected = expected.set_index(pd.Index(["smart", "fun"], dtype="object"))
        assert_frame_equal(result, expected)

    def test_get_results(self) -> None:
        with open(self.CONFIG, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        raw = Decision._get_raw(config, self.RAW, Decision._get_scorers(config))
        scores = Decision._get_scores(
            raw,
            Decision._get_scorers(config),
        )
        weights = Decision._get_weights(config, raw)
        result = Decision._get_results(scores, weights)
        expected = pd.DataFrame(
            data=[
                ["one", 0.4666666666666667, 0.05],
                ["two", 0.5166666666666667, 0.225],
                ["three", 0.5, 0.4],
                ["four", 0.55, 0.575],
                ["five", 0.5333333333333333, 0.75],
            ],
            columns=["choice", "smart", "fun"],
        )
        expected = expected.set_index("choice")
        assert_frame_equal(result, expected)

    def test_ctor(self) -> None:
        decision = Decision(config_path=self.CONFIG, raw_path=self.RAW)
        expected = pd.DataFrame(
            data=[
                ["one", 0.4666666666666667, 0.05],
                ["two", 0.5166666666666667, 0.225],
                ["three", 0.5, 0.4],
                ["four", 0.55, 0.575],
                ["five", 0.5333333333333333, 0.75],
            ],
            columns=["choice", "smart", "fun"],
        )
        expected = expected.set_index("choice")
        assert_frame_equal(decision.results, expected)

    def test_getters(self) -> None:
        decision = Decision(config_path=self.CONFIG, raw_path=self.RAW)
        self.assertEqual(decision.choices(), ["one", "two", "three", "four", "five"])
        self.assertEqual(decision.metrics(), ["smart", "fun"])
        self.assertEqual(decision.factors(), ["cost", "size", "looks", "economy", "power"])
