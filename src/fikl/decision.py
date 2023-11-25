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

    @staticmethod
    def _get_scorers(config: dict) -> dict[str, dict[str, Any]]:
        """
        Determine which scorer to use for each factor within each metric. The same factor may
        have different scorers for different metrics.
        A scorer is constructed using the config, then it takes in the value from self.raw
        and returns a score between 0 and 1. The score is then stored in self.scores.

        Parameters
        ----------
        config : dict
            dict of config values

        Returns
        -------
        dict[str, dict[str, Any]]
            dict of scorers for each metric
            key: metric name
            value: dict of scorers for each factor
                key: factor name
                value: Any
        """
        scorers = {
            metric: {
                factor: SCORER_LOOKUP[cfg["scoring"]["type"]](**cfg["scoring"]["config"])
                for factor, cfg in config["metrics"][metric].items()
            }
            for metric in config["metrics"]
        }
        return scorers

    @staticmethod
    def _get_raw(config: dict, raw_path: str, scorers: dict[str, dict[str, Any]]) -> pd.DataFrame:
        """
        Read the ranking matrix from the csv as a dataframe. The index is the choice name, the columns
        are the factors.

        Parameters
        ----------
        config : dict
            dict of config values
        raw_path : str
            File path where data csv should be read
        scorers : dict[str, dict[str, Any]]
            dict of scorers for each metric
            key: metric name
            value: dict of scorers for each factor
                key: factor name
                value: Any

        Returns
        -------
        pd.DataFrame
        """
        logger = logging.getLogger()

        raw = pd.read_csv(raw_path, index_col="choice")

        # read the ranking matrix from the csv as a dataframe
        # the index is the choice name, the columns are the factors
        raw = pd.read_csv(raw_path, index_col="choice")

        # dict of factors for each metric
        # key: metric name
        # value: list of factor names
        factors = {metric: list(config["metrics"][metric].keys()) for metric in config["metrics"]}
        logger.debug("factors: {}".format(pprint.pformat(factors)))
        all_factors = [factor for metric in factors for factor in factors[metric]]
        logger.debug("all_factors: {}".format(pprint.pformat(all_factors)))

        # any factor that is not a column in the raw data already will need to be fetched
        fetchers = {
            factor: FETCHER_LOOKUP[factor]() for factor in all_factors if factor not in raw.columns
        }
        logger.debug("fetchers: {}".format(pprint.pformat(fetchers)))
        for factor, fetcher in fetchers.items():
            raw[factor] = fetcher.fetch(self.choices())

        # allow the user to input executable code in the csv. eval it here.
        raw = raw.map(lambda x: eval(x) if isinstance(x, str) else x)

        # each scorer requires a certain dtype for the input. iterate over each factor/column and
        # make sure that the dtype is correct. if not, try to cast it to the correct type and log a
        # warning.
        for metric, metric_scorers in scorers.items():
            for factor, factor_scorer in metric_scorers.items():
                dtype = factor_scorer.DTYPE
                if not raw[factor].dtype == dtype:
                    logging.warning(
                        f"factor {factor} has dtype {raw[factor].dtype} but scorer {factor_scorer} requires dtype {dtype}, casting to {dtype}"
                    )
                    raw[factor] = raw[factor].astype(dtype)

        return raw

    @staticmethod
    def _get_scores(
        raw: pd.DataFrame, scorers: dict[str, dict[str, Any]]
    ) -> dict[str, pd.DataFrame]:
        """
        Generate a score dataframe for each metric. The index is the choice name, the columns are
        the factors. The values are the scores for that factor for that choice. If the column is
        not included in that metric, the value is np.nan

        Parameters
        ----------
        raw : pd.DataFrame
            the raw user input matrix. the index is the choice name, the columns are the factors.
        scorers : dict[str, dict[str, Any]]
            dict of scorers for each metric
            key: metric name
            value: dict of scorers for each factor
                key: factor name
                value: Any

        Returns
        -------
        dict[str, pd.DataFrame]
            dict of scores for each metric
            key: metric name
            value: dataframe with the the ranking matrix. the index is the choice name, the columns are
            the factors. values are floats between 0 and 1. for columns which are not included in that
            metric, the value is np.nan
        """
        ZEROS = lambda col: pd.Series(np.zeros(len(col)), index=col.index)
        scores = {}
        for metric, metric_scorers in scorers.items():
            fun = (
                lambda col: metric_scorers[col.name](col)
                if col.name in metric_scorers
                else ZEROS(col)
            )
            scores[metric] = raw.apply(fun, axis=0)
        return scores

    @staticmethod
    def _get_weights(config: dict, raw: pd.DataFrame) -> pd.DataFrame:
        """
        Generate the weights dataframe. The index is the metric name, the columns are the factors.
        The values are the weights for that factor for that metric. If the column is not included
        in that metric, the value is np.nan

        Parameters
        ----------
        config : dict
            dict of config values

        Returns
        -------
        pd.DataFrame
            the weights for each factor for each metric. the index is the metric name, the columns are
            the factors. the "All" metric is automatically added which includes all factors
        """
        weights = pd.DataFrame(
            0,
            columns=raw.columns,
            index=list(config["metrics"].keys()),
        )
        # for each metric, set the weights for each factor
        for metric in config["metrics"]:
            for factor in config["metrics"][metric]:
                weights.loc[metric, factor] = config["metrics"][metric][factor]["weight"]
        # normalize the weights for each metric (along each row)
        weights = weights.div(weights.sum(axis=1), axis=0)
        return weights

    @staticmethod
    def _get_results(scores: dict[str, pd.DataFrame], weights: pd.DataFrame) -> pd.DataFrame:
        """
        Generate the results dataframe. The index is the choice name, the columns are the metrics.
        The values are the results for that choice for that metric. If the column is not included
        in that metric, the value is np.nan

        Parameters
        ----------
        scores : dict[str, pd.DataFrame]
            dict of scores for each metric
            key: metric name
            value: dataframe with the the ranking matrix. the index is the choice name, the columns are
            the factors. values are floats between 0 and 1. for columns which are not included in that
            metric, the value is np.nan
        weights : pd.DataFrame
            the weights for each factor for each metric. the index is the metric name, the columns are
            the factors. the "All" metric is automatically added which includes all factors

        Returns
        -------
        pd.DataFrame
            the results table. the index is the choice name, the columns are the metrics. values are
            floats between 0 and 1.
        """
        # ensure that all entries in scores have the same rows
        index = list(scores.values())[0].index
        for _, score in scores.items():
            if not score.index.equals(index):
                raise ValueError(
                    "score index {} does not match index {}".format(score.index, index)
                )
        results = pd.DataFrame(
            data=np.empty((len(index), len(scores))),
            columns=list(scores.keys()),
            index=index,
        )
        for metric, score in scores.items():
            results[metric] = score.dot(weights.loc[metric])
        return results

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
        logger = logging.getLogger()

        # read the config yaml
        with open(config_path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        scorers = self._get_scorers(config)
        logger.debug("scorers:\n{}".format(pprint.pformat(scorers)))

        self.raw = self._get_raw(config, raw_path, scorers)
        logger.debug("raw scores:\n{}".format(self.raw))

        self.scores = self._get_scores(self.raw, scorers)
        logger.debug("Scores")
        for metric, scores in self.scores.items():
            logger.debug(f"{metric}:\n{scores}")

        self.weights = self._get_weights(config, self.raw)
        logger.debug("Weights:\n{}".format(pprint.pformat(self.weights)))

        # check and make sure that the columns are shared between scores and weights
        for metric in config["metrics"]:
            if set(self.scores[metric].columns) != set(self.weights.columns):
                raise ValueError(
                    "score columns {} do not match weight columns {}".format(
                        set(self.scores[metric].columns), set(self.weights.columns)
                    )
                )

        # generate the results table
        self.results = self._get_results(self.scores, self.weights)
        logger.debug("Results:\n{}".format(pprint.pformat(self.results)))

        # store docs for each factor and scorer
        self.factor_docs = {
            metric: {
                factor: config["metrics"][metric][factor]["doc"]
                if "doc" in config["metrics"][metric][factor]
                else "\n"
                for factor in config["metrics"][metric]
            }
        }
        self.scorer_docs = {
            metric: {factor: scorers[metric][factor].doc() for factor in scorers[metric]}
            for metric in scorers
        }

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
