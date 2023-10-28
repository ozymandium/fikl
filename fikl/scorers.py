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
"""
from fikl.util import ensure_type

import logging
from collections import namedtuple
from typing import Optional, Any, Dict, List, Callable

import pandas as pd
import numpy as np


class Star:
    """
    scorer that accepts input as ints on a fixed scale, such as the 5 start scale, where
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


class Bucket:
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


class Relative:
    """Assigns scores by setting the highest value to 1 and the lowest value to 0. All other values
    are linearly interpolated between those two values."""

    CODE = "relative"
    DTYPE = float

    def __init__(self, invert: bool):
        self.invert = invert

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
            logging.warning(
                f"column dtype is {col.dtype} but scorer {self} requires dtype {self.DTYPE}, casting to {self.DTYPE}"
            )
            col = col.astype(self.DTYPE)
        # compute the return
        ret = (col - col.min()) / (col.max() - col.min())
        if self.invert:
            ret = 1.0 - ret
        # make sure all values lie between 0 and 1
        assert (ret >= 0).all()
        assert (ret <= 1).all()
        return ret


class Interpolate:
    """Scorer that assigns scores by fitting a spline to user-supplied knots. Linear spline for all

    To view what cubic spines will look like:
    https://tools.timodenk.com/cubic-spline-interpolation


    """

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


LOOKUP = {
    scorer.CODE: scorer
    for scorer in [
        Star,
        Bucket,
        Relative,
        Interpolate,
    ]
}
