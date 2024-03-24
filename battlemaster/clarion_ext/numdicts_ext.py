from typing import Optional, List

import pyClarion as cl
from pyClarion import nd

from .attention import GroupedChunk


def relative_normalize(d: nd.NumDict) -> nd.NumDict:
    if len(d) == 0:
        return d
    return d / nd.reduce_max(d)


def absolute_normalize(d: nd.NumDict, divisor: float) -> nd.NumDict:
    if len(d) == 0:
        return d
    return d / divisor


def get_feature_value_by_name(feature_name: str, chunk: cl.chunk, chunk_db: cl.Chunks) -> str:
    try:
        features = chunk_db[chunk].features
        return [feature for feature in features if feature.tag == feature_name][0].val
    except IndexError:
        raise ValueError(f'chunk {chunk} does not have a feature with the name "{feature_name}"')


def get_features_by_name(feature_name: str, chunk: cl.chunk, chunk_db: cl.Chunks) -> List[cl.feature]:
    features = chunk_db[chunk].features
    return [feature for feature in features if feature.tag == feature_name]


def get_chunk_from_numdict(chunk_name: str, d: nd.NumDict) -> Optional[cl.chunk]:
    for chunk in d.keys():
        if chunk.cid == chunk_name:
            return chunk
    else:
        return None


def filter_chunks_by_group(group: str, d: nd.NumDict) -> nd.NumDict:
    result = nd.MutableNumDict(default=d.default)
    for chunk, weight in d.items():
        if isinstance(chunk, GroupedChunk) and chunk.group == group:
            result[chunk] = weight

    return nd.NumDict(result, default=d.default)


def get_only_value_from_numdict(d: nd.NumDict):
    return next(iter(d))


def is_empty(d: nd.NumDict):
    return len(d) == 0
