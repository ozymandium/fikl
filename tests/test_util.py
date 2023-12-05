"""
Tests code in src/fikl/util.py.
"""
import unittest
from collections import OrderedDict
from numbers import Number

from fikl.util import (
    ensure_type,
    build_ordered_depth_first_tree,
    merge_dicts,
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
        )  # type: ignore
        self.assertEqual(build_ordered_depth_first_tree(items, levels), expected)

    def test_nest(self) -> None:
        items = ["a", "b", "c"]
        levels = [0, 1, 2]
        expected = OrderedDict(
            [
                ("a", OrderedDict([("b", OrderedDict([("c", OrderedDict())]))])),
            ]
        )  # type: ignore
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


class TestMergeDicts(unittest.TestCase):
    """Tests merge_dicts, which merges two dicts as long as they don't have conflicting keys."""

    def test_simple(self) -> None:
        a = {"a": 1}
        b = {"b": 2}
        expected = {"a": 1, "b": 2}
        self.assertEqual(merge_dicts(a, b), expected)

    def test_conflict(self) -> None:
        a = {"a": 1}
        b = {"a": 2}
        with self.assertRaises(ValueError):
            merge_dicts(a, b)

    def test_nested(self) -> None:
        a = {"a": {"b": 1}}
        b = {"a": {"c": 2}}
        expected = {"a": {"b": 1, "c": 2}}
        self.assertEqual(merge_dicts(a, b), expected)

    def test_nested_conflict(self) -> None:
        a = {"a": {"b": 1}}
        b = {"a": {"b": 2}}
        with self.assertRaises(ValueError):
            merge_dicts(a, b)

    def test_nested_conflict_2(self) -> None:
        a = {"a": {"b": 1}}
        b = {"a": 2}
        with self.assertRaises(ValueError):
            merge_dicts(a, b)

    def test_nested_conflict_3(self) -> None:
        a = {"a": 2}
        b = {"a": {"b": 1}}
        with self.assertRaises(ValueError):
            merge_dicts(a, b)

    def test_nested_conflict_4(self) -> None:
        a = {"a": {"b": 1}}
        b = {"a": {"b": {"c": 2}}}
        with self.assertRaises(ValueError):
            merge_dicts(a, b)

    def test_nested_conflict_5(self) -> None:
        a = {"a": {"b": {"c": 2}}}
        b = {"a": {"b": 1}}
        with self.assertRaises(ValueError):
            merge_dicts(a, b)

    def test_nested_conflict_6(self) -> None:
        a = {"a": {"b": {"c": 2}}}
        b = {"a": {"b": {"c": 3}}}
        with self.assertRaises(ValueError):
            merge_dicts(a, b)

    def test_3_levels(self) -> None:
        a = {"a": {"b": {"c": 2}}}
        b = {"a": {"d": 3}}
        expected = {"a": {"b": {"c": 2}, "d": 3}}
        self.assertEqual(merge_dicts(a, b), expected)

    def test_3_levels_update(self) -> None:
        a = {"a": {"b": {"c": 2}}}
        b = {"a": {"b": {"d": 3}}}
        expected = {"a": {"b": {"c": 2, "d": 3}}}
        self.assertEqual(merge_dicts(a, b), expected)
