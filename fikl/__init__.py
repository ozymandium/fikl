import numpy as np
import yaml
import pandas as pd
import seaborn as sns

from collections import namedtuple
import logging
import pprint
from typing import Optional, Any


def ensure_type(obj, t):
    """Ensure that an object is of a certain type"""
    if type(obj) is not t:
        raise TypeError("object {} is not of type {}".format(obj, t))


def scorer_int(val: Any, config: dict) -> int:
    """scoring function that simply returns the value as an int"""
    return int(val)


def scorer_bin(val: Any, config: dict) -> int:
    """scoring function that bins the value based on the config"""
    for ret, (min, max) in config.items():
        if min <= val < max:
            return int(ret)
    raise ValueError("value {} is not in any bin.\nconfig: {}".format(val, pprint.pformat(config)))


SCORERS = {
    "int": scorer_int,
    "bin": scorer_bin,
}


class MinMax(namedtuple("MinMax", ["min", "max"])):
    """A simple class to hold a min and max value, both of which are ints"""

    def __new__(cls, min: int, max: int):
        if min > max:
            raise ValueError("min {} must be <= max {}".format(min, max))
        ensure_type(min, int)
        ensure_type(max, int)
        return super().__new__(cls, min, max)

    def __str__(self):
        return "({}, {})".format(self.min, self.max)

    def normalize(self, score: int) -> float:
        """
        Parameters
        ----------
        score : int
            the score to normalize

        Returns
        -------
        float
            the normalized score
        """
        return float(score - self.min) / float(self.range())

    def range(self) -> int:
        """
        Returns
        -------
        int
            the range between the min and max
        """
        return self.max - self.min


class Decision:
    """
    Members
    -------
    logger : logging.Logger
        logger for this class
    scores : pd.DataFrame
        the ranking matrix. the index is the choice name, the columns are the factors
    score_range : MinMax
        the minimum and maximum possible scores.
    weights : pd.DataFrame
        the weights for each factor for each metric. the index is the metric name, the columns are
        the factors. the "All" metric is automatically added which includes all factors
    """

    def __init__(self, config_path: str, data_path: str):
        """
        TODO: get away from having ctor and parsing in different formats, and make it so that the
        ctor args are exactly the same as the yaml content. intermediate variable creation should be
        moved to ctor

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
        self.scores = pd.read_csv(data_path, index_col="choice")
        self.logger.info("Scores:\n{}".format(pprint.pformat(self.scores)))

        # # ensure that scores has a "choice" column and all other colums are factors
        # if set(self.scores.columns) != set(config["factors"].keys()):
        #     raise ValueError(
        #         "score columns {} do not match config factors {}".format(
        #             set(self.scores.columns), set(config["factors"].keys())
        #         )
        #     )

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

        score_range = MinMax(**config["score"])
        self.score_range = score_range
        self.logger.debug("Score range: {}".format(self.score_range))

        # check and make sure that the columns are shared between scores and weights
        if set(self.scores.columns) != set(self.weights.columns):
            raise ValueError(
                "score columns {} do not match weight columns {}".format(
                    set(self.scores.columns), set(self.weights.columns)
                )
            )

    def factors(self) -> list[str]:
        """
        Returns
        -------
        list[str]
            list of factor names
        """
        return list(self.scores.columns)

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

    def _aggregate(self, metric: str, choice: str):
        """
        compute the aggregate score for a choice for a metric. this should be automatically
        normalized to [0, 1]. compute as the dot product of the weights for the metric and the
        scores for the choice.

        Parameters
        ----------
        metric : str
            the metric to compute the aggregate score for
        choice : str
            the choice to compute the aggregate score for

        Returns
        -------
        float
            the aggregate score for the choice for the metric
        """
        return np.dot(self.weights.loc[metric], self.scores.loc[choice])

    def _get_results(self) -> pd.DataFrame:
        results = pd.DataFrame(
            index=self.choices(),
            columns=self.metrics(),
            dtype=float,
        )
        for choice in self.choices():
            for metric in self.metrics():
                results.loc[choice, metric] = self.score_range.normalize(
                    self._aggregate(metric, choice)
                )
        return results

    def to_html(self, path: str = None) -> Optional[str]:
        """
        Parameters
        ----------
        path : str or None
            File path where html should be written. If None, return the html as a string.

        Returns
        -------
        str or None
            If path is None, return the html as a string. Otherwise, None.
        """
        table = pd.concat((self.scores, self._get_results()), axis=1)
        self.logger.debug("table:\n{}".format(table))
        table = table.sort_values(self.metrics()[0], ascending=False)

        styler = table.style
        # scores need a color gradient that is independent of the results, but also is set based
        # on the score range, not the resultant range for that factor (column)
        styler = styler.background_gradient(
            axis="index",
            cmap=sns.color_palette("blend:darkred,green", as_cmap=True),
            subset=self.scores.columns.to_list(),
            vmin=self.score_range.min,
            vmax=self.score_range.max,
        )
        # background gradient for the results is separate, those are percentages
        styler = styler.background_gradient(
            axis="index",
            cmap=sns.color_palette("blend:darkred,green", as_cmap=True),
            subset=list(self.metrics()),
            vmin=0,
            vmax=1,
        )
        styler = styler.format({metric: "{0:.0%}" for metric in self.metrics()})
        styler = styler.set_table_styles(
            [{"selector": "th", "props": [("font-family", "Courier"), ("font-size", "11px")]}]
        )
        styler = styler.set_properties(
            **{
                "text-align": "center",
                "font-family": "Courier",
                "font-size": "11px",
            }
        )
        html = styler.to_html()

        if path is not None:
            with open(path, "w") as f:
                f.write(html)
        else:
            return html
