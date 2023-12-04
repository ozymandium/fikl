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

    def compare_lists(self, l1: list, l2: list) -> None:
        self.assertEqual(len(l1), len(l2))
        for i in range(len(l1)):
            if isinstance(l1[i], dict):
                self.compare_dicts(l1[i], l2[i])
            elif isinstance(l1[i], float):
                self.assertAlmostEqual(l1[i], l2[i], places=3)
            elif isinstance(l1[i], int):
                self.assertAlmostEqual(float(l1[i]), float(l2[i]), places=3)
            else:
                self.assertEqual(l1[i], l2[i])

    def compare_dicts(self, d1: dict, d2: dict) -> None:
        """round tripping yaml to json to binary to json to yaml sometimes results in floats being
        stored as ints or losing some precision, so we need to compare the yaml files by loading them
        and individually compare the fields and values (not the types). any numerical values need to
        be compared with some tolerance.
        """
        for k, v in d1.items():
            print(k, v)
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.compare_dicts(v, d2[k])
            elif isinstance(v, float):
                self.assertAlmostEqual(v, d2[k], places=3)
            elif isinstance(v, int):
                self.assertAlmostEqual(float(v), float(d2[k]), places=3)
            elif isinstance(v, list):
                self.compare_lists(v, d2[k])
            else:
                self.assertEqual(v, d2[k])

    def setUp(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.maxDiff = None

    def test_yaml_to_json_roundtrip(self) -> None:
        # get a temporary json file
        json_path = tempfile.NamedTemporaryFile(suffix=".json").name
        # convert the yaml file to json
        fikl.config._yaml_to_json(self.CONFIG, json_path)
        self.assertTrue(os.path.exists(json_path))
        # convert the json file back to yaml
        yaml_path = tempfile.NamedTemporaryFile(suffix=".yaml").name
        fikl.config._json_to_yaml(json_path, yaml_path)
        self.assertTrue(os.path.exists(yaml_path))
        with open(yaml_path, "r") as yaml_f, open(self.CONFIG, "r") as yaml_f2:
            self.assertEqual(yaml.safe_load(yaml_f), yaml.safe_load(yaml_f2))

    def test_yaml_to_binary_roundtrip(self) -> None:
        # get a temporary binary file
        binary_path = tempfile.NamedTemporaryFile(suffix=".bin").name
        # convert the yaml file to binary
        fikl.config._yaml_to_binary(self.CONFIG, binary_path)
        self.assertTrue(os.path.exists(binary_path))
        # convert the binary file back to yaml
        yaml_path = tempfile.NamedTemporaryFile(suffix=".yaml").name
        print(f"yaml_path: {yaml_path}")
        fikl.config._binary_to_yaml(binary_path, yaml_path)
        self.assertTrue(os.path.exists(yaml_path))
        # want to check that the contents of the yaml file are the same as the original yaml file
        # but the dumped yaml file may store floats as ints, so we need to load the yaml files
        # and just compare the fields and values (not the types)
        with open(yaml_path, "r") as yaml_f, open(self.CONFIG, "r") as yaml_f2:
            self.compare_dicts(yaml.safe_load(yaml_f), yaml.safe_load(yaml_f2))

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
        for i in range(len(config.factors)):
            scoring_type = str(config.factors[i].scoring.which)
