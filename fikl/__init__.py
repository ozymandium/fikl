import numpy as np
import yaml
import pandas as pd
import seaborn as sns

from collections import namedtuple
import logging
import pprint


MinMax = namedtuple("MinMax", ["min", "max"])


class Decision:

    ALL_KEY = "All"

    def __init__(
        self,
        choices: list[str],
        scores: dict[str, dict[str, float]],
        factors: list[str],
        weights: np.array,
        score_range: MinMax,
        metrics: dict[str, list[str]] = None,
    ):
        """
        Parameters
        ----------
        choices : list[str]
            names of the rows in the `choices` matrix. each row is a different choice.
        scores : np.array
            2d array. each row is a choice, each column is a value.
        factors : list[str]
            names of the columns in the `choices1` matrix. each column is a different value.
        weights : np.array
            1d array with a weighting for each value
        score_range : MinMax
            the minimum and maximum possible scores. if none provided, it will be inferred from
            `scores`.
        metrics : dict[str, list[str]]
            different types of metrics. each key is a metric name, each value is a list of factors
            that are included in that metric. an "All" metric is automatically added which includes
            all factors
        """
        self.logger = logging.getLogger()

        assert set(choices) == set(scores.keys())
        # assert len(factors) == scores.shape[1]
        assert len(factors) == len(weights)
        for _, included_factors in metrics.items():
            for factor in included_factors:
                assert factor in factors

        self.choices = choices
        self.scores = scores
        self.factors = factors
        self.weights = weights
        self.score_range = score_range
        # automatically add a metric with all factors
        self.metrics = {self.ALL_KEY: factors}
        if metrics is not None:
            for name, included_factors in metrics.items():
                self.metrics[name] = included_factors

        self.results = self._get_results()
        self.logger.debug("Results:\n{}".format(pprint.pformat(self.results)))

    @staticmethod
    def from_yaml(path: str):
        """
        TODO: get away from having ctor and parsing in different formats, and make it so that the
        ctor args are exactly the same as the yaml content. intermediate variable creation should be
        moved to ctor

        Parameters
        ----------
        path : str
            File path where yaml should be read

        Returns
        -------
        Decision
        """
        with open(path, "r") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)

        choices = list(data["scores"].keys())
        factors = [k for k, _ in sorted(data["weights"].items(), key=lambda item: item[1])]
        scores = data["scores"]
        weights = [data["weights"][factor] for factor in factors]
        metrics = data["metrics"]
        score_range = MinMax(**data["score_range"])

        return Decision(
            choices=choices,
            scores=scores,
            factors=factors,
            weights=weights,
            metrics=metrics,
            score_range=score_range,
        )

    def _aggregate_score(self, choice, metric):
        factors = self.metrics[metric]
        # weights are in same order as factors
        weights = np.array([self.weights[self.factors.index(factor)] for factor in factors])
        # normalize the weights
        weights = weights / np.linalg.norm(weights)
        # scores in order of factors
        scores = np.array([self.scores[choice][factor] for factor in factors])
        return weights.dot(scores)

    def _get_results(self):
        return {
            metric: {choice: self._aggregate_score(choice, metric) for choice in self.choices}
            for metric in self.metrics.keys()
        }

    def _get_scores_array(self):
        arr = np.empty((len(self.choices), len(self.factors)))
        for row, choice in enumerate(self.choices):
            for col, factor in enumerate(self.factors):
                arr[row, col] = self.scores[choice][factor]
        return arr

    def _get_results_array(self):
        metrics = list(self.metrics.keys())
        arr = np.empty((len(self.choices), len(self.metrics)))
        for row, choice in enumerate(self.choices):
            for col, metric in enumerate(metrics):
                arr[row, col] = self.results[metric][choice]
        return arr, metrics

    # def _score_to_scalar(self, score):
    #     return (score - self.score_range.min) / (self.score_range.max - self.score_range.min)

    # def _scalar_to_score(self, scalar):
    #     return scalar * (self.score_range.max - self.score_range.min) + self.score_range.min

    def to_html(self, path: str = None):
        """
        Parameters
        ----------
        path : str
            File path where html should be written
        """
        self.logger.debug("choices:\n{}".format(pprint.pformat(self.choices)))
        scores_arr = self._get_scores_array()
        results_arr, metrics = self._get_results_array()
        arr = np.concatenate((scores_arr, results_arr), axis=1)
        self.logger.debug("array\n:{}".format(arr))

        cols = self.factors + metrics
        self.logger.debug("Colums:\n{}".format(pprint.pformat(cols)))

        table = pd.DataFrame(arr, index=self.choices, columns=cols)
        table = table.sort_values(self.ALL_KEY)

        cmap = sns.color_palette("blend:darkred,green", as_cmap=True)

        html = table.style.background_gradient(axis=None, cmap=cmap).format(precision=2).to_html()

        if path is not None:
            with open(path, "w") as f:
                f.write(html)
        else:
            return html
