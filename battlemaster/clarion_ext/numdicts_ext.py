import pyClarion as cl
from pyClarion import nd


def normalize(d: nd.NumDict) -> nd.NumDict:
    if len(d) == 0:
        return d
    return d / nd.reduce_max(d)


def get_feature_value_by_name(feature_name: str, chunk: cl.chunk, chunk_db: cl.Chunks) -> str:
    try:
        features = chunk_db[chunk].features
        return [feature for feature in features if feature.cid[0][0] == feature_name][0].val
    except:
        raise ValueError(f'chunk {chunk} does not have a feature with the name "{feature_name}"')
