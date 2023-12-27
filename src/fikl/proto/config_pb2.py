# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: config.proto
# Protobuf Python Version: 4.25.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x0c\x63onfig.proto",\n\x10StarScorerConfig\x12\x0b\n\x03min\x18\x01 \x02(\x05\x12\x0b\n\x03max\x18\x02 \x02(\x05"r\n\x12\x42ucketScorerConfig\x12+\n\x07\x62uckets\x18\x01 \x03(\x0b\x32\x1a.BucketScorerConfig.Bucket\x1a/\n\x06\x42ucket\x12\x0b\n\x03min\x18\x01 \x02(\x02\x12\x0b\n\x03max\x18\x02 \x02(\x02\x12\x0b\n\x03val\x18\x03 \x02(\x02"&\n\x14RelativeScorerConfig\x12\x0e\n\x06invert\x18\x01 \x02(\x08"h\n\x17InterpolateScorerConfig\x12,\n\x05knots\x18\x01 \x03(\x0b\x32\x1d.InterpolateScorerConfig.Knot\x1a\x1f\n\x04Knot\x12\n\n\x02in\x18\x01 \x02(\x02\x12\x0b\n\x03out\x18\x02 \x02(\x02"0\n\x11RangeScorerConfig\x12\x0c\n\x04\x62\x65st\x18\x01 \x02(\x02\x12\r\n\x05worst\x18\x02 \x02(\x02" \n\x10\x42oolScorerConfig\x12\x0c\n\x04good\x18\x01 \x02(\x08"\x81\x02\n\x07Scoring\x12!\n\x04star\x18\x01 \x01(\x0b\x32\x11.StarScorerConfigH\x00\x12%\n\x06\x62ucket\x18\x02 \x01(\x0b\x32\x13.BucketScorerConfigH\x00\x12)\n\x08relative\x18\x03 \x01(\x0b\x32\x15.RelativeScorerConfigH\x00\x12/\n\x0binterpolate\x18\x04 \x01(\x0b\x32\x18.InterpolateScorerConfigH\x00\x12#\n\x05range\x18\x05 \x01(\x0b\x32\x12.RangeScorerConfigH\x00\x12!\n\x04\x62ool\x18\x06 \x01(\x0b\x32\x11.BoolScorerConfigH\x00\x42\x08\n\x06\x63onfig"O\n\x07Measure\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x0e\n\x06source\x18\x02 \x02(\t\x12\x19\n\x07scoring\x18\x03 \x02(\x0b\x32\x08.Scoring\x12\x0b\n\x03\x64oc\x18\x04 \x01(\t"&\n\x06\x46\x61\x63tor\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x0e\n\x06weight\x18\x02 \x02(\x02"0\n\x06Metric\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x18\n\x07\x66\x61\x63tors\x18\x02 \x03(\x0b\x32\x07.Factor"M\n\x06\x43onfig\x12\x1a\n\x08measures\x18\x01 \x03(\x0b\x32\x08.Measure\x12\x18\n\x07metrics\x18\x02 \x03(\x0b\x32\x07.Metric\x12\r\n\x05\x66inal\x18\x03 \x02(\t'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "config_pb2", _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _globals["_STARSCORERCONFIG"]._serialized_start = 16
    _globals["_STARSCORERCONFIG"]._serialized_end = 60
    _globals["_BUCKETSCORERCONFIG"]._serialized_start = 62
    _globals["_BUCKETSCORERCONFIG"]._serialized_end = 176
    _globals["_BUCKETSCORERCONFIG_BUCKET"]._serialized_start = 129
    _globals["_BUCKETSCORERCONFIG_BUCKET"]._serialized_end = 176
    _globals["_RELATIVESCORERCONFIG"]._serialized_start = 178
    _globals["_RELATIVESCORERCONFIG"]._serialized_end = 216
    _globals["_INTERPOLATESCORERCONFIG"]._serialized_start = 218
    _globals["_INTERPOLATESCORERCONFIG"]._serialized_end = 322
    _globals["_INTERPOLATESCORERCONFIG_KNOT"]._serialized_start = 291
    _globals["_INTERPOLATESCORERCONFIG_KNOT"]._serialized_end = 322
    _globals["_RANGESCORERCONFIG"]._serialized_start = 324
    _globals["_RANGESCORERCONFIG"]._serialized_end = 372
    _globals["_BOOLSCORERCONFIG"]._serialized_start = 374
    _globals["_BOOLSCORERCONFIG"]._serialized_end = 406
    _globals["_SCORING"]._serialized_start = 409
    _globals["_SCORING"]._serialized_end = 666
    _globals["_MEASURE"]._serialized_start = 668
    _globals["_MEASURE"]._serialized_end = 747
    _globals["_FACTOR"]._serialized_start = 749
    _globals["_FACTOR"]._serialized_end = 787
    _globals["_METRIC"]._serialized_start = 789
    _globals["_METRIC"]._serialized_end = 837
    _globals["_CONFIG"]._serialized_start = 839
    _globals["_CONFIG"]._serialized_end = 916
# @@protoc_insertion_point(module_scope)
