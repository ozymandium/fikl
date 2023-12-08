"""
Tools for parsing a YAML config file into a protobuf Config object, as defined in
fikl/proto/config.proto.
"""
from fikl.proto import config_pb2
from fikl.util import load_yamls as dict_from_yamls

import os
import yaml
import json
import tempfile
import logging
from typing import List

from google.protobuf.json_format import ParseDict


def load_yaml(*config_yaml_paths: List[str]) -> config_pb2.Config:
    """
    Parse YAML config files into a protobuf Config object.

    Parameters
    ----------
    config_yaml_path : str
        Path to the YAML config file.

    Returns
    -------
    Config
        Cap'n Proto Config object
    """
    config_dict = dict_from_yamls(*config_yaml_paths)
    config = config_pb2.Config()
    ParseDict(config_dict, config)
    return config


# def find_factor(config: config_pb2.Config, name: str) -> config_pb2.Factor:
#     """
#     Get a factor from a config object by name.

#     Parameters
#     ----------
#     config : Config
#         Cap'n Proto Config object
#     name : str
#         Name of the factor to get.

#     Returns
#     -------
#     Factor
#         Cap'n Proto Factor object
#     """
#     matching = [f for f in config.factors if f.name == name]
#     if len(matching) != 1:
#         raise ValueError(f"Could not find unique factor with name {name}")
#     return matching[0]
