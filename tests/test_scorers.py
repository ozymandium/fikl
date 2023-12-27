"""
Unit tests for fikl.scorers, located in src/fikl/scorers.py
"""
import unittest
import pandas as pd
import numpy as np

from fikl.scorers import Star, Bucket, Relative, Interpolate, Range, Bool, get_scorer_info
from fikl.proto import config_pb2


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

    def test_eq(self) -> None:
        """
        Test that the __eq__ method works as expected
        """
        self.assertEqual(Star(min=1, max=5), Star(min=1, max=5))
        self.assertNotEqual(Star(min=1, max=5), Star(min=1, max=4))
        self.assertNotEqual(Star(min=1, max=5), Star(min=2, max=5))
        self.assertNotEqual(Star(min=1, max=5), Star(min=2, max=4))


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

    def test_eq(self):
        """
        Test that the __eq__ method works as expected
        """
        self.assertEqual(
            Bucket(
                [
                    {"min": 0.0, "max": 1.0, "val": 0.2},
                    {"min": 1.0, "max": 2.0, "val": 0.4},
                    {"min": 2.0, "max": 3.0, "val": 0.6},
                    {"min": 3.0, "max": 4.0, "val": 0.8},
                    {"min": 4.0, "max": 5.0, "val": 1.0},
                ]
            ),
            Bucket(
                [
                    {"min": 0.0, "max": 1.0, "val": 0.2},
                    {"min": 1.0, "max": 2.0, "val": 0.4},
                    {"min": 2.0, "max": 3.0, "val": 0.6},
                    {"min": 3.0, "max": 4.0, "val": 0.8},
                    {"min": 4.0, "max": 5.0, "val": 1.0},
                ]
            ),
        )
        self.assertNotEqual(
            Bucket(
                [
                    {"min": 0.0, "max": 1.0, "val": 0.2},
                    {"min": 1.0, "max": 2.0, "val": 0.4},
                    {"min": 2.0, "max": 3.0, "val": 0.6},
                    {"min": 3.0, "max": 4.0, "val": 0.8},
                    {"min": 4.0, "max": 5.0, "val": 1.0},
                ]
            ),
            Bucket(
                [
                    {"min": 0.0, "max": 1.0, "val": 0.2},
                    {"min": 1.0, "max": 2.0, "val": 0.4},
                    {"min": 2.0, "max": 3.0, "val": 0.6},
                    {"min": 3.0, "max": 4.0, "val": 0.8},
                    {"min": 4.0, "max": 5.0, "val": 0.9},
                ]
            ),
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

    def test_eq(self) -> None:
        """
        Test that the __eq__ method works as expected
        """
        self.assertEqual(Relative(invert=False), Relative(invert=False))
        self.assertNotEqual(Relative(invert=False), Relative(invert=True))


class TestInterpolate(unittest.TestCase):
    """
    Unit tests for fikl.scorers.Interpolate
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

    def test_eq(self) -> None:
        """
        Test that the __eq__ method works as expected
        """
        self.assertEqual(
            Interpolate(
                knots=[
                    {"in": -1.0, "out": 0.0},
                    {"in": 0.0, "out": 1.0},
                    {"in": 1.0, "out": 0.0},
                ]
            ),
            Interpolate(
                knots=[
                    {"in": -1.0, "out": 0.0},
                    {"in": 0.0, "out": 1.0},
                    {"in": 1.0, "out": 0.0},
                ]
            ),
        )
        self.assertNotEqual(
            Interpolate(
                knots=[
                    {"in": -1.0, "out": 0.0},
                    {"in": 0.0, "out": 1.0},
                    {"in": 1.0, "out": 0.0},
                ]
            ),
            Interpolate(
                knots=[
                    {"in": -1.0, "out": 0.0},
                    {"in": 0.0, "out": 1.0},
                    {"in": 1.0, "out": 1.0},
                ]
            ),
        )
        self.assertNotEqual(
            Interpolate(
                knots=[
                    {"in": -1.0, "out": 0.0},
                    {"in": 0.0, "out": 1.0},
                    {"in": 1.0, "out": 0.0},
                ]
            ),
            Interpolate(
                knots=[
                    {"in": -1.0, "out": 0.0},
                    {"in": 0.0, "out": 1.0},
                ]
            ),
        )


class TestRange(unittest.TestCase):
    """
    Unit tests for fikl.scorers.Range
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

    def test_eq(self) -> None:
        """
        Test that the __eq__ method works as expected
        """
        self.assertEqual(Range(worst=0.0, best=100.0), Range(worst=0.0, best=100.0))
        self.assertNotEqual(Range(worst=0.0, best=100.0), Range(worst=100.0, best=0.0))


class TestBool(unittest.TestCase):
    """
    Unit tests for fikl.scorers.Bool
    """

    def test_expected(self) -> None:
        """
        Test that the score method returns the correct value.
        """
        self.assertEqual(
            Bool(good=True)(pd.Series([True, False, True, False])).tolist(), [1.0, 0.0, 1.0, 0.0]
        )
        self.assertEqual(
            Bool(good=False)(pd.Series([True, False, True, False])).tolist(), [0.0, 1.0, 0.0, 1.0]
        )

    def test_eq(self) -> None:
        """
        Test that the __eq__ method works as expected
        """
        self.assertEqual(Bool(good=True), Bool(good=True))
        self.assertEqual(Bool(good=False), Bool(good=False))
        self.assertNotEqual(Bool(good=True), Bool(good=False))
        self.assertNotEqual(Bool(good=False), Bool(good=True))


class TestGetScorerInfo(unittest.TestCase):
    def test_star(self) -> None:
        """
        Test that the get_scorer_info function returns the correct scorer when the factor is
        "star".
        """
        measure = config_pb2.Measure(
            name="name",
            source="source",
            scoring=config_pb2.Scoring(star=config_pb2.StarScorerConfig(min=1, max=5)),
        )
        scorer_info = get_scorer_info(measure)
        self.assertEqual(scorer_info.scorer, Star(min=1, max=5))
        self.assertEqual(scorer_info.measure, "name")
        self.assertEqual(scorer_info.source, "source")

    def test_bucket(self) -> None:
        """
        Test that the get_scorer_info function returns the correct scorer when the factor is
        "bucket".
        """
        measure = config_pb2.Measure(
            name="name",
            source="source",
            scoring=config_pb2.Scoring(
                bucket=config_pb2.BucketScorerConfig(
                    buckets=[
                        config_pb2.BucketScorerConfig.Bucket(min=0.0, max=1.0, val=0.2),
                        config_pb2.BucketScorerConfig.Bucket(min=1.0, max=2.0, val=0.4),
                        config_pb2.BucketScorerConfig.Bucket(min=2.0, max=3.0, val=0.6),
                        config_pb2.BucketScorerConfig.Bucket(min=3.0, max=4.0, val=0.8),
                        config_pb2.BucketScorerConfig.Bucket(min=4.0, max=5.0, val=1.0),
                    ]
                )
            ),
        )
        scorer_info = get_scorer_info(measure)
        expected = Bucket(
            [
                {"min": 0.0, "max": 1.0, "val": 0.2},
                {"min": 1.0, "max": 2.0, "val": 0.4},
                {"min": 2.0, "max": 3.0, "val": 0.6},
                {"min": 3.0, "max": 4.0, "val": 0.8},
                {"min": 4.0, "max": 5.0, "val": 1.0},
            ]
        )
        self.assertEqual(scorer_info.scorer, expected)
        self.assertEqual(scorer_info.measure, "name")
        self.assertEqual(scorer_info.source, "source")

    def test_relative(self) -> None:
        """
        Test that the get_scorer_info function returns the correct scorer when the factor is
        "relative".
        """
        measure = config_pb2.Measure(
            name="name",
            source="source",
            scoring=config_pb2.Scoring(relative=config_pb2.RelativeScorerConfig(invert=False)),
        )
        scorer_info = get_scorer_info(measure)
        self.assertEqual(scorer_info.scorer, Relative(invert=False))
        self.assertEqual(scorer_info.measure, "name")
        self.assertEqual(scorer_info.source, "source")

    def test_interpolate(self) -> None:
        """
        Test that the get_scorer_info function returns the correct scorer when the factor is
        "interpolate".

        FIXME: stop using "in" as a variable name
        """
        measure = config_pb2.Measure(
            name="name",
            source="source",
            scoring=config_pb2.Scoring(
                interpolate=config_pb2.InterpolateScorerConfig(
                    knots=[
                        config_pb2.InterpolateScorerConfig.Knot(**{"in": -1.0, "out": 0.0}),
                        config_pb2.InterpolateScorerConfig.Knot(**{"in": 0.0, "out": 1.0}),
                        config_pb2.InterpolateScorerConfig.Knot(**{"in": 1.0, "out": 0.0}),
                    ]
                )
            ),
        )
        scorer_info = get_scorer_info(measure)
        expected = Interpolate(
            [
                {"in": -1.0, "out": 0.0},
                {"in": 0.0, "out": 1.0},
                {"in": 1.0, "out": 0.0},
            ]
        )
        self.assertEqual(scorer_info.scorer, expected)
        self.assertEqual(scorer_info.measure, "name")
        self.assertEqual(scorer_info.source, "source")

    def test_range(self) -> None:
        """
        Test that the get_scorer_info function returns the correct scorer when the factor is
        "range".
        """
        measure = config_pb2.Measure(
            name="name",
            source="source",
            scoring=config_pb2.Scoring(range=config_pb2.RangeScorerConfig(worst=0.0, best=100.0)),
        )
        scorer_info = get_scorer_info(measure)
        self.assertEqual(scorer_info.scorer, Range(worst=0.0, best=100.0))
        self.assertEqual(scorer_info.measure, "name")
        self.assertEqual(scorer_info.source, "source")
