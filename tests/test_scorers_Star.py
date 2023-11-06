"""
Unit tests for fikl.scorers.Star, located in src/fikl/scorers.py
"""
import unittest
import pandas as pd
import numpy as np

from fikl.scorers import Star


class TestStar(unittest.TestCase):
    """
    Unit tests for fikl.scorers.Star
    """

    def setUp(self):
        """
        Setup for unit tests
        """
        self.scorer = Star(min=1, max=5)

    def test_expected(self):
        """
        Test that the score method returns the correct value.
        """
        self.assertEqual(
            self.scorer(pd.Series([1, 2, 3, 4, 5])).tolist(),
            np.array([0.0, 0.25, 0.50, 0.75, 1.0]).tolist(),
        )

    def test_outside_range(self):
        """
        Test that ValueError is raised when the value is outside the range
        """
        with self.assertRaises(ValueError):
            self.scorer(pd.Series([0, 1, 2, 3, 4, 5]))
        with self.assertRaises(ValueError):
            self.scorer(pd.Series([1, 2, 3, 4, 5, 6]))

    def test_improper_ctor_types(self) -> None:
        """
        Test that TypeError is raised when the wrong types are passed to the constructor
        """
        with self.assertRaises(TypeError):
            Star(min=1.0, max=5)
        with self.assertRaises(TypeError):
            Star(min=1, max=5.0)
        with self.assertRaises(TypeError):
            Star(min=1.0, max=5.0)

    def test_improper_ctor_values(self) -> None:
        """
        Test that ValueError is raised when the wrong values are passed to the constructor
        """
        with self.assertRaises(ValueError):
            Star(min=1, max=1)
        with self.assertRaises(ValueError):
            Star(min=5, max=1)

    def test_improper_call_types(self) -> None:
        """
        Test that TypeError is raised when the wrong types are passed to the call method
        """
        with self.assertRaises(TypeError):
            self.scorer(1.0)
        with self.assertRaises(TypeError):
            self.scorer("1")
        with self.assertRaises(TypeError):
            self.scorer([1])
        with self.assertRaises(TypeError):
            self.scorer((1,))
        with self.assertRaises(TypeError):
            self.scorer(1)

    def test_improper_call_dtypes(self) -> None:
        """
        Test that TypeError is raised when the wrong types are passed to the call method
        """
        with self.assertRaises(TypeError):
            self.scorer(pd.Series([1.0]))
        with self.assertRaises(TypeError):
            self.scorer(pd.Series(["1"]))

    def test_call_values(self) -> None:
        """
        Test that the values that are return from the call method are correct
        """
        self.assertEqual(self.scorer(pd.Series([1])).tolist(), np.array([0.0]).tolist())
        self.assertEqual(self.scorer(pd.Series([2])).tolist(), np.array([0.25]).tolist())
        self.assertEqual(self.scorer(pd.Series([3])).tolist(), np.array([0.5]).tolist())
        self.assertEqual(self.scorer(pd.Series([4])).tolist(), np.array([0.75]).tolist())
        self.assertEqual(self.scorer(pd.Series([5])).tolist(), np.array([1.0]).tolist())
