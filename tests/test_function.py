"""function tests that simply check for whether the pipeline runs end to end without error"""
import os
import unittest

from fikl.decision import Decision
from fikl.html import report
from fikl.config import load_yaml


class TestFunction(unittest.TestCase):
    """Just run all the examples in the data folder and make sure they don't crash"""

    def test_basic(self) -> None:
        # get a list of all files in the data folder
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        folders = [f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))]
        for folder in folders:
            # consider every yaml part of the overall config
            config_paths = [
                os.path.join(data_dir, folder, f)
                for f in os.listdir(os.path.join(data_dir, folder))
                if f.endswith(".yaml")
            ]
            # should only be a single csv file
            raw_path = [
                os.path.join(data_dir, folder, f)
                for f in os.listdir(os.path.join(data_dir, folder))
                if f.endswith(".csv")
            ]
            self.assertEqual(len(raw_path), 1)
            raw_path = raw_path[0]
            config = load_yaml(*config_paths)
            decision = Decision(config=config, raw_path=raw_path)
            html = report(decision)
            # TODO: check that the html is valid
