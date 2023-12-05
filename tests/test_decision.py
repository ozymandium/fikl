"""
Unit tests for fikl.decision.Decision, located in src/fikl/decision.py
"""
import unittest
import os
import yaml
import pprint

from fikl.decision import Decision, SourceScorer
import fikl.scorers
from fikl.proto import config_pb2
from fikl.config import load as load_config

import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
import numpy as np


class TestDecision(unittest.TestCase):
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "simple.yaml")
    RAW = os.path.join(os.path.dirname(__file__), "data", "simple.csv")

    def setUp(self) -> None:
        self.maxDiff = None

    def test_get_scorers(self) -> None:
        config = load_config(self.CONFIG_PATH)
        scorers = Decision._get_scorers(config)
        expected = {
            "smart": {
                "cost": SourceScorer(
                    source="cost",
                    scorer=fikl.scorers.Relative(invert=True),
                ),
                "size": SourceScorer(
                    source="size",
                    scorer=fikl.scorers.Interpolate(
                        knots=[
                            {"in": 0.0, "out": 0.0},
                            {"in": 5.0, "out": 1.0},
                            {"in": 10.0, "out": 0.0},
                        ]
                    ),
                ),
                "economy": SourceScorer(
                    source="economy",
                    scorer=fikl.scorers.Bucket(
                        buckets=[
                            {"min": 0.0, "max": 2.0, "val": 0.2},
                            {"min": 2.0, "max": 4.0, "val": 0.4},
                            {"min": 4.0, "max": 6.0, "val": 0.6},
                            {"min": 6.0, "max": 8.0, "val": 0.8},
                            {"min": 8.0, "max": 10.0, "val": 1.0},
                        ]
                    ),
                ),
            },
            "fun": {
                "looks": SourceScorer(
                    source="looks",
                    scorer=fikl.scorers.Star(min=1, max=5),
                ),
                "power2": SourceScorer(
                    source="power",
                    scorer=fikl.scorers.Range(best=10.0, worst=0.0),
                ),
            },
        }
        self.assertEqual(scorers.keys(), expected.keys())
        for key in scorers.keys():
            self.assertEqual(scorers[key].keys(), expected[key].keys())
            for subkey in scorers[key].keys():
                self.assertEqual(scorers[key][subkey], expected[key][subkey])

    def test_get_raw(self) -> None:
        config = load_config(self.CONFIG_PATH)
        result = Decision._get_raw(config, self.RAW, Decision._get_scorers(config))
        expected = pd.DataFrame(
            data=[
                [1.0, 1.0, 1, 1.0, 1.0],
                [2.0, 2.0, 2, 2.0, 2.0],
                [3.0, 3.0, 3, 3.0, 3.0],
                [4.0, 4.0, 4, 4.0, 4.0],
                [5.0, 5.0, 5, 5.0, 5.0],
            ],
            columns=["cost", "size", "looks", "economy", "power"],
            index=pd.Index(["one", "two", "three", "four", "five"], dtype="object", name="choice"),
        )
        # sort the columns in expected alphabetically
        expected = expected.sort_index(axis=1)
        assert_frame_equal(result, expected)

    def test_get_scores(self) -> None:
        config = load_config(self.CONFIG_PATH)
        raw = Decision._get_raw(config, self.RAW, Decision._get_scorers(config))
        scorers = Decision._get_scorers(config)
        scores = Decision._get_scores(raw, scorers)
        expected = {
            "smart": pd.DataFrame(
                data=[
                    [1.0, 0.2, 0.2],
                    [0.75, 0.4, 0.4],
                    [0.5, 0.6, 0.4],
                    [0.25, 0.8, 0.6],
                    [0.0, 1.0, 0.6],
                ],
                columns=["cost", "size", "economy"],
                index=pd.Index(
                    ["one", "two", "three", "four", "five"], dtype="object", name="choice"
                ),
            ),
            "fun": pd.DataFrame(
                data=[
                    [0.0, 0.1],
                    [0.25, 0.2],
                    [0.5, 0.3],
                    [0.75, 0.4],
                    [1.0, 0.5],
                ],
                columns=["looks", "power2"],
                index=pd.Index(
                    ["one", "two", "three", "four", "five"], dtype="object", name="choice"
                ),
            ),
        }
        self.assertEqual(scores.keys(), expected.keys())
        for key in scores.keys():
            assert_frame_equal(scores[key], expected[key], check_exact=False)

    def test_get_metric_weights(self) -> None:
        config = load_config(self.CONFIG_PATH)
        raw = Decision._get_raw(config, self.RAW, Decision._get_scorers(config))
        metric_weights = Decision._get_metric_weights(config)
        expected = pd.DataFrame(
            data=[
                [1.0 / 3.0, 1.0 / 3.0, 0.0, 1.0 / 3.0, 0.0],
                [0.0, 0.0, 0.5, 0.0, 0.5],
            ],
            columns=["cost", "size", "looks", "economy", "power2"],
            index=pd.Index(["smart", "fun"], dtype="object", name="metric"),
        )
        # sort the columns in expected alphabetically
        expected = expected.sort_index(axis=1)
        # sort the rows in expected alphabetically
        expected = expected.sort_index(axis=0)
        assert_frame_equal(metric_weights, expected)

    def test_get_metric_results(self) -> None:
        config = load_config(self.CONFIG_PATH)
        raw = Decision._get_raw(config, self.RAW, Decision._get_scorers(config))
        scores = Decision._get_scores(
            raw,
            Decision._get_scorers(config),
        )
        weights = Decision._get_metric_weights(config)
        result = Decision._get_metric_results(scores, weights)
        expected = pd.DataFrame(
            data=[
                [0.4666666666666667, 0.05],
                [0.5166666666666667, 0.225],
                [0.5, 0.4],
                [0.55, 0.575],
                [0.5333333333333333, 0.75],
            ],
            columns=["smart", "fun"],
            index=pd.Index(["one", "two", "three", "four", "five"], dtype="object", name="choice"),
        )
        assert_frame_equal(result, expected)

    def test_get_final_weights(self) -> None:
        config = load_config(self.CONFIG_PATH)
        scorers = Decision._get_scorers(config)
        raw = Decision._get_raw(config, self.RAW, scorers)
        scores = Decision._get_scores(raw, scorers)
        weights = Decision._get_metric_weights(config)
        results = Decision._get_metric_results(scores, weights)
        final_weights = Decision._get_final_weights(config)
        expected = pd.Series(
            data=[0.67, 0.33],
            index=pd.Index(["smart", "fun"], dtype="object", name="metric"),
        )
        # sort the rows in expected alphabetically
        expected = expected.sort_index(axis=0)
        assert_series_equal(final_weights, expected)

    def test_ctor(self) -> None:
        decision = Decision(config=load_config(self.CONFIG_PATH), raw_path=self.RAW)
        expected_final_results = pd.Series(
            data=[0.604833, 0.558250, 0.467000, 0.420417, 0.329167],
            index=pd.Index(["five", "four", "three", "two", "one"], dtype="object", name="choice"),
        )
        assert_series_equal(decision.final_results, expected_final_results)

    def test_getters(self) -> None:
        decision = Decision(config=load_config(self.CONFIG_PATH), raw_path=self.RAW)
        self.assertEqual(decision.choices(), ["one", "two", "three", "four", "five"])
        self.assertEqual(decision.metrics(), sorted(["smart", "fun"]))
        self.assertEqual(
            decision.all_factors(), sorted(["cost", "size", "looks", "economy", "power2"])
        )
        self.assertEqual(
            decision.metric_factors(),
            {"smart": sorted(["cost", "size", "economy"]), "fun": sorted(["looks", "power2"])},
        )
