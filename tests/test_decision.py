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

import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
import numpy as np


class TestDecisionBase(unittest.TestCase):
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


class TestGetSourceData(TestDecisionBase):
    """Tests fikl.decision._get_source_data"""

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


class TestGetMeasureData(TestDecisionBase):
    """Tests fikl.decision._get_measure_data"""

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
