from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class StarScorerConfig(_message.Message):
    __slots__ = ("min", "max")
    MIN_FIELD_NUMBER: _ClassVar[int]
    MAX_FIELD_NUMBER: _ClassVar[int]
    min: int
    max: int
    def __init__(self, min: _Optional[int] = ..., max: _Optional[int] = ...) -> None: ...

class BucketScorerConfig(_message.Message):
    __slots__ = ("buckets",)
    class Bucket(_message.Message):
        __slots__ = ("min", "max", "val")
        MIN_FIELD_NUMBER: _ClassVar[int]
        MAX_FIELD_NUMBER: _ClassVar[int]
        VAL_FIELD_NUMBER: _ClassVar[int]
        min: float
        max: float
        val: float
        def __init__(
            self,
            min: _Optional[float] = ...,
            max: _Optional[float] = ...,
            val: _Optional[float] = ...,
        ) -> None: ...
    BUCKETS_FIELD_NUMBER: _ClassVar[int]
    buckets: _containers.RepeatedCompositeFieldContainer[BucketScorerConfig.Bucket]
    def __init__(
        self, buckets: _Optional[_Iterable[_Union[BucketScorerConfig.Bucket, _Mapping]]] = ...
    ) -> None: ...

class RelativeScorerConfig(_message.Message):
    __slots__ = ("invert",)
    INVERT_FIELD_NUMBER: _ClassVar[int]
    invert: bool
    def __init__(self, invert: bool = ...) -> None: ...

class InterpolateScorerConfig(_message.Message):
    __slots__ = ("knots",)
    class Knot(_message.Message):
        __slots__ = ("out",)
        IN_FIELD_NUMBER: _ClassVar[int]
        OUT_FIELD_NUMBER: _ClassVar[int]
        out: float
        def __init__(self, out: _Optional[float] = ..., **kwargs) -> None: ...
    KNOTS_FIELD_NUMBER: _ClassVar[int]
    knots: _containers.RepeatedCompositeFieldContainer[InterpolateScorerConfig.Knot]
    def __init__(
        self, knots: _Optional[_Iterable[_Union[InterpolateScorerConfig.Knot, _Mapping]]] = ...
    ) -> None: ...

class RangeScorerConfig(_message.Message):
    __slots__ = ("best", "worst")
    BEST_FIELD_NUMBER: _ClassVar[int]
    WORST_FIELD_NUMBER: _ClassVar[int]
    best: float
    worst: float
    def __init__(self, best: _Optional[float] = ..., worst: _Optional[float] = ...) -> None: ...

class Scoring(_message.Message):
    __slots__ = ("star", "bucket", "relative", "interpolate", "range")
    STAR_FIELD_NUMBER: _ClassVar[int]
    BUCKET_FIELD_NUMBER: _ClassVar[int]
    RELATIVE_FIELD_NUMBER: _ClassVar[int]
    INTERPOLATE_FIELD_NUMBER: _ClassVar[int]
    RANGE_FIELD_NUMBER: _ClassVar[int]
    star: StarScorerConfig
    bucket: BucketScorerConfig
    relative: RelativeScorerConfig
    interpolate: InterpolateScorerConfig
    range: RangeScorerConfig
    def __init__(
        self,
        star: _Optional[_Union[StarScorerConfig, _Mapping]] = ...,
        bucket: _Optional[_Union[BucketScorerConfig, _Mapping]] = ...,
        relative: _Optional[_Union[RelativeScorerConfig, _Mapping]] = ...,
        interpolate: _Optional[_Union[InterpolateScorerConfig, _Mapping]] = ...,
        range: _Optional[_Union[RangeScorerConfig, _Mapping]] = ...,
    ) -> None: ...

class Measure(_message.Message):
    __slots__ = ("name", "source", "scoring", "doc")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    SCORING_FIELD_NUMBER: _ClassVar[int]
    DOC_FIELD_NUMBER: _ClassVar[int]
    name: str
    source: str
    scoring: Scoring
    doc: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        source: _Optional[str] = ...,
        scoring: _Optional[_Union[Scoring, _Mapping]] = ...,
        doc: _Optional[str] = ...,
    ) -> None: ...

class Factor(_message.Message):
    __slots__ = ("name", "weight")
    NAME_FIELD_NUMBER: _ClassVar[int]
    WEIGHT_FIELD_NUMBER: _ClassVar[int]
    name: str
    weight: float
    def __init__(self, name: _Optional[str] = ..., weight: _Optional[float] = ...) -> None: ...

class Metric(_message.Message):
    __slots__ = ("name", "factors")
    NAME_FIELD_NUMBER: _ClassVar[int]
    FACTORS_FIELD_NUMBER: _ClassVar[int]
    name: str
    factors: _containers.RepeatedCompositeFieldContainer[Factor]
    def __init__(
        self,
        name: _Optional[str] = ...,
        factors: _Optional[_Iterable[_Union[Factor, _Mapping]]] = ...,
    ) -> None: ...

class Config(_message.Message):
    __slots__ = ("measures", "metrics", "final")
    MEASURES_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    FINAL_FIELD_NUMBER: _ClassVar[int]
    measures: _containers.RepeatedCompositeFieldContainer[Measure]
    metrics: _containers.RepeatedCompositeFieldContainer[Metric]
    final: str
    def __init__(
        self,
        measures: _Optional[_Iterable[_Union[Measure, _Mapping]]] = ...,
        metrics: _Optional[_Iterable[_Union[Metric, _Mapping]]] = ...,
        final: _Optional[str] = ...,
    ) -> None: ...
