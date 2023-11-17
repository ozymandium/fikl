"""
Tests code in src/fikl/util.py.
"""
import unittest
from collections import OrderedDict
from numbers import Number

from fikl.util import (
    ensure_type,
    build_ordered_depth_first_tree,
)


class TestEnsureType(unittest.TestCase):
    """
    Tests ensure_type(), which ra
    """

    def test_simple(self) -> None:
        """
        Tests a simple case.
        """
        ensure_type(1, int)
        ensure_type(1.0, float)

    def test_cast_fail(self) -> None:
        """
        Tests a simple case.
        """
        with self.assertRaises(TypeError):
            ensure_type(1, str)

    def test_inheritance(self) -> None:
        """
        Tests a simple case.
        """
        ensure_type(1, Number, inherit=True)
        ensure_type(1.0, Number, inherit=True)
        with self.assertRaises(TypeError):
            ensure_type("1", Number, inherit=True)
        with self.assertRaises(TypeError):
            ensure_type("1", Number, inherit=False)
        with self.assertRaises(TypeError):
            ensure_type(1, str, inherit=True)


class TestBuildOrderedDepthFirstTree(unittest.TestCase):
    """
    Tests build_ordered_depth_first_tree().

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
        self.assertEqual(build_ordered_depth_first_tree(items, levels), expected)

    def test_nest(self) -> None:
        items = ["a", "b", "c"]
        levels = [0, 1, 2]
        expected = OrderedDict(
            [
                ("a", OrderedDict([("b", OrderedDict([("c", OrderedDict())]))])),
            ]
        )
        self.assertEqual(build_ordered_depth_first_tree(items, levels), expected)

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
        self.assertEqual(build_ordered_depth_first_tree(items, levels), expected)
