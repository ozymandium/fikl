from fikl.scorers import LOOKUP

from typing import Optional, Any, Dict, List, Callable
import logging
import yaml
import pprint

import pandas as pd
import numpy as np
import seaborn as sns


class Decision:
    """
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

    def _table_to_html(self, table: pd.DataFrame, is_score: bool) -> Optional[str]:
        """
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

        if is_score:
            # apply a background gradient to the whole table based on the score range
            # it is possible to apply a background gradient to a subset of the columns, using `subset`
            styler = styler.background_gradient(
                axis="index",
                cmap=sns.color_palette("blend:darkred,green", as_cmap=True),
                vmin=0.0,
                vmax=1.0,
            )

            # scores are all floats between 0 and 1, so format them as percentages
            # it is possible to apply a format to a subset of the columns, by passing a dict to format
            styler = styler.format("{0:.0%}")

        else:

            # raw data may be floats or ints. either way, we just want to remove trailing zeros so
            # that only significant digits are shown
            styler = styler.format("{0:g}")

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
        return styler.to_html()

    def to_html(self, path: str = None) -> Optional[str]:
        """ """
        raw_html = self._table_to_html(self.raw, is_score=False)
        score_html = self._table_to_html(self.scores, is_score=True)
        results_html = self._table_to_html(self._get_results(), is_score=True)

        # dump the html blobs into a template
        html = f"""
        <!DOCTYPE html>
        <html>
            <body>
                <h1>Raw Data</h1>
                <div>
                    {raw_html}
                </div>
                <h1>Scores</h1>
                <div>
                    {score_html}
                </div>
                <h1>Results</h1>
                <div>
                    {results_html}
                </div>
            </body>
        </html>
        """

        if path is not None:
            with open(path, "w") as f:
                f.write(html)
        else:
            return html
