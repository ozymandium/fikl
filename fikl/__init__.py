import numpy as np
import yaml
import pandas as pd
import seaborn as sns

from collections import namedtuple
import logging
import pprint
from typing import Optional, Any, Dict, List, Callable


def ensure_type(obj, t):
    """Ensure that an object is of a certain type"""
    if type(obj) is not t:
        raise TypeError("object {} is not of type {}".format(obj, t))


class StarScorer:
    """
    scorer that accepts input as ints on a fixed scale, such as the 5 start scale, where
    1 is the lowest and 5 is the highest.
    """

    # how user requests that scoring be done using this scorer
    CODE = "star"
    # required type of input
    DTYPE = int

    def __init__(self, min: int, max: int):
        ensure_type(min, int)
        ensure_type(max, int)
        if min >= max:
            raise ValueError("min {} must be < max {}".format(min, max))
        self.min = min
        self.max = max
        self.range = max - min

    def __call__(self, col: pd.Series) -> pd.Series:
        """
        Parameters
        ----------
        col : pd.Series
            the column to score

        Returns
        -------
        pd.Series
            the scored column, with values between 0 and 1
        """
        # make sure all values are between the min and max
        if not (col >= self.min).all():
            raise ValueError(f"all values in column must be >= {self.min}, but got\n{col}")
        if not (col <= self.max).all():
            raise ValueError(f"all values in column must be <= {self.max}, but got\n{col}")
        # make sure all values are ints
        if not col.dtype == int:
            raise ValueError(f"all values in column must be ints but col dtype is {col.dtype}")
        # compute the return
        ret = (col - self.min) / self.range
        # make sure all values lie between 0 and 1
        if not (ret >= 0).all():
            raise ValueError(f"all values in column must be >= 0, but got\n{ret}")
        if not (ret <= 1).all():
            raise ValueError(f"all values in column must be <= 1, but got\n{ret}")
        return ret


class BucketScorer:
    """User sets bins for lumping input values into groups that all get that same score."""

    # how user requests that scoring be done using this scorer
    CODE = "bucket"
    # required type of input
    DTYPE = float

    class Bucket(namedtuple("Bucket", ["min", "max", "val"])):
        """A bucket is a range of values that all get the same score."""

        def __new__(cls, min: float, max: float, val: float):
            # if inputs are not floats, cast them to floats, but log a warning
            if not isinstance(min, float):
                logging.warning(f"min {min} is not a float, casting to float")
                min = float(min)
            if not isinstance(max, float):
                logging.warning(f"max {max} is not a float, casting to float")
                max = float(max)
            if not isinstance(val, float):
                logging.warning(f"val {val} is not a float, casting to float")
                val = float(val)
            # validate inputs
            if min >= max:
                raise ValueError(f"min {min} must be < max {max}")
            if val < 0 or val > 1:
                raise ValueError(f"val {val} must be between 0 and 1")
            return super().__new__(cls, min, max, val)

    def __init__(self, buckets: List[Dict[str, float]]):
        """
        Parameters
        ----------
        buckets : dict
            each bucket is a dict with keys "min", "max", and "val". min and max are the range of
            values that get the score val. min and max must be the same type. val must be a float
            between 0 and 1.
        """
        ensure_type(buckets, list)
        # store buckets in order of increasing min. Allow the bucket ctor to do the validation.
        self.buckets: List[Bucket] = sorted(
            [self.Bucket(**b) for b in buckets], key=lambda b: b.min
        )
        # ensure that the buckets are contiguous
        for i, bucket in enumerate(self.buckets[:-1]):
            if bucket.max != self.buckets[i + 1].min:
                raise ValueError(
                    "buckets must be contiguous, but got buckets {} and {}".format(
                        bucket, self.buckets[i + 1]
                    )
                )
        # ensure the type of the min and max are the same for all buckets
        if not all([type(bucket.min) is type(self.buckets[0].min) for bucket in self.buckets]):
            raise TypeError(
                "all buckets must have the same type for min and max, but got {}".format(
                    [type(bucket.min) for bucket in self.buckets]
                )
            )

    def __call__(self, col: pd.Series) -> pd.Series:
        """
        Parameters
        ----------
        col : pd.Series
            the column to score

        Returns
        -------
        pd.Series
            the scored column, with values between 0 and 1
        """
        # make sure all values are between the min and max
        if not (col >= self.buckets[0].min).all():
            raise ValueError(
                f"all values in column must be >= {self.buckets[0].min}, but got\n{col}"
            )
        if not (col <= self.buckets[-1].max).all():
            raise ValueError(
                f"all values in column must be <= {self.buckets[-1].max}, but got\n{col}"
            )
        # make sure all values are same type as bucket min and max
        if not col.dtype == type(self.buckets[0].min):
            raise ValueError(
                f"all values in column must be same type as bucket min {self.buckets[0].min} but col dtype is {col.dtype}"
            )
        # make sure all inputs are between the min and max of some bucket
        if not (col >= self.buckets[0].min).any():
            raise ValueError(
                f"all values in column must be >= {self.buckets[0].min}, but got\n{col}"
            )
        if not (col <= self.buckets[-1].max).any():
            raise ValueError(
                f"all values in column must be <= {self.buckets[-1].max}, but got\n{col}"
            )
        # compute the return
        ret = np.zeros_like(col, dtype=float)
        for bucket in self.buckets:
            ret[(col >= bucket.min) & (col < bucket.max)] = bucket.val
        # make sure all values lie between 0 and 1
        if not (ret >= 0).all():
            raise ValueError(f"all values in column must be >= 0, but got\n{ret}")
        if not (ret <= 1).all():
            raise ValueError(f"all values in column must be <= 1, but got\n{ret}")
        return ret


SCORERS = {
    StarScorer,
    BucketScorer,
}
SCORERS_LOOKUP = {scorer.CODE: scorer for scorer in SCORERS}


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
        scorers: Dict[str, Callable] = {}
        for factor, cfg in config["factors"].items():
            scorer_t = SCORERS_LOOKUP[cfg["type"]]
            scorer_config = cfg["config"]
            scorers[factor] = scorer_t(**scorer_config)
        self.logger.debug(f"scorers: {scorers}")

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
            vmin=0.0,
            vmax=1.0,
        )
        # # background gradient for the results is separate, those are percentages
        # styler = styler.background_gradient(
        #     axis="index",
        #     cmap=sns.color_palette("blend:darkred,green", as_cmap=True),
        #     subset=list(self.metrics()),
        #     vmin=0,
        #     vmax=1,
        # )
        # styler = styler.format({metric: "{0:.0%}" for metric in self.metrics()})
        styler = styler.format("{0:.0%}")
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
