"""
Unit tests for fikl.config module, located in src/fikl/config.py
"""
import unittest
import os
import tempfile
import logging
import json
import yaml

import fikl.config
from fikl.proto import config_pb2


class TestLoad(unittest.TestCase):
    CONFIG = os.path.join(os.path.dirname(__file__), "data", "simple.yaml")

    def setUp(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.maxDiff = None

    def test_load(self) -> None:
        config = fikl.config.load(self.CONFIG)
        self.assertEqual(len(config.factors), 5)

        self.assertEqual(
            [config.factors[i].name for i in range(len(config.factors))],
            ["cost", "size", "looks", "economy", "power2"],
        )

        self.assertEqual(
            [config.factors[i].source for i in range(len(config.factors))],
            ["cost", "size", "looks", "economy", "power"],
        )

        self.assertEqual(config.factors[0].doc, "This is a comment\n")
        self.assertEqual(config.factors[1].doc, "")

        # scoring
        self.assertEqual(
            config.factors[0].scoring.relative, config_pb2.RelativeScorerConfig(invert=True)
        )
        self.assertEqual(
            config.factors[1].scoring.interpolate,
            config_pb2.InterpolateScorerConfig(
                knots=[
                    config_pb2.InterpolateScorerConfig.Knot(**{"in": 0.0, "out": 0.0}),
                    config_pb2.InterpolateScorerConfig.Knot(**{"in": 5.0, "out": 1.0}),
                    config_pb2.InterpolateScorerConfig.Knot(**{"in": 10.0, "out": 0.0}),
                ]
            ),
        )
        self.assertEqual(
            config.factors[2].scoring.star,
            config_pb2.StarScorerConfig(min=1, max=5),
        )
        self.assertEqual(
            config.factors[3].scoring.bucket,
            config_pb2.BucketScorerConfig(
                buckets=[
                    config_pb2.BucketScorerConfig.Bucket(min=0, max=2, val=0.2),
                    config_pb2.BucketScorerConfig.Bucket(min=2, max=4, val=0.4),
                    config_pb2.BucketScorerConfig.Bucket(min=4, max=6, val=0.6),
                    config_pb2.BucketScorerConfig.Bucket(min=6, max=8, val=0.8),
                    config_pb2.BucketScorerConfig.Bucket(min=8, max=10, val=1.0),
                ]
            ),
        )
        self.assertEqual(
            config.factors[4].scoring.range,
            config_pb2.RangeScorerConfig(best=10, worst=0),
        )

        # metrics
        self.assertEqual(len(config.metrics), 2)
        self.assertEqual(config.metrics[0].name, "smart")
        self.assertEqual(
            config.metrics[0].factors,
            [
                config_pb2.NameWeight(name="cost", weight=1.0),
                config_pb2.NameWeight(name="size", weight=1.0),
                config_pb2.NameWeight(name="economy", weight=1.0),
            ],
        )
        self.assertEqual(config.metrics[1].name, "fun")
        self.assertEqual(
            config.metrics[1].factors,
            [
                config_pb2.NameWeight(name="looks", weight=1.0),
                config_pb2.NameWeight(name="power2", weight=1.0),
            ],
        )

        # final
        self.assertEqual(len(config.final), 2)
        self.assertEqual(config.final[0], config_pb2.NameWeight(name="smart", weight=0.67))
        self.assertEqual(config.final[1], config_pb2.NameWeight(name="fun", weight=0.33))
