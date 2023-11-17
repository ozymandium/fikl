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


def _factors_to_html(decision: Decision) -> str:
    """
    Get HTML text section which describes each factor and its scoring.

    Parameters
    ----------
    decision : Decision
        Decision to get the factors from

    Returns
    -------
    str
        html as a string.
    """
    return fill_template(
        "factors",
        factors=decision.factors(),
        descriptions=[html_from_doc(decision.factor_docs[factor]) for factor in decision.factors()],
        scorings=[html_from_doc(decision.scorer_docs[factor]) for factor in decision.factors()],
    )


def _metrics_allotment_pie_chart_to_html(decision: Decision, metric: str, assets_dir: str) -> str:
    """
    use matplotlib.pyplot.pie to generate a pie chart for a row in decision.weights to show the
    relative weights of each factor for a given metric. remove all columns that have a weight of
    0. save the pie chart as a png and create an html img tag to display it.

    Parameters
    ----------
    metric : str
        the metric to generate the pie chart for
    assets_dir : str
        folder to stick html assets

    Returns
    -------
    str
        html as a string.
    """
    # get the weights for the given metric
    weights = decision.weights.loc[metric]
    # remove all columns that have a weight of 0
    weights = weights[weights != 0.0]
    # get the labels for the pie chart
    labels = weights.index
    # get the values for the pie chart
    values = weights.values
    # get the colors for the pie chart
    colors = sns.color_palette("deep", len(labels))

    # generate the pie chart
    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")

    # save to png
    png_abs_path = os.path.join(assets_dir, f"{metric}.png")
    fig.savefig(png_abs_path)

    # convert to html
    # want it to be relative to the html file, so use a relative path
    png_rel_path = os.path.relpath(png_abs_path, os.path.dirname(assets_dir))
    # take up 50% of screen
    html = f"""<img src="{png_rel_path}" alt="{metric}" width="50%"/>"""

    return html


def _metrics_to_html(decision: Decision, assets_dir: str) -> str:
    """
    Get HTML for the metrics table and pie charts which show the relative weights of each
    factor for each metric.

    Parameters
    ----------
    assets_dir : str
        folder to stick html assets

    Returns
    -------
    str
        html as a string.
    """
    return fill_template(
        "metrics",
        table=_table_to_html(decision.weights, color_score=True, percent=True),
        metrics=decision.metrics(),
        charts=[
            _metrics_allotment_pie_chart_to_html(decision, metric, assets_dir)
            for metric in decision.metrics()
        ],
    )


def report(decision: Decision, path: str = None) -> Optional[str]:
    """
    Parameters
    ----------
    path : str
        File path where html should be written

    Returns
    -------
    Optional[str]
        html as a string if path is None, else None
    """
    # folder to stick html assets should have the same name as the html file, but with _assets
    # and remove the extension
    assets_dir = os.path.join(os.path.dirname(path), f"{os.path.basename(path)}_assets")
    os.makedirs(assets_dir, exist_ok=True)

    raw_html = _table_to_html(decision.raw)
    score_html = _table_to_html(decision.scores, color_score=True, percent=True)
    results_html = _table_to_html(decision.results, color_score=True, percent=True)
    metrics_html = _metrics_to_html(decision, assets_dir)
    factors_html = _factors_to_html(decision)
    # a factor is ignored if all values in its column in the weights table are 0
    ignored_factors = [
        factor for factor in decision.factors() if np.all(decision.weights[factor] == 0.0)
    ]

    # dump the html blobs into a template
    html = fill_template(
        "index",
        raw=raw_html,
        score=score_html,
        results=results_html,
        metrics=metrics_html,
        factors=factors_html,
        ignored_factors=ignored_factors,
    )
    html = add_toc(html)
    html = bs4.BeautifulSoup(html, "html.parser").prettify()

    if path is not None:
        with open(path, "w") as f:
            f.write(html)
    else:
        return html
