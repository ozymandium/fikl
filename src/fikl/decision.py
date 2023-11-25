from fikl.scorers import LOOKUP as SCORER_LOOKUP
from fikl.fetchers import LOOKUP as FETCHER_LOOKUP

from typing import Optional, Any, Dict, List
import logging
import yaml
import pprint
import os

import pandas as pd
import numpy as np


class Decision:
    """
    TODO: swap to functional/imperative style instead of OOP.

    Members
    -------
    logger : logging.Logger
        logger for this class
    raw : pd.DataFrame
        the raw user input matrix. the index is the choice name, the columns are the factors. 
        when a column is missing from the user-provided csv, it is fetched from the fetcher and 
        added to the dataframe
    scores : dict[str, pd.DataFrame]
        scores for each metric.
        key: the name of the metric
        value: dataframe with the the ranking matrix. the index is the choice name, the columns are 
        the factors. values are floats between 0 and 1. for columns which are not included in that
        metric, the value is np.nan
    weights : pd.DataFrame
        the weights for each factor for each metric. the index is the metric name, the columns are
        the factors. the "All" metric is automatically added which includes all factors
    results : pd.DataFrame
        the results table. the index is the choice name, the columns are the metrics. values are
        floats between 0 and 1.

    Methods
    -------
    choices() -> list[str]
        Get the list of choice names
    metrics() -> list[str]
        Get the list of metric names
    factors(metric) -> list[str]
        Get the list of all factor names if no metric is provided, or the list of factor names for
        the given metric
    """

    def __init__(self, config_path: str, raw_path: str):
        """
        Parameters
        ----------
        config_path : str
            File path where config yaml should be read
        raw_path : str
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
        self.raw = pd.read_csv(raw_path, index_col="choice")

        # dict of factors for each metric
        # key: metric name
        # value: list of factor names
        factors = {
            metric: list(config["metrics"][metric].keys())
            for metric in config["metrics"]
        }
        self.logger.debug("factors: {}".format(pprint.pformat(factors)))
        all_factors = [factor for metric in factors for factor in factors[metric]]
        self.logger.debug("all_factors: {}".format(pprint.pformat(all_factors)))

        # any factor that is not a column in the raw data already will need to be fetched
        fetchers = {
            factor: FETCHER_LOOKUP[factor]()
            for factor in all_factors
            if factor not in self.raw.columns
        }
        self.logger.debug("fetchers: {}".format(pprint.pformat(fetchers)))
        for factor, fetcher in fetchers.items():
            self.raw[factor] = fetcher.fetch(self.choices())

        # allow the user to input executable code in the csv. eval it here.
        self.raw = self.raw.map(lambda x: eval(x) if isinstance(x, str) else x)
        self.logger.debug("raw scores:\n{}".format(self.raw))

        # determine which scorer to use for each factor within each metric. the same factor may
        # have different scorers for different metrics.
        # a scorer is constructed using the config, then it takes in the value from self.raw
        # and returns a score between 0 and 1. the score is then stored in self.scores.
        scorers = {
            metric: {
                factor: SCORER_LOOKUP[cfg["scoring"]["type"]](**cfg["scoring"]["config"])
                for factor, cfg in config["metrics"][metric].items()
            }
            for metric in config["metrics"]
        }
        self.logger.debug("scorers:\n{}".format(pprint.pformat(scorers)))

        # each scorer requires a certain dtype for the input. iterate over each factor/column and
        # make sure that the dtype is correct. if not, try to cast it to the correct type and log a
        # warning.
        for metric, scorer_dict in scorers.items():
            for factor, scorer in scorer_dict.items():
                dtype = scorer.DTYPE
                if not self.raw[factor].dtype == dtype:
                    logging.warning(
                        f"factor {factor} has dtype {self.raw[factor].dtype} but scorer {scorer} requires dtype {dtype}, casting to {dtype}"
                    )
                    self.raw[factor] = self.raw[factor].astype(dtype)

        # for each metric, generate a score dataframe where the index is the choice name and the
        # columns are the factors. the values are the scores for that factor for that choice.
        # if the column is not included in that metric, the value is np.nan
        self.scores = {
            metric: self.raw.apply(lambda col: scorers[col.name](col) if col.name in scorers else np.nan, axis=0)
            for metric, scorers in scorers.items()
        }
        self.logger.debug("Scores")
        for metric, scores in self.scores.items():
            self.logger.debug(f"{metric}:\n{scores}")

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
        self.logger.debug("Weights:\n{}".format(pprint.pformat(self.weights)))

        # check and make sure that the columns are shared between scores and weights
        if set(self.scores.columns) != set(self.weights.columns):
            raise ValueError(
                "score columns {} do not match weight columns {}".format(
                    set(self.scores.columns), set(self.weights.columns)
                )
            )

        # generate the results table
        self.results = self.scores.dot(self.weights.T)
        self.logger.debug("Results:\n{}".format(pprint.pformat(self.results)))

        # store docs for each factor and scorer
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
        return list(self.raw.index)

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
