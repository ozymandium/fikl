"""
Common utilities
"""
from collections import OrderedDict
import logging
import os
from typing import Any, Type
import yaml
import json

import jinja2
import numpy as np


def ensure_type(obj: Any, t: Type, inherit: bool = False) -> None:
    """Ensure that an object is of a certain type.

    Parameters
    ----------
    obj : Any
        The object to check
    t : type
        The type to check against
    inherit : bool (default: False)
        If True, then the object is allowed to be a subclass of the type. If False, then the object
        must be exactly the type.
    """
    if inherit:
        if not isinstance(obj, t):
            raise TypeError("object {} is not of type {}".format(obj, t))
    else:
        if type(obj) is not t:
            raise TypeError("object {} is not of type {}".format(obj, t))


def fill_template(template_name, **kwargs):
    """
    Generate HTML content from a Jinja2 template. Relies on the templates directory being in the
    same directory as this file.

    Parameters
    ----------
    template_name : str
        Name of the template to use. This should be the name of a file in the
        templates directory. It should not include the file extension.
    """
    logger = logging.getLogger(__name__)
    logger.debug("Generating HTML from template: %s", template_name)
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
    logger.debug("Template directory: %s", template_dir)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    # display the list of templates that jinja sees
    logger.debug(f"Available templates: {env.list_templates()}")
    template = env.get_template(f"{template_name}.html.j2")
    return template.render(**kwargs)


def build_ordered_depth_first_tree(items: list[Any], levels: list[int]) -> OrderedDict:
    """
    An bulleted outline (like in writing) is a tree. This function builds a tree from a list of
    items and their heading levels. The top level is 0. The items must be in order. The levels
    must be in order. The levels must increase by 1. No skipping levels except on the way back up.

    Parameters
    ----------
    items : list[Any]
        List of items to build the tree from.
    levels : list[int]
        List of heading levels to build the tree from. The top level is 0

    Returns
    -------
    dict
        A tree where each node is a dict. The keys of the dict are the items. The values of the dict

    """
    # must have positive levels
    if min(levels) < 0:
        raise ValueError(f"levels must be positive. have {min(levels)}.")
    # must be same length
    if len(items) != len(levels):
        raise ValueError(f"len(items) != len(levels): {len(items)} != {len(levels)}")
    # when the level increases, it must only increase by 1 (no skipping levels)
    if max(np.diff(levels)) > 1:
        raise ValueError("levels must increase by 1. No skipping levels.")
    # first level must be 0
    if levels[0] != 0:
        raise ValueError(f"levels[0] != 0: have {levels[0]}")

    # create the tree by first finding parents
    # top level items have their own index set
    parent_idxs = [None for _ in range(len(items))]
    for i in range(len(parent_idxs)):
        if levels[i] == 0:
            parent_idxs[i] = i
            continue
        assert i > 0
        if levels[i] > levels[i - 1]:
            parent_idxs[i] = i - 1
            continue
        if levels[i] == levels[i - 1]:
            parent_idxs[i] = parent_idxs[i - 1]
            continue
        if levels[i] < levels[i - 1]:
            # start off with the parent of the previous item
            parent_idxs[i] = parent_idxs[i - 1]
            # now figure out how far up the tree we have to go
            diff = levels[i - 1] - levels[i]
            # go up the tree
            for _ in range(diff):
                parent_idxs[i] = parent_idxs[parent_idxs[i]]
    # assert every parent idx is set
    assert all([x is not None for x in parent_idxs])

    # create the tree
    tree = OrderedDict()
    # contains pointers to the nodes in the tree that have been added
    nodes = [None for _ in range(len(items))]
    for i in range(len(items)):
        parent_idx = parent_idxs[i]
        item = items[i]
        if parent_idx == i:
            # this is a top level item
            tree[item] = OrderedDict()
            nodes[i] = tree[item]
            continue
        # this is not a top level item
        # get the parent node
        parent_node = nodes[parent_idx]
        # add the item to the parent node
        parent_node[item] = OrderedDict()
        # set the node
        nodes[i] = parent_node[item]

    return tree


def load_yaml(stream):
    """
    Load YAML from a stream, fully expanding aliases. This is a hack.

    Parameters
    ----------
    stream : str or file-like
        The YAML to load

    Returns
    -------
    dict
        The loaded YAML data
    """
    data = yaml.load(stream, Loader=yaml.FullLoader)
    return json.loads(json.dumps(data))
