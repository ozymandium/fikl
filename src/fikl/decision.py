from fikl.scorers import ScorerInfo, get_scorer_info_from_config
from fikl.proto import config_pb2
from fikl.graph import create_graph
from fikl.fetchers import fetch

from typing import Optional, Any, Dict, List, Callable
import logging
import pprint
import os
import yaml
from collections import namedtuple

import pandas as pd
import numpy as np
import networkx as nx


def _get_source_data(config: config_pb2.Config, raw_path: str) -> pd.DataFrame:
    """
    Read all source data, which is referred to by the `source` field of each config_pb2.Measure.

    Parameters
    ----------
    config : dict
        dict of config values
    raw_path : str
        File path where data csv should be read

    Returns
    -------
    pd.DataFrame
        User input matrix and/or fetched data. The index is the choice name, the columns are the
        sources. The values are the values for that source for that choice.
    """
    logger = logging.getLogger()

    # read the ranking matrix from the csv as a dataframe
    # the index is the choice name, the columns are the source names
    raw = pd.read_csv(raw_path, index_col="choice")

    # allow the user to input executable code in the csv. eval it here.
    # FIXME: this is deeply unsafe. need to find a better way to do this.
    raw = raw.map(lambda x: eval(x) if isinstance(x, str) else x)

    # set of all requested sources from the config
    req_sources = set([measure.source for measure in config.measures])
    # any source that is not a column in the raw data already will need to be fetched
    missing_sources = list(req_sources.difference(set(raw.columns)))
    logger.debug("requested sources: {}".format(pprint.pformat(req_sources)))
    logger.debug("available CSV columns: {}".format(pprint.pformat(raw.columns)))
    logger.debug("missing sources:\n{}".format(pprint.pformat(missing_sources)))

    # fetch the missing sources
    fetched = fetch(missing_sources, raw.index)

    # merge
    ret = pd.concat([raw, fetched], axis=1)

    # now that the table is complete, sort the columns alphabetically
    ret = ret.reindex(sorted(ret.columns), axis=1)

    return ret


def _get_measure_data(source_data: pd.DataFrame, scorer_info: list[ScorerInfo]) -> pd.DataFrame:
    """
    Generate the measure data, which is the values for each measure for each choice. The index
    is the choice name, the columns are the measures. The values are floats between 0 and 1.

    Parameters
    ----------
    source_data : pd.DataFrame
        User input matrix and/or fetched data. The index is the choice name, the columns are the
        sources.
    scorer_info : list[ScorerInfo]
        list of scorer info objects

    Returns
    -------
    pd.DataFrame
        the measure data
    """
    # for each measure, compute the value for each choice
    measure_data = pd.DataFrame(
        index=source_data.index, columns=[entry.measure for entry in scorer_info]
    )
    for entry in scorer_info:
        measure_data[entry.measure] = entry.scorer(source_data[entry.source])
    return measure_data


def _get_weights(config: config_pb2.Config) -> pd.DataFrame:
    """
    Generate the metric weights dataframe, which is necessary to compute scores for each metric.
    The index is the metric name. The columns are all possible factors. Factors are all things
    which may be included in the weighted average used to compute each metric score. That means
    that factors include all measures and all metrics. The values are floats between 0 and 1.
    Sources are not included in the factors.

    Parameters
    ----------
    config : config_pb2.Config

    Returns
    -------
    pd.DataFrame
    """
    measure_names = [measure.name for measure in config.measures]
    metric_names = [metric.name for metric in config.metrics]
    weights = pd.DataFrame(
        0,
        index=pd.Index(metric_names, name="metric", dtype="object"),
        columns=measure_names + metric_names,
    )
    # for each metric, set the raw weights for each factor
    for metric in config.metrics:
        for factor in metric.factors:
            # a factor may be a measure or a metric
            weights.loc[metric.name, factor.name] = factor.weight
    # normalize the weights for each metric (along each row)
    weights = weights.div(weights.sum(axis=1), axis=0)
    return weights


def _get_metric_results(
    measure_data: pd.DataFrame, weights: pd.DataFrame, eval_order: list[str]
) -> pd.DataFrame:
    """
    Generate the results dataframe. The index is the choice name, the columns are the metric
    names. The values are floats between 0 and 1. Its size will be NxM where N is the number of
    choices and M is the number of metrics.

    Parameters
    ----------
    measure_data : pd.DataFrame
        the measure data, generated by _get_measure_data
    weights : pd.DataFrame
        the metric weights, generated by _get_weights
    eval_order : list[str]
        the order in which to evaluate the metrics. this is necessary because metrics may depend
        on other metrics, so we need to evaluate them in the correct order. this list will be
        assumed to include sources, and those will be ignored.

    Returns
    -------
    pd.DataFrame
        the results table. the index is the choice name, the columns are the metrics. values are
        floats between 0 and 1.
    """
    # the leftmost columns of weights should be the same as the columns of measure_data, but not
    # all of the columns of weights will be included in measure_data. just check that the first
    # columns of weights match the columns of measure_data.
    if not weights.columns[: len(measure_data.columns)].equals(measure_data.columns):
        raise ValueError(
            "weights columns are not a subset of measure_data columns. "
            f"weights columns: {weights.columns}, measure_data columns: {measure_data.columns}"
        )

    # initialize the results table as a superset. we need it to have all the columns of weights,
    # even if they are not included in measure_data. after everything is computed, we will drop
    # the columns that are measures so that only metrics remain.
    results = pd.DataFrame(
        data=0,
        index=measure_data.index,
        columns=weights.columns,
        dtype=np.float64,
    )
    # set the measure data columns
    results[measure_data.columns] = measure_data

    # compute the results for each metric sequentially in the correct order.
    # we are evaluating the results matrix in specified order because we're using it to compute
    # itself. we need to make sure that we don't use the results of a metric before it has been
    # computed.
    metric_eval_order = [metric for metric in eval_order if metric in weights.index]
    choices = measure_data.index
    for metric in metric_eval_order:
        # get the weight for all factors for this metric (row in weights)
        factor_weights = weights.loc[metric]
        # compute the results for this metric
        for choice in choices:
            # compute the weighted average
            results.loc[choice, metric] = np.dot(factor_weights, results.loc[choice])

    # drop the measure columns
    results = results.drop(columns=measure_data.columns)

    return results


class Decision:
    """
    Members
    -------
    graph : nx.DiGraph
        the graph of the config. nodes are sources, measures, and metrics. edges are factors.

    data : pd.DataFrame
        values for all sources, measures, and metrics for all choices. the index is the choice name,
        the columns are the sources, measures, and metrics. this is a heterogeneous dataframe, so
        the source columns are not constrained, and the measure/metric columns will be floats
        between 0 and 1.

    config : config_pb2.Config
        the config protobuf

    scorer_info : list[ScorerInfo]
        list of scorer info objects

    weights : pd.DataFrame
        the metric weights, generated by _get_weights
    """

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
        self.graph = create_graph(config)
        source_data = _get_source_data(config, raw_path)
        self.scorer_info = get_scorer_info_from_config(config)
        measure_data = _get_measure_data(source_data, self.scorer_info)
        self.weights = _get_weights(config)
        metric_eval_order = list(nx.topological_sort(self.graph))
        metric_results = _get_metric_results(measure_data, self.weights, metric_eval_order)

        # store dataframe with all data
        self.data = pd.concat([source_data, measure_data, metric_results], axis=1)

        self.config = config

    def sources(self) -> List[str]:
        """
        Get the names of all sources.

        Returns
        -------
        List[str]
            the names of all sources
        """
        return [measure.source for measure in self.config.measures]

    def measures(self) -> List[str]:
        """
        Get the names of all measures.

        Returns
        -------
        List[str]
            the names of all measures
        """
        return [measure.name for measure in self.config.measures]

    def metrics(self) -> List[str]:
        """
        Get the names of all metrics.

        Returns
        -------
        List[str]
            the names of all metrics
        """
        return [metric.name for metric in self.config.metrics]

    def measure_docs(self) -> List[str]:
        """
        Get the docs for all measures.

        Returns
        -------
        List[str]
            the docs for all measures
        """
        return [measure.doc for measure in self.config.measures]

    def scorer_docs(self) -> List[str]:
        """
        Get the docs for all scorers.

        Returns
        -------
        List[str]
            the docs for all scorers
        """
        return [entry.scorer.doc() for entry in self.scorer_info]

    def sources_table(self) -> pd.DataFrame:
        """
        Get the source table. This is the raw data that was input by the user, plus any data that
        was fetched. The index is the choice name, the columns are the sources.

        Returns
        -------
        pd.DataFrame
            the source table
        """
        return self.data[self.sources()]

    def measures_table(self) -> pd.DataFrame:
        """
        Get the measure table. This is the results of all measures. The index is the choice name,
        the columns are the measures.

        Returns
        -------
        pd.DataFrame
            the measure table
        """
        return self.data[self.measures()]

    # def metrics_table(self) -> pd.DataFrame:
    #     """
    #     Get the metric table. This is the results of all metrics. The index is the choice name,
    #     the columns are the metrics.

    #     Returns
    #     -------
    #     pd.DataFrame
    #         the metric table
    #     """
    #     return self.data[self.metrics()]

    def final_table(self, sort: bool = False) -> pd.DataFrame:
        """
        Get the final results. This is the final metric results, sorted by score.

        Returns
        -------
        pd.DataFrame
            the final results. the index is the choice name, the columns are the metrics. values are
            floats between 0 and 1.
        """
        ret = self.data[[self.config.final]]
        if sort:
            ret = ret.sort_values(by=self.config.final, ascending=False)
        return ret

    def answer(self) -> str:
        """
        Get top choice for the final metric.

        Returns
        -------
        str
            the top choice for the final metric
        """
        # pull out the actual value
        return self.final_table().idxmax()[0]

    def metrics_tables(self) -> List[pd.DataFrame]:
        """
        For every metric, get a table with columns for each of its factors, and a final rightmost
        column for that metric itself. The index is the choice name, the columns are the factors.

        Returns
        -------
        dict[str, pd.DataFrame]
            a dict of metric name to metric table
        """
        ret = []
        for metric_idx, metric in enumerate(self.metrics()):
            factors = [factor.name for factor in self.config.metrics[metric_idx].factors]
            metric_table = self.data[factors + [metric]]
            ret.append(metric_table)
        return ret

    def metrics_weight_tables(self) -> List[pd.Series]:
        """
        Get the weights for each metric. Order is the same as the order of metrics returned by
        Decision.metrics(). Each entry in the list is a series of weights for each factor for that
        metric. The index of the series is the factor name. Metrics which are weighted zero will
        not be included in the list.

        Returns
        -------
        List[pd.Series]
            a list of series of weights for each metric
        """
        ret = []
        for metric_idx, metric in enumerate(self.metrics()):
            factors = [factor.name for factor in self.config.metrics[metric_idx].factors]
            weights = self.weights.loc[metric][factors]
            ret.append(weights)
        return ret

    def ignored_metrics(self) -> List[str]:
        """
        Get a list of metrics that were ignored because they were not included in the final metric,
        or in any metric used by the final metric. Use the graph to work backwards from the final
        metric to find all metrics that are not used.

        Returns
        -------
        List[str]
            a list of metrics that were ignored because they were not included in the final metric
        """
        return [
            metric
            for metric in self.metrics()
            if not nx.has_path(self.graph, metric, self.config.final)
        ]

    def ignored_measures(self) -> List[str]:
        """
        Get a list of measures that were ignored because they were not included in any metric. Use
        the graph to work backwards from the final metric to find all measures that are not used.

        Returns
        -------
        List[str]
            a list of measures that were ignored because they were not included in any metric
        """
        return [
            measure
            for measure in self.measures()
            if not nx.has_path(self.graph, measure, self.config.final)
        ]

    def final_metric_idx(self) -> int:
        """
        Get the index of the final metric within the list of metrics that is output by
        Decision.metrics().

        Returns
        -------
        int
            the index of the final metric
        """
        return self.metrics().index(self.config.final)

    def metric_print_order(self) -> List[int]:
        """
        Get the order in which metrics should be shown to the user. This is the reverse of the order
        in which metrics should be evaluated. The final metric should be shown first, and
        constituents should be shown after their dependents.

        Returns
        -------
        List[int]
            a list of indices into the list of metrics that is output by Decision.metrics()
        """
        internal_metric_names = self.metrics()
        print_metric_names = list(reversed(list(nx.topological_sort(self.graph))))
        # remove everything that isn't a metric
        print_metric_names = [metric for metric in print_metric_names if metric in self.metrics()]
        # get the indices
        return [internal_metric_names.index(metric) for metric in print_metric_names]
