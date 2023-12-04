"""
Unit tests for fikl.config module, located in src/fikl/config.py
"""
import unittest
import os
import tempfile
import logging
import json
import yaml

import fikl.config


class TestParse(unittest.TestCase):
    CONFIG = os.path.join(os.path.dirname(__file__), "data", "simple.yaml")

    # def compare_lists(self, l1: list, l2: list) -> None:
    #     self.assertEqual(len(l1), len(l2))
    #     for i in range(len(l1)):
    #         if isinstance(l1[i], dict):
    #             self.compare_dicts(l1[i], l2[i])
    #         elif isinstance(l1[i], float):
    #             self.assertAlmostEqual(l1[i], l2[i], places=3)
    #         elif isinstance(l1[i], int):
    #             self.assertAlmostEqual(float(l1[i]), float(l2[i]), places=3)
    #         else:
    #             self.assertEqual(l1[i], l2[i])

    # def compare_dicts(self, d1: dict, d2: dict) -> None:
    #     """round tripping yaml to json to binary to json to yaml sometimes results in floats being
    #     stored as ints or losing some precision, so we need to compare the yaml files by loading them
    #     and individually compare the fields and values (not the types). any numerical values need to
    #     be compared with some tolerance.
    #     """
    #     for k, v in d1.items():
    #         print(k, v)
    #         self.assertTrue(k in d2)
    #         if isinstance(v, dict):
    #             self.compare_dicts(v, d2[k])
    #         elif isinstance(v, float):
    #             self.assertAlmostEqual(v, d2[k], places=3)
    #         elif isinstance(v, int):
    #             self.assertAlmostEqual(float(v), float(d2[k]), places=3)
    #         elif isinstance(v, list):
    #             self.compare_lists(v, d2[k])
    #         else:
    #             self.assertEqual(v, d2[k])

    def setUp(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.maxDiff = None

    def test_parse(self) -> None:
        config = fikl.config.load(self.CONFIG)
        self.assertEqual(len(config.factors), 5)
        self.assertEqual(
            [config.factors[i].name for i in range(len(config.factors))],
            ["cost", "size", "looks", "economy", "power"],
        )
        self.assertEqual(
            [config.factors[i].source for i in range(len(config.factors))],
            ["cost", "size", "looks", "economy", "power"],
        )
        # for i in range(len(config.factors)):
        #     scoring = config.factors[i].scoring
        #     self.assertEqual(type(scoring).__name__, "Scoring")
        #     scorer_code = scoring.WhichOneOf("config")
        #     scorer_config = getattr(config.factors[i].scoring, scorer_code)
