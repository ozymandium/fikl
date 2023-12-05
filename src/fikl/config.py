"""
Tools for parsing a YAML config file into a protobuf Config object, as defined in
fikl/proto/config.proto.
"""
from fikl.proto import config_pb2

import os
import yaml
import json
import tempfile
import logging

from google.protobuf.json_format import ParseDict


def load(config_yaml_path: str) -> config_pb2.Config:
    """
    Parse a YAML config file into a

    Parameters
    ----------
    config_yaml_path : str
        Path to the YAML config file.

    Returns
    -------
    Config
        Cap'n Proto Config object
    """
    config = config_pb2.Config()
    with open(config_yaml_path, "r") as config_yaml_f:
        config_dict = yaml.safe_load(config_yaml_f)
    ParseDict(config_dict, config)
    return config


def find_factor(config: config_pb2.Config, name: str) -> config_pb2.Factor:
    """
    Get a factor from a config object by name.

    Parameters
    ----------
    config : Config
        Cap'n Proto Config object
    name : str
        Name of the factor to get.

    Returns
    -------
    Factor
        Cap'n Proto Factor object
    """
    matching = [f for f in config.factors if f.name == name]
    if len(matching) != 1:
        raise ValueError(f"Could not find unique factor with name {name}")
    return matching[0]
