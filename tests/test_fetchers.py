"""
Unit tests for fikl.fetchers module, located in src/fikl/fetchers.py
"""
import unittest
import os

import fikl.fetchers

import pandas as pd


class TestFetch(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None

    def test_fetch(self) -> None:
        data = fikl.fetchers.fetch(
            [
                "fikl.fetchers.ExampleFetcher",
            ],
            ["a", "bc"],
        )
        expected = pd.DataFrame(
            {"fikl.fetchers.ExampleFetcher": [1.0, 2.0]},
            index=["a", "bc"],
        )
        pd.testing.assert_frame_equal(data, expected)
