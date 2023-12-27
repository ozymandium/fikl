"""
Scorers are used to assign scores to columns of data. The user specifies the scorer and its
parameters in the config file. The scorer is then used to assign scores to the column of data
specified by the user.

Each scorer class has a CODE attribute that the user specifies in the config file. The scorer
class is then looked up in the LOOKUP dict using the CODE as the key. The scorer class is then
instantiated with the parameters specified in the config file. 

The config file should have a section that looks like this:

```yaml
<data column name>:
    type: <scorer code>
    config:
        <scorer config dict, which is passed to the scorer class as kwargs>
```

TODO:
- each scorer only ever gets used once. as such, they don't have to be as robust as they are. 
- make each constructor take in the corresponding protobuf scorer config object instead of kwargs
"""
from fikl.util import ensure_type
from fikl.proto import config_pb2

import logging
from collections import namedtuple
from typing import Optional, Any, Dict, List, Callable
from inspect import cleandoc

import pandas as pd
import numpy as np
from google.protobuf.json_format import MessageToDict


class Star:
    """
    Scorer that accepts input as ints on a fixed scale, such as the 5 start scale, where
    1 is the lowest and 5 is the highest.
    """

    # how user requests that scoring be done using this scorer
    CODE = "star"
    # required type of input
    DTYPE = int

    def __init__(self, min: int, max: int):
        """
        Parameters
        ----------
        min : int
            the minimum value in the input scale. For example, this would be 1 for the 5 star scale.
            An input with this value will get a 0.0 return value from the scorer.
        max : int
            the maximum value in the input scale. For example, this would be 5 for the 5 star scale.
            An input with this value will get a 1.0 return value from the scorer.
        """
        ensure_type(min, int)
        ensure_type(max, int)
        if min >= max:
            raise ValueError("min {} must be < max {}".format(min, max))
        self.min = min
        self.max = max
        self.range = max - min

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Star):
            return False
        return self.min == other.min and self.max == other.max

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
        ensure_type(col, pd.Series)
        # make sure all values are between the min and max
        if not (col >= self.min).all():
            raise ValueError(f"all values in column must be >= {self.min}, but got\n{col}")
        if not (col <= self.max).all():
            raise ValueError(f"all values in column must be <= {self.max}, but got\n{col}")
        # make sure all values are ints
        if not col.dtype == int:
            raise TypeError(f"all values in column must be ints but col dtype is {col.dtype}")
        # compute the return
        ret = (col - self.min) / self.range
        # make sure all values lie between 0 and 1. use assertion since this should never happen.
        assert (ret >= 0).all() and (ret <= 1).all()
        return ret

    def doc(self) -> str:
        """Publish Markdown documentation for this scorer."""
        return """
            {min} to {max} stars, where {min} = 0%, and {max} = 100%.
            """.format(
            min=self.min, max=self.max
        )


class Bucket:
    """User sets bins for lumping input values into groups that all get that same score."""

    # how user requests that scoring be done using this scorer
    CODE = "bucket"
    # required type of input
    DTYPE = float

    class Pail:
        """A range of values that all get the same score.

        TODO: replace with config_pb2.BucketScorerConfig.Bucket
        """

        def __init__(self, min: float, max: float, val: float):
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
            # store inputs
            self.min = min
            self.max = max
            self.val = val

        def __eq__(self, other: Any) -> bool:
            if not isinstance(other, Bucket.Pail):
                return False
            return self.min == other.min and self.max == other.max and self.val == other.val

        def __repr__(self) -> str:
            return f"Bucket.Pail(min={self.min}, max={self.max}, val={self.val})"

    def __init__(self, buckets: List[Dict[str, float]]):
        """
        Parameters
        ----------
        pails : dict
            each bucket is a dict with keys "min", "max", and "val". min and max are the range of
            values that get the score val. min and max must be the same type. val must be a float
            between 0 and 1.
        """
        ensure_type(buckets, list)
        # store pails in order of increasing min. Allow the bucket ctor to do the validation.
        self.pails: List[Bucket.Pail] = sorted(
            [Bucket.Pail(**entry) for entry in buckets], key=lambda b: b.min
        )
        # ensure that the pails are contiguous
        for i, pail in enumerate(self.pails[:-1]):
            if pail.max != self.pails[i + 1].min:
                raise ValueError(
                    "pails must be contiguous, but got pails {} and {}".format(
                        pail, self.pails[i + 1]
                    )
                )
        # ensure the type of the min and max are the same for all pails
        if not all([type(pail.min) is type(self.pails[0].min) for pail in self.pails]):
            raise TypeError(
                "all pails must have the same type for min and max, but got {}".format(
                    [type(pail.min) for pail in self.pails]
                )
            )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Bucket):
            return False
        return self.pails == other.pails

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
        if not (col >= self.pails[0].min).all():
            raise ValueError(f"all values in column must be >= {self.pails[0].min}, but got\n{col}")
        if not (col < self.pails[-1].max).all():
            raise ValueError(
                f"all values in column must be <= {self.pails[-1].max}, but got\n{col}"
            )
        # make sure all values are same type as bucket min and max
        if not col.dtype == type(self.pails[0].min):
            raise ValueError(
                f"all values in column must be same type as bucket min {self.pails[0].min} but col dtype is {col.dtype}"
            )
        # compute the return and check for values which are not in any bucket
        ret = pd.Series(np.zeros(len(col)), index=col.index)  # type: ignore
        for bucket in self.pails:
            ret[(col >= bucket.min) & (col < bucket.max)] = bucket.val
        # make sure all values lie between 0 and 1
        assert (ret >= 0).all() and (ret <= 1).all()
        return ret

    def doc(self) -> str:
        """Publish Markdown documentation for this scorer."""
        return (
            cleandoc(
                """
            Buckets: The following buckets are used to assign scores:
            
            | Min | Max | Score (%) |
            |-----|-----|-----------|
            """
            )
            + "\n{}".format(
                "\n".join(
                    [f"| {pail.min} | {pail.max} | {pail.val * 100} |" for pail in self.pails]
                )
            )
        )


class Relative:
    """Assigns scores by setting the highest value to 1 and the lowest value to 0. All other values
    are linearly interpolated between those two values.
    """

    CODE = "relative"
    DTYPE = float

    def __init__(self, invert: bool):
        self.invert = invert

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Relative):
            return False
        return self.invert == other.invert

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
        # make sure all values are DTYPE. if not, try to cast them to DTYPE and log a warning.
        ensure_type(col, pd.Series)
        if not col.dtype == self.DTYPE:
            logging.warning(
                f"column dtype is {col.dtype} but scorer {self} requires dtype {self.DTYPE}, casting to {self.DTYPE}"
            )
            col = col.astype(self.DTYPE)
        # compute the return
        ret = (col - col.min()) / (col.max() - col.min())
        if self.invert:
            ret = 1.0 - ret
        # make sure all values lie between 0 and 1
        assert (ret >= 0).all() and (ret <= 1).all()
        return ret

    def doc(self) -> str:
        """Publish Markdown documentation for this scorer."""
        if self.invert:
            return """
                Relative to other values & lower is better: The highest value gets 0%, and the lowest value gets 100%.
                """
        else:
            return """
                Relative to other values & higher is better: The lowest value gets 0%, and the highest value gets 100%.
                """


class Interpolate:
    """Scorer that does linear interpolates between user-specified knots."""

    CODE = "interpolate"
    DTYPE = float

    def __init__(self, knots: List[dict[str, float]]):
        """
        Parameters
        ----------
        knot_config : dict
            each knot is a dict with keys "in" and "out". "in" is the x value, and "out" is the y
            value. "out" must be between 0 and 1. "in" corresponds to user input, and "out" is the
            score that will be assigned to that input.
        """
        # let's call x the input and y the output
        self.knots = pd.DataFrame(knots)
        # ensure that the knots are given in increasing "in" order
        if not (self.knots["in"].diff()[1:] >= 0).all():  # first diff is NaN
            raise ValueError("knots must be given in increasing order of input")
        # ensure that outputs are all between 0 and 1
        if not (self.knots["out"] >= 0).all() or not (self.knots["out"] <= 1).all():
            raise ValueError("all outputs must be between 0 and 1")
        # create a function to interpolate between the knots
        self.spline = lambda x: np.interp(x, self.knots["in"], self.knots["out"])

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Interpolate):
            return False
        return self.knots.equals(other.knots)

    def __call__(self, col: pd.Series) -> np.ndarray:
        """
        Parameters
        ----------
        col : pd.Series
            the column to score

        Returns
        -------
        np.ndarray
            scored column, with values between 0 and 1
        """
        # make sure all values are DTYPE. if not, try to cast them to DTYPE and log a warning.
        if not col.dtype == self.DTYPE:
            logging.warning(
                f"column dtype is {col.dtype} but scorer {self} requires dtype {self.DTYPE}, casting to {self.DTYPE}"
            )
            col = col.astype(self.DTYPE)
        # we don't want to extrapolate, so make sure all values are between the min and max
        if not (col >= self.knots["in"].min()).all() or not (col <= self.knots["in"].max()).all():
            raise ValueError(
                f"all values in column must be between {self.knots['in'].min()} and {self.knots['in'].max()}, but got\n{col}"
            )
        # compute the return
        ret = self.spline(col)
        # make sure all values lie between 0 and 1
        if not (ret >= 0).all() or not (ret <= 1).all():
            raise ValueError(f"all values in column must be between 0 and 1, but got\n{ret}")
        return ret

    def doc(self) -> str:
        """Publish Markdown documentation for this scorer. Print out the knots in a Markdown table,
        and multiply the "out" column by 100 so that it's a percentage, but don't change the "in"
        column.
        """
        return (
            cleandoc(
                """
            Linearly interpolated between the following knots:
            
            | Value | Score (%) |
            |-------|-----------|
            """
            )
            + "\n{}".format(
                "\n".join(
                    [
                        f"| {knot['in']} | {knot['out'] * 100} |"
                        for knot in self.knots.to_dict(orient="records")
                    ]
                )
            )
        )


class Range(Interpolate):
    """Simplified version of Interpolate that only allows two knots, one at 0 score output and one
    at 1 score output. The input values are linearly interpolated between the two knots.
    """

    CODE = "range"
    DTYPE = float

    def __init__(self, worst: float, best: float):
        # may be that lower value is max and higher value is min, so swap them if necessary.
        # best is always 1.0 and worst is always 0.0, but the knots have to be given in the
        # correct order.
        if worst < best:
            super().__init__([{"in": worst, "out": 0}, {"in": best, "out": 1}])
        elif worst > best:
            super().__init__([{"in": best, "out": 1}, {"in": worst, "out": 0}])
        else:
            raise ValueError("worst and best must be different")

    def doc(self) -> str:
        """Publish Markdown documentation for this scorer. Print out the knots in text format."""
        return f"""
            Linearly interpolated with {self.knots["in"][0]} mapped to {self.knots["out"][0] * 100}%
            and {self.knots["in"][1]} mapped to {self.knots["out"][1] * 100}%.
            """


class Bool:
    """Scorer that assigns a boolean value to either 0% or 100%."""

    CODE = "bool"
    DTYPE = bool

    def __init__(self, good: bool):
        """
        Parameters
        ----------
        good : bool
            whether true is good or bad. if true, then true will be assigned 100% and false will be
            assigned 0%. if false, then true will be assigned 0% and false will be assigned 100%.
        """
        self.good = good

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Bool):
            return False
        return self.good == other.good

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
        # make sure all values are DTYPE. if not, try to cast them to DTYPE and log a warning.
        if not col.dtype == self.DTYPE:
            raise TypeError(
                f"column dtype is {col.dtype} but scorer {self} requires dtype {self.DTYPE}"
            )
        # compute the return
        if self.good:
            return col.astype(float)
        else:
            return (~col).astype(float)

    def doc(self) -> str:
        """Publish Markdown documentation for this scorer."""
        if self.good:
            return """
                Boolean & true is good: True gets 100%, False gets 0%.
                """
        else:
            return """
                Boolean & false is good: True gets 0%, False gets 100%.
                """


# FIXME: this is kinda ugly, do an import / module getattr in Decision instead?
_SCORER_TYPES = [Star, Bucket, Relative, Interpolate, Range, Bool]
_LOOKUP = {scorer_type.CODE: scorer_type for scorer_type in _SCORER_TYPES}


ScorerInfo = namedtuple("ScorerInfo", ["measure", "source", "scorer"])
ScorerInfo.__doc__ = """
A tuple of a source and a scorer. This is used to store the scorer for each factor for each metric.

Attributes
----------
measure : str
    measure name
source : str
    source name
scorer : Callable
    scorer class that has been instantiated
"""


def get_scorer_info(measure: config_pb2.Measure) -> ScorerInfo:
    """Given a measure, return the scorer that it specifies.

    Parameters
    ----------
    measure : config_pb2.Measure

    Returns
    -------
    ScorerInfo
    """
    which = measure.scoring.WhichOneof("config")
    if which is None:
        raise ValueError("Measure {} does not specify a scorer".format(measure))
    scorer_type = _LOOKUP[which]
    assert which == scorer_type.CODE
    scorer_config = getattr(measure.scoring, which)
    scorer_config_dict = MessageToDict(scorer_config)
    return ScorerInfo(
        measure=measure.name, source=measure.source, scorer=scorer_type(**scorer_config_dict)
    )


def get_scorer_info_from_config(config: config_pb2.Config) -> List[ScorerInfo]:
    """Given a config, return a list of scorer info for each measure.

    Parameters
    ----------
    config : config_pb2.Config

    Returns
    -------
    List[ScorerInfo]
    """
    return [get_scorer_info(measure) for measure in config.measures]
