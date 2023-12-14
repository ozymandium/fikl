"""
Handle generating HTML content from Jinja2 templates located in src/templates
"""
from fikl.decision import Decision
from fikl.util import fill_template, build_ordered_depth_first_tree

import os
import logging
import bs4
import re
import uuid
from collections import OrderedDict
from typing import Any, Optional, Union, List
from inspect import cleandoc
import tempfile

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from markdown import markdown as html_from_md


def html_from_doc(doc: str) -> str:
    """
    take an indented markdown string and convert it to html

    Parameters
    ----------
    doc : str
        indented markdown string

    Returns
    -------
    str
        html as a string
    """
    return html_from_md(cleandoc(doc), extensions=["extra"])


def prettify(html: str) -> str:
    """
    Take an html string and prettify it.

    Parameters
    ----------
    html : str

    Returns
    -------
    str
        prettified html
    """
    return bs4.BeautifulSoup(html, "html.parser").prettify()


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

    def _add_items_from_tree(
        tree: OrderedDict, soup: bs4.BeautifulSoup, current_list: bs4.element.Tag
    ) -> None:
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
    toc.h1.string = "Table of Contents"  # type: ignore
    # give the toc an id so that we can style it
    toc.h1["id"] = "toc_h1"  # type: ignore
    toc_list = soup.new_tag("ul")
    # limit the height of the toc list to half the screen or shorter and make it scrollable, but if it's too
    # short, then don't make it scrollable.
    toc_list["style"] = "overflow-y: scroll; max-height: 50vh;"
    toc.append(toc_list)
    # add the toc to the soup
    soup.body.insert(0, toc)  # type: ignore

    # now call the recursive function to add the items to the toc with proper indentation and links
    _add_items_from_tree(tree, soup, toc_list)

    # make each heading clickable by wrapping it in an anchor tag
    for heading in soup.find_all(re.compile("h[0-9]{1}")):
        anchor = soup.new_tag("a", href=f"#{heading['id']}")
        anchor.string = heading.get_text()
        heading.string = ""
        heading.append(anchor)

    return str(soup)


def _table_to_html(
    obj: Union[pd.Series, pd.DataFrame], color_score: bool = False, percent: bool = False
) -> str:
    """
    Convert a DataFrame to html. apply a background gradient to the whole table based on the
    score range.

    TODO: Figure out how to make row label backgrounds not transparent.
    https://pandas.pydata.org/pandas-docs/stable/user_guide/style.html
    https://stackoverflow.com/questions/68140575/styling-the-background-color-of-pandas-index-cell
    https://betterdatascience.com/style-pandas-dataframes/

    Parameters
    ----------
    table : either a pd.Series or a pd.DataFrame
        DataFrame to convert to html
    color_score : bool
        Whether to apply a background gradient to the whole table based on the value. the score
        range is assumed to be between 0 and 1.
    percent : bool
        Whether to format the values as percentages. if False, then trailing zeros will be removed
        so that only significant digits are shown.

    Returns
    -------
    str
        html as a string.
    """
    # if the object is a Series, need to make it a DataFrame with one column
    if isinstance(obj, pd.Series):
        table = pd.DataFrame(obj)
        # don't give the column a name
        table.columns = [""]
        # don't give the index a name
        table.index.name = None
    else:
        table = obj

    styler = table.style

    # apply a background gradient to the whole table based on the score range. it is possible to apply a background gradient to a subset of the columns, using `subset`
    if color_score:
        styler = styler.background_gradient(
            axis="index",
            # cmap=sns.color_palette("YlGnBu", as_cmap=True),
            # cmap = sns.diverging_palette(10, 150, as_cmap=True),
            # cmap=sns.light_palette("seagreen", as_cmap=True),
            cmap=sns.color_palette("RdYlGn", as_cmap=True),
            vmin=0.0,
            vmax=1.0,
        )

    if percent:
        # scores are all floats between 0 and 1, so format them as percentages
        # it is possible to apply a format to a subset of the columns, by passing a dict to format
        styler = styler.format("{0:.0%}")
    else:
        # raw data may be floats or ints. either way, we just want to remove trailing zeros so
        # that only significant digits are shown
        styler = styler.format("{0:g}")

    styler = styler.set_table_styles([{"selector": "th", "props": [("font-family", "Courier")]}])
    styler = styler.set_properties(
        **{
            "text-align": "center",
            "font-family": "Courier",
            "font-size": "11px",
        }
    )
    # make the index (city name) sticky so that it stays on the left side of the screen when scrolling
    styler = styler.set_sticky(axis="index")

    return styler.to_html()


def _reorder_list(l: List, idxs: List[int]) -> List:
    """
    reorder a list based on a list of indices. the indices are into the original list.

    Parameters
    ----------
    l : List
        list to reorder
    idxs : List[int]
        list of indices into the original list

    Returns
    -------
    List
        reordered list
    """
    return [l[i] for i in idxs]


def _metrics_weight_table_to_png(name: str, weights: pd.Series, assets_dir: str) -> str:
    """
    use matplotlib to generate a bar chart for factor weights for each entry in
    Decision.metrics_weights_tables.
    save the chart as a png in the assets_dir. return the relative path to the png file within
    the assets_dir.

    Parameters
    ----------
    metric : str
        name of the metric
    weights : pd.Series
        weights for a single metric. index is the factor names. values are the weights (0-1).
    assets_dir : str
        folder to stick html assets

    Returns
    -------
    str
        relative path to the png file
    """
    # get the labels for the bar chart
    labels = weights.index
    # get the values for the bar chart as percentages
    values = 100 * weights.values

    # generate the horizontal chart
    fig, ax = plt.subplots()
    ax.set_title(f"Factor Weighting for Metric: {name}")
    ax.barh(labels, values)
    # disable x axis
    ax.xaxis.set_visible(False)
    # show the values of each bar as a right hand y axis label. each label should be outside of the
    # chart area. format as a percentage.
    right_yax = ax.twinx()
    right_yax.set_yticklabels([f"{v:.0f}%" for v in values], ha="left")
    # set ytick locations to be the same as the bar locations
    right_yax.set_yticks(ax.get_yticks())
    # set the limits of the right y axis to be the same as the left y axis
    right_yax.set_ylim(ax.get_ylim())

    # tight fit to make sure the labels aren't cut off
    fig.tight_layout()

    # save to png
    png_abs_path = os.path.join(assets_dir, f"{name}.png")
    fig.savefig(png_abs_path)

    # convert to html
    # want it to be relative to the html file, so use a relative path
    png_rel_path = os.path.relpath(png_abs_path, os.path.dirname(assets_dir))

    return png_rel_path


def report(decision: Decision, path: Optional[str] = None) -> Optional[str]:
    """
    Generate an html report for a decision.

    Parameters
    ----------
    decision : Decision
        Decision to generate the report for
    path : str, optional
        Path to write the html to. If None, then the html will be returned as a string.

    Returns
    -------
    Optional[str]
        If path is None, then the html as a string. Otherwise, None.
    """
    # folder to stick html assets should have the same name as the html file, but with _assets
    # if path is None, then just use a temp folder
    if path is None:
        assets_dir = tempfile.mkdtemp()
    else:
        assets_dir = os.path.join(os.path.dirname(path), f"{os.path.basename(path)}_assets")
        os.makedirs(assets_dir, exist_ok=True)

    # sort the final table by the final score
    final_table = _table_to_html(decision.final_table(sort=True), color_score=True, percent=True)

    # get the order of the metrics to print. this is a list of int indices into Decision.metrics()
    # to use to rearrange metrics lists
    metric_order = decision.metric_print_order()

    # list of metric names
    metrics = _reorder_list(decision.metrics(), metric_order)
    # list of metric tables
    metrics_tables = [
        _table_to_html(table, color_score=True, percent=True) for table in decision.metrics_tables()
    ]
    metrics_tables = _reorder_list(metrics_tables, metric_order)
    # list of weight tables for each metric
    metrics_weight_tables = [
        _metrics_weight_table_to_png(metric, weights, assets_dir)
        for metric, weights in zip(decision.metrics(), decision.metrics_weight_tables())
    ]
    metrics_weight_tables = _reorder_list(metrics_weight_tables, metric_order)

    measures_table = _table_to_html(decision.measures_table(), color_score=True, percent=True)
    sources_table = _table_to_html(decision.sources_table(), color_score=False, percent=False)

    sources_per_measure = [measure.source for measure in decision.config.measures]

    # get the docs
    measure_docs = [html_from_doc(measure.doc) for measure in decision.config.measures]
    scorer_docs = [html_from_doc(doc) for doc in decision.scorer_docs()]

    # dump the html blobs into a template
    html = fill_template(
        "index",
        answer=decision.answer(),
        final_table=final_table,
        metrics=metrics,
        metrics_tables=metrics_tables,
        metrics_weight_tables=metrics_weight_tables,
        ignored_metrics=decision.ignored_metrics(),
        measures_table=measures_table,
        sources_table=sources_table,
        measures=decision.measures(),
        sources_per_measure=sources_per_measure,
        measure_docs=measure_docs,
        scorer_docs=scorer_docs,
    )
    html = add_toc(html)
    html = bs4.BeautifulSoup(html, "html.parser").prettify()

    if path is None:
        return html
    else:
        with open(path, "w") as f:
            f.write(html)
        return None
