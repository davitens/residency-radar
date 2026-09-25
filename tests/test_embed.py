import numpy as np
import pytest

from src.embed import embed_texts


def test_shape_and_unit_norm():
    vecs = embed_texts(["hello world", "another text"])
    assert vecs.shape == (2, 384)
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-3)


@pytest.mark.integration
def test_semantic_similarity():
    a, b, c = embed_texts(
        [
            "machine learning for tabular forecasting",
            "deep learning and large language models",
            "medieval poetry and garden design",
        ]
    )
    assert float(a @ b) > float(a @ c)
