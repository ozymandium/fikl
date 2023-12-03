"""
Unit tests for fikl.fetchers, located in src/fikl/fetchers.py
"""
import unittest
import pandas as pd
import numpy as np

from fikl.fetchers import LOOKUP as FETCHER_LOOKUP
from fikl.fetchers import CityToCountyLookup


class TestObesityFetcher(unittest.TestCase):
    """
    Unit tests for fikl.fetchers.ObesityFetcher
    """

    def setUp(self) -> None:
        """
        Setup for unit tests
        """
        self.fetcher = FETCHER_LOOKUP["Obesity"]()

    def test_fetch(self) -> None:
        """
        Test that the fetch method returns the correct value.
        """
        self.assertEqual(
            self.fetcher.fetch(["Birmingham, AL", "Phoenix, AZ"]).tolist(),
            np.array([42.0, 31.0]).tolist(),
        )

    def test_fetch_duplicate_choices(self) -> None:
        """
        Test that ValueError is raised when duplicate choices are passed to the fetch method
        """
        with self.assertRaises(ValueError):
            self.fetcher.fetch(["Birmingham, AL", "Birmingham, AL"])

    def test_fetch_choices_not_in_data(self) -> None:
        """
        Test that ValueError is raised when choices not in the data are passed to the fetch method
        """
        with self.assertRaises(ValueError):
            self.fetcher.fetch(["Birmingham, AL", "Birmingham, AK"])

    def test_missing_state(self) -> None:
        """
        Test that ValueError is raised when a choice is missing a state
        """
        with self.assertRaises(ValueError):
            self.fetcher.fetch(["Birmingham, AL", "Birmingham"])

    def test_missing_city(self) -> None:
        """
        Test that ValueError is raised when a choice is missing a city
        """
        with self.assertRaises(ValueError):
            self.fetcher.fetch(["Birmingham, AL", "AL"])
        with self.assertRaises(ValueError):
            self.fetcher.fetch(["Birmingham, AL", ", AL"])

    def test_fetch_improper_values(self) -> None:
        """
        Test that ValueError is raised when the wrong values are passed to the fetch method
        """
        with self.assertRaises(ValueError):
            self.fetcher.fetch(["Birmingham, AL", "Birmingham, AK", "Birmingham, AL"])
        with self.assertRaises(ValueError):
            self.fetcher.fetch(["Birmingham, AL", "Birmingham, AK", "Birmingham, AL"])
        with self.assertRaises(ValueError):
            self.fetcher.fetch(["Birmingham, AL", "Birmingham, AK", "Birmingham, AL"])
        with self.assertRaises(ValueError):
            self.fetcher.fetch([1, 2, 3])  # type: ignore
        with self.assertRaises(ValueError):
            self.fetcher.fetch([1.0, 2.0, 3.0])  # type: ignore
        with self.assertRaises(ValueError):
            self.fetcher.fetch([1, 2.0, 3])  # type: ignore


class TestCityToCountyLookup(unittest.TestCase):
    def setUp(self) -> None:
        self.fetcher = CityToCountyLookup()

    def test_call(self) -> None:
        self.assertEqual(self.fetcher("AL", "Birmingham"), "Jefferson")
        self.assertEqual(self.fetcher("LA", "New Orleans"), "Orleans")

    def test_get_state_abbr(self) -> None:
        self.assertEqual(self.fetcher._get_state_abbr("Alabama"), "AL")
        self.assertEqual(self.fetcher._get_state_abbr("Louisiana"), "LA")

    def test_get_county_pop(self) -> None:
        self.assertEqual(self.fetcher._get_county_pop("AL", "Jefferson"), 665409)

    def test_get_counties(self) -> None:
        self.assertEqual(self.fetcher._get_counties("AL", "Birmingham"), ["Jefferson", "Shelby"])
