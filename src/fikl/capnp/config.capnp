@0x8f94dde285510ffc;

# # 1 entry for each scorer in fikl.scorers
# enum Scorer {
#     star @0;
#     bucket @1;
#     relative @2;
#     interpolate @3;
#     range @4;
# }

struct StarScorerConfig {
    min @0 :Int32;
    max @1 :Int32;
}

struct BucketScorerConfig {
    struct Bucket {
        min @0 :Float32;
        max @1 :Float32;
        val @2 :Float32;
    }
    buckets @0 :List(Bucket);
}

struct RelativeScorerConfig {
    invert @0 :Bool;
}

struct InterpolateScorerConfig {
    struct Knot {
        in @0 :Float32;
        out @1 :Float32;
    }
    knots @0 :List(Knot);
}

struct RangeScorerConfig {
    best @0 :Float32;
    worst @1 :Float32;
}

struct Factor {
    name @0 :Text;
    # the name that will be referred to in Metric.factors

    source @1 :Text;
    # this must correspond to either a column name in the user provided CSV, or a fetcher

    scoring :union {
        none @2 :Void;
        # unusable value placed here to ensure default construction raises an error
        star @3 :StarScorerConfig;
        bucket @4 :BucketScorerConfig;
        relative @5 :RelativeScorerConfig;
        interpolate @6 :InterpolateScorerConfig;
        range @7 :RangeScorerConfig;
    }
    # this creates an enum that is then used to lookup an associated scorer class in 
    # fikl.scorers.LOOKUP

    doc @8 :Text;
}

struct NameWeight {
    name @0 :Text;
    weight @1 :Float32;
}

struct Metric {
    # the name that will be referred to in Config.final
    name @0 :Text;
    # factor name and weight
    factors @1 :List(NameWeight);
}

struct Config {
    factors @0 :List(Factor);
    metrics @1 :List(Metric);
    # metric name and weight
    final @2 :List(NameWeight);
}