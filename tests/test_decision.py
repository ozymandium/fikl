"""
Unit tests for fikl.decision.Decision, located in src/fikl/decision.py
"""
import unittest
import os

from fikl.decision import Decision

import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np


class TestDecision(unittest.TestCase):
    CONFIG = os.path.join(os.path.dirname(__file__), "data", "config.yaml")
    RAW = os.path.join(os.path.dirname(__file__), "data", "raw.csv")

    def setUp(self):
        self.decision = Decision(config_path=self.CONFIG, raw_path=self.RAW)

    def test_raw(self):
        expected = pd.read_csv(self.RAW, index_col="choice")
        # evaluate the expression column (power)
        expected["power"] = expected["power"].map(lambda x: eval(x))
        assert_frame_equal(self.decision.raw, expected)
