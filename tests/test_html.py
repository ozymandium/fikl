"""
Tests code in src/fikl/html.py.
"""
import unittest
from collections import OrderedDict

import fikl.html


class TestBuildOrderedDepthFirstTree(unittest.TestCase):
    """
    Tests fikl.html.build_ordered_depth_first_tree().

    This function is the generalized solution to receiving an outline in the form of a list of
    headings and their levels and converting it to a tree.
    """

    def test_simple(self) -> None:
        """
        Tests a simple outline.
        """
        items = ["A", "B", "C"]
        levels = [0, 0, 0]
        expected = OrderedDict(
            [
                ("A", OrderedDict()),
                ("B", OrderedDict()),
                ("C", OrderedDict()),
            ]
        )
        self.assertEqual(fikl.html.build_ordered_depth_first_tree(items, levels), expected)

    def test_nest(self) -> None:
        items = ["a", "b", "c"]
        levels = [0, 1, 2]
        expected = OrderedDict(
            [
                ("a", OrderedDict([("b", OrderedDict([("c", OrderedDict())]))])),
            ]
        )

    def test_complicated(self) -> None:
        """
        Tests a complicated outline.
        """
        items = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
        levels = [0, 0, 1, 2, 2, 1, 2, 3, 0]
        expected = OrderedDict(
            [
                ("A", OrderedDict()),
                (
                    "B",
                    OrderedDict(
                        [
                            ("C", OrderedDict([("D", OrderedDict()), ("E", OrderedDict())])),
                            (
                                "F",
                                OrderedDict(
                                    [
                                        ("G", OrderedDict([("H", OrderedDict())])),
                                    ]
                                ),
                            ),
                        ]
                    ),
                ),
                ("I", OrderedDict()),
            ]
        )
        self.assertEqual(fikl.html.build_ordered_depth_first_tree(items, levels), expected)
