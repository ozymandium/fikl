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

        # assert that all scores are ints
        assert type(score_range.min) is int
        assert type(score_range.max) is int
        for choice in scores:
            for factor in scores[choice]:
                assert type(scores[choice][factor]) is int

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

    def _aggregate(self, metric, choice: str = None, fixed_score: float = None):
        factors = self.metrics[metric]
        # weights are in same order as factors
        weights = np.array([self.weights[self.factors.index(factor)] for factor in factors])
        # normalize the weights
        weights = weights / np.linalg.norm(weights)
        # scores in order of factors
        if fixed_score is not None:
            scores = fixed_score * np.ones((len(factors),))
        else:
            scores = np.array([self.scores[choice][factor] for factor in factors])
        return weights.dot(scores)

    def _get_results(self):
        results = {}
        for metric in self.metrics.keys():
            agg_range = MinMax(
                min=self._aggregate(metric, fixed_score=self.score_range.min),
                max=self._aggregate(metric, fixed_score=self.score_range.max),
            )
            results[metric] = {}
            for choice in self.choices:
                agg = self._aggregate(metric, choice)
                scalar = Decision._scalar_from_score(agg, agg_range)
                results[metric][choice] = Decision._score_from_scalar(scalar, self.score_range)
        return results

    def _get_scores_df(self) -> pd.DataFrame:
        arr = np.empty((len(self.choices), len(self.factors)), dtype=np.int32)
        for row, choice in enumerate(self.choices):
            for col, factor in enumerate(self.factors):
                arr[row, col] = self.scores[choice][factor]
        return pd.DataFrame(arr, columns=self.factors, index=self.choices)

    def _get_results_df(self) -> pd.DataFrame:
        metrics = list(self.metrics.keys())
        arr = np.empty((len(self.choices), len(metrics)))
        for row, choice in enumerate(self.choices):
            for col, metric in enumerate(metrics):
                arr[row, col] = self.results[metric][choice]
        df = pd.DataFrame(arr, columns=metrics, index=self.choices)
        return df

    @staticmethod
    def _scalar_from_score(score, score_range):
        return (score - score_range.min) / (score_range.max - score_range.min)

    @staticmethod
    def _score_from_scalar(scalar, score_range):
        return scalar * (score_range.max - score_range.min) + score_range.min

    def to_html(self, path: str = None):
        """
        Parameters
        ----------
        path : str
            File path where html should be written
        """
        self.logger.debug("choices:\n{}".format(pprint.pformat(self.choices)))
        scores_df = self._get_scores_df()
        results_df = self._get_results_df()

        table = pd.concat((scores_df, results_df), axis=1)
        self.logger.debug("table:\n{}".format(table))

        table = table.sort_values(self.ALL_KEY)

        cmap = sns.color_palette("blend:darkred,green", as_cmap=True)

        html = (
            table.style.background_gradient(axis=None, cmap=cmap)
            .format(precision=2)
            .set_table_styles(
                [{"selector": "th", "props": [("font-family", "Courier"), ("font-size", "11px")]}]
            )
            .set_properties(
                **{
                    "text-align": "center",
                    "font-family": "Courier",
                    "font-size": "11px",
                }
            )
            .to_html()
        )

        if path is not None:
            with open(path, "w") as f:
                f.write(html)
        else:
            return html
