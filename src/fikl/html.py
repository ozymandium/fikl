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

    def _add_items_from_tree(tree, soup, current_list) -> None:
        """
        Recursive function to add items to the table of contents from a tree.

        Parameters
        ----------
        tree : OrderedDict
            Tree to add items from. Keys are (heading name, heading id) tuples, where the heading name is a string that
            will be displayed in the table of contents, and the heading id is the id of the heading
            that the table of contents item links to. Values are OrderedDicts that contain the
            children of the heading. If a heading has no children, then the value is an empty.
        soup : bs4.BeautifulSoup
            BeautifulSoup object that contains the HTML content.
        current_list : bs4.element.Tag
            BeautifulSoup tag that is the current list to add items to.
        """
        for (text, link), children in tree.items():
            # create the link to the heading
            heading_link = soup.new_tag("a", href=f"#{link}")
            heading_link.string = text
            # create the list item for the table of contents
            toc_list_item = soup.new_tag("li")
            toc_list_item.append(heading_link)
            # add the list item to the table of contents
            current_list.append(toc_list_item)
            # if the heading has children, then create a new list and add it to the list item
            if len(children) > 0:
                new_list = soup.new_tag("ul")
                toc_list_item.append(new_list)
                # call this function recursively to add the children
                _add_items_from_tree(children, soup, new_list)

    # first parse the html
    soup = bs4.BeautifulSoup(html, "html.parser")

    # now iterate through the headings and record the title, level, and id. for every heading that
    # doesn't have an id, create one. along the way, we're building lists of the heading name, levels,
    # and ids, so that we can build the tree.
    titles = []
    levels = []
    ids = []
    for heading in soup.find_all(re.compile("h[0-9]{1}")):
        # if the heading doesn't have an id, create one
        if heading.get("id") is None:
            heading["id"] = str(uuid.uuid4())
        # record the name, level, and id
        titles.append(heading.get_text())
        # subtract 1 from the heading level so that the top level is 0
        levels.append(int(heading.name[1]) - 1)
        ids.append(heading["id"])

    # build the tree
    tree = build_ordered_depth_first_tree(list(zip(titles, ids)), levels)

    # start the toc list
    toc = soup.new_tag("div", id="toc_div")
    toc.append(soup.new_tag("h1"))
    toc.h1.string = "Table of Contents"
    # give the toc an id so that we can style it
    toc.h1["id"] = "toc_h1"
    toc_list = soup.new_tag("ul")
    # limit the height of the toc list to half the screen and make it scrollable
    toc_list["style"] = "height: 50vh; overflow-y: scroll;"
    toc.append(toc_list)
    # add the toc to the soup
    soup.body.insert(0, toc)

    # now call the recursive function to add the items to the toc with proper indentation and links
    _add_items_from_tree(tree, soup, toc_list)

    # make each heading clickable by wrapping it in an anchor tag
    for heading in soup.find_all(re.compile("h[0-9]{1}")):
        anchor = soup.new_tag("a", href=f"#{heading['id']}")
        anchor.string = heading.get_text()
        heading.string = ""
        heading.append(anchor)

    return str(soup)
