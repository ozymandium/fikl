"""
Unit tests for fikl.scorers, located in src/fikl/scorers.py
"""
import unittest
import pandas as pd
import numpy as np

from fikl.scorers import Star, Bucket, Relative, Interpolate, Range


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
            Star(min=1.0, max=5)  # type: ignore
        with self.assertRaises(TypeError):
            Star(min=1, max=5.0)  # type: ignore
        with self.assertRaises(TypeError):
            Star(min=1.0, max=5.0)  # type: ignore

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
        self.assertEqual(
            self.scorer(pd.Series([1, 2, 3, 4, 5])).tolist(), [0.0, 0.25, 0.50, 0.75, 1.0]
        )


class TestBucket(unittest.TestCase):
    """
    Unit tests for fikl.scorers.Bucket
    """

    def setUp(self):
        """
        Setup for unit tests
        """
        self.scorer = Bucket(
            [
                {"min": 0.0, "max": 1.0, "val": 0.2},
                {"min": 1.0, "max": 2.0, "val": 0.4},
                {"min": 2.0, "max": 3.0, "val": 0.6},
                {"min": 3.0, "max": 4.0, "val": 0.8},
                {"min": 4.0, "max": 5.0, "val": 1.0},
            ]
        )

    def test_expected(self):
        """
        Test that the score method returns the correct value.
        """
        self.assertEqual(
            self.scorer(pd.Series([0.0, 1.0, 2.0, 3.0, 4.0])).tolist(),
            np.array([0.2, 0.4, 0.6, 0.8, 1.0]).tolist(),
        )


class TestRelative(unittest.TestCase):
    """
    Unit tests for fikl.scorers.Relative
    """

    def test_non_inverted(self) -> None:
        """
        Test that the score method returns the correct value when higher is better.
        """
        scorer = Relative(invert=False)
        self.assertEqual(
            scorer(pd.Series([1, 2, 3, 4, 5])).tolist(),
            np.array([0.0, 0.25, 0.50, 0.75, 1.0]).tolist(),
        )

    def test_inverted(self) -> None:
        """
        Test that the score method returns the correct value when lower is better.
        """
        scorer = Relative(invert=True)
        self.assertEqual(
            scorer(pd.Series([1, 2, 3, 4, 5])).tolist(),
            np.array([1.0, 0.75, 0.50, 0.25, 0.0]).tolist(),
        )

    def test_improper_call_types(self) -> None:
        """
        Test that TypeError is raised when the wrong types are passed to the call method
        """
        scorer = Relative(invert=False)
        with self.assertRaises(TypeError):
            scorer(1.0)  # type: ignore
        with self.assertRaises(TypeError):
            scorer("1")  # type: ignore
        with self.assertRaises(TypeError):
            scorer([1])  # type: ignore
        with self.assertRaises(TypeError):
            scorer((1,))  # type: ignore
        with self.assertRaises(TypeError):
            scorer(1)  # type: ignore


class TestInterpolate(unittest.TestCase):
    """
    Unit tests for fikl.scores.Interpolate
    """

    def setUp(self) -> None:
        self.scorer = Interpolate(
            knots=[
                {"in": -1.0, "out": 0.0},
                {"in": 0.0, "out": 1.0},
                {"in": 1.0, "out": 0.0},
            ]
        )

    def test_expected(self) -> None:
        """
        Test that the score method returns the correct value.
        """
        self.assertEqual(
            self.scorer(pd.Series([-1.0, -0.5, 0.0, 0.5, 1.0])).tolist(),
            np.array([0.0, 0.5, 1.0, 0.5, 0.0]).tolist(),
        )


class TestRange(unittest.TestCase):
    """
    Unit tests for fikl.scores.Range
    """

    def test_expected(self) -> None:
        """
        Test that the score method returns the correct value.
        """
        self.assertEqual(
            Range(worst=0.0, best=100.0)(pd.Series([0.0, 25.0, 50.0, 75.0, 100.0])).tolist(),
            np.array([0.0, 0.25, 0.50, 0.75, 1.0]).tolist(),
        )
        self.assertEqual(
            Range(worst=100.0, best=0.0)(pd.Series([0.0, 25.0, 50.0, 75.0, 100.0])).tolist(),
            np.array([1.0, 0.75, 0.50, 0.25, 0.0]).tolist(),
        )
