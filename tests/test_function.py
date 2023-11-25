"""function tests that simply check for whether the pipeline runs end to end without error"""
import os
import unittest

from fikl.decision import Decision
from fikl.html import report


class TestFunction(unittest.TestCase):
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
            html = report(decision)
            # TODO: check that the html is valid
