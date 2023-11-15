"""
Handle generating HTML content from Jinja2 templates located in src/templates
"""
import os
import jinja2
import logging
import bs4
import re
import uuid
from collections import OrderedDict
from typing import Any

import numpy as np


def generate_html(template_name, **kwargs):
    """
    Generate HTML content from a Jinja2 template.

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


def add_toc(html):
    """
    Add a table of contents to an HTML document with hyperlinks to each heading. Each subsection of
    the table of contents will be indented based on the heading level. Headings without an id will
    be given a unique id.

    Parameters
    ----------
    html : str
        HTML content to add the table of contents to.

    Returns
    -------
    str
        HTML content with the table of contents added.
    """
    # # this code generates a list of headings, but they are not indented.
    # soup = bs4.BeautifulSoup(html, "html.parser")
    # toc = soup.new_tag("div", id="toc")
    # toc.append(soup.new_tag("h2"))
    # toc.h2.string = "Table of Contents"
    # toc_list = soup.new_tag("ul")
    # toc.append(toc_list)
    # for heading in soup.find_all(re.compile("h[0-9]{1}")):
    #     # if the heading doesn't have an id, create one
    #     if heading.get("id") is None:
    #         heading["id"] = str(uuid.uuid4())
    #     # create the link to the heading
    #     heading_link = soup.new_tag("a", href=f"#{heading['id']}")
    #     heading_link.string = heading.get_text()
    #     # create the list item for the table of contents
    #     toc_list_item = soup.new_tag("li")
    #     toc_list_item.append(heading_link)
    #     # add the list item to the table of contents
    #     toc_list.append(toc_list_item)
    # # add the table of contents to the document
    # soup.body.insert(0, toc)
    # return str(soup)

    # this code generates a list of headings, and they are indented based on the heading level.
    soup = bs4.BeautifulSoup(html, "html.parser")
    toc = soup.new_tag("div", id="toc")
    toc.append(soup.new_tag("h1"))
    toc.h1.string = "Table of Contents"
    toc_list = soup.new_tag("ul")
    toc.append(toc_list)
    # keep track of the current list item
    current_list_item = toc_list
    # keep track of the current heading level
    current_heading_level = 0
    for heading in soup.find_all(re.compile("h[0-9]{1}")):
        # if the heading doesn't have an id, create one
        if heading.get("id") is None:
            heading["id"] = str(uuid.uuid4())
        # create the link to the heading
        heading_link = soup.new_tag("a", href=f"#{heading['id']}")
        heading_link.string = heading.get_text()
        # create the list item for the table of contents
        toc_list_item = soup.new_tag("li")
        toc_list_item.append(heading_link)
        # add the list item to the table of contents
        # if the heading level is greater than the current heading level, then add the list item
        # as a child of the current list item
        if int(heading.name[1]) > current_heading_level:
            # need to start a new sublist since the heading level is greater than the current heading level
            # so that the list item can be added as a child of the current list item
            if current_list_item.name != "ul":
                new_list = soup.new_tag("ul")
                current_list_item.append(new_list)
                current_list_item = new_list
            current_list_item.append(toc_list_item)
            current_list_item = toc_list_item
        # if the heading level is less than the current heading level, then we are going back up
        # the list, so we need to go back up the list to the correct level
        elif int(heading.name[1]) < current_heading_level:
            # go back up the list to the correct level
            while int(heading.name[1]) < current_heading_level:
                current_list_item = current_list_item.parent
                current_heading_level = int(current_list_item.name[1])
            current_list_item.append(toc_list_item)
            current_list_item = toc_list_item

        # if the heading level is the same as the current heading level, then add the list item
        # as a sibling of the current list item
        else:
            current_list_item.append(toc_list_item)
            current_list_item = toc_list_item
        # update the current heading level
        current_heading_level = int(heading.name[1])
    # add the table of contents to the document
    soup.body.insert(0, toc)
    return str(soup)


def build_ordered_depth_first_tree(items: list[Any], levels: list[int]):
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
