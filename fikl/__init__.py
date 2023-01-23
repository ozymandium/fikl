import numpy as np

import yaml

# from typing import Dict


class Decision:
    def __init__(
        self,
        choices: list[str],
        scores: np.array,
        factors: list[str],
        weights: np.array,
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
        metrics : dict[str, list[str]]
            different types of metrics. each key is a metric name, each value is a list of factors
            that are included in that metric. an "All" metric is automatically added which includes
            all factors
        """
        assert len(choices) == scores.dim[0]
        assert len(factors) == scores.dim[1]
        assert len(factors) == len(weights)
        for _, included_factors in metrics.items():
            for factor in included_factors:
                assert factor in factors

        self.choices = choices
        self.scores = scores
        self.factors = factors
        self.weights = weights
        # automatically add
        self.metrics = {"All": factors}
        if metrics is not None:
            for name, included_factors in metrics.items():
                metrics[name] = included_factors

    @staticmethod
    def from_yaml(path: str):
        """
        Parameters
        ----------
        path : str
            File path where yaml should be read
        """
        with open(path, "r") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)

        choices = data.scores.keys()
        scores = np.empty((len(choices), len(factors)))
        for row, choice in enumerate(choices):
            for col, factor in enumerate(factors):
                scores[row, col] = data.scores[choice][factor]
        factors = [k for k, v in sorted(data.weights.items(), key=lambda item: item[1])]
        weights = [data.weights[factor] for factor in factors]
        metrics = data.metrics

        return Decision(
            choices=choices, scores=scores, factors=factors, weights=weights, metrics=metrics
        )

    def to_html(self, path: str):
        """
        Parameters
        ----------
        path : str
            File path where html should be written
        """
        pass
