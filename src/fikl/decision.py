from fikl.scorers import get_scorer_from_factor
from fikl.fetchers import LOOKUP as FETCHER_LOOKUP
from fikl.util import load_yaml
from fikl.config import load as load_config
from fikl.config import find_factor
from fikl.proto import config_pb2


from typing import Optional, Any, Dict, List
import logging
import pprint
import os
import yaml
from collections import namedtuple

import pandas as pd
import numpy as np


SourceScorer = namedtuple("SourceScorer", ["source", "scorer"])
SourceScorer.__doc__ = """
A tuple of a source and a scorer. This is used to store the scorer for each factor for each metric.
"""


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
        the factors. values are floats between 0 and 1. columns which are not included in that
        metric are no longer included in the dataframe.
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
    def _get_scorers(config: config_pb2.Config) -> dict[str, dict[str, SourceScorer]]:
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
        scorers = {}
        for metric in config.metrics:
            scorers[metric.name] = {}
            for factor_nw in metric.factors:
                factor_pb = find_factor(config, factor_nw.name)
                scorer = get_scorer_from_factor(factor_pb)
                scorers[metric.name][factor_nw.name] = SourceScorer(
                    source=factor_pb.source,
                    scorer=scorer,
                )
        return scorers

    @staticmethod
    def _get_raw(
        config: config_pb2.Config, raw_path: str, scorers: dict[str, dict[str, SourceScorer]]
    ) -> pd.DataFrame:
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

        # read the ranking matrix from the csv as a dataframe
        # the index is the choice name, the columns are the factors
        raw = pd.read_csv(raw_path, index_col="choice")

        # set of all requested sources from the config
        req_sources = set([factor.source for factor in config.factors])
        logger.debug("requested sources: {}".format(pprint.pformat(req_sources)))
        logger.debug("available CSV columns: {}".format(pprint.pformat(raw.columns)))
        logger.debug("avalable fetcher sources: {}".format(pprint.pformat(FETCHER_LOOKUP.keys())))

        # any factor that is not a column in the raw data already will need to be fetched
        fetchers = {
            source: FETCHER_LOOKUP[source]() for source in req_sources if source not in raw.columns
        }
        logger.debug("fetchers: {}".format(pprint.pformat(fetchers)))
        for source, fetcher in fetchers.items():
            raw[source] = fetcher.fetch(list(raw.index))

        # allow the user to input executable code in the csv. eval it here.
        # FIXME: this is deeply unsafe. need to find a better way to do this.
        raw = raw.map(lambda x: eval(x) if isinstance(x, str) else x)

        # each scorer requires a certain dtype for the input. iterate over each factor/column and
        # make sure that the dtype is correct. if not, try to cast it to the correct type and log a
        # warning.
        for metric, metric_scorers in scorers.items():
            for factor_name, (source, scorer) in metric_scorers.items():
                have_dtype = raw[source].dtype
                req_dtype = scorer.DTYPE
                if have_dtype != req_dtype:
                    logger.warning(
                        f"factor {factor_name} for metric {metric} has dtype {have_dtype} "
                        f"but requires dtype {req_dtype}. attempting to cast."
                    )
                    raw[source] = raw[source].astype(req_dtype)

        # now that the table is complete, sort the columns alphabetically
        raw = raw.reindex(sorted(raw.columns), axis=1)

        return raw

    @staticmethod
    def _get_scores(
        raw: pd.DataFrame, scorers: dict[str, dict[str, SourceScorer]]
    ) -> dict[str, pd.DataFrame]:
        """
        Generate a score dataframe for each metric. The index is the choice name, the columns are
        the factors. The values are the scores for that factor for that choice. No columns which
        are not included in that metric are included in the dataframe.

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
            the factors. values are floats between 0 and 1.
        """
        ZEROS = lambda factor_col: pd.Series(np.zeros(len(factor_col)), index=factor_col.index)
        scores = {}
        for metric, factor_scorers in scorers.items():
            factor_names = list(factor_scorers.keys())
            scores[metric] = pd.DataFrame(
                data=np.empty((len(raw), len(factor_names))) * np.nan,
                columns=factor_names,
                index=raw.index,
            )
            for factor_name, (source, scorer) in factor_scorers.items():
                scores[metric][factor_name] = scorer(raw[source])
            # ensure no nans remain
            assert not scores[metric].isna().any().any()
        return scores

    @staticmethod
    def _get_metric_weights(config: config_pb2.Config) -> pd.DataFrame:
        """
        Generate the metric weights dataframe, which is necessary to compute results from the scores.
        The index is the metric name, the columns are the factors.
        The values are the weights for that factor for that metric. If the column is not included
        in that metric, the value is 0.

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
            columns=[factor.name for factor in config.factors],
            index=pd.Index(
                [metric.name for metric in config.metrics], name="metric", dtype="object"
            ),
        )

        # for each metric, set the weights for each factor
        for metric in config.metrics:
            for factor_nw in metric.factors:
                weights.loc[metric.name, factor_nw.name] = factor_nw.weight
        # normalize the weights for each metric (along each row)
        weights = weights.div(weights.sum(axis=1), axis=0)
        # sort
        weights = weights.sort_index(axis=0)
        weights = weights.sort_index(axis=1)
        return weights

    @staticmethod
    def _get_final_weights(config: config_pb2.Config) -> pd.Series:
        """
        Generate the final weights for each metric. The index is the metric name, the values are
        floats between 0 and 1. This is used for computing the final results from the metric results.

        Parameters
        ----------
        config : dict
            dict of config values

        Returns
        -------
        pd.Series
            the final weights for each metric. the index is the metric name, the values are floats
            between 0 and 1.
        """
        weights = pd.Series(
            data=[metric_nw.weight for metric_nw in config.final],
            index=pd.Index(
                [metric_nw.name for metric_nw in config.final], name="metric", dtype="object"
            ),
        )
        # normalize the weights
        weights = weights.div(weights.sum())
        # sort the rows alphabetically
        weights = weights.reindex(sorted(weights.index))
        return weights

    @staticmethod
    def _get_metric_results(
        scores: dict[str, pd.DataFrame], metric_weights: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Generate the results dataframe. The index is the choice name, the columns are the metrics.
        The values are the results for that choice for that metric. If the column is not included
        in that metric, it will not be included in the dataframe.

        Parameters
        ----------
        scores : dict[str, pd.DataFrame]
            dict of scores for each metric
            key: metric name
            value: dataframe with the the ranking matrix. the index is the choice name, the columns are
            the factors. values are floats between 0 and 1. columns which are not included in that
            metric are no longer included in the dataframe.
        metric_weights : pd.DataFrame
            the weights for each factor for each metric. the index is the metric name, the
            columns are the factors.

        Returns
        -------
        pd.DataFrame
            the results table. the index is the choice name, the columns are the metrics. values are
            floats between 0 and 1.
        """
        # for each table in scores, ensure that all columns are included in metric_weights
        for _, score in scores.items():
            if set(score.columns).difference(set(metric_weights.columns)):
                raise ValueError(
                    "score columns {} are not included in metric weights columns {}".format(
                        set(score.columns), set(metric_weights.columns)
                    )
                )
        # ensure that all entries in scores have the same rows
        index = list(scores.values())[0].index
        for _, score in scores.items():
            if not score.index.equals(index):
                raise ValueError(
                    "score index {} does not match index {}".format(score.index, index)
                )
        results = pd.DataFrame(
            data=np.empty((len(index), len(scores))) * np.nan,
            columns=list(scores.keys()),
            index=index,
        )
        for metric, score in scores.items():
            # metric_weights will have a column for every possible factors, but each dataframe in scores
            # will only have columns for the factors included in that metric. so we need to drop the
            # columns from metric_weights that are not included in any of the scores dataframes.
            # this is necessary because we will be multiplying the scores dataframes by the metric
            this_metric_weights = metric_weights.drop(
                columns=set(metric_weights.columns).difference(set(score.columns))
            )
            results[metric] = score.dot(this_metric_weights.T).loc[:, metric]
        assert not results.isna().any().any()
        return results

    @staticmethod
    def _get_final_results(metric_results: pd.DataFrame, final_weights: pd.Series) -> pd.Series:
        """
        Generate the final results. The index is the choice name, the values are the final results
        for that choice, and they are sorted in descending order so that the first choice is the
        best choice.

        Parameters
        ----------
        metric_results: pd.DataFrame
            the results table. the index is the choice name, the columns are the metrics. values are
            floats between 0 and 1. this is the output of _get_results()
        final_weights : pd.Series
            the final weights for each metric. the index is the metric name, the values are floats
            between 0 and 1. this is the output of _get_final_weights()

        Returns
        -------
        pd.Series
            the final results. the index is the choice name, the values are floats between 0 and 1.
        """
        # check and make sure that the columns are shared between results and final weights
        if set(metric_results.columns) != set(final_weights.index):
            raise ValueError(
                "results columns {} do not match final weights columns {}".format(
                    set(metric_results.columns), set(final_weights.index)
                )
            )
        final_results = metric_results.dot(final_weights)
        # sort by the final results
        final_results = final_results.sort_values(ascending=False)
        return final_results

    @staticmethod
    def _get_factor_docs(config: config_pb2.Config) -> dict[str, dict[str, str]]:
        """
        Get the documentation for each factor for each metric.

        Parameters
        ----------
        config : dict
            dict of config values

        Returns
        -------
        dict[str, dict[str, str]]
            dict of docs for each factor for each metric
            key: metric name
            value: dict of docs for each factor
                key: factor name
                value: str
        """
        factor_docs = {}
        for metric_pb in config.metrics:
            factor_docs[metric_pb.name] = {}
            for factor_nw in metric_pb.factors:
                factor_pb = find_factor(config, factor_nw.name)
                factor_docs[metric_pb.name][factor_nw.name] = factor_pb.doc
        return factor_docs

    @staticmethod
    def _get_scorer_docs(scorers: dict[str, dict[str, SourceScorer]]) -> dict[str, dict[str, str]]:
        """
        Get the documentation for each scorer for each metric.

        Parameters
        ----------
        scorers : dict[str, dict[str, SourceScorer]]
            dict of scorers for each metric
            key: metric name
            value: dict of scorers for each factor
                key: factor name
                value: SourceScorer

        Returns
        -------
        dict[str, dict[str, str]]
            dict of docs for each scorer for each metric
            key: metric name
            value: dict of docs for each scorer
                key: factor name
                value: str
        """
        scorer_docs = {}
        for metric, metric_scorers in scorers.items():
            scorer_docs[metric] = {}
            for factor_name, (source, scorer) in metric_scorers.items():
                scorer_docs[metric][factor_name] = scorer.doc()
        return scorer_docs

    def __init__(self, config: config_pb2, raw_path: str):
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

        scorers = self._get_scorers(config)
        logger.debug("scorers:\n{}".format(pprint.pformat(scorers)))

        self.raw = self._get_raw(config, raw_path, scorers)
        logger.debug("raw scores:\n{}".format(self.raw))

        self.scores = self._get_scores(self.raw, scorers)
        logger.debug("Scores")
        for metric, scores in self.scores.items():
            logger.debug(f"{metric}:\n{scores}")

        self.metric_weights = self._get_metric_weights(config)
        logger.debug("Weights:\n{}".format(pprint.pformat(self.metric_weights)))

        # generate the results table
        self.metric_results = self._get_metric_results(self.scores, self.metric_weights)
        logger.debug("Results:\n{}".format(pprint.pformat(self.metric_results)))

        # generate the final weights
        self.final_weights = self._get_final_weights(config)

        # generate the final results
        self.final_results = self._get_final_results(self.metric_results, self.final_weights)

        # store docs for each factor and scorer
        self.factor_docs = self._get_factor_docs(config)
        self.scorer_docs = self._get_scorer_docs(scorers)

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
        return list(self.metric_weights.index)

    def all_factors(self) -> list[str]:
        """
        Returns
        -------
        list[str]
            list of factor names
        """
        return list(self.metric_weights.columns)

    def metric_factors(self) -> dict[str, list[str]]:
        """
        Get a list of factors for each metric whose weights are non-zero

        Returns
        -------
        dict[str, list[str]]
            dict of factors for each metric
            key: metric name
            value: list of factor names
        """
        return {
            metric: list(self.metric_weights.columns[self.metric_weights.loc[metric] > 0])
            for metric in self.metrics()
        }

    def answer(self) -> str:
        """
        Returns
        -------
        str
            the best choice
        """
        return self.final_results.index[0]
