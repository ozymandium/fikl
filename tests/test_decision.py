"""
Unit tests for fikl.decision.Decision, located in src/fikl/decision.py
"""
import unittest
import os
import yaml
import pprint

import fikl.decision
import fikl.config

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


class TestGetSourceData(TestDecisionBase):
    """Tests fikl.decision._get_source_data"""
    def test_get_source_data(self) -> None:
        """Tests fikl.decision._get_source_data"""
        data = fikl.decision._get_source_data(self.config, self.raw_path)
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
        assert_frame_equal(data, expected)

