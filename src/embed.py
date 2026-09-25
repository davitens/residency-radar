from __future__ import annotations

from functools import lru_cache

import numpy as np

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=2)
def _model(model_name: str):
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model_name)


def embed_texts(texts: list[str], model_name: str = DEFAULT_MODEL) -> np.ndarray:
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    vecs = np.asarray(list(_model(model_name).embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.clip(norms, 1e-8, None)
