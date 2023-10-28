#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="fikl",
    version="0.0.1",
    description="A Python tool for decision making using weighted scores.",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points = {
        "console_scripts": [
            "fikl = fikl.cli:main",
        ],
    },
    # unit tests are in the test directory
    test_suite="tests",
)
