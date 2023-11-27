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
from typing import Any, Optional
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


def _table_to_html(table: pd.DataFrame, color_score: bool = False, percent: bool = False) -> str:
    """
    Convert a DataFrame to html. apply a background gradient to the whole table based on the
    score range.

    TODO: Figure out how to make row label backgrounds not transparent.
    https://pandas.pydata.org/pandas-docs/stable/user_guide/style.html
    https://stackoverflow.com/questions/68140575/styling-the-background-color-of-pandas-index-cell
    https://betterdatascience.com/style-pandas-dataframes/

    Parameters
    ----------
    table : pd.DataFrame
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
    styler = table.style

    # apply a background gradient to the whole table based on the score range. it is possible to apply a background gradient to a subset of the columns, using `subset`
    if color_score:
        styler = styler.background_gradient(
            axis="index",
            cmap=sns.color_palette("YlGnBu", as_cmap=True),
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


def _metrics_weight_chart_to_png(decision: Decision, metric: str, assets_dir: str) -> str:
    """
    use matplotlib to generate a chart for a row in decision.metric_weights to show the
    relative weights of each factor for a given metric. remove all columns that have a weight of
    0. save the chart as a png in the assets_dir. return the relative path to the png file within
    the assets_dir.

    Parameters
    ----------
    metric : str
        the metric to generate the pie chart for
    assets_dir : str
        folder to stick html assets

    Returns
    -------
    str
        relative path to the png file
    """
    # get the weights for the given metric
    weights = decision.metric_weights.loc[metric]
    # remove all columns that have a weight of 0
    weights = weights[weights != 0.0]
    # get the labels for the pie chart
    labels = weights.index
    # get the values for the pie chart as percentages
    values = 100 * weights.values
    # # get the colors for the pie chart
    # colors = sns.color_palette("deep", len(labels))

    # generate the horizontal chart
    fig, ax = plt.subplots()
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
    png_abs_path = os.path.join(assets_dir, f"{metric}.png")
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

    raw_table = _table_to_html(decision.raw)

    # scores dataframes include columns for factors that are ignored, so remove those
    scores_tables = {}
    for metric in decision.metrics():
        df = decision.scores[metric].copy()
        # a factor is ignored for this metric if the value for this metric row and this factor
        # column in the weights table is 0
        ignored_factors = [
            factor
            for factor in decision.all_factors()
            if decision.metric_weights.loc[metric, factor] == 0.0
        ]
        df = df.drop(columns=ignored_factors)
        scores_tables[metric] = _table_to_html(df, color_score=True, percent=True)

    results_table = _table_to_html(decision.metric_results, color_score=True, percent=True)
    weights_table = _table_to_html(decision.metric_weights, color_score=True, percent=True)
    weight_charts = {
        metric: _metrics_weight_chart_to_png(decision, metric, assets_dir)
        for metric in decision.metrics()
    }
    factor_descriptions = {
        metric: {
            factor: html_from_doc(decision.factor_docs[metric][factor])
            for factor in decision.factor_docs[metric]
        }
        for metric in decision.factor_docs
    }
    factor_scorings = {
        metric: {
            factor: html_from_doc(decision.scorer_docs[metric][factor])
            for factor in decision.scorer_docs[metric]
        }
        for metric in decision.scorer_docs
    }
    # a factor is ignored if all values in its column in the weights table are 0
    ignored_factors = [
        factor for factor in decision.all_factors() if all(decision.metric_weights[factor] == 0.0)
    ]

    # dump the html blobs into a template
    html = fill_template(
        "index",
        raw_table=raw_table,
        scores_tables=scores_tables,
        results_table=results_table,
        weights_table=weights_table,
        weight_charts=weight_charts,
        factor_descriptions=factor_descriptions,
        factor_scorings=factor_scorings,
        metric_factors=decision.metric_factors(),
        ignored_factors=ignored_factors,
    )
    html = add_toc(html)
    html = bs4.BeautifulSoup(html, "html.parser").prettify()

    if path is None:
        return html
    else:
        with open(path, "w") as f:
            f.write(html)
        return None
