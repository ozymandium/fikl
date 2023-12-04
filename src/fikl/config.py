"""
Tools for parsing a YAML config file into a Cap'n Proto Config object, as defined in
src/fikl/config.capnp.
"""
import capnp

import os
import yaml
import json
import tempfile
import logging

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "capnp", "config.capnp")
SCHEMA = capnp.load(SCHEMA_PATH)
# Config = SCHEMA.Config


def _yaml_to_json(yaml_path, json_path):
    with open(yaml_path, "r") as f:
        yaml_dict = yaml.safe_load(f)
    with open(json_path, "w") as f:
        json.dump(yaml_dict, f, indent=4, sort_keys=True)


def _json_to_yaml(json_path, yaml_path):
    with open(json_path, "r") as f:
        json_dict = json.load(f)
    with open(yaml_path, "w") as f:
        yaml.dump(json_dict, f, indent=4, sort_keys=True)


def _call(cmd: str) -> None:
    """
    Call a command in the shell and raise an error if it fails.

    Parameters
    ----------
    cmd : str
        Command to call in the shell.
    """
    ret = os.system(cmd)
    if ret != 0:
        raise RuntimeError(f"Command failed with return code {ret}:\n{cmd}")


def _json_to_binary(json_path, binary_path):
    _call(f"capnp convert json:binary {SCHEMA} Config < {json_path} > {binary_path}")


def _binary_to_json(binary_path, json_path):
    _call(f"capnp convert binary:json {SCHEMA} Config < {binary_path} > {json_path}")


def _yaml_to_binary(yaml_path, binary_path):
    # convert yaml to a temporary json file
    json_path = tempfile.NamedTemporaryFile(suffix=".json").name
    _yaml_to_json(yaml_path, json_path)
    _json_to_binary(json_path, binary_path)


def _binary_to_yaml(binary_path, yaml_path):
    # convert binary to a temporary json file
    json_path = tempfile.NamedTemporaryFile(suffix=".json").name
    _binary_to_json(binary_path, json_path)
    _json_to_yaml(json_path, yaml_path)


def load(config_yaml_path: str) -> "Config":
    """
    Parse a YAML config file into a Cap'n Proto Config object.

    Parameters
    ----------
    config_yaml_path : str
        Path to the YAML config file.

    Returns
    -------
    Config
        Cap'n Proto Config object
    """
    binary_path = tempfile.NamedTemporaryFile(suffix=".bin").name
    _yaml_to_binary(config_yaml_path, binary_path)
    logging.info(f"Dumping binary config to {binary_path}")
    with open(binary_path, "rb") as f:
        config = Config.read(f)
    return config
