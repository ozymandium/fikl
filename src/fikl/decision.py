from fikl.scorers import LOOKUP
from fikl.util import html_from_doc
from fikl.html import generate_html

from typing import Optional, Any, Dict, List, Callable
import logging
import yaml
import pprint
import os

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import bs4


class Decision:
    """
    TODO: swap to functional/imperative style instead of OOP.

    Members
    -------
    logger : logging.Logger
        logger for this class
    raw : pd.DataFrame
        the raw user input matrix. the index is the choice name, the columns are the factors
    scores : pd.DataFrame
        the ranking matrix. the index is the choice name, the columns are the factors. values are
        floats between 0 and 1.
    score_range : MinMax
        the minimum and maximum possible scores.
    weights : pd.DataFrame
        the weights for each factor for each metric. the index is the metric name, the columns are
        the factors. the "All" metric is automatically added which includes all factors
    """

    def __init__(self, config_path: str, data_path: str):
        """
        Parameters
        ----------
        config_path : str
            File path where config yaml should be read
        data_path : str
            File path where data csv should be read

        Returns
        -------
        Decision
        """
        self.logger = logging.getLogger()

        # read the config yaml
        with open(config_path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        # read the ranking matrix from the csv as a dataframe
        # the index is the choice name, the columns are the factors
        self.raw = pd.read_csv(data_path, index_col="choice")
        # allow the user to input executable code in the csv. eval it here.
        self.raw = self.raw.applymap(lambda x: eval(x) if isinstance(x, str) else x)
        self.logger.debug("raw scores:\n{}".format(self.raw))

        # determine which scorer to use for each factor
        # a scorer takes in the value from raw_scores and the config for that factor, and returns
        # an int score that is inside of the score range described by MinMax
        scorers = {
            factor: LOOKUP[cfg["type"]](**cfg["config"])
            for factor, cfg in config["factors"].items()
        }

        # each scorer requires a certain dtype for the input. iterate over each factor/column and
        # make sure that the dtype is correct. if not, try to cast it to the correct type and log a
        # warning.
        for factor, scorer in scorers.items():
            dtype = scorer.DTYPE
            if not self.raw[factor].dtype == dtype:
                logging.warning(
                    f"factor {factor} has dtype {self.raw[factor].dtype} but scorer {scorer} requires dtype {dtype}, casting to {dtype}"
                )
                self.raw[factor] = self.raw[factor].astype(dtype)

        # for each column in self.raw, apply the scorer that corresponds to that factor
        self.scores = self.raw.apply(lambda col: scorers[col.name](col), axis=0)
        self.logger.info("Scores:\n{}".format(pprint.pformat(self.scores)))

        # weight should be a DataFrame where the columns are factors and the index is the metric.
        # columns should be the same as the factors in the scores. Initialize with all zeros.
        self.weights = pd.DataFrame(
            0,
            columns=self.scores.columns,
            index=list(config["metrics"].keys()),
        )
        # for each metric, set the weights for each factor
        for metric in config["metrics"]:
            for factor in config["metrics"][metric]:
                self.weights.loc[metric, factor] = config["metrics"][metric][factor]
        # normalize the weights for each metric (along each row)
        self.weights = self.weights.div(self.weights.sum(axis=1), axis=0)
        self.logger.info("Weights:\n{}".format(pprint.pformat(self.weights)))

        # check and make sure that the columns are shared between scores and weights
        if set(self.scores.columns) != set(self.weights.columns):
            raise ValueError(
                "score columns {} do not match weight columns {}".format(
                    set(self.scores.columns), set(self.weights.columns)
                )
            )

        self.factor_docs = {
            factor: config["factors"][factor]["doc"] if "doc" in config["factors"][factor] else "\n"
            for factor in config["factors"]
        }
        self.scorer_docs = {factor: scorers[factor].doc() for factor in scorers}

    def choices(self) -> list[str]:
        """
        Returns
        -------
        list[str]
            list of choice names
        """
        return list(self.scores.index)

    def metrics(self) -> list[str]:
        """
        Returns
        -------
        list[str]
            list of metric names
        """
        return list(self.weights.index)

    def factors(self) -> list[str]:
        """
        Returns
        -------
        list[str]
            list of factor names
        """
        return list(self.weights.columns)

    def _get_results(self) -> pd.DataFrame:
        results = pd.DataFrame(
            index=self.choices(),
            columns=self.metrics(),
            dtype=float,
        )
        for choice in self.choices():
            for metric in self.metrics():
                results.loc[choice, metric] = np.dot(
                    self.weights.loc[metric], self.scores.loc[choice]
                )
        return results

    def _table_to_html(
        self, table: pd.DataFrame, color_score: bool = False, percent: bool = False
    ) -> Optional[str]:
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

        styler = styler.set_table_styles(
            [{"selector": "th", "props": [("font-family", "Courier")]}]
        )
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

    def _factors_to_html(self) -> str:
        """
        Get HTML text section which describes each factor and its scoring.

        Returns
        -------
        str
            html as a string.
        """
        return generate_html(
            "factors",
            factors=self.factors(),
            descriptions=[html_from_doc(self.factor_docs[factor]) for factor in self.factors()],
            scorings=[html_from_doc(self.scorer_docs[factor]) for factor in self.factors()],
        )

    def _pie_chart_to_html(self, metric: str, assets_dir: str) -> str:
        """
        use matplotlib.pyplot.pie to generate a pie chart for a row in self.weights to show the
        relative weights of each factor for a given metric. remove all columns that have a weight of
        0. use mpld3 to convert the matplotlib figure to html.

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
        weights = self.weights.loc[metric]
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

    def _metrics_to_html(self, assets_dir: str) -> str:
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
        return generate_html(
            "metrics",
            table=self._table_to_html(self.weights, color_score=True, percent=True),
            metrics=self.metrics(),
            charts=[self._pie_chart_to_html(metric, assets_dir) for metric in self.metrics()],
        )

    def to_html(self, path: str = None) -> Optional[str]:
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

        raw_html = self._table_to_html(self.raw)
        score_html = self._table_to_html(self.scores, color_score=True, percent=True)
        results_html = self._table_to_html(self._get_results(), color_score=True, percent=True)
        metrics_html = self._metrics_to_html(assets_dir)
        factors_html = self._factors_to_html()
        # a factor is ignored if all values in its column in the weights table are 0
        ignored_factors = [
            factor for factor in self.factors() if np.all(self.weights[factor] == 0.0)
        ]

        # dump the html blobs into a template
        html = generate_html(
            "index",
            raw=raw_html,
            score=score_html,
            results=results_html,
            metrics=metrics_html,
            factors=factors_html,
            ignored_factors=ignored_factors,
        )
        html = bs4.BeautifulSoup(html, "html.parser").prettify()

        if path is not None:
            with open(path, "w") as f:
                f.write(html)
        else:
            return html
